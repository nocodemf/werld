"""
Story Generator — creates plain-English narrative chapters from simulation data.

Every STORY_CHAPTER_EVERY ticks, a new chapter is generated summarising what
happened in the civilisation during that period.  No LLM required — the text
is template-driven but reads naturally.

Chapters are stored in the story_chapters table and displayed on the dashboard.
"""

from __future__ import annotations

import json
import math
from typing import Optional, Dict, Any, List

from persistence.db import get_connection
import config as cfg

# ── Configuration ─────────────────────────────────────────────────────────────
STORY_CHAPTER_EVERY = 10000  # Generate a chapter every N ticks


# ── Chapter name table (for the first ~20 chapters, then generate) ───────────
CHAPTER_TITLES = [
    "The Beginning",
    "First Steps",
    "Finding a Way",
    "Growing Pains",
    "Competition Rises",
    "Adaptation",
    "New Horizons",
    "The Struggle",
    "Branching Out",
    "Turning Points",
    "Consolidation",
    "The Long Game",
    "Deep Roots",
    "Emergence",
    "Complexity",
    "Cycles",
    "Resilience",
    "Innovation",
    "Equilibrium",
    "The Next Era",
]


def _get_title(chapter: int) -> str:
    if chapter < len(CHAPTER_TITLES):
        return CHAPTER_TITLES[chapter]
    return f"Epoch {chapter + 1}"


def _get_stats_at(tick: int) -> Optional[Dict[str, Any]]:
    """Get population_stats closest to the given tick."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM population_stats WHERE tick <= ? ORDER BY tick DESC LIMIT 1",
        (tick,),
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def _get_brain_stats_at(tick: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM brain_stats WHERE tick <= ? ORDER BY tick DESC LIMIT 1",
        (tick,),
    ).fetchone()
    return dict(row) if row else None


def _count_events_in_range(tick_start: int, tick_end: int, event_type: str) -> int:
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) as c FROM events WHERE tick > ? AND tick <= ? AND event_type = ?",
        (tick_start, tick_end, event_type),
    ).fetchone()
    return row["c"] if row else 0


def _count_species_at(tick: int) -> int:
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(DISTINCT species_id) as c FROM species_stats WHERE tick = ?",
        (tick,),
    ).fetchone()
    return row["c"] if row else 0


def _get_max_generation_at(tick: int) -> int:
    conn = get_connection()
    row = conn.execute(
        "SELECT MAX(generation) as g FROM lineage WHERE born_tick <= ?",
        (tick,),
    ).fetchone()
    return row["g"] if row and row["g"] is not None else 0


def _get_comms_at(tick: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM comms_stats WHERE tick <= ? ORDER BY tick DESC LIMIT 1",
        (tick,),
    ).fetchone()
    return dict(row) if row else None


def _pop_description(pop: int) -> str:
    if pop <= 2:
        return "barely clinging to existence"
    if pop <= 5:
        return "a fragile handful"
    if pop <= 15:
        return "a small community"
    if pop <= 30:
        return "a growing settlement"
    if pop <= 60:
        return "a thriving colony"
    if pop <= 100:
        return "a substantial civilisation"
    return "a vast society"


def _trend_word(delta: float) -> str:
    if delta > 20:
        return "surged"
    if delta > 5:
        return "grew"
    if delta > 0:
        return "edged up slightly"
    if delta == 0:
        return "held steady"
    if delta > -5:
        return "dipped slightly"
    if delta > -20:
        return "declined"
    return "plummeted"


def _energy_health(avg_energy: float, max_energy: float = 150.0) -> str:
    ratio = avg_energy / max(max_energy, 1)
    if ratio > 0.7:
        return "well-fed and energetic"
    if ratio > 0.4:
        return "maintaining adequate reserves"
    if ratio > 0.2:
        return "running lean on energy"
    return "starving and desperate"


def _brain_description(avg_nodes: float, avg_conns: float) -> str:
    if avg_nodes < 10:
        return "simple reflexive"
    if avg_nodes < 20:
        return "developing"
    if avg_nodes < 35:
        return "moderately complex"
    if avg_nodes < 60:
        return "sophisticated"
    return "highly complex"


def generate_chapter(tick_end: int) -> Optional[str]:
    """
    Generate a story chapter covering the most recent STORY_CHAPTER_EVERY ticks.
    Returns the chapter content, or None if insufficient data.
    Stores the chapter in the database.
    """
    chapter_num = (tick_end // STORY_CHAPTER_EVERY) - 1
    tick_start = tick_end - STORY_CHAPTER_EVERY

    # Don't regenerate existing chapters
    conn = get_connection()
    existing = conn.execute(
        "SELECT chapter FROM story_chapters WHERE chapter = ?",
        (chapter_num,),
    ).fetchone()
    if existing:
        return None

    # Get data at start and end of chapter period
    stats_start = _get_stats_at(tick_start)
    stats_end = _get_stats_at(tick_end)

    if stats_end is None:
        return None

    # Defaults for start stats (very first chapter)
    if stats_start is None:
        stats_start = {
            "population": cfg.INITIAL_AGENT_COUNT,
            "total_births": 0,
            "total_deaths": 0,
            "avg_energy": 100.0,
            "avg_entropy": 0.0,
            "avg_age": 0,
            "max_generation": 0,
            "avg_cortex_size": 0,
            "substrate_energy": 0,
        }

    brain_end = _get_brain_stats_at(tick_end)
    brain_start = _get_brain_stats_at(tick_start)
    births_this_chapter = int(stats_end.get("total_births", 0)) - int(stats_start.get("total_births", 0))
    deaths_this_chapter = int(stats_end.get("total_deaths", 0)) - int(stats_start.get("total_deaths", 0))
    macros_discovered = _count_events_in_range(tick_start, tick_end, "macro_discovered")
    species_count = _count_species_at(tick_end)
    comms_end = _get_comms_at(tick_end)
    comms_start = _get_comms_at(tick_start)

    pop_start = int(stats_start.get("population", 0))
    pop_end = int(stats_end.get("population", 0))
    pop_delta = pop_end - pop_start
    avg_energy = stats_end.get("avg_energy", 0)
    avg_entropy = stats_end.get("avg_entropy", 0)
    avg_age = stats_end.get("avg_age", 0)
    max_gen = int(stats_end.get("max_generation", 0))
    avg_cortex = stats_end.get("avg_cortex_size", 0)

    # ── Build narrative paragraphs ────────────────────────────────────────
    paragraphs: List[str] = []

    # Opening
    title = _get_title(chapter_num)
    time_desc = f"Ticks {tick_start + 1:,} to {tick_end:,}"

    # Population paragraph
    pop_trend = _trend_word(pop_delta)
    pop_desc = _pop_description(pop_end)
    if chapter_num == 0:
        paragraphs.append(
            f"The world awakened with {pop_start} agents on a network of "
            f"{cfg.SUBSTRATE_NUM_NODES} interconnected nodes. "
            f"Over this first epoch, the population {pop_trend} to {pop_end} — "
            f"{pop_desc}. "
            f"There were {births_this_chapter} births and {deaths_this_chapter} deaths."
        )
    else:
        paragraphs.append(
            f"The population {pop_trend} from {pop_start} to {pop_end} — "
            f"{pop_desc}. "
            f"This epoch saw {births_this_chapter} births and {deaths_this_chapter} deaths"
            f"{', a net gain of ' + str(pop_delta) if pop_delta > 0 else ', a net loss of ' + str(abs(pop_delta)) if pop_delta < 0 else ', perfectly balanced'}."
        )

    # Generational progress
    gen_start = int(stats_start.get("max_generation", 0))
    if max_gen > gen_start:
        paragraphs.append(
            f"Generational depth advanced from {gen_start} to {max_gen}. "
            f"New lineages are emerging as the genetic code diversifies through "
            f"crossover and mutation. The average agent lives to age {avg_age:.0f}."
        )
    elif max_gen > 0:
        paragraphs.append(
            f"The civilisation remains at generation {max_gen}. "
            f"The average agent lives to age {avg_age:.0f}, "
            f"{'a testament to their evolved survival strategies.' if avg_age > 100 else 'still learning the ways of this world.'}"
        )

    # Energy & survival
    health = _energy_health(avg_energy)
    paragraphs.append(
        f"Agents are {health}, with an average energy of {avg_energy:.1f} "
        f"and entropy of {avg_entropy:.1f}. "
        f"The world holds {stats_end.get('substrate_energy', 0):,.0f} units of ambient energy."
    )

    # Brain complexity
    if brain_end:
        avg_n = brain_end.get("avg_nodes", 0)
        avg_c = brain_end.get("avg_connections", 0)
        max_n = brain_end.get("max_nodes", 0)
        max_c = brain_end.get("max_connections", 0)
        cost = brain_end.get("avg_metabolic_cost", 0)
        desc = _brain_description(avg_n, avg_c)

        brain_grew = False
        if brain_start:
            old_n = brain_start.get("avg_nodes", 0)
            old_c = brain_start.get("avg_connections", 0)
            if avg_n > old_n * 1.1:
                brain_grew = True

        if brain_grew:
            paragraphs.append(
                f"Neural architecture is evolving rapidly. "
                f"Brains now average {avg_n:.0f} neurons and {avg_c:.0f} connections — "
                f"{desc} networks. "
                f"The most complex brain has {max_n} neurons and {max_c} connections. "
                f"This cognitive machinery costs {cost:.2f} energy per tick to run."
            )
        else:
            paragraphs.append(
                f"Brains average {avg_n:.0f} neurons and {avg_c:.0f} connections — "
                f"{desc} networks. "
                f"The most complex brain has {max_n} neurons with {max_c} connections, "
                f"costing {cost:.2f} energy per tick to maintain."
            )

    # Species & diversity
    if species_count > 0:
        if species_count == 1:
            paragraphs.append(
                "All agents belong to a single species — "
                "genetic diversity is low, and the population is homogeneous."
            )
        elif species_count <= 3:
            paragraphs.append(
                f"The population has split into {species_count} distinct species. "
                f"Early diversification is underway as different survival strategies emerge."
            )
        else:
            paragraphs.append(
                f"A rich ecosystem of {species_count} species now coexists. "
                f"Each has evolved distinct brain architectures and behavioral profiles."
            )

    # Learning & innovation
    if avg_cortex > 0:
        cortex_msg = f"Agents carry an average of {avg_cortex:.0f} learned associations in their cortex"
        if macros_discovered > 0:
            cortex_msg += (
                f", and {macros_discovered} new motor patterns were discovered this epoch — "
                f"compound behaviours that chain basic actions into efficient routines."
            )
        else:
            cortex_msg += "."
        paragraphs.append(cortex_msg)

    # Communication
    if comms_end:
        signals_end_total = int(comms_end.get("total_deliveries", 0))
        signals_start_total = int(comms_start.get("total_deliveries", 0)) if comms_start else 0
        signals_this_chapter = signals_end_total - signals_start_total
        if signals_this_chapter > 0:
            senders = int(comms_end.get("unique_senders", 0))
            paragraphs.append(
                f"Communication channels carried {signals_this_chapter:,} signal deliveries this epoch. "
                f"{senders} agents are actively broadcasting through evolved neural channels, "
                f"though what meaning these signals carry — if any — is for the agents alone to know."
            )
        elif chapter_num > 2:
            paragraphs.append(
                "The airwaves remain quiet. Agents have not yet found a reason "
                "to invest energy in broadcasting signals."
            )

    # Closing / outlook
    if pop_end <= 2:
        paragraphs.append(
            "The civilisation teeters on the edge of extinction. "
            "Only a few souls remain to carry forward whatever has been learned."
        )
    elif pop_delta > 10:
        paragraphs.append(
            "The trajectory is promising — growth continues, "
            "and the agents appear to be finding their footing in this world."
        )
    elif pop_delta < -10:
        paragraphs.append(
            "The decline raises questions about sustainability. "
            "Can they adapt before it's too late?"
        )
    else:
        if chapter_num < 3:
            paragraphs.append("The story of this civilisation is only beginning.")
        else:
            paragraphs.append(
                "Life continues on the network — neither flourishing nor failing, "
                "but evolving, one tick at a time."
            )

    content = "\n\n".join(paragraphs)

    # Store in DB
    conn.execute(
        "INSERT OR REPLACE INTO story_chapters (chapter, tick_start, tick_end, title, content) "
        "VALUES (?, ?, ?, ?, ?)",
        (chapter_num, tick_start + 1, tick_end, title, content),
    )
    conn.commit()

    return content


def save_substrate_topology(substrate: Any) -> None:
    """
    Store the substrate graph topology in simulation_meta for dashboard visualization.
    Called once at simulation start.
    """
    nodes_data = []
    edges_set = set()

    for nid, node in substrate.nodes.items():
        nodes_data.append({
            "id": nid,
            "x": round(node.vis_x, 2),
            "y": round(node.vis_y, 2),
            "degree": node.degree,
        })
        for neighbor_id in node.neighbors:
            edge = (min(nid, neighbor_id), max(nid, neighbor_id))
            edges_set.add(edge)

    edges_data = [list(e) for e in sorted(edges_set)]

    topology = json.dumps({
        "nodes": nodes_data,
        "edges": edges_data,
        "num_nodes": len(nodes_data),
        "num_edges": len(edges_data),
    })

    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO simulation_meta (key, value) VALUES (?, ?)",
        ("substrate_topology", topology),
    )
    conn.commit()

