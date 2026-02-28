"""
Story Generator — creates plain-English narrative chapters from simulation data.

Every STORY_CHAPTER_EVERY ticks, a new chapter is generated summarising what
happened during that period.  No LLM required — the text is template-driven
with varied phrasing, narrative memory across chapters, milestone detection,
and agent spotlights.

Chapters are stored in the story_chapters table and displayed on the dashboard.
"""

from __future__ import annotations

import json
import math
import random as _random_module
from typing import Optional, Dict, Any, List, Tuple

from persistence.db import get_connection
import config as cfg

# ── Configuration ─────────────────────────────────────────────────────────────
STORY_CHAPTER_EVERY = 50000  # Generate a chapter every N ticks


# ── Template banks ────────────────────────────────────────────────────────────
# Each bank has 4-6 variants.  _pick() selects one at random and formats it.

_POP_FIRST_EPOCH = [
    "The world awakened with {pop_start} agents scattered across a network of {num_nodes:,} interconnected nodes. Over this first epoch, the population {trend} to {pop_end} — {desc}. There were {births} births and {deaths} deaths.",
    "Life began with {pop_start} agents on a graph of {num_nodes:,} nodes. By epoch's end the population had {trend} to {pop_end}, {desc}. {births} were born; {deaths} perished.",
    "{pop_start} agents opened their eyes on a substrate of {num_nodes:,} nodes. The population {trend} to {pop_end} during this founding epoch — {desc} — with {births} births and {deaths} deaths.",
    "The simulation sparked to life: {pop_start} agents, {num_nodes:,} nodes, and nothing but physics. By tick {tick_end:,} the count had {trend} to {pop_end} ({desc}), after {births} births and {deaths} deaths.",
    "Genesis: {pop_start} agents materialized across {num_nodes:,} nodes. The first epoch saw the population {trend} to {pop_end} — {desc}. {births} new agents were born, {deaths} were lost.",
]

_POP_GROWTH = [
    "The population {trend} from {pop_start} to {pop_end} — {desc}. This epoch saw {births} births against {deaths} deaths, a net gain of {delta}.",
    "Numbers climbed: {pop_start} at the epoch's dawn, {pop_end} at its close — {desc}. {births} births, {deaths} deaths, net +{delta}.",
    "Growth continued as the population {trend} from {pop_start} to {pop_end}. With {births} births outpacing {deaths} deaths, the world gained {delta} agents.",
    "The colony expanded from {pop_start} to {pop_end} ({desc}). {births} new agents entered the world while {deaths} departed — a surplus of {delta}.",
    "Reproduction outran mortality: the population {trend} from {pop_start} to {pop_end}, adding {delta} agents net across {births} births and {deaths} deaths.",
]

_POP_DECLINE = [
    "The population {trend} from {pop_start} to {pop_end} — {desc}. {deaths} deaths outnumbered {births} births, a net loss of {abs_delta}.",
    "Numbers fell: from {pop_start} down to {pop_end} — {desc}. {births} births could not offset {deaths} deaths, leaving a deficit of {abs_delta}.",
    "A difficult epoch. The population {trend} from {pop_start} to {pop_end}, losing {abs_delta} agents net. {births} were born, {deaths} died.",
    "Decline set in as the count dropped from {pop_start} to {pop_end} ({desc}). With {deaths} deaths against only {births} births, {abs_delta} agents were lost.",
    "Mortality prevailed: {deaths} deaths to {births} births. The population {trend} from {pop_start} to {pop_end}, shedding {abs_delta} agents.",
]

_POP_STABLE = [
    "The population held roughly steady at {pop_end} — {desc}. {births} births and {deaths} deaths kept things in balance.",
    "Little changed in headcount: {pop_start} at the start, {pop_end} at the end — {desc}. {births} births, {deaths} deaths.",
    "Equilibrium prevailed. The population remained near {pop_end} ({desc}), with {births} births balancing {deaths} deaths.",
    "Stability defined this epoch: the population hovered around {pop_end}, {desc}. Births ({births}) and deaths ({deaths}) nearly cancelled out.",
    "A steady epoch. The count barely moved from {pop_start} to {pop_end} — {desc}. {births} arrived, {deaths} departed.",
]

_GEN_ADVANCE = [
    "Generational depth advanced from {gen_start} to {gen_end}. New lineages are diversifying through crossover and mutation. The average agent lives to age {avg_age:.0f}.",
    "Evolution pushed generations from {gen_start} to {gen_end}. The genetic code is branching as agents reproduce and mutate, with a typical lifespan of {avg_age:.0f} ticks.",
    "The generational frontier reached {gen_end}, up from {gen_start}. Each new generation carries mutations that may — or may not — serve it well. Average age: {avg_age:.0f}.",
    "Generations climbed from {gen_start} to {gen_end}. Crossover is shuffling the genome in new ways. Agents live {avg_age:.0f} ticks on average.",
    "From generation {gen_start} to {gen_end}: the lineage tree grows deeper. Average lifespan stands at {avg_age:.0f} ticks.",
]

_GEN_STABLE = [
    "The civilisation remains at generation {gen_end}. The average agent lives to age {avg_age:.0f}{age_comment}.",
    "Generational depth holds at {gen_end} — no new lineages this epoch. Average age: {avg_age:.0f}{age_comment}.",
    "Still generation {gen_end}. Reproduction hasn't pushed the frontier further. Agents average {avg_age:.0f} ticks of age{age_comment}.",
    "The generational ceiling stayed at {gen_end}. Average lifespan: {avg_age:.0f} ticks{age_comment}.",
]

_BRAIN_GROWING = [
    "Neural architecture is evolving rapidly. Brains now average {avg_n:.0f} neurons and {avg_c:.0f} connections — {desc} networks. The most complex brain has {max_n} neurons and {max_c} connections, costing {cost:.2f} energy per tick.",
    "Brains are getting bigger: {avg_n:.0f} neurons and {avg_c:.0f} connections on average ({desc}). Peak complexity: {max_n} neurons, {max_c} connections. Metabolic cost: {cost:.2f}/tick.",
    "Cognitive complexity surged. Average brains carry {avg_n:.0f} neurons and {avg_c:.0f} connections ({desc}), with the largest reaching {max_n} neurons. The thinking tax: {cost:.2f} energy per tick.",
    "Evolution is building bigger brains — {avg_n:.0f} neurons and {avg_c:.0f} connections on average, {desc} in complexity. The champion brain holds {max_n} neurons at a cost of {cost:.2f}/tick.",
    "Neural growth continued: averages reached {avg_n:.0f} neurons / {avg_c:.0f} connections ({desc}). Maximum brain: {max_n} neurons, {max_c} connections, burning {cost:.2f} energy per tick.",
]

_BRAIN_STABLE = [
    "Brains average {avg_n:.0f} neurons and {avg_c:.0f} connections — {desc} networks. The most complex brain has {max_n} neurons with {max_c} connections, costing {cost:.2f} energy per tick.",
    "Neural architecture held steady: {avg_n:.0f} neurons, {avg_c:.0f} connections on average ({desc}). Peak brain: {max_n} neurons, {max_c} connections. Cost: {cost:.2f}/tick.",
    "Brain complexity plateaued at {avg_n:.0f} neurons / {avg_c:.0f} connections ({desc}). The largest brain carries {max_n} neurons for {cost:.2f} energy per tick.",
    "Cognitive structure is stable: {avg_n:.0f} neurons, {avg_c:.0f} connections ({desc}). Maximum: {max_n}n/{max_c}c. Metabolic overhead: {cost:.2f}/tick.",
]

_SPECIES_MONO = [
    "All agents belong to a single species — genetic diversity is low and the population is homogeneous.",
    "One species, one gene pool. The population remains genetically uniform.",
    "Speciation has not occurred: every agent belongs to the same genetic cluster.",
    "The world holds a single species. Diversity may yet come — or this uniformity may be its own advantage.",
]

_SPECIES_FEW = [
    "The population has split into {n} distinct species. Early diversification is underway as different survival strategies emerge.",
    "{n} species now coexist, each exploring a different corner of the fitness landscape.",
    "Speciation has begun: {n} species, each evolving its own brain architecture and behavioral profile.",
    "The gene pool fractured into {n} species. Competition between strategies is heating up.",
]

_SPECIES_MANY = [
    "A rich ecosystem of {n} species now coexists. Each has evolved distinct brain architectures and behavioral profiles.",
    "{n} species populate the substrate — a diverse ecosystem of competing survival strategies.",
    "Biodiversity is high: {n} species, each with unique neural wiring and drive configurations.",
    "The world teems with {n} species. Evolutionary experimentation is in full swing.",
]

_ENERGY_TEMPLATES = [
    "Agents are {health}, with an average energy of {avg_energy:.1f} and entropy of {avg_entropy:.1f}. The world holds {substrate_energy:,.0f} units of ambient energy.",
    "Average energy stands at {avg_energy:.1f} (agents are {health}), with entropy at {avg_entropy:.1f}. Substrate energy: {substrate_energy:,.0f}.",
    "The population is {health}: {avg_energy:.1f} average energy, {avg_entropy:.1f} average entropy. The substrate provides {substrate_energy:,.0f} total energy.",
    "Energy levels paint a picture of agents {health} — averaging {avg_energy:.1f} energy and {avg_entropy:.1f} entropy across {substrate_energy:,.0f} units of world energy.",
]

_COMMS_ACTIVE = [
    "Communication channels carried {signals:,} signal deliveries this epoch. {senders} agents are actively broadcasting through evolved neural channels, though what meaning these signals carry — if any — is for the agents alone to know.",
    "{signals:,} signals were delivered this epoch by {senders} active broadcasters. The content is brain-driven — evolved, not designed.",
    "The airwaves buzzed with {signals:,} signal deliveries from {senders} senders. Whether these broadcasts carry genuine information or are just neural noise remains an open question.",
    "{senders} agents broadcast signals totalling {signals:,} deliveries. The evolved broadcast channels hum with activity whose meaning, if any, belongs to the agents.",
    "Signal traffic reached {signals:,} deliveries from {senders} broadcasters. Communication bandwidth is being used, but its semantic content — if it exists — emerged through evolution, not engineering.",
]

_COMMS_SILENT = [
    "The airwaves remain quiet. Agents have not yet found a reason to invest energy in broadcasting signals.",
    "Communication stayed dormant this epoch. Broadcasting costs energy, and evolution hasn't yet rewarded it.",
    "No significant signal activity. The agents keep their neural broadcasts to themselves — or haven't evolved the circuitry to use them.",
    "Silence on the broadcast channels. Perhaps communication will emerge when the selection pressure is right.",
]

_CLOSING_GOOD = [
    "The trajectory is promising — growth continues, and the agents appear to be finding their footing in this world.",
    "Things are looking up. The population grows, brains evolve, and the substrate provides.",
    "A strong epoch. The colony is expanding and adapting, one mutation at a time.",
    "The arc bends toward prosperity. Whether it lasts remains to be seen.",
    "Momentum builds. The agents are carving out niches and filling them.",
]

_CLOSING_BAD = [
    "The decline raises questions about sustainability. Can they adapt before it's too late?",
    "Dark times. The population shrinks and the future is uncertain.",
    "Survival is not guaranteed. The agents face mounting pressure with dwindling numbers.",
    "The outlook is grim. Without adaptation, extinction looms.",
    "A troubled epoch. The colony struggles against forces it may not overcome.",
]

_CLOSING_NEUTRAL = [
    "Life continues on the network — neither flourishing nor failing, but evolving, one tick at a time.",
    "The world turns. Neither boom nor bust — just the steady grind of evolution.",
    "Stability, for now. The agents persist, adapting at the margins.",
    "Another epoch passes. The simulation hums along its course.",
    "The story continues — no climax, no crisis, just the quiet work of natural selection.",
]

_CLOSING_EARLY = [
    "The story of this civilisation is only beginning.",
    "Early days. Everything that follows will build on what happened here.",
    "The foundation is laid. What the agents make of it is up to evolution.",
    "A young world finding its rhythm. The real story hasn't started yet.",
]

# Milestone-specific templates
_MILESTONE_POP_HIGH = [
    "A new all-time population record was set: {value} agents alive simultaneously.",
    "Population reached an unprecedented {value} — the highest count in the simulation's history.",
    "History was made: {value} agents coexisted, surpassing all previous peaks.",
]

_MILESTONE_POP_LOW = [
    "The population touched a historic low of {value} during this epoch — the closest to extinction yet.",
    "A near-extinction event: the count dropped to just {value}, the lowest on record.",
    "Dark waters: the population hit {value}, its all-time minimum, before recovering.",
]

_MILESTONE_FIRST_SPECIATION = [
    "For the first time, the population split into multiple species — a landmark in the simulation's evolutionary history.",
    "Speciation occurred for the first time. The once-uniform gene pool has fractured.",
    "A watershed moment: the first species divergence. Evolution has found more than one way to survive.",
]

_MILESTONE_GEN_RECORD = [
    "A new generational record was reached: generation {value}. The lineage tree grows ever deeper.",
    "Generation {value} — the deepest lineage yet. Each generation carries the accumulated mutations of all its ancestors.",
    "The generational frontier pushed to {value}, a new record for evolutionary depth.",
]

_MILESTONE_BRAIN_RECORD = [
    "A brain complexity record was broken: {value} neurons in a single agent's neural network.",
    "The most complex brain ever observed: {value} neurons. Cognitive evolution is accelerating.",
    "Record-breaking neural architecture: one agent grew a brain with {value} neurons.",
]

_MILESTONE_FIRST_COMMS = [
    "Signals were transmitted for the first time. Agents have begun using their evolved broadcast channels.",
    "A first: agents broadcast signals across the substrate. Communication has entered the world.",
    "The first signal deliveries were recorded. Whether this marks the dawn of meaningful communication remains to be seen.",
]

_MILESTONE_FIRST_MACRO = [
    "The first motor pattern was discovered — an agent detected a repeating sequence in its own behavior and promoted it to a compound action.",
    "A behavioral milestone: the first compound action was invented. An agent found a useful sequence and remembered it.",
    "Motor pattern discovery began. Agents are starting to build behavioral routines from raw effector sequences.",
]

_MILESTONE_NEAR_EXTINCTION = [
    "The population dropped to {value} during this epoch before recovering — a brush with extinction.",
    "Near-extinction: the count fell to just {value} before births restored numbers. A close call.",
    "Survival was in doubt when the population cratered to {value}, but the colony clawed its way back.",
]

# Narrative memory templates (cross-chapter references)
_NARRATIVE_CONTINUED_GROWTH = [
    "For the {streak_word} epoch running, the population is growing.",
    "Growth continues for the {streak_word} consecutive epoch.",
    "The growth streak extends to {streak} epochs.",
]

_NARRATIVE_CONTINUED_DECLINE = [
    "For the {streak_word} epoch running, the population is shrinking.",
    "The decline continues — {streak} epochs of falling numbers now.",
    "Another epoch of losses, the {streak_word} in a row.",
]

_NARRATIVE_RECOVERY = [
    "After last epoch's decline, the population has bounced back.",
    "Recovery: the downward trend reversed, and numbers are climbing again.",
    "The colony rallied after the previous epoch's losses.",
]

_NARRATIVE_REVERSAL_DOWN = [
    "After last epoch's growth, the population has turned downward.",
    "The growth streak ended. Numbers fell this epoch after previously rising.",
    "A reversal: last epoch's gains gave way to losses.",
]

_NARRATIVE_POST_CRISIS = [
    "After last epoch's brush with extinction, the colony is rebuilding.",
    "The near-extinction event of the previous epoch still casts a shadow, but numbers are stabilizing.",
    "Recovery from the crisis continues. The population is finding its feet again.",
]

# Spotlight templates
_SPOTLIGHT_OLDEST = [
    "Agent-{agent_id}, now {age} ticks old, is the longest-lived agent in the world — a survivor from generation {gen}.",
    "The elder of the colony is Agent-{agent_id}, generation {gen}, at {age} ticks old and still going.",
    "Agent-{agent_id} has endured for {age} ticks (generation {gen}), making it the oldest living agent.",
]

_SPOTLIGHT_HIGHEST_GEN = [
    "Agent-{agent_id} carries the deepest lineage: generation {gen}, the product of {gen} rounds of mutation and crossover.",
    "The most evolved agent is Agent-{agent_id}, generation {gen} — the endpoint of a long chain of ancestors.",
    "Generation {gen}: Agent-{agent_id} stands at the leading edge of the evolutionary frontier.",
]

_SPOTLIGHT_PROLIFIC = [
    "Agent-{agent_id} was the most prolific parent this epoch, producing {offspring} offspring.",
    "The busiest reproducer: Agent-{agent_id}, with {offspring} children born this epoch.",
    "Agent-{agent_id} spawned {offspring} new agents this epoch — the most of any parent.",
]

_SPOTLIGHT_CORTEX = [
    "Agent-{agent_id} has the largest cortex with {cortex} learned associations — the most experienced reflex system in the population.",
    "The most learned agent: Agent-{agent_id}, with {cortex} cortex entries. Experience has been a good teacher.",
    "Agent-{agent_id}'s cortex holds {cortex} associations, the largest reflex memory in the colony.",
]

# Dynamic title pools
_TITLES_GROWTH = [
    "Expansion", "Rising Tide", "Ascent", "Proliferation", "The Climb",
    "Growing Stronger", "Momentum", "Upswing", "Surge", "Flourishing",
]

_TITLES_DECLINE = [
    "Decline", "Ebb Tide", "Under Pressure", "The Contraction", "Thinning Ranks",
    "Hard Times", "Retreat", "Fading", "The Downturn", "Erosion",
]

_TITLES_MILESTONE = [
    "Breakthrough", "A First", "New Territory", "The Record", "Uncharted",
    "Landmark", "Turning Point", "Watershed", "The Frontier", "Discovery",
]

_TITLES_GENERAL = [
    "Another Epoch", "The Long Game", "Steady State", "Persistence",
    "Continuity", "The Middle Road", "Cycles", "Equilibrium", "Onward",
    "Deep Roots", "Adaptation", "The Current", "Holding Pattern",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pick(templates: List[str], rng: _random_module.Random, **kwargs: Any) -> str:
    """Select a random template and format it with kwargs."""
    return rng.choice(templates).format(**kwargs)


def _streak_word(n: int) -> str:
    words = {2: "second", 3: "third", 4: "fourth", 5: "fifth",
             6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth"}
    return words.get(n, f"{n}th")


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


# ── Data queries ──────────────────────────────────────────────────────────────

def _get_stats_at(tick: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM population_stats WHERE tick <= ? ORDER BY tick DESC LIMIT 1",
        (tick,),
    ).fetchone()
    return dict(row) if row else None


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
    # Find the nearest tick with species data
    row = conn.execute(
        "SELECT COUNT(DISTINCT species_id) as c FROM species_stats "
        "WHERE tick = (SELECT MAX(tick) FROM species_stats WHERE tick <= ?)",
        (tick,),
    ).fetchone()
    return row["c"] if row else 0


def _get_comms_at(tick: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM comms_stats WHERE tick <= ? ORDER BY tick DESC LIMIT 1",
        (tick,),
    ).fetchone()
    return dict(row) if row else None


# ── Narrative memory ──────────────────────────────────────────────────────────

def _get_chapter_history() -> List[Dict[str, Any]]:
    """Get all previous chapters with their associated population data."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT chapter, tick_start, tick_end FROM story_chapters ORDER BY chapter"
    ).fetchall()
    history = []
    for r in rows:
        ch = dict(r)
        stats = _get_stats_at(ch["tick_end"])
        ch["pop_end"] = int(stats["population"]) if stats else 0
        history.append(ch)
    return history


def _build_narrative_context(history: List[Dict[str, Any]], pop_end: int) -> Dict[str, Any]:
    """Compute narrative context from chapter history."""
    ctx: Dict[str, Any] = {
        "streak_dir": None,   # "up" / "down" / None
        "streak_len": 0,
        "was_crisis": False,  # True if last chapter pop was <= 2
        "prev_delta": None,   # pop delta of previous chapter
    }
    if len(history) < 1:
        return ctx

    # Previous chapter's population
    prev_pop = history[-1]["pop_end"]
    if len(history) >= 2:
        prev_prev_pop = history[-2]["pop_end"]
        ctx["prev_delta"] = prev_pop - prev_prev_pop
    ctx["was_crisis"] = prev_pop <= 2

    # Compute current streak
    pops = [h["pop_end"] for h in history] + [pop_end]
    streak = 0
    direction = None
    for i in range(len(pops) - 1, 0, -1):
        delta = pops[i] - pops[i - 1]
        if delta > 0:
            d = "up"
        elif delta < 0:
            d = "down"
        else:
            break
        if direction is None:
            direction = d
        if d == direction:
            streak += 1
        else:
            break

    ctx["streak_dir"] = direction
    ctx["streak_len"] = streak
    return ctx


def _narrative_memory_paragraph(
    ctx: Dict[str, Any], pop_delta: int, rng: _random_module.Random,
) -> Optional[str]:
    """Generate a cross-chapter reference paragraph, if warranted."""
    # Post-crisis recovery
    if ctx["was_crisis"] and pop_delta > 0:
        return _pick(_NARRATIVE_POST_CRISIS, rng)

    # Continued growth/decline streaks (only mention if >= 2 epochs)
    if ctx["streak_len"] >= 2:
        sw = _streak_word(ctx["streak_len"])
        if ctx["streak_dir"] == "up":
            return _pick(_NARRATIVE_CONTINUED_GROWTH, rng,
                         streak=ctx["streak_len"], streak_word=sw)
        if ctx["streak_dir"] == "down":
            return _pick(_NARRATIVE_CONTINUED_DECLINE, rng,
                         streak=ctx["streak_len"], streak_word=sw)

    # Direction reversal
    if ctx["prev_delta"] is not None:
        if ctx["prev_delta"] > 0 and pop_delta < -2:
            return _pick(_NARRATIVE_REVERSAL_DOWN, rng)
        if ctx["prev_delta"] < 0 and pop_delta > 2:
            return _pick(_NARRATIVE_RECOVERY, rng)

    return None


# ── Milestone detection ───────────────────────────────────────────────────────

def _detect_milestones(
    tick_start: int, tick_end: int,
    stats_end: Dict[str, Any],
    brain_end: Optional[Dict[str, Any]],
    species_count: int,
    comms_end: Optional[Dict[str, Any]],
) -> List[str]:
    """Detect notable firsts and records during this epoch. Returns milestone sentences."""
    conn = get_connection()
    milestones: List[str] = []
    rng = _random_module.Random(tick_end)  # deterministic per chapter

    pop_end = int(stats_end.get("population", 0))

    # All-time population high
    row = conn.execute(
        "SELECT MAX(population) as m FROM population_stats WHERE tick < ?",
        (tick_start,),
    ).fetchone()
    prev_max_pop = row["m"] if row and row["m"] is not None else 0
    if pop_end > prev_max_pop and pop_end > cfg.INITIAL_AGENT_COUNT:
        milestones.append(_pick(_MILESTONE_POP_HIGH, rng, value=pop_end))

    # Near-extinction recovery (pop hit <= 2 during this epoch but recovered)
    row = conn.execute(
        "SELECT MIN(population) as m FROM population_stats WHERE tick > ? AND tick <= ?",
        (tick_start, tick_end),
    ).fetchone()
    min_pop_epoch = row["m"] if row and row["m"] is not None else pop_end
    if min_pop_epoch <= 2 and pop_end > 5:
        milestones.append(_pick(_MILESTONE_NEAR_EXTINCTION, rng, value=min_pop_epoch))

    # All-time population low (only after the first epoch)
    if tick_start > 0 and pop_end > 0:
        row = conn.execute(
            "SELECT MIN(population) as m FROM population_stats WHERE tick < ? AND population > 0",
            (tick_start,),
        ).fetchone()
        prev_min_pop = row["m"] if row and row["m"] is not None else pop_end
        if pop_end < prev_min_pop and pop_end <= 5:
            milestones.append(_pick(_MILESTONE_POP_LOW, rng, value=pop_end))

    # First speciation ever
    if species_count > 1:
        row = conn.execute(
            "SELECT COUNT(DISTINCT species_id) as c FROM species_stats WHERE tick < ?",
            (tick_start,),
        ).fetchone()
        prev_species = row["c"] if row else 0
        if prev_species <= 1:
            milestones.append(_pick(_MILESTONE_FIRST_SPECIATION, rng))

    # Generation record
    max_gen = int(stats_end.get("max_generation", 0))
    if max_gen > 0:
        row = conn.execute(
            "SELECT MAX(max_generation) as m FROM population_stats WHERE tick < ?",
            (tick_start,),
        ).fetchone()
        prev_max_gen = row["m"] if row and row["m"] is not None else 0
        if max_gen > prev_max_gen and max_gen > 1:
            milestones.append(_pick(_MILESTONE_GEN_RECORD, rng, value=max_gen))

    # Brain complexity record
    if brain_end:
        max_n = brain_end.get("max_nodes", 0)
        if max_n > 0:
            row = conn.execute(
                "SELECT MAX(max_nodes) as m FROM brain_stats WHERE tick < ?",
                (tick_start,),
            ).fetchone()
            prev_max_nodes = row["m"] if row and row["m"] is not None else 0
            if max_n > prev_max_nodes * 1.2 and prev_max_nodes > 0:
                milestones.append(_pick(_MILESTONE_BRAIN_RECORD, rng, value=max_n))

    # First communication ever
    if comms_end and int(comms_end.get("total_deliveries", 0)) > 0:
        row = conn.execute(
            "SELECT MAX(total_deliveries) as m FROM comms_stats WHERE tick < ?",
            (tick_start,),
        ).fetchone()
        prev_deliveries = row["m"] if row and row["m"] is not None else 0
        if (prev_deliveries is None or prev_deliveries == 0):
            milestones.append(_pick(_MILESTONE_FIRST_COMMS, rng))

    # First motor pattern ever
    macros_this = _count_events_in_range(tick_start, tick_end, "macro_discovered")
    if macros_this > 0:
        prev_macros = conn.execute(
            "SELECT COUNT(*) as c FROM events WHERE tick <= ? AND event_type = 'macro_discovered'",
            (tick_start,),
        ).fetchone()
        if prev_macros and prev_macros["c"] == 0:
            milestones.append(_pick(_MILESTONE_FIRST_MACRO, rng))

    return milestones


# ── Agent spotlights ──────────────────────────────────────────────────────────

def _query_spotlight_agents(
    tick_end: int, tick_start: int,
) -> Dict[str, Optional[Dict[str, Any]]]:
    """Query notable agents for spotlight paragraphs."""
    conn = get_connection()
    spotlights: Dict[str, Optional[Dict[str, Any]]] = {
        "oldest": None,
        "highest_gen": None,
        "prolific": None,
        "largest_cortex": None,
    }

    # Find the latest snapshot tick
    row = conn.execute(
        "SELECT MAX(tick) as t FROM snapshots WHERE tick <= ? AND alive = 1",
        (tick_end,),
    ).fetchone()
    if not row or row["t"] is None:
        return spotlights
    snap_tick = row["t"]

    # Oldest living agent
    row = conn.execute(
        "SELECT agent_id, age, generation FROM snapshots "
        "WHERE tick = ? AND alive = 1 ORDER BY age DESC LIMIT 1",
        (snap_tick,),
    ).fetchone()
    if row:
        spotlights["oldest"] = {"agent_id": row["agent_id"], "age": row["age"],
                                "gen": row["generation"]}

    # Highest generation alive
    row = conn.execute(
        "SELECT agent_id, generation, age FROM snapshots "
        "WHERE tick = ? AND alive = 1 ORDER BY generation DESC LIMIT 1",
        (snap_tick,),
    ).fetchone()
    if row:
        spotlights["highest_gen"] = {"agent_id": row["agent_id"],
                                     "gen": row["generation"], "age": row["age"]}

    # Most prolific parent this epoch
    row = conn.execute(
        "SELECT parent_a_id as pid, COUNT(*) as cnt FROM lineage "
        "WHERE born_tick > ? AND born_tick <= ? AND parent_a_id >= 0 "
        "GROUP BY parent_a_id ORDER BY cnt DESC LIMIT 1",
        (tick_start, tick_end),
    ).fetchone()
    if row and row["cnt"] >= 2:
        spotlights["prolific"] = {"agent_id": row["pid"], "offspring": row["cnt"]}

    # Largest cortex alive
    row = conn.execute(
        "SELECT agent_id, cortex_size, generation FROM snapshots "
        "WHERE tick = ? AND alive = 1 ORDER BY cortex_size DESC LIMIT 1",
        (snap_tick,),
    ).fetchone()
    if row and row["cortex_size"] and row["cortex_size"] > 0:
        spotlights["largest_cortex"] = {"agent_id": row["agent_id"],
                                        "cortex": row["cortex_size"],
                                        "gen": row["generation"]}

    return spotlights


def _spotlight_paragraph(
    spotlights: Dict[str, Optional[Dict[str, Any]]],
    chapter_num: int,
    rng: _random_module.Random,
) -> Optional[str]:
    """Generate a spotlight paragraph, rotating which type to feature."""
    order = ["oldest", "highest_gen", "prolific", "largest_cortex"]
    templates = {
        "oldest": _SPOTLIGHT_OLDEST,
        "highest_gen": _SPOTLIGHT_HIGHEST_GEN,
        "prolific": _SPOTLIGHT_PROLIFIC,
        "largest_cortex": _SPOTLIGHT_CORTEX,
    }

    # Rotate primary spotlight by chapter number
    primary_idx = chapter_num % len(order)
    # Try primary first, then others
    attempts = [order[(primary_idx + i) % len(order)] for i in range(len(order))]

    parts = []
    for key in attempts:
        data = spotlights.get(key)
        if data and len(parts) < 2:
            parts.append(_pick(templates[key], rng, **data))

    return " ".join(parts) if parts else None


# ── Dynamic titles ────────────────────────────────────────────────────────────

def _generate_title(
    chapter_num: int, pop_delta: int, milestones: List[str],
    rng: _random_module.Random,
) -> str:
    """Generate a chapter title, avoiding recent repeats."""
    conn = get_connection()

    # Choose pool based on epoch character
    if milestones:
        pool = _TITLES_MILESTONE
    elif pop_delta > 5:
        pool = _TITLES_GROWTH
    elif pop_delta < -5:
        pool = _TITLES_DECLINE
    else:
        pool = _TITLES_GENERAL

    # Get recent titles to avoid repeats
    rows = conn.execute(
        "SELECT title FROM story_chapters ORDER BY chapter DESC LIMIT 5"
    ).fetchall()
    recent = {r["title"] for r in rows}

    # Try to pick a non-repeated title
    candidates = [t for t in pool if t not in recent]
    if not candidates:
        candidates = pool  # all repeated — just pick any

    return rng.choice(candidates)


# ── Main chapter generation ──────────────────────────────────────────────────

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

    # Query data at chapter boundaries
    stats_start = _get_stats_at(tick_start)
    stats_end = _get_stats_at(tick_end)

    if stats_end is None:
        return None

    if stats_start is None:
        stats_start = {
            "population": cfg.INITIAL_AGENT_COUNT,
            "total_births": 0, "total_deaths": 0,
            "avg_energy": 100.0, "avg_entropy": 0.0,
            "avg_age": 0, "max_generation": 0,
            "avg_cortex_size": 0, "substrate_energy": 0,
        }

    brain_end = _get_brain_stats_at(tick_end)
    brain_start = _get_brain_stats_at(tick_start)
    births_this = int(stats_end.get("total_births", 0)) - int(stats_start.get("total_births", 0))
    deaths_this = int(stats_end.get("total_deaths", 0)) - int(stats_start.get("total_deaths", 0))
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

    # Deterministic RNG for reproducible chapter text
    rng = _random_module.Random(tick_end + chapter_num * 7919)

    # Load chapter history and build narrative context
    history = _get_chapter_history()
    narrative_ctx = _build_narrative_context(history, pop_end)

    # Detect milestones
    milestones = _detect_milestones(
        tick_start, tick_end, stats_end, brain_end, species_count, comms_end,
    )

    # Query spotlight agents
    spotlights = _query_spotlight_agents(tick_end, tick_start)

    # ── Build paragraphs ──────────────────────────────────────────────────
    paragraphs: List[str] = []

    # Narrative memory (cross-chapter reference) — leads the chapter
    if chapter_num > 0:
        mem_para = _narrative_memory_paragraph(narrative_ctx, pop_delta, rng)
        if mem_para:
            paragraphs.append(mem_para)

    # Population paragraph
    trend = _trend_word(pop_delta)
    desc = _pop_description(pop_end)
    fmt = dict(
        pop_start=pop_start, pop_end=pop_end, trend=trend, desc=desc,
        births=births_this, deaths=deaths_this, delta=abs(pop_delta),
        abs_delta=abs(pop_delta), num_nodes=cfg.SUBSTRATE_NUM_NODES,
        tick_end=tick_end,
    )

    if chapter_num == 0:
        paragraphs.append(_pick(_POP_FIRST_EPOCH, rng, **fmt))
    elif pop_delta > 2:
        paragraphs.append(_pick(_POP_GROWTH, rng, **fmt))
    elif pop_delta < -2:
        paragraphs.append(_pick(_POP_DECLINE, rng, **fmt))
    else:
        paragraphs.append(_pick(_POP_STABLE, rng, **fmt))

    # Milestones (dedicated paragraph if any)
    if milestones:
        paragraphs.append(" ".join(milestones))

    # Generational progress
    gen_start = int(stats_start.get("max_generation", 0))
    age_comment = (", a testament to their evolved survival strategies"
                   if avg_age > 100 else
                   ", still learning the ways of this world")
    if max_gen > gen_start:
        paragraphs.append(_pick(_GEN_ADVANCE, rng,
                                gen_start=gen_start, gen_end=max_gen, avg_age=avg_age))
    elif max_gen > 0:
        paragraphs.append(_pick(_GEN_STABLE, rng,
                                gen_end=max_gen, avg_age=avg_age, age_comment=age_comment))

    # Energy & survival
    health = _energy_health(avg_energy)
    paragraphs.append(_pick(_ENERGY_TEMPLATES, rng,
                            health=health, avg_energy=avg_energy,
                            avg_entropy=avg_entropy,
                            substrate_energy=stats_end.get("substrate_energy", 0)))

    # Brain complexity
    if brain_end:
        avg_n = brain_end.get("avg_nodes", 0)
        avg_c = brain_end.get("avg_connections", 0)
        max_n = brain_end.get("max_nodes", 0)
        max_c = brain_end.get("max_connections", 0)
        cost = brain_end.get("avg_metabolic_cost", 0)
        bdesc = _brain_description(avg_n, avg_c)

        brain_grew = False
        if brain_start:
            old_n = brain_start.get("avg_nodes", 0)
            if avg_n > old_n * 1.1:
                brain_grew = True

        brain_fmt = dict(avg_n=avg_n, avg_c=avg_c, max_n=max_n, max_c=max_c,
                         cost=cost, desc=bdesc)
        if brain_grew:
            paragraphs.append(_pick(_BRAIN_GROWING, rng, **brain_fmt))
        else:
            paragraphs.append(_pick(_BRAIN_STABLE, rng, **brain_fmt))

    # Species & diversity
    if species_count > 0:
        if species_count == 1:
            paragraphs.append(_pick(_SPECIES_MONO, rng))
        elif species_count <= 3:
            paragraphs.append(_pick(_SPECIES_FEW, rng, n=species_count))
        else:
            paragraphs.append(_pick(_SPECIES_MANY, rng, n=species_count))

    # Agent spotlight
    spot = _spotlight_paragraph(spotlights, chapter_num, rng)
    if spot:
        paragraphs.append(spot)

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
        signals_this = signals_end_total - signals_start_total
        senders = int(comms_end.get("unique_senders", 0))
        if signals_this > 0:
            paragraphs.append(_pick(_COMMS_ACTIVE, rng,
                                    signals=signals_this, senders=senders))
        elif chapter_num > 2:
            paragraphs.append(_pick(_COMMS_SILENT, rng))

    # Closing / outlook
    if pop_end <= 2:
        paragraphs.append(
            "The civilisation teeters on the edge of extinction. "
            "Only a few souls remain to carry forward whatever has been learned."
        )
    elif pop_delta > 10:
        paragraphs.append(_pick(_CLOSING_GOOD, rng))
    elif pop_delta < -10:
        paragraphs.append(_pick(_CLOSING_BAD, rng))
    elif chapter_num < 3:
        paragraphs.append(_pick(_CLOSING_EARLY, rng))
    else:
        paragraphs.append(_pick(_CLOSING_NEUTRAL, rng))

    content = "\n\n".join(paragraphs)

    # Generate dynamic title
    title = _generate_title(chapter_num, pop_delta, milestones, rng)

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
