"""
Actions — continuous effector interpretation and primitive motor outputs.

Phase C: Naturalized Motor Interface
  The brain produces continuous "muscle" activations (effector outputs).
  The physics engine interprets them all simultaneously via interpret_effectors().

  Effector layout (indices into the effector vector):
    0: locomotion direction  (continuous → maps to neighbor index)
    1: locomotion intensity  (sigmoid → 0=stay, >threshold=move)
    2: harvest intensity     (sigmoid → energy extraction)
    3: social channel        (tanh → negative=attack, positive=transfer)
    4: maintenance intensity (sigmoid → self-repair)
    5: reproduction drive    (sigmoid → >threshold=attempt fork)
    6: signal intensity      (sigmoid → >threshold=broadcast)
    7-10: broadcast channels (tanh → evolved signal content)

  "Observe" and "idle" are gone — perception is automatic,
  idle is the absence of any effector activation.  No action dispatch table.

Legacy execute_action() is still available for compound action execution
and cortex fallback.
"""

from __future__ import annotations

import math
from typing import List, TYPE_CHECKING

import config as cfg
from agents.cortex import ACTION_NAMES, NUM_ACTIONS

if TYPE_CHECKING:
    from agents.agent import Agent
    from engine.substrate import Substrate

# Effector index constants
EFF_LOCO_DIR = 0
EFF_LOCO_INT = 1
EFF_HARVEST = 2
EFF_SOCIAL = 3
EFF_MAINTAIN = 4
EFF_REPRODUCE = 5
EFF_SIGNAL = 6
EFF_BROADCAST_START = 7

# Thresholds (all in sigmoid-space, 0-1, applied after sigmoid squash)
MOVE_THRESHOLD = 0.35
HARVEST_THRESHOLD = 0.2
SOCIAL_THRESHOLD = 0.25  # absolute value
MAINTAIN_THRESHOLD = 0.25
SIGNAL_THRESHOLD = 0.3

# Map effector names for logging
EFFECTOR_NAMES = [
    "locomotion_dir", "locomotion_int", "harvest", "social",
    "maintenance", "reproduction", "signal",
    "broadcast_0", "broadcast_1", "broadcast_2", "broadcast_3",
]


def _sigmoid(x: float) -> float:
    """Squash to [0, 1]."""
    return 1.0 / (1.0 + math.exp(-max(-10.0, min(10.0, x))))


def _tanh(x: float) -> float:
    """Squash to [-1, 1]."""
    return math.tanh(max(-10.0, min(10.0, x)))


def interpret_effectors(
    agent: "Agent",
    effector_outputs: List[float],
    substrate: "Substrate",
    all_agents: List["Agent"],
    perception: dict,
) -> str:
    """
    Interpret all continuous effector outputs simultaneously.

    The brain produces raw activations.  This function applies sigmoid/tanh
    to squash them into the appropriate range, then executes all effects
    that exceed their respective thresholds.

    Returns a composite description of everything that happened.
    """
    descriptions: List[str] = []

    # Pad if too short (need at least 7 effector channels)
    while len(effector_outputs) < 7:
        effector_outputs.append(0.0)

    # Squash effectors into their appropriate ranges
    loco_dir_raw = effector_outputs[EFF_LOCO_DIR]   # Raw → will be used as continuous direction
    loco_int = _sigmoid(effector_outputs[EFF_LOCO_INT])
    harvest_int = _sigmoid(effector_outputs[EFF_HARVEST])
    social_val = _tanh(effector_outputs[EFF_SOCIAL])  # [-1, 1]: neg=attack, pos=transfer
    maintain_int = _sigmoid(effector_outputs[EFF_MAINTAIN])
    reproduce_int = _sigmoid(effector_outputs[EFF_REPRODUCE])
    signal_int = _sigmoid(effector_outputs[EFF_SIGNAL])

    # Track dominant action for logging (the strongest activation)
    dominant_action = "idle"
    dominant_intensity = 0.0

    # ── Locomotion ──────────────────────────────────────────────────────
    if loco_int >= MOVE_THRESHOLD:
        # Convert continuous direction to a discrete neighbor index
        node = substrate.node(agent.state.node_id)
        num_neighbors = node.degree
        if num_neighbors > 0:
            # Map continuous direction to neighbor index
            direction = int((_sigmoid(loco_dir_raw)) * num_neighbors) % num_neighbors
            desc = _do_move(agent, substrate, direction, loco_int)
            descriptions.append(desc)
            if loco_int > dominant_intensity:
                dominant_action = "move"
                dominant_intensity = loco_int

    # ── Harvest ─────────────────────────────────────────────────────────
    if harvest_int >= HARVEST_THRESHOLD:
        desc = _do_harvest(agent, substrate, harvest_int)
        descriptions.append(desc)
        if harvest_int > dominant_intensity:
            dominant_action = "harvest"
            dominant_intensity = harvest_int

    # ── Social (attack or transfer) ─────────────────────────────────────
    if abs(social_val) >= SOCIAL_THRESHOLD:
        if social_val < 0:
            # Negative social → attack
            attack_intensity = abs(social_val)
            desc = _do_attack(agent, perception, attack_intensity)
            descriptions.append(desc)
            if attack_intensity > dominant_intensity:
                dominant_action = "attack"
                dominant_intensity = attack_intensity
        else:
            # Positive social → transfer
            desc = _do_transfer(agent, perception, social_val)
            descriptions.append(desc)
            if social_val > dominant_intensity:
                dominant_action = "transfer"
                dominant_intensity = social_val

    # ── Maintenance ─────────────────────────────────────────────────────
    if maintain_int >= MAINTAIN_THRESHOLD:
        desc = _do_maintain(agent, maintain_int)
        descriptions.append(desc)
        if maintain_int > dominant_intensity:
            dominant_action = "maintain"
            dominant_intensity = maintain_int

    # ── Reproduction ────────────────────────────────────────────────────
    if reproduce_int >= cfg.FORK_INTENSITY_THRESHOLD:
        desc = _do_fork(agent, perception, reproduce_int)
        descriptions.append(desc)
        if reproduce_int > dominant_intensity:
            dominant_action = "fork"
            dominant_intensity = reproduce_int

    # ── Signal ──────────────────────────────────────────────────────────
    if signal_int >= SIGNAL_THRESHOLD:
        desc = _do_signal(agent, perception, signal_int)
        descriptions.append(desc)
        if signal_int > dominant_intensity:
            dominant_action = "signal"
            dominant_intensity = signal_int

    # No effector above threshold → idle
    if not descriptions:
        descriptions.append("idle")

    # Store dominant action for tracking/logging
    agent.state.last_action = dominant_action

    return " | ".join(descriptions)


# ── Legacy dispatch (for compound actions and backward compat) ──────────────

def execute_action(
    action_id: int,
    agent: "Agent",
    substrate: "Substrate",
    all_agents: List["Agent"],
    perception: dict,
    intensity: float = 1.0,
) -> str:
    """
    Legacy action dispatch (kept for compound action execution).
    """
    intensity = max(0.0, min(1.0, intensity))

    if action_id >= NUM_ACTIONS:
        return _execute_compound(action_id, agent, substrate, all_agents, perception, intensity)

    name = ACTION_NAMES.get(action_id, "idle")

    if name.startswith("move_"):
        direction = int(name.split("_")[1])
        return _do_move(agent, substrate, direction, intensity)
    elif name == "harvest":
        return _do_harvest(agent, substrate, intensity)
    elif name == "transfer":
        return _do_transfer(agent, perception, intensity)
    elif name == "signal":
        return _do_signal(agent, perception, intensity)
    elif name == "maintain":
        return _do_maintain(agent, intensity)
    elif name == "fork":
        return _do_fork(agent, perception, intensity)
    elif name == "observe":
        return _do_observe(agent, perception, intensity)
    elif name == "attack":
        return _do_attack(agent, perception, intensity)
    elif name == "idle":
        return _do_idle(agent)
    else:
        return _do_idle(agent)


def _execute_compound(
    action_id: int,
    agent: "Agent",
    substrate: "Substrate",
    all_agents: List["Agent"],
    perception: dict,
    intensity: float = 1.0,
) -> str:
    """Execute a compound (macro) action — a sequence of primitives in one tick."""
    idx = action_id - NUM_ACTIONS
    compound_list = list(agent.compound_actions.items())
    if idx < 0 or idx >= len(compound_list):
        return _do_idle(agent)

    name, ca_data = compound_list[idx]
    sequence = ca_data["sequence"]
    descriptions = []

    for primitive_id in sequence:
        if not agent.alive:
            break
        prim_name = ACTION_NAMES.get(primitive_id, "idle")
        if prim_name.startswith("move_"):
            direction = int(prim_name.split("_")[1])
            desc = _do_move(agent, substrate, direction, intensity)
        elif prim_name == "harvest":
            desc = _do_harvest(agent, substrate, intensity)
        elif prim_name == "transfer":
            desc = _do_transfer(agent, perception, intensity)
        elif prim_name == "signal":
            desc = _do_signal(agent, perception, intensity)
        elif prim_name == "maintain":
            desc = _do_maintain(agent, intensity)
        elif prim_name == "attack":
            desc = _do_attack(agent, perception, intensity)
        elif prim_name == "observe":
            desc = _do_observe(agent, perception, intensity)
        elif prim_name == "idle":
            desc = _do_idle(agent)
        else:
            desc = _do_idle(agent)
        descriptions.append(desc)

    ca_data["success_count"] = ca_data.get("success_count", 0) + 1
    return f"MACRO[{name}]: {' -> '.join(descriptions)}"


# ── Cost scaling helper ──────────────────────────────────────────────────────

def _scaled_cost(base_cost: float, intensity: float) -> float:
    """Scale energy cost by intensity if configured."""
    if cfg.ACTION_INTENSITY_COST_SCALE:
        return base_cost * intensity
    return base_cost


# ── Primitive action implementations ─────────────────────────────────────────


def _do_move(agent: "Agent", substrate: "Substrate", direction: int, intensity: float = 1.0) -> str:
    """
    Move to a neighboring node in the graph.
    Direction (0-3) maps to: neighbors[direction % node_degree].
    Movement is binary — intensity only affects cost.
    """
    cost = _scaled_cost(cfg.ACTION_COSTS["move"], intensity)
    agent.state.spend_energy(cost)

    old_node = agent.state.node_id
    new_node = substrate.move_agent(old_node, direction)
    agent.state.node_id = new_node

    if new_node == old_node:
        return f"moved(×{intensity:.1f}) stayed — dead end"
    return f"moved(×{intensity:.1f}) {old_node}→{new_node}"


def _do_harvest(agent: "Agent", substrate: "Substrate", intensity: float = 1.0) -> str:
    """Harvest scales with intensity — higher intensity extracts more."""
    cost = _scaled_cost(cfg.ACTION_COSTS["harvest"], intensity)
    agent.state.spend_energy(cost)
    node = substrate.node(agent.state.node_id)
    harvest_amount = cfg.HARVEST_AMOUNT * intensity
    extracted = node.extract(harvest_amount)
    actual = agent.state.gain_energy(extracted, agent.genome.traits["max_energy"])
    return f"harvested(×{intensity:.1f}) +{actual:.0f}e"


def _do_transfer(agent: "Agent", perception: dict, intensity: float = 1.0) -> str:
    """Transfer energy — amount scales with intensity."""
    nearby: List["Agent"] = perception.get("nearby_agents", [])
    if not nearby:
        return "transfer: nobody nearby"
    target = nearby[0]
    amount = min(cfg.TRANSFER_MAX * intensity, agent.state.energy * 0.5)
    if amount <= 0:
        return "transfer: no energy to give"
    agent.state.spend_energy(amount)
    actual = target.state.gain_energy(amount, target.genome.traits["max_energy"])
    return f"transferred(×{intensity:.1f}) {actual:.0f}e to Agent-{target.id}"


def _do_signal(agent: "Agent", perception: dict, intensity: float = 1.0) -> str:
    """
    Emit a signal.

    Unstructured mode (Phase 5): signal content comes from the brain's
    broadcast output neurons.  The agent evolves what to encode — there
    is no hardcoded channel layout.  Intensity scales the signal
    amplitude and adds noise inversely proportional to intensity.

    Structured mode (legacy): hardcoded channel layout encodes
    energy ratio, entropy ratio, local resource, crowding.
    """
    cost = _scaled_cost(cfg.ACTION_COSTS["signal"], intensity)
    agent.state.spend_energy(cost)

    max_energy = agent.genome.traits["max_energy"]
    energy_ratio = min(1.0, agent.state.energy / max(max_energy, 1.0))
    entropy_ratio = min(1.0, agent.state.entropy / max(cfg.LETHAL_ENTROPY, 1.0))

    if cfg.UNSTRUCTURED_COMMS:
        # ── Phase 5: Brain-driven broadcast ──────────────────────────
        # Signal content is produced by evolved output neurons.
        # The brain decides what to communicate.
        # broadcast_width (genome trait) controls how many channels are active.
        broadcast = getattr(agent, "_broadcast_buffer", None) or [0.0] * cfg.BROADCAST_CHANNELS
        active_bw = int(agent.genome.traits.get("broadcast_width", 4))
        width = min(active_bw, len(broadcast))

        signal_vec: list = []
        noise_scale = 0.05 / max(intensity, 0.1)
        for i in range(active_bw):
            if i < len(broadcast):
                # Scale by intensity, add noise inversely proportional
                val = broadcast[i] * intensity + agent.rng.gauss(0, noise_scale)
                signal_vec.append(max(-1.0, min(1.0, val)))
            else:
                signal_vec.append(0.0)
    else:
        # ── Legacy: Hardcoded channel encoding ───────────────────────
        width = int(agent.genome.traits["signal_width"])
        local_e = min(1.0, perception.get("local_energy", 0.0) / 100.0)
        crowding = min(1.0, perception.get("agents_nearby", 0) / 5.0)

        channels = [energy_ratio, entropy_ratio, local_e, crowding]
        signal_vec = []
        noise_scale = 0.05 / max(intensity, 0.1)
        for i in range(width):
            if i < len(channels):
                val = channels[i] * intensity + agent.rng.gauss(0, noise_scale)
                signal_vec.append(max(0.0, min(1.0, val)))
            else:
                signal_vec.append(agent.rng.random() * intensity)

    agent.state.last_action_result = {
        "type": "signal",
        "vector": signal_vec,
        "sender_id": agent.id,
        "sender_energy": energy_ratio,
        "sender_entropy": entropy_ratio,
        "intensity": intensity,
    }
    formatted = ",".join(f"{v:.2f}" for v in signal_vec)
    return f"signaled(×{intensity:.1f}) [{formatted}]"


def _do_maintain(agent: "Agent", intensity: float = 1.0) -> str:
    """Maintenance — entropy reduction scales with intensity."""
    cost = _scaled_cost(cfg.ACTION_COSTS["maintain"], intensity)
    agent.state.spend_energy(cost)
    reduced = agent.state.reduce_entropy(cfg.MAINTAIN_REDUCTION * intensity)
    return f"maintained(×{intensity:.1f}) -{reduced:.0f} entropy"


def _do_fork(agent: "Agent", perception: dict, intensity: float = 1.0) -> str:
    """
    Fork requires high intensity commitment (configurable threshold).
    Cost is always full (no scaling) to prevent cheap reproduction.
    """
    # Fork requires strong activation
    if cfg.CONTINUOUS_ACTIONS and intensity < cfg.FORK_INTENSITY_THRESHOLD:
        return f"fork: intensity too low ({intensity:.2f} < {cfg.FORK_INTENSITY_THRESHOLD})"

    cost = cfg.ACTION_COSTS["fork"]  # Full cost always
    threshold = agent.genome.traits["fork_threshold"]
    if agent.state.energy < threshold:
        return "fork: insufficient energy"
    nearby: List["Agent"] = perception.get("nearby_agents", [])
    partner = None
    for other in nearby:
        if other.alive and other.state.energy >= other.genome.traits["fork_threshold"]:
            partner = other
            break
    if partner is None:
        return "fork: no viable partner nearby"
    agent.state.spend_energy(cost)
    agent.state.last_action_result = {"type": "fork_request", "partner_id": partner.id}
    return f"fork(×{intensity:.1f}) requested with Agent-{partner.id}"


def _do_observe(agent: "Agent", perception: dict, intensity: float = 1.0) -> str:
    """Observe — cost scales with intensity, always succeeds."""
    cost = _scaled_cost(cfg.ACTION_COSTS["observe"], intensity)
    agent.state.spend_energy(cost)
    n_signals = len(agent.state.signal_buffer)
    return f"observed(×{intensity:.1f}) ({n_signals} signals, local_e={perception['local_energy']:.0f}, deg={perception['node_degree']})"


def _do_attack(agent: "Agent", perception: dict, intensity: float = 1.0) -> str:
    """
    Attack another agent at the same node to steal energy.
    Requires high intensity and a target at the same node.
    Success depends on relative entropy resistance (evolutionary defense).
    """
    if not cfg.ATTACK_ENABLED:
        return "attack: disabled"

    # Attack requires strong commitment
    if cfg.CONTINUOUS_ACTIONS and intensity < cfg.ATTACK_INTENSITY_THRESHOLD:
        return f"attack: intensity too low ({intensity:.2f})"

    cost = _scaled_cost(cfg.ACTION_COSTS["attack"], intensity)
    agent.state.spend_energy(cost)

    # Find a target at the same node
    nearby: List["Agent"] = perception.get("nearby_agents", [])
    target = None
    for other in nearby:
        if other.alive and other.state.node_id == agent.state.node_id:
            target = other
            break

    if target is None:
        return "attack: no target at node"

    # Attack success depends on relative traits
    # Attacker advantage scales with intensity
    attack_power = intensity * agent.state.energy / max(agent.genome.traits["max_energy"], 1.0)
    # Defender's resistance based on entropy_resistance trait
    defense_power = target.genome.traits["entropy_resistance"] * cfg.ATTACK_DEFENSE_FACTOR

    if attack_power > defense_power:
        # Successful attack: steal energy
        steal_amount = target.state.energy * cfg.ATTACK_STEAL_FRACTION * intensity
        steal_amount = min(steal_amount, target.state.energy * 0.5)  # Can't steal more than half
        target.state.spend_energy(steal_amount)
        actual = agent.state.gain_energy(steal_amount, agent.genome.traits["max_energy"])
        return f"attacked(×{intensity:.1f}) Agent-{target.id}: stole {actual:.0f}e"
    else:
        # Failed attack: attacker takes recoil damage
        recoil = cost * 0.5
        agent.state.spend_energy(recoil)
        return f"attacked(×{intensity:.1f}) Agent-{target.id}: FAILED (defense too strong)"


def _do_idle(agent: "Agent") -> str:
    return "idle"
