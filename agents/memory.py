"""
Episodic Memory — event-based memory for agents.

Each agent maintains a bounded buffer of remembered events.  Unlike the
cortex (which stores state→action weights), episodic memory stores *what
happened*: "at tick T, I was at position P, I did action A, and drives
changed by D, while Agent-X was nearby."

Memories have an importance score that decays over time.  When the buffer
is full, the least important memories are pruned.  This feeds into:
  - LLM reasoning context (the agent can "remember" past events)
  - Compound action discovery (detecting repeated beneficial sequences)
  - Social memory (remembering interactions with specific agents)
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional, Tuple, Union
import config as cfg


class Episode:
    """A single remembered event."""

    __slots__ = (
        "tick", "action", "action_id", "position", "energy_before", "energy_after",
        "entropy_before", "entropy_after", "drive_delta", "agents_present",
        "signals_received", "importance", "result_desc",
    )

    def __init__(
        self,
        tick: int,
        action: str,
        action_id: int,
        position: Any,  # node_id (int) in graph topology
        energy_before: float,
        energy_after: float,
        entropy_before: float,
        entropy_after: float,
        drive_delta: float,
        agents_present: List[int],
        signals_received: int,
        result_desc: str,
        social_weight: float = 0.5,
    ) -> None:
        self.tick = tick
        self.action = action
        self.action_id = action_id
        self.position = position  # node_id in graph topology
        self.energy_before = energy_before
        self.energy_after = energy_after
        self.entropy_before = entropy_before
        self.entropy_after = entropy_after
        self.drive_delta = drive_delta  # positive = drives improved
        self.agents_present = agents_present
        self.signals_received = signals_received
        self.result_desc = result_desc

        # Importance: drive magnitude + evolvable social weight
        self.importance = abs(drive_delta) + (social_weight if agents_present else 0.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tick": self.tick,
            "action": self.action,
            "action_id": self.action_id,
            "position": self.position,
            "energy_before": round(self.energy_before, 1),
            "energy_after": round(self.energy_after, 1),
            "entropy_before": round(self.entropy_before, 1),
            "entropy_after": round(self.entropy_after, 1),
            "drive_delta": round(self.drive_delta, 3),
            "agents_present": self.agents_present,
            "signals_received": self.signals_received,
            "importance": round(self.importance, 3),
            "result_desc": self.result_desc,
        }

    def to_narrative(self) -> str:
        """Convert to a natural-language sentence for LLM context."""
        delta_word = "improved" if self.drive_delta > 0 else "worsened"
        others = f" (agents {self.agents_present} nearby)" if self.agents_present else ""
        return (
            f"Tick {self.tick}: At {self.position}, did '{self.action}' -> "
            f"{self.result_desc}. Energy {self.energy_before:.0f}->{self.energy_after:.0f}, "
            f"entropy {self.entropy_before:.0f}->{self.entropy_after:.0f}. "
            f"Drives {delta_word} by {abs(self.drive_delta):.2f}.{others}"
        )


class EpisodicMemory:
    """Bounded episodic memory buffer with importance-based pruning.

    Decay rate and social weight are now evolvable genome traits,
    allowing different species to evolve different memory strategies.
    """

    def __init__(
        self,
        capacity: int,
        decay_rate: float = 0.95,
        social_weight: float = 0.5,
    ) -> None:
        self.capacity = int(capacity)
        self.decay_rate = decay_rate
        self.social_weight = social_weight
        self.episodes: List[Episode] = []

    def record(self, episode: Episode) -> None:
        """Add a new episode, pruning if over capacity."""
        self.episodes.append(episode)
        if len(self.episodes) > self.capacity:
            self._prune()

    def decay(self) -> None:
        """Decay importance of all memories (older = less important)."""
        for ep in self.episodes:
            ep.importance *= self.decay_rate
        # Remove memories below threshold
        self.episodes = [
            ep for ep in self.episodes
            if ep.importance >= cfg.MEMORY_MIN_IMPORTANCE
        ]

    def _prune(self) -> None:
        """Remove least important memories to stay within capacity."""
        if len(self.episodes) <= self.capacity:
            return
        self.episodes.sort(key=lambda e: e.importance, reverse=True)
        self.episodes = self.episodes[:self.capacity]

    def recent(self, n: int = 10) -> List[Episode]:
        """Return the N most recent episodes."""
        return self.episodes[-n:]

    def most_important(self, n: int = 10) -> List[Episode]:
        """Return the N highest-importance episodes."""
        return sorted(self.episodes, key=lambda e: e.importance, reverse=True)[:n]

    def involving_agent(self, agent_id: int) -> List[Episode]:
        """Return all memories involving a specific other agent."""
        return [ep for ep in self.episodes if agent_id in ep.agents_present]

    def recent_action_sequence(self, n: int = 5) -> List[int]:
        """Return the action IDs of the last N actions."""
        return [ep.action_id for ep in self.episodes[-n:]]

    def narrative_summary(self, n: int = 8) -> str:
        """Build a narrative summary of recent + important memories for LLM."""
        recent = self.recent(n // 2)
        important = self.most_important(n // 2)
        # Merge and deduplicate
        seen_ticks = set()
        merged = []
        for ep in important + recent:
            if ep.tick not in seen_ticks:
                seen_ticks.add(ep.tick)
                merged.append(ep)
        merged.sort(key=lambda e: e.tick)
        return "\n".join(ep.to_narrative() for ep in merged[-n:])

    def serialise(self) -> List[Dict[str, Any]]:
        """Serialise all episodes for checkpoint."""
        return [ep.to_dict() for ep in self.episodes]

    @classmethod
    def deserialise(
        cls,
        data: List[Dict[str, Any]],
        capacity: int,
        decay_rate: float = 0.95,
        social_weight: float = 0.5,
    ) -> "EpisodicMemory":
        """Restore from serialised data."""
        mem = cls(capacity, decay_rate=decay_rate, social_weight=social_weight)
        for d in data:
            ep = Episode(
                tick=d["tick"],
                action=d["action"],
                action_id=d["action_id"],
                position=d["position"] if isinstance(d["position"], int) else (d["position"][0] if isinstance(d["position"], list) else d["position"]),
                energy_before=d["energy_before"],
                energy_after=d["energy_after"],
                entropy_before=d["entropy_before"],
                entropy_after=d["entropy_after"],
                drive_delta=d["drive_delta"],
                agents_present=d["agents_present"],
                signals_received=d["signals_received"],
                result_desc=d["result_desc"],
            )
            ep.importance = d.get("importance", 0.1)
            mem.episodes.append(ep)
        return mem

    def __len__(self) -> int:
        return len(self.episodes)

    def __repr__(self) -> str:
        return f"EpisodicMemory({len(self.episodes)}/{self.capacity})"

