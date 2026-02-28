# Werld — Project Reference

## Design Philosophy

This is **not** a simulation of the human world. It is a computational ecosystem where autonomous agents evolve their own ways of being. No human-world assumptions are injected: no language, no economy, no society templates. Agents live on an abstract graph, perceive through evolved sensory channels, act through continuous effectors, and communicate through brain-driven broadcasts. Everything — brains, senses, drives, signals, memory, motor patterns, cortex reliance — is evolvable. Natural selection is the only teacher.

The goal is **open-ended evolution**: agents should be able to naturally advance beyond any initial constraints. No part of their cognition is hardcoded. The simulation is designed to run indefinitely on persistent storage.

---

## Project Overview

A Python simulation of autonomous agents that live, perceive, act, reproduce, and evolve on a graph-based substrate. Agents possess **NEAT-style evolvable neural networks**, an optionally-active associative cortex, episodic memory with evolvable parameters, heritable genomes with evolvable drives and I/O dimensions, evolvable sensory processing (64 channels including 19 latent slots), continuous motor effectors with evolvable broadcast bandwidth (up to 16 channels), and the ability to discover compound motor patterns with genome-gated thresholds.

The **Werld Observatory** is a Next.js dashboard providing real-time god-like analysis with 13 sections (Welcome, Methods, Overview, Story, World Map, Population, Evolution, Brain, Intelligence, Ecology, Resources, Communication, Agents), a story generator, world map visualization, pervasive tooltips, and a simulation uptime timer.

The simulation automatically **posts updates to X (Twitter)** every 10,000 ticks via Gemini-generated tweet threads in a nature documentary narrator style. The public dashboard is hosted at **werld.uravshah.com** via Cloudflare Tunnel.

The simulation is written in **pure Python** (no ML frameworks). The dashboard is **Next.js / React / TypeScript** with **Recharts** and **shadcn/ui**, reading from the same SQLite database.

---

## Naming

- **Project name**: Werld
- **Platform name**: Werld Observatory
- **Public URL**: `https://werld.uravshah.com`
- **Hosting**: Cloudflare Tunnel routing `werld.uravshah.com` → `localhost:3000` (dashboard runs locally from hard drive)
- **X account**: Posts automated tweet threads summarising each epoch

---

## Architecture

```
world_v2/
├── main.py                  # Entry point — CLI, config, SIGTERM handler, watchdog
├── config.py                # All tunable simulation parameters (centralized)
├── claude.md                # This file — comprehensive project reference
├── .env                     # API keys (X, Gemini) — gitignored
├── .gitignore               # Excludes __pycache__, data/, .env, dashboard build artifacts
├── engine/
│   ├── simulation.py        # Core loop, checkpointing, pruning, safeguards, story gen, X posting
│   └── substrate.py         # Graph world (Watts-Strogatz), pheromones, seasons, vis coords
├── agents/
│   ├── agent.py             # Central agent class (perceive → decide → learn), 64-input/23-output
│   ├── state.py             # Mutable agent state (energy, entropy, node_id, age)
│   ├── genome.py            # Heritable traits (29) + NEAT node/connection genes + sensory genes
│   ├── cortex.py            # Associative weight table with evolvable drive biases + resolution
│   └── memory.py            # Episodic memory (bounded, importance-pruned, evolvable decay)
├── reasoning/
│   ├── neat_brain.py        # NEAT neural network — evolvable topology, metabolic cost
│   └── brain.py             # Legacy NativeBrain (deprecated, file kept for compat)
├── systems/
│   ├── actions.py           # Continuous effector interpretation + legacy action dispatch
│   ├── signals.py           # Signal propagation (BFS on graph, variable-width vectors)
│   ├── forking.py           # Reproduction, crossover, knowledge transfer, genome-gated macros
│   ├── evolution.py         # Motor pattern (macro) discovery with evolvable capacity/length
│   └── entropy.py           # Entropy accumulation system
├── persistence/
│   ├── db.py                # SQLite schema, connection, compaction, story_chapters table
│   ├── event_log.py         # Logging births, deaths, stats, snapshots
│   ├── state_store.py       # Gzipped JSON checkpoint save/load/milestones
│   └── story.py             # Story chapter generation + substrate topology persistence
├── social/
│   ├── __init__.py          # Module init
│   └── x_poster.py          # X (Twitter) auto-poster — Gemini thread generation + tweepy posting
├── utils/
│   ├── logger.py            # Console output formatting
│   └── events.py            # Event helper utilities
├── data/
│   ├── simulation.db        # SQLite database (live simulation data)
│   ├── checkpoints/         # Rotating gzipped JSON checkpoints
│   └── milestones/          # Permanent milestone checkpoints (never deleted)
└── dashboard/               # Next.js observatory dashboard
    ├── src/
    │   ├── app/
    │   │   ├── page.tsx             # Main page (sidebar + 13-section routing + uptime timer)
    │   │   ├── layout.tsx           # Root layout (fonts, light theme, "Werld Observatory" title)
    │   │   ├── globals.css          # Light theme CSS variables
    │   │   └── api/simulation/
    │   │       └── route.ts         # API endpoint — all simulation data + start time
    │   ├── components/
    │   │   ├── dashboard/
    │   │   │   ├── welcome-section.tsx      # Plain-English welcome page for general audience
    │   │   │   ├── methods-section.tsx      # Deep technical reference (collapsible sections)
    │   │   │   ├── overview-section.tsx     # Metrics, population trend, event feed
    │   │   │   ├── story-section.tsx        # Story chapters, chronological/reverse toggle
    │   │   │   ├── world-map-section.tsx    # Canvas world visualization (agents, energy, density)
    │   │   │   ├── population-section.tsx   # Pop history, birth/death, generations
    │   │   │   ├── evolution-section.tsx    # Species, generation, fitness trajectories
    │   │   │   ├── brain-section.tsx        # Brain topology, metabolic cost, complexity
    │   │   │   ├── intelligence-section.tsx # Effector activity, cortex growth, motor patterns
    │   │   │   ├── ecology-section.tsx      # Pop & diversity, energy flow, homeostasis
    │   │   │   ├── resources-section.tsx    # Energy/entropy trends, distributions
    │   │   │   ├── communication-section.tsx# Signal activity, decoder, content averages
    │   │   │   └── agents-section.tsx       # Sortable roster, detail panel, genome view
    │   │   └── ui/
    │   │       ├── info-tip.tsx      # Reusable tooltip component (? icon + hover popover)
    │   │       ├── card.tsx          # shadcn card
    │   │       ├── table.tsx         # shadcn table
    │   │       ├── tabs.tsx          # shadcn tabs
    │   │       ├── badge.tsx         # shadcn badge
    │   │       ├── separator.tsx     # shadcn separator
    │   │       └── scroll-area.tsx   # shadcn scroll area
    │   ├── hooks/
    │   │   └── use-simulation.ts    # Auto-polling hook (every 4s), includes simulationStartTime
    │   └── lib/
    │       ├── db.ts                # SQLite queries, effector queries, DB TTL, story/topology/startTime
    │       └── utils.ts             # cn helper
    └── package.json
```

---

## Simulation Engine (Python)

### Graph Topology (Substrate)

The world is a **Watts-Strogatz small-world graph**. No grid, no Cartesian coordinates.

| Parameter | Config Key | Default | Description |
|---|---|---|---|
| Nodes | `SUBSTRATE_NUM_NODES` | 800 | Total resource nodes |
| Avg Degree | `SUBSTRATE_AVG_DEGREE` | 4 | Avg connections per node |
| Rewire Prob | `SUBSTRATE_REWIRE_PROB` | 0.15 | Shortcut probability |

Each `GraphNode` has: `id`, `energy`, `neighbors` (list of connected node IDs), `pheromone` (float), `vis_x`/`vis_y` (for dashboard visualization).

**Pheromones**: Agents leave chemical traces on visited nodes. Pheromones decay at `PHEROMONE_DECAY_RATE` per tick, capped at `PHEROMONE_MAX`. Deposit rate is optionally proportional to agent energy fraction.

**Seasons**: Energy regeneration fluctuates sinusoidally with period `SEASON_PERIOD` (200 ticks) and amplitude `SEASON_AMPLITUDE` (0.6). Creates periodic environmental pressure.

### Agent Architecture

Each `Agent` combines six subsystems:

#### 1. Genome (`agents/genome.py`)

Three-part heritable blueprint:

**a) Traits** — Flat numeric vector governing physical capacities, behavioral drives, and cognitive architecture (29 total):
- Physical: `tick_cost`, `max_energy`, `entropy_resistance`, `sense_range`, `signal_range`, `signal_width`
- Learning: `learning_rate`, `exploration_factor`, `mutation_rate`, `knowledge_transfer`, `cortex_capacity`, `memory_capacity`
- Behavioral: `fork_threshold`, `macro_discovery_rate`, `cultural_transfer`
- **Evolvable drives** (Phase A): `harvest_drive`, `maintain_drive`, `explore_drive`, `social_drive` (signed: negative=aggression, positive=cooperation), `reproduce_drive`, `signal_drive`
- **Evolvable I/O** (Phase F): `broadcast_width` (1-16, how many broadcast channels are active)
- **Evolvable cortex** (Phase F): `cortex_reliance` (0-1, probability cortex fires when brain is active), `cortex_resolution` (2-6, bins per perceptual dimension in state hash)
- **Evolvable memory** (Phase F): `memory_decay` (0.80-0.99, importance decay per tick), `memory_social_weight` (0-2, social presence importance boost)
- **Evolvable macros** (Phase F): `macro_capacity` (5-50, max compound actions), `macro_pattern_length` (2-8, max length of discovered patterns)

Integer traits (rounded after mutation/crossover): `signal_width`, `cortex_capacity`, `memory_capacity`, `sense_range`, `signal_range`, `broadcast_width`, `cortex_resolution`, `macro_capacity`, `macro_pattern_length`

**b) NEAT topology** — Node genes + connection genes with global innovation numbers:
- `NodeGene`: id, type (input/hidden/output), bias, activation function (tanh/relu/sigmoid/identity/sin/abs/step)
- `ConnectionGene`: innovation number, from_node, to_node, weight, enabled flag
- Crossover aligns genes by innovation number (NEAT-style)
- Mutations: add connection, add node (splits connection), mutate weight, toggle connection, mutate bias, mutate activation

**c) Evolvable sensory processing** (Phase B):
- `sensory_gains`: per-channel gain multiplier (core channels default 1.0, latent channels default 0.01; range [0.01, 5])
- `sensory_offsets`: per-channel offset (default 0.0, range [-2, 2])
- Applied to raw sensory inputs: `processed = raw * gain + offset`
- Mutations via gaussian perturbation (30% per-channel probability for gains, 20% for offsets)

**Crossover**: On reproduction, both parents contribute. For traits: randomly inherit each from either parent. For NEAT: gene-by-gene alignment by innovation number (matching genes randomly chosen, excess/disjoint from fitter parent). For sensory genes: uniform crossover per channel.

**Mutation**: All three parts mutate independently. Traits clamp to configured ranges. NEAT topology grows through structural mutations. Sensory gains/offsets undergo gaussian perturbation.

#### 2. AgentState (`agents/state.py`)

Mutable runtime state:
- `energy` (float), `entropy` (float), `age` (int), `node_id` (int), `alive` (bool)
- `signal_buffer`: received signal vectors (list of float lists, variable length per sender's broadcast_width)
- `last_action`, `last_action_result`
- `tick_upkeep()`: deducts `tick_cost` + brain metabolic cost from energy, accumulates entropy

#### 3. Cortex (`agents/cortex.py`)

Fast associative weight table — a secondary/fallback reflex system:
- Maps `(state_hash, action_id)` → weight
- State hash computed from: energy bucket, entropy bucket, local energy, agents nearby, node degree, signal count
- **Evolvable resolution** (Phase F): `cortex_resolution` trait controls how many bins per perceptual dimension (2-6). Higher resolution = finer discrimination but slower generalisation and more memory.
- **Evolvable reliance** (Phase F): `cortex_reliance` trait (0-1) controls the probability the cortex fires when the brain is active. Agents can evolve `cortex_reliance → 0.0` to become pure NEAT-brain creatures, or keep it high for reflex backup. Evolution decides.
- Action selection via **genome-driven drive modulation** + exploration noise + softmax
- **Evolvable internal drives** (Phase A): instead of hardcoded behavioral biases, drive modulation uses genome traits (`harvest_drive`, `maintain_drive`, etc.)
- Bounded by `cortex_capacity` (LRU eviction when full)
- Experience-based reinforcement: weight updates based on drive-before/drive-after delta
- Inheritance: child cortex inherits fraction of parental weights via `cultural_transfer` trait

#### 4. NEATBrain (`reasoning/neat_brain.py`)

Evolvable topology neural network (NEAT-style):
- **No gradient descent**. Weights evolve through natural selection and mutation.
- Network topology grows/shrinks through NEAT structural mutations.
- Supports recurrent connections (hidden→hidden) for working memory.
- Activation functions per node: tanh, relu, sigmoid, identity, sin, abs, step.
- Forward pass uses topological sort with cycle handling for recurrent connections.
- `metabolic_cost` = `num_active_nodes × NEURON_COST` + `num_active_connections × CONNECTION_COST` + `sensory_excess × SENSORY_COST` + `active_broadcast_channels × BROADCAST_COST`
  - `sensory_excess` = sum of `|gain - 1.0|` across all sensory channels
  - `active_broadcast_channels` = genome trait `broadcast_width` (only active channels cost energy)
- This cost is deducted from energy each tick, creating selection pressure against unnecessary complexity and unused broadcast bandwidth.
- `compute_reward()` is **vestigial** — returns 0.0. The NEAT brain evolves through natural selection, not reward signals.

#### 5. EpisodicMemory (`agents/memory.py`)

Bounded, importance-based memory with evolvable parameters:
- Stores `Episode` objects (tick, action, node_id, energy/entropy deltas, agents_present)
- **Evolvable decay** (Phase F): `memory_decay` trait (0.80-0.99) replaces the fixed `MEMORY_IMPORTANCE_DECAY` constant. Each species evolves its own forgetting rate.
- **Evolvable social weight** (Phase F): `memory_social_weight` trait (0-2) controls how much social presence boosts an episode's importance. Social species evolve high social_weight; solitary species may evolve it toward 0.
- Importance = `|drive_delta| + social_weight × (1 if agents_present else 0)`
- `narrative_summary()` for potential future integration

#### 6. Motor Patterns / Compound Actions (`systems/evolution.py`)

Self-discovered action sequences with genome-gated thresholds:
- `SequenceTracker` bins continuous effector values into coarse buckets and tracks patterns
- **Evolvable pattern length** (Phase F): `macro_pattern_length` trait (2-8) controls the maximum length of detected sequences. Replaces the fixed `MAX_COMPOUND_LENGTH`.
- **Evolvable capacity** (Phase F): `macro_capacity` trait (5-50) controls the maximum number of compound actions an agent can hold. Replaces the fixed `MAX_COMPOUND_ACTIONS`.
- `macro_discovery_rate` (already evolvable since Phase 3) controls the probability of promoting a candidate.
- `COMPOUND_SUCCESS_THRESHOLD` (3) remains as physics — minimum repetitions needed to confirm a pattern.
- Promoted to `CompoundAction` when consistently beneficial
- Inheritable (with mutation, respecting genome's `macro_pattern_length`) during reproduction
- Represent emergent behavioral complexity — "motor programs"

### Agent Lifecycle: `perceive → decide → act → learn`

Each tick, for each alive agent:

1. **`tick_upkeep()`**: Deduct tick_cost + brain metabolic cost from energy, accumulate entropy
2. **`perceive()`**: BFS within `sense_range` hops — collects 64-dimensional sensory vector (45 core + 19 latent)
3. **`decide()`**: NEAT brain produces continuous effector outputs (23 values: 7 motor + 16 broadcast); cortex fires with probability `cortex_reliance` (fallback if no brain)
4. **`interpret_effectors()`**: Physics engine translates continuous effector activations into world effects
5. **`learn()`**: Cortex reinforces based on drive delta; brain records experience count; episodic memory stores episode (with evolvable social_weight); sequence tracker checks for motor pattern discovery (with genome-gated capacity/length)

### Sensory Inputs (64 channels)

| Range | Category | Channels |
|-------|----------|----------|
| 0-12 | Proprioceptive | Energy deficit, entropy pressure, age, energy ratio, entropy ratio, brain nodes/connections, hidden activations ×3, energy/entropy deltas, compound count |
| 13-22 | Exteroceptive | Local energy, best/avg neighbor energy, node degree, agents at/near node, agents 1-hop, hub detection, movement edges, 2nd-hop energy |
| 23-32 | Social | Signal count, 4 signal channel averages, kin presence, unique senders (approx), last action flags (harvest/move/maintain) |
| 33-35 | Pheromone | Local, best neighbor, avg neighbor pheromone |
| 36-40 | Environmental/Temporal | Season sin/cos, season regen multiplier, circadian clock, last action type |
| 41-44 | Stochastic/Utility | Constant bias (1.0), uniform noise, gaussian noise, age-modulated pulse |
| **45-48** | **Effector Echo** | Last tick's locomotion dir/intensity, harvest, social (proprioceptive motor feedback) |
| **49-52** | **Broadcast Echo** | Last tick's broadcast channels 0-3 (self-monitoring of own signals) |
| **53-56** | **Derivative Signals** | Rate of change: d(energy)/dt, d(entropy)/dt, d(local_energy)/dt, d(population)/dt |
| **57-60** | **Cross-Products** | energy×entropy, local_energy×agents_nearby, pheromone×season, age×entropy |
| **61-63** | **Memory Aggregates** | Avg recent drive_delta, action variety (diversity of recent actions), memory fullness ratio |

Channels 45-63 are **latent**: their sensory gains initialize at 0.01 (near-zero), making them dormant until evolution discovers their value by evolving the gain away from 0. This is how agents expand their sensory field without changing the brain's I/O dimensionality.

Raw features are processed through evolvable `sensory_gains` and `sensory_offsets` before reaching the brain.

### Effector Outputs (23 channels)

| Idx | Effector | Type | Description |
|-----|----------|------|-------------|
| 0 | Locomotion direction | Continuous | Signed value mapped to neighbor index |
| 1 | Locomotion intensity | 0-1 | Movement commitment |
| 2 | Harvest intensity | 0-1 | Energy extraction from current node |
| 3 | Social interaction | Signed | Negative = attack, positive = transfer |
| 4 | Maintenance intensity | 0-1 | Self-repair |
| 5 | Reproduction intensity | 0-1 | Above `FORK_INTENSITY_THRESHOLD` = fork |
| 6 | Signal intensity | 0-1 | Above threshold = broadcast |
| **7-22** | **Broadcast channels** | **Continuous** | **Up to 16 evolved signal content channels (agent uses `broadcast_width` of them; rest zeroed)** |

"Observe" and "idle" are gone — perception is automatic, idle is the absence of effector activation. Multiple effectors can fire simultaneously. The `interpret_effectors()` function in `systems/actions.py` translates these into world effects.

**Evolvable broadcast bandwidth** (Phase F): Each agent's genome trait `broadcast_width` (1-16) controls how many of the 16 broadcast channels are active. Channels beyond `broadcast_width` are zeroed in both the brain output and signal propagation. Metabolic cost is proportional to active channels only (`BROADCAST_COST × broadcast_width`), creating selection pressure against unused bandwidth.

### Systems

- **Actions** (`systems/actions.py`): `interpret_effectors()` converts continuous effector outputs into world effects. Respects `broadcast_width` when constructing signal vectors. Legacy `execute_action()` dispatch is kept for backward compatibility.
- **Signals** (`systems/signals.py`): BFS propagation within `signal_range` hops. When `UNSTRUCTURED_COMMS=True`, signal content comes from the brain's broadcast channels (evolved, not hardcoded). Signal vector length varies per sender (determined by `broadcast_width`).
- **Forking** (`systems/forking.py`): Reproduction — energy cost, genome crossover/mutation (traits + NEAT topology + sensory genes), cortex/brain inheritance with evolvable transfer strength, drive weights, cortex resolution. Macro inheritance respects child's `macro_capacity` and `macro_pattern_length`.
- **Evolution** (`systems/evolution.py`): Motor pattern discovery from binned effector activation sequences. `discover_compound_actions` accepts `max_capacity` from genome. `mutate_compound_action` accepts `max_length` from genome. Patterns are inheritable and mutable.
- **Entropy** (`systems/entropy.py`): Entropy accumulation and lethal threshold mechanics.

### Story Generation (`persistence/story.py`)

Every `STORY_CHAPTER_EVERY` ticks (default: **10,000**), the simulation generates a plain-English narrative chapter summarising what happened during that epoch. Chapters cover:

- Population changes (births, deaths, net growth)
- Generational progress (max generation, average age)
- Energy and survival (health assessment, substrate energy)
- Brain complexity (neuron/connection counts, metabolic cost, growth trends)
- Species diversity (how many species, diversification status)
- Learning and innovation (cortex size, new motor patterns discovered)
- Communication (signal deliveries, active broadcasters)
- Closing outlook (trajectory assessment)

Chapters are stored in the `story_chapters` table and displayed in the Story dashboard section.

The `save_substrate_topology()` function stores the graph layout (node positions, edges) in `simulation_meta` for the World Map visualization. Called once at simulation start and checkpoint restore.

### X (Twitter) Auto-Posting (`social/x_poster.py`)

After each story chapter is generated, the simulation attempts to post a tweet thread to X:

1. **Rate limiting**: `MIN_HOURS_BETWEEN_POSTS = 12` — max 2 threads/day to stay within X free tier (500 posts/month). At ~7 tweets/thread × 2/day × 30 days = ~420/month.
2. **Gemini rewrite**: The raw chapter is sent to Gemini (`gemini-2.0-flash`) with a system prompt that produces a nature documentary-style tweet thread. Voice: warm, observant, plain language, no jargon, no hashtags, no performed reactions.
3. **Thread structure**: 1 hook tweet (ends with 🧵) + up to 6 follow-up replies. Each tweet ≤ 275 characters. Final tweet includes the dashboard URL.
4. **Posting**: Uses `tweepy.Client` to post the hook and reply chain to X.
5. **Tracking**: Posted chapters are recorded in the `posted_tweets` table to prevent duplicates.
6. **Non-blocking**: Posting failures (API errors, rate limits) are caught and logged but never crash the simulation.

**Dependencies**: `tweepy`, `google-genai`, `python-dotenv`

**Configuration**: API keys stored in `.env` (gitignored):
- `X_CONSUMER_KEY`, `X_CONSUMER_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`
- `GEMINI_API_KEY`
- `DASHBOARD_URL` (defaults to `https://werld.uravshah.com`)

### Persistence

**SQLite** (`persistence/db.py`, `persistence/event_log.py`):
- Tables: `simulation_meta`, `events`, `lineage`, `snapshots`, `population_stats`, `comms_stats`, `species_stats`, `brain_stats`, `story_chapters`, `posted_tweets`
- `brain_decision` events store `{"effectors": [7 floats], "continuous": true}` instead of action IDs
- DB compaction (`prune_old_data`) runs every `DB_PRUNE_EVERY` ticks, deleting old `signal_sent` and `brain_decision` events, keeping last `DB_PRUNE_AFTER_TICKS` ticks of full detail

**Checkpoints** (`persistence/state_store.py`):
- Gzipped JSON with full simulation state (substrate, agents, tick, innovation counter, pheromone data)
- Rotating checkpoints (keep last `CHECKPOINT_KEEP`)
- **Milestone checkpoints** every `MILESTONE_EVERY` ticks (never deleted)
- Resume via `--resume` or `--checkpoint <path>`

### Indefinite Running Infrastructure

- **SIGTERM handler**: Saves checkpoint on graceful shutdown
- **Watchdog mode** (`--watchdog`): Auto-restart on crash
- **Extinction safeguard**: Auto-spawns mutants when population drops to 1 (`EXTINCTION_SAFEGUARD`). Safeguard spawns happen **before** logging, so all births/deaths are properly counted in statistics.
- **Dead agent purging**: Removes long-dead agents from memory every `DEAD_AGENT_PURGE_EVERY` ticks
- **DB compaction**: Prunes old events to prevent unbounded DB growth
- **Simulation start time**: Stored in `simulation_meta` (key: `simulation_start_time`) as an ISO timestamp. Used by the dashboard uptime timer.

### Configuration (`config.py`)

All parameters centralized. Key sections:
- Substrate: topology, energy regen, pheromones, seasons
- Genome: 29 trait ranges (min, max, default) including 6 evolvable drives, evolvable I/O, cortex, memory, and macro params
- Action costs and thresholds (continuous system)
- NEAT brain: mutation probabilities, weight ranges, speciation, metabolic costs
- Unstructured comms: 16 max broadcast channels
- Persistence: DB pruning, checkpoints, milestones
- Indefinite running: extinction safeguard, dead agent purging

---

## Dashboard (Next.js / TypeScript)

### Tech Stack

- **Next.js 16** (App Router, Turbopack)
- **React** with client-side components
- **TypeScript** strict mode
- **Recharts** for data visualization
- **shadcn/ui** component library
- **Tailwind CSS** with custom light theme
- **better-sqlite3** for server-side SQLite reads
- **Lucide React** for icons
- **Inter** + **JetBrains Mono** fonts via `next/font`

### Theme

Light-themed with oklch color variables in `globals.css`:
- Background: near-white with slight blue tint
- Foreground: near-black
- Card: pure white
- Primary: deep indigo/blue
- Custom scrollbar styling

### Branding

- Page title: "Werld Observatory" (set in `layout.tsx`)
- Sidebar header: "WERLD" + "Observatory"
- Default landing page: "Welcome" section

### Tooltip System (`components/ui/info-tip.tsx`)

A reusable `InfoTip` component provides contextual help throughout the dashboard:
- Small `(?)` icon that shows a popover on hover
- `TitleWithTip` helper for section headings with integrated tooltips
- Used across all 11 data-driven dashboard sections to explain technical concepts in plain language
- Goal: make the dashboard understandable even for non-technical users

### Uptime Timer

The sidebar displays a live uptime timer showing how long the simulation has been running:
- `UptimeTimer` component in `page.tsx` reads `simulationStartTime` from the API
- Updates every second, displays in `Xd Xh Xm` / `Xh Xm Xs` / `Xm Xs` format
- Start time stored in `simulation_meta` table as ISO timestamp, set on fresh simulation init
- Shows "—" if no start time is available

### Data Flow

1. `use-simulation.ts` hook polls `GET /api/simulation` every 4 seconds
2. `route.ts` calls query functions from `lib/db.ts`
3. `db.ts` manages SQLite connection with **10-second TTL** (prevents stale data when simulation restarts)
4. Data flows to section components via props from `page.tsx`
5. API response includes `simulationStartTime` for the uptime timer

### Dashboard Sections (13 total)

#### 1. Welcome (static)
- Plain-English explanation of the project for a general audience
- Sections: "What is this?", "How does it work?", "What makes this different?", "What are we looking for?", "Using the Dashboard"
- Dashboard section guide listing all 11 data sections with descriptions
- No data dependency — renders without simulation data

#### 2. Methods (static)
- Deep technical reference with collapsible accordion sections
- Sections: Architecture Overview, Brain (NEAT), Sensory System (64 channels), Motor System (23 effectors), Genome and Inheritance (29 traits), Cortex (reflex system), Episodic Memory, Motor Patterns, Communication, Natural Selection, Environmental Physics
- Full trait table with ranges and descriptions
- "Expand all" / "Collapse all" controls
- No data dependency — renders without simulation data

#### 3. Overview
- Metric cards with tooltips: tick, population, avg energy/entropy/age, max generation, substrate energy
- Population trend area chart
- Recent events feed (births, deaths, inventions)

#### 4. Story
- Chronological/reverse-chronological toggle
- Each chapter: title, tick range, full narrative content
- Progress bar showing ticks until next chapter (every 10,000 ticks)
- Chapters generated from simulation data via template-driven narrative

#### 5. World Map
- Canvas-based force-directed graph visualization
- Three view modes: **Agents** (where agents are), **Energy** (node energy levels), **Density** (agent clustering)
- Interactive pan and zoom
- Summary stats (total nodes, edges, agents, avg energy)
- Node colors reflect the selected view mode

#### 6. Population
- Summary stats with tooltips
- Population over time with births/deaths
- Generation distribution bar chart
- Max generation and avg age trends

#### 7. Evolution
- Species population over time
- Generation distribution
- Active species table
- Species fitness trajectories

#### 8. Brain Complexity
- Brain topology growth (nodes + connections over time)
- Peak brain complexity
- Metabolic cost trend
- Species brain comparison

#### 9. Intelligence
- **Effector activity** bar chart (avg continuous activation per effector channel) — falls back to legacy action distribution if no effector data
- **Effector activation over time** stacked area chart (locomotion, harvest, social, maintenance, reproduction, signal)
- Cortex growth over time
- Motor pattern (macro) discovery log

#### 10. Ecology
- Population & species diversity
- Birth/death dynamics
- Energy flow
- Homeostasis pressure

#### 11. Resources
- Energy & entropy over time
- Substrate energy trend
- Energy/entropy distribution histograms

#### 12. Communication
- Signal activity over time
- Signal decoder
- Message type distribution
- Signal content averages

#### 13. Agents
- Sortable roster table (energy, entropy, age, generation, cortex, memory, macros)
- Click-to-inspect detail panel with vitals and full genome display
- Genome traits include all 29 traits (drives, I/O, cortex, memory, macros)
- Recent event feed sidebar

### Key Database Queries (`lib/db.ts`)

- `getOverview()`: Current tick, population, averages, totals
- `getFullHistory(limit)`: Time series of all population stats
- `getActionDistribution(limit)`: Legacy action frequency from recent events
- `getEffectorActivity(recentTicks)`: Average continuous effector activation per channel
- `getEffectorHistory(recentTicks)`: Time-binned effector activations for area chart
- `getCommsHistory(limit)`: Communication stats over time
- `getGenerationDistribution()`: Agent count per generation
- `getRecentSignals(limit)`: Recent signal events with decoded content
- `getAgentSnapshots()`: All alive agents at latest tick with full state + lineage + genome
- `getRecentMacros(limit)`: Recent motor pattern discovery events
- `getRecentEvents(limit)`: Recent events of all types
- `getBrainHistory(limit)`: Brain complexity metrics over time
- `getSpeciesHistory(limit)`: Species population and fitness over time
- `getLatestSpecies()`: Current species snapshot
- `getEcologyHistory(limit)`: Population, diversity, energy flow over time
- `getStoryChapters()`: All story chapters (chapter number, tick range, title, content)
- `getSubstrateTopology()`: Graph topology from `simulation_meta` (nodes with positions, edges)
- `getAgentPositions()`: Current agent positions on the graph for world map
- `getNodeEnergyData()`: Per-node energy and agent count for world map
- `getSimulationStartTime()`: ISO timestamp from `simulation_meta` for uptime timer

---

## Database Schema

### `simulation_meta`
- `key TEXT PRIMARY KEY`, `value TEXT`
- Stores: `substrate_topology` (JSON with nodes, edges, positions), `simulation_start_time` (ISO timestamp)

### `events`
- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `tick INTEGER`, `event_type TEXT`, `agent_id INTEGER`
- `description TEXT`, `data TEXT` (JSON)
- Event types: `birth`, `death`, `brain_decision`, `signal_sent`, `macro_discovered`
- `brain_decision` data format: `{"effectors": [float×7], "continuous": true}`

### `lineage`
- `child_id INTEGER PRIMARY KEY`
- `parent_a_id INTEGER`, `parent_b_id INTEGER`
- `born_tick INTEGER`, `died_tick INTEGER`, `generation INTEGER`, `genome TEXT`

### `snapshots`
- `tick INTEGER`, `agent_id INTEGER`
- `energy REAL`, `entropy REAL`, `age INTEGER`, `node_id INTEGER`
- `alive INTEGER`, `generation INTEGER`, `cortex_size INTEGER`
- `memory_size INTEGER`, `compound_actions INTEGER`, `genome TEXT`

### `population_stats`
- `tick INTEGER PRIMARY KEY`
- `population INTEGER`, `total_births INTEGER`, `total_deaths INTEGER`
- `avg_energy REAL`, `avg_entropy REAL`, `avg_age REAL`
- `max_generation INTEGER`, `avg_cortex_size REAL`, `substrate_energy REAL`

### `comms_stats`
- `tick INTEGER PRIMARY KEY`
- `signals_sent INTEGER`, `signals_received INTEGER`
- `unique_senders INTEGER`, `unique_receivers INTEGER`
- `avg_distance REAL`, `total_deliveries INTEGER`
- `avg_signal_energy REAL`, `avg_signal_entropy REAL`, `avg_signal_resource REAL`

### `species_stats`
- `tick INTEGER`, `species_id INTEGER` (composite PK)
- `count INTEGER`, `avg_fitness REAL`, `avg_brain_nodes INTEGER`, `avg_brain_conns INTEGER`

### `brain_stats`
- `tick INTEGER PRIMARY KEY`
- `avg_nodes REAL`, `avg_connections REAL`, `max_nodes INTEGER`, `max_connections INTEGER`
- `avg_metabolic_cost REAL`

### `story_chapters`
- `chapter INTEGER PRIMARY KEY`
- `tick_start INTEGER NOT NULL`, `tick_end INTEGER NOT NULL`
- `title TEXT NOT NULL`, `content TEXT NOT NULL`
- `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`

### `posted_tweets`
- `chapter INTEGER PRIMARY KEY`
- `tweet_ids TEXT` (JSON array of tweet ID strings)
- `posted_at TEXT` (ISO timestamp)

---

## Genome Traits Reference (29 traits)

### Physical Traits
| Trait | Range (min, max, default) | Description |
|---|---|---|
| `tick_cost` | (0.3, 2.0, 0.8) | Energy cost per tick to exist |
| `max_energy` | (100.0, 250.0, 150.0) | Maximum energy capacity |
| `entropy_resistance` | (0.5, 2.0, 1.0) | Resistance to entropy accumulation |
| `sense_range` | (1, 4, 2) | Perception range in hops |
| `signal_range` | (1, 5, 3) | Signal broadcast range in hops |
| `signal_width` | (2, 8, 4) | Signal encoding width |

### Learning Traits
| Trait | Range (min, max, default) | Description |
|---|---|---|
| `learning_rate` | (0.01, 0.5, 0.15) | Cortex learning speed |
| `exploration_factor` | (0.05, 0.5, 0.2) | Action exploration vs exploitation |
| `mutation_rate` | (0.01, 0.3, 0.05) | Genome mutation magnitude |
| `knowledge_transfer` | (0.0, 1.0, 0.5) | Brain weight inheritance fraction |
| `cortex_capacity` | (50, 500, 200) | Max cortex entries |
| `memory_capacity` | (10, 100, 40) | Episodic memory size |

### Behavioral Traits
| Trait | Range (min, max, default) | Description |
|---|---|---|
| `fork_threshold` | (40.0, 80.0, 55.0) | Energy needed to reproduce |
| `macro_discovery_rate` | (0.01, 0.2, 0.05) | Motor pattern discovery chance |
| `cultural_transfer` | (0.1, 0.8, 0.4) | Motor pattern inheritance fidelity |

### Evolvable Internal Drives (Phase A)
| Trait | Range (min, max, default) | Description |
|---|---|---|
| `harvest_drive` | (0.0, 1.0, 0.5) | Bias toward energy extraction when hungry |
| `maintain_drive` | (0.0, 1.0, 0.5) | Bias toward self-repair when entropic |
| `explore_drive` | (0.0, 1.0, 0.3) | Bias toward movement |
| `social_drive` | (-1.0, 1.0, 0.0) | Negative=aggression, positive=cooperation |
| `reproduce_drive` | (0.0, 1.0, 0.3) | Bias toward forking when energy surplus |
| `signal_drive` | (0.0, 1.0, 0.2) | Bias toward broadcasting |

### Evolvable I/O Dimensions (Phase F)
| Trait | Range (min, max, default) | Description |
|---|---|---|
| `broadcast_width` | (1, 16, 4) | Active broadcast channels (rest zeroed, only active ones cost energy) |

### Evolvable Cortex Architecture (Phase F)
| Trait | Range (min, max, default) | Description |
|---|---|---|
| `cortex_reliance` | (0.0, 1.0, 0.5) | Probability cortex fires when brain is active |
| `cortex_resolution` | (2, 6, 4) | Bins per perceptual dimension in state hash |

### Evolvable Memory (Phase F)
| Trait | Range (min, max, default) | Description |
|---|---|---|
| `memory_decay` | (0.80, 0.99, 0.95) | Importance decay rate per tick |
| `memory_social_weight` | (0.0, 2.0, 0.5) | Social presence importance boost in memory |

### Evolvable Macro Discovery (Phase F)
| Trait | Range (min, max, default) | Description |
|---|---|---|
| `macro_capacity` | (5, 50, 20) | Maximum compound actions per agent |
| `macro_pattern_length` | (2, 8, 5) | Maximum length of discovered motor patterns |

---

## Evolutionary Design: What is Evolvable vs Fixed

### Fully Evolvable (natural selection decides)
- Brain topology (neurons, connections, activation functions)
- Brain weights and biases
- Sensory processing (per-channel gain and offset for all 64 channels)
- Sensory field expansion (latent channels 45-63 with dormant gains)
- Internal drives (how much to weight each behavioral impulse)
- All 29 genome traits (via crossover + mutation)
- Motor patterns (compound action discovery + inheritance)
- Motor pattern capacity and maximum pattern length
- Communication content (brain-driven broadcast channels)
- Communication bandwidth (broadcast_width: 1-16 active channels)
- Cortex reliance (whether to use reflex system or go pure brain)
- Cortex perceptual resolution (how finely to bin the world)
- Memory decay rate (how fast memories fade)
- Memory social weighting (how much social encounters matter)

### Fixed by Physics (the "laws of nature")
- Graph topology (the substrate doesn't change)
- Energy regeneration mechanics and seasonal cycles
- Entropy accumulation and lethality
- Pheromone decay rates
- Action costs (energy price of each effector)
- Fork mechanics (energy cost, parent contribution)
- Signal propagation range
- Perception range in hops
- `COMPOUND_SUCCESS_THRESHOLD` (3 repetitions needed to confirm a pattern — physics of learning)

### Deliberately Absent
- Reward function (vestigial, returns 0.0 — evolution is the teacher)
- Hardcoded behavioral biases (replaced by evolvable drives)
- Hardcoded sensory normalizations (replaced by evolvable gains/offsets)
- Discrete named actions (replaced by continuous effectors)
- Fixed cortex reliance (now genome-gated)
- Fixed memory parameters (now genome-driven)
- Fixed macro thresholds (now genome-driven)
- Fixed broadcast bandwidth (now evolvable)
- Language, economy, social structures (must emerge, not be injected)

---

## Public Hosting & Social

### Cloudflare Tunnel
- The simulation and dashboard run locally from an external hard drive
- A Cloudflare Tunnel routes `werld.uravshah.com` → `localhost:3000`
- The tunnel runs as a system service (`cloudflared`) — persists across reboots
- GoDaddy nameservers are set to Cloudflare for the `uravshah.com` domain
- No Vercel/cloud hosting needed — the dashboard reads directly from the local SQLite file

### X (Twitter) Integration
- Automated tweet threads posted after each story chapter (every 10,000 ticks)
- Rate-limited to max 2 threads/day (MIN_HOURS_BETWEEN_POSTS = 12)
- Tweet generation via Gemini `gemini-2.0-flash` model
- Nature documentary narrator voice: warm, observant, plain language, no jargon
- Thread format: 1 hook tweet (🧵) + up to 6 replies, each ≤ 275 chars
- Final tweet includes live dashboard link
- Credentials in `.env` file (gitignored)

---

## Running the Project

### Simulation
```bash
cd /path/to/world_v2
python main.py                          # Fresh run (indefinite)
python main.py --seed 42 --ticks 10000  # Seeded, limited run
python main.py --resume                 # Resume from latest checkpoint
python main.py --no-brain               # Cortex-only mode
python main.py --watchdog               # Auto-restart on crash
```

### Dashboard
```bash
cd /path/to/world_v2/dashboard
npm install
npm run dev                             # Starts on http://localhost:3000
# Or for production:
npm run build && npm start              # Production build on http://localhost:3000
```

The dashboard reads SQLite from `../data/simulation.db` relative to the dashboard directory.

### Production Deployment (Hard Drive)
```bash
# From the hard drive (e.g. /Volumes/Samsung Harddrive /world_v2/)
# 1. Start dashboard (production)
cd dashboard && npm run build && npm start &

# 2. Start simulation
cd .. && python3 main.py --watchdog

# 3. Cloudflare tunnel (runs as system service, auto-starts)
# werld.uravshah.com → localhost:3000
```

### Required Python Packages
```bash
pip install tweepy google-genai python-dotenv
```

### Environment Variables (`.env`)
```
X_CONSUMER_KEY=...
X_CONSUMER_SECRET=...
X_ACCESS_TOKEN=...
X_ACCESS_TOKEN_SECRET=...
GEMINI_API_KEY=...
DASHBOARD_URL=https://werld.uravshah.com
```

---

## Known Issues & Historical Context

1. **Grid → Graph Migration**: Originally used a 2D grid (`pos_x`, `pos_y`). Migrated to Watts-Strogatz graph (`node_id`). Old checkpoints are incompatible.

2. **NativeBrain → NEAT Migration**: The original `NativeBrain` (fixed-topology, backprop-trained) in `reasoning/brain.py` has been replaced by `NEATBrain` (evolvable topology, evolution-trained) in `reasoning/neat_brain.py`. The old file is kept but no longer used.

3. **Discrete Actions → Continuous Effectors**: The 12 discrete named actions (move_0–3, harvest, transfer, signal, maintain, fork, observe, idle, attack) have been replaced by 7 continuous effector channels + up to 16 broadcast channels. Legacy action IDs are still used internally for cortex reinforcement and motor pattern tracking.

4. **Reward System Retired**: `compute_reward()` in `neat_brain.py` is a vestigial stub returning 0.0. The NEAT brain evolves through natural selection (survival → reproduction), not through reward signals.

5. **Hardcoded Biases Removed**: Cortex drive modulation is now genome-driven (Phase A). Sensory normalization is now evolvable (Phase B). Signal content is now brain-driven (Phase 5). Cortex reliance, memory parameters, and macro thresholds are all genome-driven (Phase F). The system has zero hardcoded behavioral assumptions.

6. **DB TTL**: The dashboard's SQLite connection has a 10-second TTL to prevent stale data when the simulation restarts or the DB is replaced.

7. **Checkpoint Compatibility**: `from_checkpoint` includes backward compatibility handling for old formats but structural changes (grid→graph, NativeBrain→NEAT, 45→64 sensory inputs, 11→23 outputs) make truly old checkpoints unusable. Sensory gains/offsets are padded on load (latent channels get 0.01 gain). Always restart from a compatible checkpoint.

8. **Latent Sensory Channels**: Channels 45-63 start with gain 0.01 (effectively dormant). Evolution can "discover" them by evolving the gain higher. This allows sensory field expansion without breaking NEAT crossover (all agents have the same I/O dimensionality).

9. **Extinction Safeguard Ordering**: Safeguard spawns (when population drops to 1) now happen **before** logging, so all births/deaths including safeguard-spawned agents are properly counted in `total_births`/`total_deaths` statistics. Previously, safeguard spawns after logging caused misleading dashboard numbers.

10. **X Free Tier Rate Limits**: The X free tier allows 500 posts/month. With chapters every 10,000 ticks (~10 seconds at 1000 ticks/sec), posting every chapter would exhaust the limit in minutes. The `MIN_HOURS_BETWEEN_POSTS = 12` rate limiter ensures max ~420 tweets/month. Chapters still accumulate on the dashboard regardless of posting.

---

## Phase History

| Phase | Name | Status | Key Changes |
|-------|------|--------|-------------|
| 0 | Infrastructure for Indefinite Running | Complete | DB compaction, milestones, SIGTERM, watchdog, extinction safeguard |
| 1 | NEAT Evolvable Brain Topology | Complete | NEATBrain, node/connection genes, speciation, metabolic cost |
| 2 | Expanded Perception | Complete | 41-channel sensory field (proprioceptive, exteroceptive, social, pheromone, temporal) |
| 3 | Continuous Action Space | Complete | Multiple actions per tick with intensities, attack action |
| 4 | Pheromones, Seasons, Competition | Complete | Stigmergic communication, seasonal cycles, energy stealing |
| 5 | Unstructured Communications | Complete | Brain-driven broadcast channels replace hardcoded signal encoding |
| 6 | Dashboard (Evolution, Brain, Ecology) | Complete | Three new dashboard sections |
| A | Evolvable Internal Drives | Complete | 6 genome drive traits replace hardcoded cortex biases, reward retired |
| B | Evolvable Sensory Processing | Complete | Per-channel gain/offset, stochastic inputs, sensory metabolic cost |
| C | Naturalized Motor Interface | Complete | 7 continuous effectors + 4 broadcast channels, interpret_effectors() |
| D | Documentation Update | Complete | Comprehensive claude.md |
| E | Story, World Map, Tooltips | Complete | Story generation (every 10,000 ticks), canvas world map, InfoTip system, 11 dashboard sections |
| **F** | **Remove Hardcoded Agent Ceilings** | **Complete** | **Evolvable broadcast bandwidth (1-16), 64-channel sensory field with 19 latent slots, cortex reliance/resolution, evolvable memory decay/social_weight, genome-gated macro capacity/pattern_length. 29 total genome traits. Zero hardcoded cognitive constraints.** |
| **G** | **Public Launch & Social** | **Complete** | **Renamed to "Werld Observatory". 2 new dashboard pages (Welcome, Methods). Removed pause button, added uptime timer. X auto-posting via Gemini tweet threads. Cloudflare Tunnel hosting at werld.uravshah.com. Extinction safeguard ordering fix. Rate-limited X posting (12h minimum).** |
