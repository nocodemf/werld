"""
Agent State — mutable runtime state for a living agent.

Tracks energy, entropy, position (node ID in graph), age, signal buffer,
and whether the agent is still alive.

Position is a node ID (integer), not coordinates.  The substrate graph
determines what "nearby" means.
"""

from __future__ import annotations

from typing import List, Tuple, Optional, Any

import config as cfg


class AgentState:
    """Mutable per-tick state of an agent process."""

    __slots__ = (
        "energy",
        "entropy",
        "age",
        "node_id",        # Position in the graph (int node ID)
        "alive",
        "inventory",
        "signal_buffer",
        "last_action",
        "last_action_result",
    )

    def __init__(
        self,
        energy: float,
        node_id: int,
        entropy: float = 0.0,
    ) -> None:
        self.energy: float = energy
        self.entropy: float = entropy
        self.age: int = 0
        self.node_id: int = node_id
        self.alive: bool = True
        self.inventory: float = 0.0
        self.signal_buffer: List[List[float]] = []
        self.last_action: Optional[str] = None
        self.last_action_result: Any = None

    # ── Position property (backward compat) ──────────────────────────────

    @property
    def position(self) -> int:
        """The agent's position is a node ID in the graph."""
        return self.node_id

    @position.setter
    def position(self, value: int) -> None:
        self.node_id = value

    # ── Energy helpers ───────────────────────────────────────────────────

    def spend_energy(self, amount: float) -> bool:
        """
        Deduct *amount* from energy.  Returns True if agent can afford it,
        False if it would kill them (energy still deducted to 0).
        """
        self.energy -= amount
        if self.energy <= 0:
            self.energy = 0.0
            self.alive = False
            return False
        return True

    def gain_energy(self, amount: float, max_energy: float) -> float:
        """Add energy, capped at max_energy.  Returns actual gained."""
        before = self.energy
        self.energy = min(self.energy + amount, max_energy)
        return self.energy - before

    # ── Entropy helpers ──────────────────────────────────────────────────

    def accumulate_entropy(self, base: float, resistance: float) -> None:
        """
        Add entropy for this tick.
        base = cfg.BASE_ENTROPY_PER_TICK + age-scaled component
        resistance = genome.entropy_resistance (lower = more entropy)
        """
        added = base / max(resistance, 0.1)
        self.entropy += added
        if self.entropy >= cfg.LETHAL_ENTROPY:
            self.alive = False

    def reduce_entropy(self, amount: float) -> float:
        """Reduce entropy (from maintain action).  Returns actual reduction."""
        before = self.entropy
        self.entropy = max(0.0, self.entropy - amount)
        return before - self.entropy

    # ── Drive vector ─────────────────────────────────────────────────────

    def drive_vector(self, max_energy: float) -> Tuple[float, float]:
        """
        Returns (energy_deficit, entropy_pressure) in [0, 1].
        These are the raw internal pressures that bias action selection.
        """
        energy_deficit = (max_energy - self.energy) / max(max_energy, 1.0)
        entropy_pressure = self.entropy / cfg.LETHAL_ENTROPY
        return (
            min(1.0, max(0.0, energy_deficit)),
            min(1.0, max(0.0, entropy_pressure)),
        )

    # ── Tick upkeep ──────────────────────────────────────────────────────

    def tick_upkeep(
        self,
        tick_cost: float,
        entropy_resistance: float,
        brain_cost: float = 0.0,
    ) -> None:
        """
        Called once per tick before the agent acts.
        Deducts tick cost energy + brain metabolic cost, accumulates entropy,
        advances age.
        """
        self.age += 1
        self.spend_energy(tick_cost + brain_cost)
        base_entropy = cfg.BASE_ENTROPY_PER_TICK + self.age * cfg.ENTROPY_AGE_FACTOR
        self.accumulate_entropy(base_entropy, entropy_resistance)
        # Clear signal buffer for this tick
        self.signal_buffer = []

    def __repr__(self) -> str:
        return (
            f"State(energy={self.energy:.1f}, entropy={self.entropy:.1f}, "
            f"age={self.age}, node={self.node_id}, alive={self.alive})"
        )
