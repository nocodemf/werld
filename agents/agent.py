"""
Agent — a single computational life form.

Ties together Genome (with NEAT topology), State (mutable runtime),
Cortex (learned decision weights), NEATBrain (evolvable neural net),
EpisodicMemory, and compound actions into one coherent entity.

Agents live on a graph, not a grid.  "Position" is a node ID.
The brain topology evolves through mutation and crossover.
Weights evolve through natural selection, not gradient descent.

Neither system has access to any human-world knowledge.
"""

from __future__ import annotations

import math
import random
from typing import Tuple, Optional, List, Dict, Any, TYPE_CHECKING

import config as cfg
from agents.genome import Genome
from agents.state import AgentState
from agents.cortex import Cortex, ACTION_NAMES, NUM_ACTIONS, _state_hash
from agents.memory import EpisodicMemory, Episode
from systems.evolution import CompoundAction, SequenceTracker, discover_compound_actions
from reasoning.neat_brain import NEATBrain, setup_initial_brain

if TYPE_CHECKING:
    from engine.substrate import Substrate

# Global agent ID counter
_next_id = 0


def _new_id() -> int:
    global _next_id
    aid = _next_id
    _next_id += 1
    return aid


def reset_id_counter(value: int = 0) -> None:
    global _next_id
    _next_id = value


# ── Sensory field definition ────────────────────────────────────────────────
# The FULL sensory field available to agents.
# Each input is a NEAT input node.  Evolution decides which to wire.
# Unused (disconnected) inputs cost nothing.

# Proprioceptive (self-sensing): 0-12
#  0: energy deficit
#  1: entropy pressure
#  2: age (normalized)
#  3: energy ratio (energy / max_energy)
#  4: entropy ratio (entropy / lethal)
#  5: brain node count (normalized)
#  6: brain connection count (normalized)
#  7: brain top hidden activation 1
#  8: brain top hidden activation 2
#  9: brain top hidden activation 3
# 10: recent energy delta (trend over last action)
# 11: recent entropy delta (trend)
# 12: compound actions discovered (normalized)

# Exteroceptive (world-sensing): 13-22
# 13: local node energy
# 14: best neighbor energy
# 15: avg neighbor energy
# 16: node degree (normalized)
# 17: agents at current node
# 18: agents within 1 hop
# 19: agents within 2 hops
# 20: is current node a hub? (degree > 2x avg)
# 21: edge count available for movement (normalized)
# 22: 2nd-hop avg energy

# Social sensing: 23-32
# 23: number of signals received
# 24: signal channel 0 avg (evolved meaning in unstructured mode)
# 25: signal channel 1 avg (evolved meaning in unstructured mode)
# 26: signal channel 2 avg (evolved meaning in unstructured mode)
# 27: signal channel 3 avg (evolved meaning in unstructured mode)
# 28: presence of kin (agents sharing parent)
# 29: approx unique signal senders
# 30: was last action: harvest
# 31: was last action: move
# 32: was last action: maintain

# Pheromone sensing: 33-35
# 33: local pheromone level
# 34: best neighbor pheromone
# 35: avg neighbor pheromone

# Environmental/temporal sensing: 36-40
# 36: season phase (sin)
# 37: season phase (cos)
# 38: season regeneration multiplier
# 39: clock (sin of tick/100, for circadian rhythms)
# 40: last action type (normalized)

# Stochastic / utility inputs: 41-44
# 41: bias (constant 1.0 — useful as a learned threshold)
# 42: random noise (uniform 0-1 per tick — substrate for stochastic decisions)
# 43: random noise (gaussian per tick, mean 0.5, std 0.2)
# 44: pulse (oscillating 0/1 based on agent age modulo evolved period)

# ── Latent channels: 45-63 (dormant until evolution discovers them) ────
# Gains initialize near 0.  Evolution "turns on" a channel by evolving
# its gain away from 0.  This is how agents expand their senses.
# 45-48: effector echo (last tick's locomotion dir/int, harvest, social)
# 49-52: broadcast echo (last tick's broadcast channels 0-3)
# 53-56: derivative signals (d/dt of energy, entropy, local energy, population)
# 57-60: cross-products (energy×entropy, local_e×agents, pheromone×season, age×entropy)
# 61-63: memory aggregates (avg recent drive_delta, action variety, memory fullness)

NUM_SENSORY_INPUTS = 64

# ── Effector layout ──────────────────────────────────────────────────────────
# Instead of discrete named actions (harvest / move_0 / etc.), the brain
# produces continuous "muscle" activations.  The physics engine interprets them.
#
# | Effector    | Idx  | Outputs | What it does                              |
# |-------------|------|---------|-------------------------------------------|
# | Locomotion  | 0-1  |   2     | direction (continuous neighbor select)     |
# |             |      |         | + intensity (movement commitment)          |
# | Harvest     | 2    |   1     | energy extraction from current node       |
# | Social      | 3    |   1     | signed: negative=attack, positive=transfer|
# | Maintenance | 4    |   1     | self-repair intensity                     |
# | Reproduction| 5    |   1     | above threshold = fork                    |
# | Signal      | 6    |   1     | above threshold = broadcast               |
# | Broadcast   | 7-22 |  16     | evolved signal content channels (agent    |
# |             |      |         | uses broadcast_width of them; rest zeroed)|
#
# "Observe" and "idle" are gone — perception is automatic, idle is the
# absence of effector activation.  No action dispatch table.

NUM_EFFECTOR_CHANNELS = 7   # Locomotion(2) + Harvest(1) + Social(1) + Maintenance(1) + Reproduction(1) + Signal(1)
NUM_BROADCAST = cfg.BROADCAST_CHANNELS  # Max broadcast slots (16)
NUM_OUTPUTS = NUM_EFFECTOR_CHANNELS + NUM_BROADCAST  # 23 total

# Legacy action constants for backward compat in logging/dashboard
NUM_ACTIONS = 12  # Keep for cortex/logging compatibility


class Agent:
    """A living computational entity with evolvable brain topology."""

    __slots__ = (
        "id", "genome", "state", "cortex", "brain", "memory", "rng",
        "generation", "parent_ids",
        "compound_actions", "sequence_tracker",
        "_last_state_features", "_last_action_id",
        "_broadcast_buffer",  # Evolved brain outputs for signal content
        "_last_effector_outputs",  # For proprioceptive effector echo
    )

    def __init__(
        self,
        genome: Genome,
        node_id: int,
        rng: Optional[random.Random] = None,
        generation: int = 0,
        parent_ids: Optional[Tuple[int, ...]] = None,
    ) -> None:
        self.id: int = _new_id()
        self.genome = genome
        self.rng = rng or random.Random()
        self.generation = generation
        self.parent_ids = parent_ids or ()

        # State — position is a node ID in the graph
        initial_energy = genome.traits["max_energy"] * cfg.INITIAL_ENERGY_FRACTION
        self.state = AgentState(energy=initial_energy, node_id=node_id)

        # Cortex (fast associative lookup — reflex system)
        # Drive weights come from genome traits — evolved, not hardcoded
        drive_traits = {
            k: genome.traits.get(k, cfg.GENOME_RANGES.get(k, (0, 1, 0.5))[2])
            for k in (
                "harvest_drive", "maintain_drive", "explore_drive",
                "social_drive", "reproduce_drive", "signal_drive",
            )
        }
        self.cortex = Cortex(
            capacity=int(genome.traits["cortex_capacity"]),
            learning_rate=genome.traits["learning_rate"],
            exploration_factor=genome.traits["exploration_factor"],
            rng=self.rng,
            drive_weights=drive_traits,
            resolution=int(genome.traits.get("cortex_resolution", 4)),
        )

        # NEAT Brain (evolvable topology neural network)
        self.brain: Optional[NEATBrain] = None
        if cfg.BRAIN_ENABLED:
            # If genome doesn't have NEAT topology yet, set it up
            if not genome.node_genes:
                setup_initial_brain(genome, NUM_SENSORY_INPUTS, NUM_OUTPUTS, self.rng)
            # Ensure sensory genes are sized to match sensory inputs
            while len(genome.sensory_gains) < NUM_SENSORY_INPUTS:
                # Latent channels (45+) start with near-zero gain — dormant until evolved
                gain_default = 1.0 if len(genome.sensory_gains) < 45 else 0.01
                genome.sensory_gains.append(gain_default)
            while len(genome.sensory_offsets) < NUM_SENSORY_INPUTS:
                genome.sensory_offsets.append(0.0)
            self.brain = NEATBrain(genome, rng=random.Random(self.rng.random()))

        # Episodic memory (decay and social weight are evolvable)
        self.memory = EpisodicMemory(
            capacity=int(genome.traits["memory_capacity"]),
            decay_rate=genome.traits.get("memory_decay", 0.95),
            social_weight=genome.traits.get("memory_social_weight", 0.5),
        )

        # Compound actions (self-modification) — pattern length is evolvable
        self.compound_actions: Dict[str, Dict[str, Any]] = {}
        self.sequence_tracker = SequenceTracker(
            max_length=int(genome.traits.get("macro_pattern_length", cfg.MAX_COMPOUND_LENGTH)),
        )

        # Last state for learning
        self._last_state_features: Optional[List[float]] = None
        self._last_action_id: int = -1

        # Broadcast buffer: populated by brain during decide(), read by signal action
        self._broadcast_buffer: List[float] = [0.0] * NUM_BROADCAST

        # Last effector outputs: for proprioceptive motor echo (latent channel 45-48)
        self._last_effector_outputs: List[float] = [0.0] * NUM_EFFECTOR_CHANNELS

    # ── Properties ───────────────────────────────────────────────────────

    @property
    def alive(self) -> bool:
        return self.state.alive

    @property
    def node_id(self) -> int:
        return self.state.node_id

    @property
    def energy(self) -> float:
        return self.state.energy

    # ── Per-tick lifecycle ───────────────────────────────────────────────

    def tick_upkeep(self) -> None:
        """Pay existence cost (including brain metabolic cost) and accumulate entropy."""
        brain_cost = self.brain.metabolic_cost if self.brain else 0.0
        self.state.tick_upkeep(
            tick_cost=self.genome.traits["tick_cost"],
            entropy_resistance=self.genome.traits["entropy_resistance"],
            brain_cost=brain_cost,
        )
        self.memory.decay()

    def perceive(self, substrate: "Substrate", all_agents: List["Agent"]) -> dict:
        """
        Gather rich perception from the graph substrate.
        Computes the full sensory field for the NEAT brain.
        """
        nid = self.state.node_id
        node = substrate.node(nid)
        sense_range = int(self.genome.traits["sense_range"])

        # Find nearby nodes within sense_range hops
        nearby_nodes = substrate.neighbor_nodes(nid, hops=sense_range)
        best_neighbor_energy = max((n.energy for n in nearby_nodes), default=0.0)
        avg_neighbor_energy = (
            sum(n.energy for n in nearby_nodes) / len(nearby_nodes)
            if nearby_nodes else 0.0
        )

        # 2nd-hop average energy
        hop2_nodes = substrate.neighbor_nodes(nid, hops=min(sense_range, 2))
        hop2_avg_energy = (
            sum(n.energy for n in hop2_nodes) / len(hop2_nodes)
            if hop2_nodes else 0.0
        )

        # Find nearby agents at different ranges
        nearby_node_ids = {n.id for n in nearby_nodes}
        nearby_node_ids.add(nid)

        # Agents at current node
        agents_at_node = 0
        # Agents within 1 hop
        hop1_nodes = set(node.neighbors) | {nid}
        agents_1hop = 0
        agents_nearby = 0
        nearby_agent_list: List["Agent"] = []
        has_kin = False

        for other in all_agents:
            if other.id == self.id or not other.alive:
                continue
            if other.state.node_id in nearby_node_ids:
                agents_nearby += 1
                nearby_agent_list.append(other)
                if other.state.node_id == nid:
                    agents_at_node += 1
                if other.state.node_id in hop1_nodes:
                    agents_1hop += 1
                # Check for kin (shared parent)
                if self.parent_ids and other.parent_ids:
                    if set(self.parent_ids) & set(other.parent_ids):
                        has_kin = True

        # Decode received signals — channel-generic averaging
        sig_buf = self.state.signal_buffer
        num_signals = len(sig_buf)
        # Average each channel across all received signals
        max_channels = max(cfg.BROADCAST_CHANNELS, 4) if cfg.UNSTRUCTURED_COMMS else 4
        signal_channel_avgs = [0.0] * max_channels

        if num_signals > 0:
            for vec in sig_buf:
                for ch in range(min(len(vec), max_channels)):
                    signal_channel_avgs[ch] += vec[ch]
            for ch in range(max_channels):
                signal_channel_avgs[ch] /= num_signals

        # Average degree of the graph (for hub detection)
        avg_degree = substrate.avg_degree() if hasattr(substrate, 'avg_degree') else 4.0

        # Pheromone sensing
        local_pheromone = node.pheromone if cfg.PHEROMONE_ENABLED else 0.0
        best_pheromone_neighbor = 0.0
        avg_pheromone_neighbor = 0.0
        if cfg.PHEROMONE_ENABLED and nearby_nodes:
            pheromone_levels = [n.pheromone for n in nearby_nodes]
            best_pheromone_neighbor = max(pheromone_levels, default=0.0)
            avg_pheromone_neighbor = sum(pheromone_levels) / len(pheromone_levels)

        # Season sensing
        season_phase = substrate.season_phase() if hasattr(substrate, 'season_phase') else 0.5
        season_regen = substrate.season_regen_multiplier() if hasattr(substrate, 'season_regen_multiplier') else 1.0

        return {
            "local_energy": node.energy,
            "best_neighbor_energy": best_neighbor_energy,
            "avg_neighbor_energy": avg_neighbor_energy,
            "hop2_avg_energy": hop2_avg_energy,
            "agents_nearby": agents_nearby,
            "nearby_agents": nearby_agent_list,
            "agents_at_node": agents_at_node,
            "agents_1hop": agents_1hop,
            "node_degree": node.degree,
            "num_signals": num_signals,
            # Generic signal channel averages (evolved meaning in unstructured mode)
            "signal_channel_avgs": signal_channel_avgs,
            "is_hub": 1.0 if node.degree > 2 * avg_degree else 0.0,
            "has_kin": has_kin,
            "edge_count": len(node.neighbors),
            # Pheromone sensing
            "local_pheromone": local_pheromone,
            "best_pheromone_neighbor": best_pheromone_neighbor,
            "avg_pheromone_neighbor": avg_pheromone_neighbor,
            # Season sensing
            "season_phase": season_phase,
            "season_regen": season_regen,
        }

    def _encode_state(self, perception: dict, tick: int = 0) -> List[float]:
        """
        Encode perception + internal state into the full sensory field vector.
        64 inputs total — the NEAT genome decides which to actually wire.

        Channels 0-44:  Core sensory field (proprioception, exteroception, social, etc.)
        Channels 45-63: Latent slots (effector echo, broadcast echo, derivatives,
                         cross-products, memory aggregates). Gains initialize near 0
                         so they're dormant until evolution discovers them.

        After computing raw normalized features, applies the genome's evolvable
        sensory gains and offsets.  Different species perceive the same world
        differently depending on what evolution has tuned their senses to.
        """
        ed, ep = self.state.drive_vector(self.genome.traits["max_energy"])
        max_e = max(self.genome.traits["max_energy"], 1.0)

        # Signal channel averages (generic — meaning is evolved, not hardcoded)
        sig_ch = perception.get("signal_channel_avgs", [0.0, 0.0, 0.0, 0.0])

        # Proprioceptive: brain self-sensing
        brain_nodes_norm = 0.0
        brain_conns_norm = 0.0
        hidden_act_1 = 0.0
        hidden_act_2 = 0.0
        hidden_act_3 = 0.0
        if self.brain:
            brain_nodes_norm = min(1.0, self.brain.num_active_nodes / 100.0)
            brain_conns_norm = min(1.0, self.brain.num_active_connections / 300.0)
            # Top 3 hidden node activations by magnitude (self-modeling!)
            hidden_acts = []
            for nid_b, ng in self.brain.genome.node_genes.items():
                if ng.node_type == "hidden":
                    hidden_acts.append(self.brain.activations.get(nid_b, 0.0))
            hidden_acts.sort(key=abs, reverse=True)
            if len(hidden_acts) > 0:
                hidden_act_1 = min(1.0, max(-1.0, hidden_acts[0]))
            if len(hidden_acts) > 1:
                hidden_act_2 = min(1.0, max(-1.0, hidden_acts[1]))
            if len(hidden_acts) > 2:
                hidden_act_3 = min(1.0, max(-1.0, hidden_acts[2]))

        # Energy/entropy trend (approximated from last drive vs current)
        energy_delta = 0.0
        entropy_delta = 0.0
        if self._last_state_features is not None and len(self._last_state_features) >= 5:
            energy_delta = (self.state.energy / max_e) - self._last_state_features[3]
            entropy_delta = (self.state.entropy / cfg.LETHAL_ENTROPY) - self._last_state_features[4]

        raw_features = [
            # Proprioceptive (0-12)
            min(1.0, max(0.0, ed)),                                    # 0
            min(1.0, max(0.0, ep)),                                    # 1
            min(1.0, self.state.age / 500.0),                          # 2
            min(1.0, self.state.energy / max_e),                       # 3
            min(1.0, self.state.entropy / cfg.LETHAL_ENTROPY),         # 4
            brain_nodes_norm,                                           # 5
            brain_conns_norm,                                           # 6
            hidden_act_1,                                               # 7
            hidden_act_2,                                               # 8
            hidden_act_3,                                               # 9
            min(1.0, max(-1.0, energy_delta * 5.0)),                   # 10
            min(1.0, max(-1.0, entropy_delta * 5.0)),                  # 11
            min(1.0, len(self.compound_actions) / 10.0),               # 12

            # Exteroceptive (13-22)
            min(1.0, perception["local_energy"] / 100.0),              # 13
            min(1.0, perception["best_neighbor_energy"] / 100.0),      # 14
            min(1.0, perception["avg_neighbor_energy"] / 100.0),       # 15
            min(1.0, perception["node_degree"] / 8.0),                 # 16
            min(1.0, perception.get("agents_at_node", 0) / 3.0),      # 17
            min(1.0, perception.get("agents_1hop", 0) / 5.0),         # 18
            min(1.0, perception["agents_nearby"] / 8.0),               # 19
            perception.get("is_hub", 0.0),                             # 20
            min(1.0, perception.get("edge_count", 4) / 8.0),          # 21
            min(1.0, perception.get("hop2_avg_energy", 0) / 100.0),   # 22

            # Social (23-32)
            # Signal channels are now generic — the brain learns their meaning
            min(1.0, perception["num_signals"] / 10.0),                # 23: signal count
            min(1.0, max(-1.0, sig_ch[0])),                            # 24: signal channel 0 avg
            min(1.0, max(-1.0, sig_ch[1])),                            # 25: signal channel 1 avg
            min(1.0, max(-1.0, sig_ch[2])),                            # 26: signal channel 2 avg
            min(1.0, max(-1.0, sig_ch[3] if len(sig_ch) > 3 else 0.0)),  # 27: signal channel 3 avg
            1.0 if perception.get("has_kin", False) else 0.0,          # 28
            min(1.0, perception["num_signals"] / 5.0),                 # 29 (approx unique senders)
            1.0 if self._last_action_id == 4 else 0.0,                # 30: was harvest
            1.0 if self._last_action_id in (0, 1, 2, 3) else 0.0,    # 31: was move
            1.0 if self._last_action_id == 7 else 0.0,                # 32: was maintain

            # Pheromone sensing (33-35)
            min(1.0, perception.get("local_pheromone", 0.0) / cfg.PHEROMONE_MAX),       # 33
            min(1.0, perception.get("best_pheromone_neighbor", 0.0) / cfg.PHEROMONE_MAX),  # 34
            min(1.0, perception.get("avg_pheromone_neighbor", 0.0) / cfg.PHEROMONE_MAX),   # 35

            # Environmental/temporal (36-40)
            math.sin(2.0 * math.pi * perception.get("season_phase", 0.5)),   # 36: season sin
            math.cos(2.0 * math.pi * perception.get("season_phase", 0.5)),   # 37: season cos
            min(1.0, perception.get("season_regen", 1.0) / 2.0),             # 38: season regen
            math.sin(tick / 100.0) * 0.5 + 0.5,                              # 39: circadian clock
            min(1.0, self._last_action_id / 10.0) if self._last_action_id >= 0 else 0.0,  # 40

            # Stochastic / utility inputs (41-44)
            1.0,                                                               # 41: constant bias
            self.rng.random(),                                                 # 42: uniform noise
            max(0.0, min(1.0, self.rng.gauss(0.5, 0.2))),                    # 43: gaussian noise
            1.0 if (self.state.age % max(1, int(self.genome.traits.get("tick_cost", 1.0) * 20))) < int(self.genome.traits.get("tick_cost", 1.0) * 10) else 0.0,  # 44: pulse
        ]

        # ── Latent channels (45-63) ──────────────────────────────────────
        # Gains for these start near 0 so they're dormant until evolution
        # discovers their value.  This is how agents expand their senses.

        # Effector echo: own last effector activations (45-48)
        last_eff = getattr(self, "_last_effector_outputs", None) or [0.0] * NUM_EFFECTOR_CHANNELS
        raw_features.append(max(-1.0, min(1.0, last_eff[0] if len(last_eff) > 0 else 0.0)))  # 45: loco dir echo
        raw_features.append(max(-1.0, min(1.0, last_eff[1] if len(last_eff) > 1 else 0.0)))  # 46: loco int echo
        raw_features.append(max(-1.0, min(1.0, last_eff[2] if len(last_eff) > 2 else 0.0)))  # 47: harvest echo
        raw_features.append(max(-1.0, min(1.0, last_eff[3] if len(last_eff) > 3 else 0.0)))  # 48: social echo

        # Broadcast echo: own last broadcast values (49-52)
        last_bc = getattr(self, "_broadcast_buffer", None) or [0.0] * NUM_BROADCAST
        raw_features.append(max(-1.0, min(1.0, last_bc[0] if len(last_bc) > 0 else 0.0)))  # 49
        raw_features.append(max(-1.0, min(1.0, last_bc[1] if len(last_bc) > 1 else 0.0)))  # 50
        raw_features.append(max(-1.0, min(1.0, last_bc[2] if len(last_bc) > 2 else 0.0)))  # 51
        raw_features.append(max(-1.0, min(1.0, last_bc[3] if len(last_bc) > 3 else 0.0)))  # 52

        # Derivative signals: rate of change (53-56)
        if self._last_state_features is not None and len(self._last_state_features) >= 20:
            energy_rate = (self.state.energy / max_e) - self._last_state_features[3]
            entropy_rate = (self.state.entropy / cfg.LETHAL_ENTROPY) - self._last_state_features[4]
            local_e_rate = min(1.0, perception["local_energy"] / 100.0) - self._last_state_features[13]
            pop_rate = min(1.0, perception["agents_nearby"] / 8.0) - self._last_state_features[19]
        else:
            energy_rate = entropy_rate = local_e_rate = pop_rate = 0.0
        raw_features.append(min(1.0, max(-1.0, energy_rate * 10.0)))   # 53: d(energy)/dt
        raw_features.append(min(1.0, max(-1.0, entropy_rate * 10.0)))  # 54: d(entropy)/dt
        raw_features.append(min(1.0, max(-1.0, local_e_rate * 10.0)))  # 55: d(local_energy)/dt
        raw_features.append(min(1.0, max(-1.0, pop_rate * 10.0)))      # 56: d(population)/dt

        # Cross-product features (57-60)
        energy_norm = min(1.0, self.state.energy / max_e)
        entropy_norm = min(1.0, self.state.entropy / cfg.LETHAL_ENTROPY)
        local_e_norm = min(1.0, perception["local_energy"] / 100.0)
        agents_norm = min(1.0, perception["agents_nearby"] / 8.0)
        phero_norm = min(1.0, perception.get("local_pheromone", 0.0) / cfg.PHEROMONE_MAX)
        season_v = perception.get("season_regen", 1.0) / 2.0
        age_norm = min(1.0, self.state.age / 500.0)
        raw_features.append(energy_norm * entropy_norm)      # 57: energy × entropy
        raw_features.append(local_e_norm * agents_norm)      # 58: local_energy × agents_nearby
        raw_features.append(phero_norm * season_v)            # 59: pheromone × season
        raw_features.append(age_norm * entropy_norm)          # 60: age × entropy

        # Aggregate memory readouts (61-63)
        recent_eps = self.memory.recent(5)
        if recent_eps:
            avg_drive_delta = sum(ep.drive_delta for ep in recent_eps) / len(recent_eps)
            action_ids = [ep.action_id for ep in recent_eps]
            action_var = len(set(action_ids)) / max(len(action_ids), 1)  # diversity of recent actions
        else:
            avg_drive_delta = 0.0
            action_var = 0.0
        mem_fullness = len(self.memory) / max(int(self.genome.traits.get("memory_capacity", 40)), 1)
        raw_features.append(min(1.0, max(-1.0, avg_drive_delta)))   # 61: avg recent drive delta
        raw_features.append(min(1.0, action_var))                    # 62: action variety
        raw_features.append(min(1.0, mem_fullness))                  # 63: memory fullness ratio

        # Apply evolvable sensory gains and offsets
        gains = self.genome.sensory_gains
        offsets = self.genome.sensory_offsets
        for i in range(min(len(raw_features), len(gains))):
            raw_features[i] = raw_features[i] * gains[i] + offsets[i]

        return raw_features[:NUM_SENSORY_INPUTS]

    def decide(
        self, perception: dict, tick: int = 0,
    ) -> Tuple[int, List[float], Optional[str]]:
        """
        Produce continuous effector activations from the brain.

        Returns (state_hash, effector_outputs, brain_info_or_None)
        where effector_outputs is a list of floats:
          [locomotion_dir, locomotion_intensity, harvest, social,
           maintenance, reproduction, signal, broadcast_0..3]
        Length = NUM_OUTPUTS (11).

        The physics engine in interpret_effectors() reads these directly.
        """
        ed, ep = self.state.drive_vector(self.genome.traits["max_energy"])
        num_compound = len(self.compound_actions)

        # State hash for cortex (still useful for reinforcement tracking)
        cortex_res = int(self.genome.traits.get("cortex_resolution", 4))
        sh = _state_hash(
            ed, ep, perception["local_energy"],
            perception["agents_nearby"],
            perception["node_degree"],
            perception.get("num_signals", 0),
            resolution=cortex_res,
        )

        brain_info = None

        # Encode state features
        state_features = self._encode_state(perception, tick)
        self._last_state_features = state_features

        # Brain decision → continuous effector outputs
        if self.brain is not None and cfg.BRAIN_ENABLED:
            base_explore = self.genome.traits["exploration_factor"]
            explore = base_explore / (1.0 + self.brain.total_experiences * cfg.BRAIN_EXPLORATION_DECAY)

            brain_info = (
                f"neat(nodes={self.brain.num_active_nodes},"
                f"conns={self.brain.num_active_connections},"
                f"cost={self.brain.metabolic_cost:.2f})"
            )

            effectors = self._compute_effectors(state_features, explore)

            # Cortex gating: cortex_reliance controls whether the cortex fires
            # when the brain is active.  Agents can evolve cortex_reliance → 0
            # to become pure brain-driven, or keep it high for reflex backup.
            cortex_reliance = self.genome.traits.get("cortex_reliance", 0.5)
            if self.rng.random() < cortex_reliance:
                self.cortex.decide(
                    energy_deficit=ed,
                    entropy_pressure=ep,
                    local_energy=perception["local_energy"],
                    agents_nearby=perception["agents_nearby"],
                    node_degree=perception["node_degree"],
                    num_compound_actions=num_compound,
                    num_signals=perception.get("num_signals", 0),
                )
            self._last_effector_outputs = effectors[:NUM_EFFECTOR_CHANNELS]
            return sh, effectors, brain_info

        # Cortex-only fallback: produce effector outputs from cortex decision
        sh_c, action_id = self.cortex.decide(
            energy_deficit=ed,
            entropy_pressure=ep,
            local_energy=perception["local_energy"],
            agents_nearby=perception["agents_nearby"],
            node_degree=perception["node_degree"],
            num_compound_actions=num_compound,
            num_signals=perception.get("num_signals", 0),
        )
        effectors = self._cortex_to_effectors(action_id)
        self._last_effector_outputs = effectors[:NUM_EFFECTOR_CHANNELS]
        return sh, effectors, brain_info

    def _compute_effectors(
        self,
        state_features: List[float],
        exploration_rate: float,
    ) -> List[float]:
        """
        Compute continuous effector outputs from the NEAT brain.

        Returns a list of NUM_OUTPUTS floats — the raw "muscle" activations.
        The physics engine interprets them all simultaneously.
        """
        assert self.brain is not None

        # Exploration: occasionally inject random effector activations
        if self.rng.random() < exploration_rate:
            active_bw = int(self.genome.traits.get("broadcast_width", 4))
            effectors = [self.rng.uniform(-1.0, 1.0) for _ in range(NUM_OUTPUTS)]
            # Zero out broadcast channels beyond active width
            for i in range(active_bw, NUM_BROADCAST):
                effectors[NUM_EFFECTOR_CHANNELS + i] = 0.0
            self._broadcast_buffer = effectors[NUM_EFFECTOR_CHANNELS:NUM_EFFECTOR_CHANNELS + NUM_BROADCAST]
            return effectors

        # Get raw brain outputs
        raw_outputs = self.brain.forward(state_features)

        # Pad if brain has fewer outputs than expected
        while len(raw_outputs) < NUM_OUTPUTS:
            raw_outputs.append(0.0)

        # Extract and store broadcast buffer, zeroing channels beyond broadcast_width
        active_bw = int(self.genome.traits.get("broadcast_width", 4))
        raw_bc = raw_outputs[NUM_EFFECTOR_CHANNELS:NUM_EFFECTOR_CHANNELS + NUM_BROADCAST]
        self._broadcast_buffer = []
        for i in range(NUM_BROADCAST):
            if i < len(raw_bc) and i < active_bw:
                self._broadcast_buffer.append(max(-1.0, min(1.0, raw_bc[i])))
            else:
                self._broadcast_buffer.append(0.0)

        return raw_outputs[:NUM_OUTPUTS]

    def _cortex_to_effectors(self, action_id: int) -> List[float]:
        """Convert a discrete cortex action into continuous effectors (fallback)."""
        effectors = [0.0] * NUM_OUTPUTS
        if action_id in (0, 1, 2, 3):    # move_N
            effectors[0] = action_id / 3.0  # direction
            effectors[1] = 0.8              # intensity
        elif action_id == 4:               # harvest
            effectors[2] = 0.8
        elif action_id == 5:               # transfer
            effectors[3] = 0.8             # positive = transfer
        elif action_id == 6:               # signal
            effectors[6] = 0.8
        elif action_id == 7:               # maintain
            effectors[4] = 0.8
        elif action_id == 8:               # fork
            effectors[5] = 0.8
        elif action_id == 11:              # attack
            effectors[3] = -0.8            # negative social = attack
        # idle / observe → all zeros (no activation)
        self._broadcast_buffer = effectors[NUM_EFFECTOR_CHANNELS:NUM_EFFECTOR_CHANNELS + NUM_BROADCAST]
        return effectors

    def learn(
        self,
        state_hash: int,
        effector_outputs: List[float],
        drive_before: Tuple[float, float],
        drive_after: Tuple[float, float],
        tick: int,
        action_desc: str,
        perception: dict,
    ) -> float:
        """
        Reinforce cortex, record experience, record memory.

        effector_outputs: the continuous effector vector from this tick.
        Cortex reinforces the dominant action (inferred from effectors).
        Brain tracks experience count only (evolution does the learning).
        """
        # Infer dominant action from effector outputs for cortex reinforcement
        primary_action_id = self._effectors_to_dominant_action(effector_outputs)

        # Cortex reinforcement (primary action)
        delta = self.cortex.reinforce(state_hash, primary_action_id, drive_before, drive_after)

        # Brain experience tracking (no reward computation — evolution does the learning)
        if self.brain is not None:
            self.brain.record_experience()

        self._last_action_id = primary_action_id

        # Record episodic memory
        agents_present = [a.id for a in perception.get("nearby_agents", [])]
        before_mag = math.sqrt(drive_before[0] ** 2 + drive_before[1] ** 2)
        after_mag = math.sqrt(drive_after[0] ** 2 + drive_after[1] ** 2)
        drive_delta = before_mag - after_mag

        episode = Episode(
            tick=tick,
            action=action_desc,
            action_id=primary_action_id,
            position=self.state.node_id,
            energy_before=drive_before[0] * self.genome.traits["max_energy"],
            energy_after=self.state.energy,
            entropy_before=drive_before[1] * cfg.LETHAL_ENTROPY,
            entropy_after=self.state.entropy,
            drive_delta=drive_delta,
            agents_present=agents_present,
            signals_received=len(self.state.signal_buffer),
            result_desc=action_desc,
            social_weight=self.memory.social_weight,
        )
        self.memory.record(episode)

        # Compound action discovery — track dominant effector as a coarse bucket
        self.sequence_tracker.record(primary_action_id, drive_delta)

        discovery_rate = self.genome.traits.get("macro_discovery_rate", 0.05)
        macro_cap = int(self.genome.traits.get("macro_capacity", cfg.MAX_COMPOUND_ACTIONS))
        new_compounds = discover_compound_actions(
            self.sequence_tracker,
            {k: {"sequence": v["sequence"], "success_count": v["success_count"]}
             for k, v in self.compound_actions.items()},
            tick,
            discovery_rate,
            self.rng,
            max_capacity=macro_cap,
        )
        for ca in new_compounds:
            self.compound_actions[ca.name] = {
                "sequence": ca.sequence,
                "success_count": ca.success_count,
                "discovered_tick": ca.discovered_tick,
            }

        return delta

    def _effectors_to_dominant_action(self, effector_outputs: List[float]) -> int:
        """Map continuous effector outputs to a dominant discrete action ID for logging/cortex."""
        if len(effector_outputs) < 7:
            return 10  # idle

        def sig(x: float) -> float:
            return 1.0 / (1.0 + math.exp(-max(-10.0, min(10.0, x))))

        loco_int = sig(effector_outputs[1])
        harvest_int = sig(effector_outputs[2])
        social_val = math.tanh(max(-10.0, min(10.0, effector_outputs[3])))
        maintain_int = sig(effector_outputs[4])
        reproduce_int = sig(effector_outputs[5])
        signal_int = sig(effector_outputs[6])

        # Find the strongest activation
        candidates = [
            (loco_int, 0),      # move_0 (approximate)
            (harvest_int, 4),   # harvest
            (abs(social_val), 11 if social_val < 0 else 5),  # attack or transfer
            (maintain_int, 7),  # maintain
            (reproduce_int, 8), # fork
            (signal_int, 6),    # signal
        ]
        best_intensity, best_action = max(candidates, key=lambda x: x[0])
        if best_intensity < 0.2:
            return 10  # idle
        return best_action

    # ── Info ─────────────────────────────────────────────────────────────

    def status_line(self) -> str:
        s = self.state
        action_desc = s.last_action or "—"
        parts = [
            f"[Agent-{self.id}] energy:{s.energy:.0f} entropy:{s.entropy:.0f} "
            f"node:{s.node_id} | {action_desc} | cortex:{self.cortex.num_associations()}"
        ]
        if self.brain:
            parts.append(
                f" neat:{self.brain.num_active_nodes}n/"
                f"{self.brain.num_active_connections}c"
                f" cost:{self.brain.metabolic_cost:.2f}"
            )
        parts.append(f" mem:{len(self.memory)}")
        if self.compound_actions:
            parts.append(f" macros:{len(self.compound_actions)}")
        return "".join(parts)

    def snapshot_dict(self) -> dict:
        """Return a dict for database snapshots."""
        d = {
            "agent_id": self.id,
            "energy": self.state.energy,
            "entropy": self.state.entropy,
            "age": self.state.age,
            "node_id": self.state.node_id,
            "alive": self.state.alive,
            "generation": self.generation,
            "cortex_size": self.cortex.num_associations(),
            "memory_size": len(self.memory),
            "compound_actions": len(self.compound_actions),
            "genome": self.genome.to_json(),
        }
        if self.brain:
            d["brain_nodes"] = self.brain.num_active_nodes
            d["brain_connections"] = self.brain.num_active_connections
            d["brain_cost"] = self.brain.metabolic_cost
        return d

    def __repr__(self) -> str:
        return f"Agent(id={self.id}, gen={self.generation}, alive={self.alive})"
