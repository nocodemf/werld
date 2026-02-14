"""
Database — SQLite setup and connection management.

Single database file holds:
  - events: complete event log (births, deaths, signals, harvests, etc.)
  - lineage: parent-child relationships across all generations
  - snapshots: periodic agent state snapshots for analytics
  - population_stats: population-level statistics per tick
  - comms_stats: communication statistics per tick
  - species_stats: per-tick species classification (Phase 1+)
  - brain_stats: per-tick brain complexity metrics (Phase 1+)

Positions are node IDs (integers) — not (x, y) coordinates.
"""

from __future__ import annotations

import os
import sqlite3
from typing import Optional

import config as cfg

_connection: Optional[sqlite3.Connection] = None


def get_connection() -> sqlite3.Connection:
    """Get or create the singleton database connection."""
    global _connection
    if _connection is not None:
        return _connection

    os.makedirs(cfg.DATA_DIR, exist_ok=True)
    _connection = sqlite3.connect(cfg.DB_PATH, check_same_thread=False)
    _connection.row_factory = sqlite3.Row
    _connection.execute("PRAGMA journal_mode=WAL")
    _connection.execute("PRAGMA synchronous=NORMAL")
    _init_schema(_connection)
    return _connection


def close_connection() -> None:
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None


def prune_old_data(current_tick: int) -> int:
    """
    Delete raw events and snapshots older than DB_PRUNE_AFTER_TICKS.
    Population_stats, comms_stats, and lineage are kept (they're small).
    Returns the number of rows deleted.
    """
    cutoff = current_tick - cfg.DB_PRUNE_AFTER_TICKS
    if cutoff <= 0:
        return 0

    conn = get_connection()
    deleted = 0

    # Prune events (keep births and deaths — they're in lineage too, but useful)
    # Delete signal_sent and brain_decision events older than cutoff
    cur = conn.execute(
        "DELETE FROM events WHERE tick < ? AND event_type IN "
        "('signal_sent', 'brain_decision')",
        (cutoff,),
    )
    deleted += cur.rowcount

    # Prune snapshots — keep only the most recent snapshot tick before cutoff
    # (so we always have at least one old reference point)
    cur = conn.execute(
        "DELETE FROM snapshots WHERE tick < ? AND tick NOT IN "
        "(SELECT MAX(tick) FROM snapshots WHERE tick < ?)",
        (cutoff, cutoff),
    )
    deleted += cur.rowcount

    conn.commit()
    return deleted


def _init_schema(conn: sqlite3.Connection) -> None:
    """Create tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS simulation_meta (
            key   TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            tick        INTEGER NOT NULL,
            event_type  TEXT NOT NULL,
            agent_id    INTEGER,
            description TEXT,
            data        TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_events_tick ON events(tick);
        CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
        CREATE INDEX IF NOT EXISTS idx_events_agent ON events(agent_id);

        CREATE TABLE IF NOT EXISTS lineage (
            child_id    INTEGER PRIMARY KEY,
            parent_a_id INTEGER,
            parent_b_id INTEGER,
            born_tick   INTEGER NOT NULL,
            died_tick   INTEGER,
            generation  INTEGER NOT NULL,
            genome      TEXT
        );

        CREATE TABLE IF NOT EXISTS snapshots (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            tick        INTEGER NOT NULL,
            agent_id    INTEGER NOT NULL,
            energy      REAL,
            entropy     REAL,
            age         INTEGER,
            node_id     INTEGER,
            alive       INTEGER,
            generation  INTEGER,
            cortex_size INTEGER,
            memory_size INTEGER,
            compound_actions INTEGER,
            genome      TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_snapshots_tick ON snapshots(tick);

        CREATE TABLE IF NOT EXISTS population_stats (
            tick            INTEGER PRIMARY KEY,
            population      INTEGER,
            total_births    INTEGER,
            total_deaths    INTEGER,
            avg_energy      REAL,
            avg_entropy     REAL,
            avg_age         REAL,
            max_generation  INTEGER,
            avg_cortex_size REAL,
            substrate_energy REAL
        );

        CREATE TABLE IF NOT EXISTS comms_stats (
            tick              INTEGER PRIMARY KEY,
            signals_sent      INTEGER DEFAULT 0,
            signals_received  INTEGER DEFAULT 0,
            unique_senders    INTEGER DEFAULT 0,
            unique_receivers  INTEGER DEFAULT 0,
            avg_distance      REAL DEFAULT 0.0,
            total_deliveries  INTEGER DEFAULT 0,
            avg_signal_energy REAL DEFAULT 0.0,
            avg_signal_entropy REAL DEFAULT 0.0,
            avg_signal_resource REAL DEFAULT 0.0
        );
        CREATE INDEX IF NOT EXISTS idx_comms_tick ON comms_stats(tick);

        -- Phase 1+: species tracking
        CREATE TABLE IF NOT EXISTS species_stats (
            tick            INTEGER NOT NULL,
            species_id      INTEGER NOT NULL,
            count           INTEGER DEFAULT 0,
            avg_fitness     REAL DEFAULT 0.0,
            avg_brain_nodes INTEGER DEFAULT 0,
            avg_brain_conns INTEGER DEFAULT 0,
            PRIMARY KEY (tick, species_id)
        );

        -- Phase 1+: brain complexity metrics
        CREATE TABLE IF NOT EXISTS brain_stats (
            tick              INTEGER PRIMARY KEY,
            avg_nodes         REAL DEFAULT 0.0,
            avg_connections   REAL DEFAULT 0.0,
            max_nodes         INTEGER DEFAULT 0,
            max_connections   INTEGER DEFAULT 0,
            avg_metabolic_cost REAL DEFAULT 0.0
        );

        -- Story chapters: plain-English narrative generated every N ticks
        CREATE TABLE IF NOT EXISTS story_chapters (
            chapter     INTEGER PRIMARY KEY,
            tick_start  INTEGER NOT NULL,
            tick_end    INTEGER NOT NULL,
            title       TEXT NOT NULL,
            content     TEXT NOT NULL,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
