"""
Signals — signal propagation on a graph substrate.

After all agents have acted in a tick, this system collects emitted signals
and delivers them to every agent within signal_range HOPS in the graph.

Distance is measured in graph hops (BFS), not physical distance.
"""

from __future__ import annotations

from typing import List, Tuple, Dict, Set, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from agents.agent import Agent
    from engine.substrate import Substrate


class SignalEvent:
    """Structured record of a single signal delivery."""
    __slots__ = ("sender_id", "receiver_id", "vector", "distance",
                 "sender_energy", "sender_entropy", "sender_node", "receiver_node")

    def __init__(
        self,
        sender_id: int,
        receiver_id: int,
        vector: List[float],
        distance: int,
        sender_energy: float,
        sender_entropy: float,
        sender_node: int,
        receiver_node: int,
    ) -> None:
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.vector = vector
        self.distance = distance
        self.sender_energy = sender_energy
        self.sender_entropy = sender_entropy
        self.sender_node = sender_node
        self.receiver_node = receiver_node

    def to_log_str(self) -> str:
        return (
            f"Agent-{self.sender_id} signal received by Agent-{self.receiver_id} "
            f"(hops={self.distance})"
        )


class SignalSummary:
    """Aggregated signal statistics for a tick."""
    __slots__ = (
        "signals_sent", "signals_received", "unique_senders",
        "unique_receivers", "avg_distance", "total_deliveries",
    )

    def __init__(self) -> None:
        self.signals_sent = 0
        self.signals_received = 0
        self.unique_senders: set = set()
        self.unique_receivers: set = set()
        self.avg_distance = 0.0
        self.total_deliveries = 0


def propagate_signals(
    agents: List[Agent],
    substrate: "Substrate",
) -> Tuple[List[str], List[SignalEvent], SignalSummary]:
    """
    Collect signals emitted this tick and deliver them to nearby agents.
    Uses BFS on the graph to determine which agents are within range.

    Returns:
        - event_strings: human-readable log lines
        - signal_events: structured SignalEvent objects for DB logging
        - summary: aggregated stats for the tick
    """
    event_strings: List[str] = []
    signal_events: List[SignalEvent] = []
    summary = SignalSummary()

    # Collect all emitted signals
    emitters: List[Tuple[Agent, Dict[str, Any]]] = []
    for agent in agents:
        if not agent.alive:
            continue
        result = agent.state.last_action_result
        if isinstance(result, dict) and result.get("type") == "signal":
            emitters.append((agent, result))
            summary.signals_sent += 1
            summary.unique_senders.add(agent.id)

    if not emitters:
        return event_strings, signal_events, summary

    # Build a lookup: node_id → list of alive agents on that node
    node_to_agents: Dict[int, List[Agent]] = {}
    for agent in agents:
        if agent.alive:
            nid = agent.state.node_id
            if nid not in node_to_agents:
                node_to_agents[nid] = []
            node_to_agents[nid].append(agent)

    total_dist = 0

    # For each emitter, BFS to find all nodes within signal range
    for emitter, result_data in emitters:
        vector = result_data["vector"]
        sender_node = emitter.state.node_id
        sig_range = int(emitter.genome.traits["signal_range"])
        sender_energy = result_data.get("sender_energy", 0.0)
        sender_entropy = result_data.get("sender_entropy", 0.0)

        # BFS: get all nodes within sig_range hops
        nodes_in_range = substrate.nodes_within_range(sender_node, sig_range)

        # Deliver to all agents on those nodes
        for target_node_id, dist in nodes_in_range.items():
            if target_node_id not in node_to_agents:
                continue
            for receiver in node_to_agents[target_node_id]:
                if receiver.id == emitter.id:
                    continue

                receiver.state.signal_buffer.append(vector)
                summary.unique_receivers.add(receiver.id)
                summary.total_deliveries += 1
                total_dist += dist

                evt = SignalEvent(
                    sender_id=emitter.id,
                    receiver_id=receiver.id,
                    vector=vector,
                    distance=dist,
                    sender_energy=sender_energy,
                    sender_entropy=sender_entropy,
                    sender_node=sender_node,
                    receiver_node=target_node_id,
                )
                signal_events.append(evt)
                event_strings.append(evt.to_log_str())

    summary.signals_received = summary.total_deliveries
    if summary.total_deliveries > 0:
        summary.avg_distance = total_dist / summary.total_deliveries

    return event_strings, signal_events, summary
