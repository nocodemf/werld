"""
Entropy — degradation system.

Entropy is the computational analog of wear.  Every tick, each agent
accumulates a small amount of entropy that increases with age.  If entropy
reaches the lethal threshold, the agent's process terminates.

The `maintain` action is the only way to reduce entropy.  Agents that
never learn to maintain themselves will eventually degrade and die, even
if they have plenty of energy.  This creates dual survival pressure:
energy AND entropy management.
"""

from __future__ import annotations

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from agents.agent import Agent


def apply_entropy_decay(agents: List[Agent]) -> List[str]:
    """
    Called once per tick AFTER agent actions.
    Entropy accumulation already happens in tick_upkeep(), so this function
    handles any additional global entropy effects and reports deaths.

    Returns event descriptions for any entropy-related deaths.
    """
    events: List[str] = []

    for agent in agents:
        if not agent.alive:
            continue

        # Check if entropy killed the agent (may have been set during tick_upkeep
        # or if maintain wasn't enough)
        if agent.state.entropy >= 100.0:  # LETHAL_ENTROPY
            agent.state.alive = False
            events.append(
                f"Agent-{agent.id} terminated: entropy overload "
                f"(entropy={agent.state.entropy:.0f}, age={agent.state.age})"
            )

    return events


def collect_deaths(agents: List[Agent]) -> List[str]:
    """
    Scan for all agents that died this tick (from any cause) and return
    event descriptions.
    """
    events: List[str] = []
    for agent in agents:
        if not agent.alive:
            cause = "unknown"
            if agent.state.energy <= 0:
                cause = "energy depletion"
            elif agent.state.entropy >= 100.0:
                cause = "entropy overload"
            events.append(
                f"Agent-{agent.id} DIED: {cause} "
                f"(age={agent.state.age}, gen={agent.generation})"
            )
    return events

