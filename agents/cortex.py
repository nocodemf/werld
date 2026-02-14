"""
Cortex — associative reflex system.

A bounded weight table mapping (state_hash, action_id) → weight.
The cortex is the SECONDARY decision system (behind the NEAT brain).
It serves as a fast reflex / fallback when the brain is unavailable or
exploration is happening.

Drive modulation uses the agent's heritable genome traits (harvest_drive,
maintain_drive, etc.) rather than hardcoded constants.  Different species
evolve different drive profiles through natural selection.

With the continuous effector interface, the cortex produces a discrete
action which is converted to effector activations via _cortex_to_effectors().
"""

from __future__ import annotations

import math
import random
from typing import Dict, Tuple, List, Optional

import config as cfg


# ── Action IDs ────────────────────────────────────────────────────────────────

ACTION_IDS: Dict[str, int] = {
    "move_0": 0,   # neighbor index 0
    "move_1": 1,   # neighbor index 1
    "move_2": 2,   # neighbor index 2
    "move_3": 3,   # neighbor index 3
    "harvest": 4,
    "transfer": 5,
    "signal": 6,
    "maintain": 7,
    "fork": 8,
    "observe": 9,
    "idle": 10,
    "attack": 11,  # Phase 4: steal energy from agent at same node
}

NUM_ACTIONS = len(ACTION_IDS)
ACTION_NAMES = {v: k for k, v in ACTION_IDS.items()}


def _state_hash(
    energy_deficit: float,
    entropy_pressure: float,
    local_energy: float,
    agents_nearby: int,
    node_degree: int,
    num_signals: int = 0,
    resolution: int = 4,
) -> int:
    """
    Discretise continuous percept into a coarse hash.
    Now includes node degree (graph topology awareness) instead of
    boolean has_signals.

    `resolution` (evolvable genome trait cortex_resolution, range 2-6)
    controls how many bins per perceptual dimension.  Higher resolution
    = finer discrimination but slower generalisation and more memory.
    """
    max_bin = resolution - 1
    e_bin = min(int(energy_deficit * resolution), max_bin)
    n_bin = min(int(entropy_pressure * resolution), max_bin)
    l_bin = min(int(local_energy / max(100.0 / resolution, 1)), max_bin)
    a_bin = min(agents_nearby, max_bin)
    d_bin = min(node_degree // max(8 // resolution, 1), max_bin)
    s_bin = min(num_signals, max(max_bin - 1, 1))
    # Variable-width bit packing
    bits = max(1, resolution.bit_length())
    return (
        (e_bin << (bits * 5)) |
        (n_bin << (bits * 4)) |
        (l_bin << (bits * 3)) |
        (a_bin << (bits * 2)) |
        (d_bin << (bits * 1)) |
        s_bin
    )


class Cortex:
    """Associative weight table with bounded capacity and dynamic action space.

    Drive modulation is now genome-driven rather than hardcoded.
    The agent's heritable drive traits (harvest_drive, maintain_drive, etc.)
    determine how internal conditions bias action selection.
    """

    def __init__(
        self,
        capacity: int,
        learning_rate: float,
        exploration_factor: float,
        rng: Optional[random.Random] = None,
        drive_weights: Optional[Dict[str, float]] = None,
        resolution: int = 4,
    ) -> None:
        self.capacity = int(capacity)
        self.learning_rate = learning_rate
        self.exploration_factor = exploration_factor
        self.rng = rng or random.Random()
        self.resolution = int(resolution)

        # Evolvable drive biases (from genome traits)
        self.drive_weights: Dict[str, float] = drive_weights or {
            "harvest_drive": 0.5,
            "maintain_drive": 0.5,
            "explore_drive": 0.3,
            "social_drive": 0.0,
            "reproduce_drive": 0.3,
            "signal_drive": 0.2,
        }

        # (state_hash, action_id) → weight
        self.weights: Dict[Tuple[int, int], float] = {}

        # Track total experience
        self.experience: int = 0

        # Dynamic action count (primitives + compound)
        self.total_actions: int = NUM_ACTIONS

    # ── Core decision ────────────────────────────────────────────────────

    def decide(
        self,
        energy_deficit: float,
        entropy_pressure: float,
        local_energy: float,
        agents_nearby: int,
        node_degree: int,
        num_compound_actions: int = 0,
        num_signals: int = 0,
    ) -> Tuple[int, int]:
        """
        Choose an action id.  Returns (state_hash, chosen_action_id).

        Drive modulation uses the agent's heritable drive traits rather
        than hardcoded constants.  Different species evolve different
        drive profiles through natural selection.
        """
        sh = _state_hash(
            energy_deficit, entropy_pressure, local_energy, agents_nearby,
            node_degree, num_signals, resolution=self.resolution,
        )
        total = NUM_ACTIONS + num_compound_actions
        self.total_actions = total

        # Read evolvable drive traits
        harvest_d = self.drive_weights.get("harvest_drive", 0.5)
        maintain_d = self.drive_weights.get("maintain_drive", 0.5)
        explore_d = self.drive_weights.get("explore_drive", 0.3)
        social_d = self.drive_weights.get("social_drive", 0.0)
        reproduce_d = self.drive_weights.get("reproduce_drive", 0.3)
        signal_d = self.drive_weights.get("signal_drive", 0.2)

        scores: List[float] = []
        for aid in range(total):
            w = self.weights.get((sh, aid), cfg.CORTEX_WEIGHT_INIT)

            # Genome-driven drive modulation — no hardcoded action biases
            drive_boost = 0.0
            if aid in (0, 1, 2, 3):    # move
                drive_boost = explore_d * (0.3 + energy_deficit * harvest_d)
            elif aid == 4:               # harvest
                drive_boost = energy_deficit * harvest_d
            elif aid == 5:               # transfer
                drive_boost = max(0.0, social_d) * (1.0 - energy_deficit)
            elif aid == 6:               # signal
                drive_boost = signal_d * 0.3
            elif aid == 7:               # maintain
                drive_boost = entropy_pressure * maintain_d
            elif aid == 8:               # fork
                drive_boost = (1.0 - energy_deficit) * reproduce_d
            elif aid == 9:               # observe
                drive_boost = 0.0        # no built-in bias
            elif aid == 10:              # idle
                drive_boost = 0.0        # no built-in bias
            elif aid == 11:              # attack
                drive_boost = max(0.0, -social_d) * energy_deficit
            elif aid >= NUM_ACTIONS:     # compound actions
                drive_boost = 0.05       # minimal compound bonus

            # Exploration noise (decays with experience)
            noise_scale = self.exploration_factor / (1.0 + self.experience * 0.001)
            noise = self.rng.gauss(0, noise_scale)

            scores.append(w + drive_boost + noise)

        action_id = self._softmax_select(scores)
        return sh, action_id

    def _softmax_select(self, scores: List[float]) -> int:
        """Weighted random selection using softmax."""
        max_s = max(scores)
        exps = [math.exp(min(s - max_s, 20)) for s in scores]
        total = sum(exps)
        if total == 0:
            return self.rng.randint(0, len(scores) - 1)

        r = self.rng.random() * total
        cumulative = 0.0
        for i, e in enumerate(exps):
            cumulative += e
            if r <= cumulative:
                return i
        return len(scores) - 1

    # ── Learning ─────────────────────────────────────────────────────────

    def reinforce(
        self,
        state_hash: int,
        action_id: int,
        drive_before: Tuple[float, float],
        drive_after: Tuple[float, float],
    ) -> float:
        """Update weight based on drive change.  Returns delta."""
        before_mag = math.sqrt(drive_before[0] ** 2 + drive_before[1] ** 2)
        after_mag = math.sqrt(drive_after[0] ** 2 + drive_after[1] ** 2)
        reward = before_mag - after_mag

        key = (state_hash, action_id)
        old_w = self.weights.get(key, cfg.CORTEX_WEIGHT_INIT)
        delta = self.learning_rate * reward
        self.weights[key] = old_w + delta
        self.experience += 1

        if len(self.weights) > self.capacity:
            self._prune()

        return delta

    def seed_weight(self, state_hash: int, action_id: int, weight: float) -> None:
        """Seed a weight directly."""
        key = (state_hash, action_id)
        self.weights[key] = weight
        if len(self.weights) > self.capacity:
            self._prune()

    def _prune(self) -> None:
        """Remove weakest associations to stay within capacity."""
        if len(self.weights) <= self.capacity:
            return
        sorted_keys = sorted(self.weights, key=lambda k: abs(self.weights[k]))
        to_remove = len(self.weights) - self.capacity
        for key in sorted_keys[:to_remove]:
            del self.weights[key]

    def decay_unused(self) -> None:
        """Slowly decay all weights toward zero."""
        to_delete = []
        for key in self.weights:
            self.weights[key] *= (1.0 - cfg.CORTEX_DECAY_RATE)
            if abs(self.weights[key]) < 0.001:
                to_delete.append(key)
        for key in to_delete:
            del self.weights[key]

    # ── Knowledge Transfer ───────────────────────────────────────────────

    @classmethod
    def inherit(
        cls,
        parent_a: "Cortex",
        parent_b: "Cortex",
        capacity: int,
        learning_rate: float,
        exploration_factor: float,
        cultural_transfer: float,
        rng: random.Random,
        drive_weights: Optional[Dict[str, float]] = None,
        resolution: int = 4,
    ) -> "Cortex":
        """
        Create a child cortex that inherits a fraction of the parents' weights.
        """
        child = cls(capacity, learning_rate, exploration_factor, rng, drive_weights, resolution=resolution)

        all_keys = set(parent_a.weights.keys()) | set(parent_b.weights.keys())

        for key in all_keys:
            if rng.random() > cultural_transfer:
                continue

            w_a = parent_a.weights.get(key, 0.0)
            w_b = parent_b.weights.get(key, 0.0)

            if abs(w_a) > abs(w_b):
                w = w_a * 0.5
            else:
                w = w_b * 0.5

            if abs(w) > 0.01:
                child.weights[key] = w

        if len(child.weights) > child.capacity:
            child._prune()

        return child

    # ── Info ─────────────────────────────────────────────────────────────

    def max_weight_for_state(self, state_hash: int) -> float:
        """Return the strongest absolute weight for a given state."""
        max_w = 0.0
        for aid in range(self.total_actions):
            w = abs(self.weights.get((state_hash, aid), 0.0))
            if w > max_w:
                max_w = w
        return max_w

    def num_associations(self) -> int:
        return len(self.weights)

    def __repr__(self) -> str:
        return f"Cortex(assoc={len(self.weights)}, exp={self.experience})"
