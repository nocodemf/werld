"""
Event Log — append-only event log to SQLite.

Every significant event in the simulation is logged with full context.
Positions are node IDs (graph topology).
"""

from __future__ import annotations

import json
from typing import List, Optional, Any, Dict

from persistence.db import get_connection


def log_event(
    tick: int,
    event_type: str,
    agent_id: Optional[int],
    description: str,
    data: Optional[Dict[str, Any]] = None,
) -> None:
    """Log a single event."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO events (tick, event_type, agent_id, description, data) "
        "VALUES (?, ?, ?, ?, ?)",
        (tick, event_type, agent_id, description, json.dumps(data) if data else None),
    )


def log_events_batch(events: List[dict]) -> None:
    """Log multiple events in a single transaction."""
    conn = get_connection()
    conn.executemany(
        "INSERT INTO events (tick, event_type, agent_id, description, data) "
        "VALUES (:tick, :event_type, :agent_id, :description, :data)",
        events,
    )
    conn.commit()


def log_birth(
    tick: int,
    child_id: int,
    parent_a_id: int,
    parent_b_id: int,
    generation: int,
    genome_json: str,
) -> None:
    """Log a birth and record lineage."""
    conn = get_connection()
    log_event(tick, "birth", child_id, f"Agent-{child_id} born (gen {generation})")
    conn.execute(
        "INSERT OR REPLACE INTO lineage (child_id, parent_a_id, parent_b_id, born_tick, generation, genome) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (child_id, parent_a_id, parent_b_id, tick, generation, genome_json),
    )
    conn.commit()


def log_death(tick: int, agent_id: int, cause: str, age: int, generation: int) -> None:
    """Log a death and update lineage."""
    conn = get_connection()
    log_event(tick, "death", agent_id, f"Agent-{agent_id} died: {cause} (age={age})")
    conn.execute(
        "UPDATE lineage SET died_tick = ? WHERE child_id = ?",
        (tick, agent_id),
    )
    conn.commit()


def log_population_stats(
    tick: int,
    population: int,
    total_births: int,
    total_deaths: int,
    avg_energy: float,
    avg_entropy: float,
    avg_age: float,
    max_generation: int,
    avg_cortex_size: float,
    substrate_energy: float,
) -> None:
    """Log population-level statistics."""
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO population_stats VALUES (?,?,?,?,?,?,?,?,?,?)",
        (tick, population, total_births, total_deaths, avg_energy, avg_entropy,
         avg_age, max_generation, avg_cortex_size, substrate_energy),
    )
    conn.commit()


def log_comms_stats(
    tick: int,
    signals_sent: int,
    signals_received: int,
    unique_senders: int,
    unique_receivers: int,
    avg_distance: float,
    total_deliveries: int,
    avg_signal_energy: float = 0.0,
    avg_signal_entropy: float = 0.0,
    avg_signal_resource: float = 0.0,
) -> None:
    """Log communication statistics for a tick."""
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO comms_stats VALUES (?,?,?,?,?,?,?,?,?,?)",
        (tick, signals_sent, signals_received, unique_senders, unique_receivers,
         avg_distance, total_deliveries, avg_signal_energy, avg_signal_entropy,
         avg_signal_resource),
    )
    conn.commit()


def log_signal_batch(tick: int, signal_events: list) -> None:
    """Log a batch of signal events to the events table (sampled to avoid DB bloat)."""
    if not signal_events:
        return
    conn = get_connection()
    import random as _rng
    sample = signal_events if len(signal_events) <= 20 else _rng.sample(signal_events, 20)
    for evt in sample:
        conn.execute(
            "INSERT INTO events (tick, event_type, agent_id, description, data) "
            "VALUES (?, ?, ?, ?, ?)",
            (tick, "signal_sent", evt.sender_id,
             f"Agent-{evt.sender_id} signaled to Agent-{evt.receiver_id} (hops={evt.distance})",
             json.dumps({
                 "receiver_id": evt.receiver_id,
                 "distance": evt.distance,
                 "vector": [round(v, 3) for v in evt.vector],
                 "sender_energy": round(evt.sender_energy, 3),
                 "sender_entropy": round(evt.sender_entropy, 3),
                 "sender_node": evt.sender_node,
                 "receiver_node": evt.receiver_node,
             })),
        )
    conn.commit()


def log_agent_snapshot(tick: int, snapshot: dict) -> None:
    """Log an agent state snapshot."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO snapshots (tick, agent_id, energy, entropy, age, node_id, "
        "alive, generation, cortex_size, memory_size, compound_actions, genome) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            tick, snapshot["agent_id"], snapshot["energy"], snapshot["entropy"],
            snapshot["age"], snapshot.get("node_id", 0),
            1 if snapshot["alive"] else 0, snapshot["generation"],
            snapshot["cortex_size"], snapshot.get("memory_size", 0),
            snapshot.get("compound_actions", 0), snapshot.get("genome", ""),
        ),
    )
