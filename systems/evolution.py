"""
Evolution — self-modification through motor pattern discovery.

Agents can discover "macros" (motor patterns) — repeating sequences of
dominant effector activations that reliably reduce drives.  The continuous
effector outputs are binned into coarse action categories for pattern
detection.  When an agent executes a beneficial pattern multiple times,
it gets compressed into a compound action that the cortex can trigger.

This is genuine self-modification: the agent's behavioral repertoire
GROWS during its lifetime, and motor patterns can be inherited by
offspring (with mutation).  Different lineages evolve different
repertoires — the computational equivalent of tool use and culture.
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional, Tuple, Any

import config as cfg


class CompoundAction:
    """A learned sequence of primitive actions."""

    __slots__ = ("name", "sequence", "success_count", "discovered_tick", "total_drive_improvement")

    def __init__(
        self,
        name: str,
        sequence: List[int],
        discovered_tick: int = 0,
        success_count: int = 0,
    ) -> None:
        self.name = name
        self.sequence = sequence
        self.discovered_tick = discovered_tick
        self.success_count = success_count
        self.total_drive_improvement = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "sequence": self.sequence,
            "discovered_tick": self.discovered_tick,
            "success_count": self.success_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CompoundAction":
        return cls(
            name=data["name"],
            sequence=data["sequence"],
            discovered_tick=data.get("discovered_tick", 0),
            success_count=data.get("success_count", 0),
        )


class SequenceTracker:
    """
    Tracks recent action sequences and identifies candidates for
    compound action discovery.
    """

    def __init__(self, max_length: int = cfg.MAX_COMPOUND_LENGTH) -> None:
        self.max_length = max_length
        self.recent_actions: List[int] = []
        self.recent_drive_deltas: List[float] = []
        # Track repeated beneficial sequences: tuple(seq) -> count
        self.sequence_counts: Dict[Tuple[int, ...], int] = {}
        self.sequence_drive_sums: Dict[Tuple[int, ...], float] = {}

    def record(self, action_id: int, drive_delta: float) -> None:
        """Record an action and its drive impact."""
        self.recent_actions.append(action_id)
        self.recent_drive_deltas.append(drive_delta)

        # Keep a sliding window
        if len(self.recent_actions) > self.max_length * 3:
            self.recent_actions = self.recent_actions[-self.max_length * 3:]
            self.recent_drive_deltas = self.recent_drive_deltas[-self.max_length * 3:]

        # Check all subsequences of length 2..max_length
        for length in range(2, min(self.max_length + 1, len(self.recent_actions) + 1)):
            seq = tuple(self.recent_actions[-length:])
            drive_sum = sum(self.recent_drive_deltas[-length:])

            if drive_sum > 0:  # Only track beneficial sequences
                self.sequence_counts[seq] = self.sequence_counts.get(seq, 0) + 1
                self.sequence_drive_sums[seq] = (
                    self.sequence_drive_sums.get(seq, 0.0) + drive_sum
                )

    def get_discovery_candidates(self) -> List[Tuple[Tuple[int, ...], int, float]]:
        """
        Return sequences that have been repeated enough times to be
        candidates for compound action discovery.
        Returns: [(sequence, count, total_drive_improvement), ...]
        """
        candidates = []
        for seq, count in self.sequence_counts.items():
            if count >= cfg.COMPOUND_SUCCESS_THRESHOLD:
                drive_sum = self.sequence_drive_sums.get(seq, 0.0)
                candidates.append((seq, count, drive_sum))
        # Sort by total drive improvement
        candidates.sort(key=lambda x: x[2], reverse=True)
        return candidates

    def clear_candidate(self, seq: Tuple[int, ...]) -> None:
        """Remove a sequence from tracking (after it's been promoted)."""
        self.sequence_counts.pop(seq, None)
        self.sequence_drive_sums.pop(seq, None)


def discover_compound_actions(
    tracker: SequenceTracker,
    existing_compounds: Dict[str, CompoundAction],
    tick: int,
    discovery_rate: float,
    rng: random.Random,
    max_capacity: int = 0,
) -> List[CompoundAction]:
    """
    Check if the agent should discover any new compound actions.
    Returns newly discovered compound actions.

    max_capacity: evolvable genome trait (macro_capacity). Falls back to
    cfg.MAX_COMPOUND_ACTIONS if 0 or not provided.
    """
    cap = max_capacity if max_capacity > 0 else cfg.MAX_COMPOUND_ACTIONS
    if len(existing_compounds) >= cap:
        return []

    candidates = tracker.get_discovery_candidates()
    discovered = []

    for seq, count, drive_sum in candidates:
        # Probabilistic discovery based on genomic trait
        if rng.random() > discovery_rate:
            continue

        # Don't rediscover existing sequences
        seq_list = list(seq)
        already_exists = any(
            (ca.get("sequence") if isinstance(ca, dict) else ca.sequence) == seq_list
            for ca in existing_compounds.values()
        )
        if already_exists:
            continue

        # Create the compound action
        name = f"macro_{len(existing_compounds)}_{tick}"
        ca = CompoundAction(
            name=name,
            sequence=seq_list,
            discovered_tick=tick,
            success_count=count,
        )
        ca.total_drive_improvement = drive_sum
        discovered.append(ca)
        tracker.clear_candidate(seq)

        if len(existing_compounds) + len(discovered) >= cap:
            break

    return discovered


def mutate_compound_action(
    ca: CompoundAction,
    rng: random.Random,
    mutation_rate: float,
    num_primitive_actions: int,
    max_length: int = 0,
) -> CompoundAction:
    """
    Mutate a compound action for inheritance.
    Can: swap steps, remove a step, add a step, or change a step.

    max_length: evolvable genome trait (macro_pattern_length).
    Falls back to cfg.MAX_COMPOUND_LENGTH if 0 or not provided.
    """
    ml = max_length if max_length > 0 else cfg.MAX_COMPOUND_LENGTH
    seq = list(ca.sequence)

    if rng.random() < mutation_rate:
        mutation_type = rng.choice(["swap", "remove", "add", "change"])

        if mutation_type == "swap" and len(seq) >= 2:
            i, j = rng.sample(range(len(seq)), 2)
            seq[i], seq[j] = seq[j], seq[i]

        elif mutation_type == "remove" and len(seq) > 2:
            idx = rng.randint(0, len(seq) - 1)
            seq.pop(idx)

        elif mutation_type == "add" and len(seq) < ml:
            new_action = rng.randint(0, num_primitive_actions - 1)
            idx = rng.randint(0, len(seq))
            seq.insert(idx, new_action)

        elif mutation_type == "change":
            idx = rng.randint(0, len(seq) - 1)
            seq[idx] = rng.randint(0, num_primitive_actions - 1)

    return CompoundAction(
        name=f"mut_{ca.name}",
        sequence=seq,
        discovered_tick=ca.discovered_tick,
        success_count=0,  # Reset — must prove itself in new host
    )

