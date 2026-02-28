"""
Werld — Global Configuration

All tunable parameters for the simulation.
Agents live on a graph topology — no grids, no human spatial metaphors.
"""

import os

# ── Simulation ────────────────────────────────────────────────────────────────
SEED = None                     # Random seed (None = system entropy)
MAX_TICKS = 0                   # 0 = run indefinitely
LOG_EVERY = 1                   # Print summary every N ticks
VERBOSE = True                  # Per-agent action detail
STATE_DUMP_EVERY = 50           # Dump human-readable state every N ticks
AUTO_SAVE_EVERY = 100           # Auto-save checkpoint every N ticks

# ── Data directory ───────────────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# ── Substrate (graph topology) ──────────────────────────────────────────────
# Agents live on nodes in a graph.  No grids.  Connectivity is the law of
# physics — some nodes have many connections, some have few.
SUBSTRATE_NUM_NODES = 800       # Total resource nodes in the world
SUBSTRATE_AVG_DEGREE = 4        # Average connections per node
SUBSTRATE_REWIRE_PROB = 0.15    # Watts-Strogatz rewiring probability (shortcuts)
ENERGY_MIN_PER_NODE = 0.0
ENERGY_MAX_PER_NODE = 100.0
ENERGY_REGEN_RATE = 1.0
ENERGY_SEED_DENSITY = 0.5
ENERGY_SEED_RANGE = (30.0, 100.0)

# ── Pheromones (stigmergic communication) ────────────────────────────────────
# Agents leave chemical traces on nodes.  Pheromones decay over time.
# This enables indirect communication: follow the trail of successful agents.
PHEROMONE_ENABLED = True
PHEROMONE_DECAY_RATE = 0.02       # Fraction lost per tick
PHEROMONE_DEPOSIT_RATE = 0.1      # Base deposit per agent per tick
PHEROMONE_MAX = 10.0              # Maximum pheromone per node
PHEROMONE_ENERGY_SCALE = True     # Deposit proportional to agent energy fraction

# ── Seasonal Cycles ─────────────────────────────────────────────────────────
# Energy regeneration fluctuates sinusoidally, creating periodic pressure.
SEASONS_ENABLED = True
SEASON_PERIOD = 200               # Ticks per full cycle
SEASON_AMPLITUDE = 0.6            # 0.0=no variation, 1.0=regen swings from 0 to 2x

# Legacy compat for code that references these
SUBSTRATE_WIDTH = 20
SUBSTRATE_HEIGHT = 20

# ── Genome trait ranges: (min, max, default) ─────────────────────────────────
GENOME_RANGES = {
    "tick_cost":               (0.3, 2.0, 0.8),
    "sense_range":             (1, 4, 2),           # Hops (integer for graph)
    "signal_width":            (2, 8, 4),
    "cortex_capacity":         (50, 500, 200),
    "fork_threshold":          (40.0, 80.0, 55.0),
    "learning_rate":           (0.01, 0.5, 0.15),
    "mutation_rate":           (0.01, 0.3, 0.05),
    "entropy_resistance":      (0.5, 2.0, 1.0),
    "max_energy":              (100.0, 250.0, 150.0),
    "signal_range":            (1, 5, 3),            # Hops (integer for graph)
    "exploration_factor":      (0.05, 0.5, 0.2),
    "memory_capacity":         (10, 100, 40),
    "macro_discovery_rate":    (0.01, 0.2, 0.05),
    "cultural_transfer":       (0.1, 0.8, 0.4),
    # New: evolvable knowledge transfer strength
    "knowledge_transfer":      (0.0, 1.0, 0.5),     # How much brain weight to inherit

    # ── Evolvable internal drives ────────────────────────────────────────
    # These replace hardcoded cortex drive modulation.  Each drive is a
    # heritable bias: when an internal condition is met (e.g. low energy),
    # this trait determines HOW MUCH to bias toward the corresponding
    # effector.  Natural selection discovers what drive profiles work.
    "harvest_drive":           (0.0, 1.0, 0.5),     # Bias toward energy extraction when hungry
    "maintain_drive":          (0.0, 1.0, 0.5),     # Bias toward self-repair when entropic
    "explore_drive":           (0.0, 1.0, 0.3),     # Bias toward movement
    "social_drive":            (-1.0, 1.0, 0.0),    # Negative=aggression, positive=cooperation
    "reproduce_drive":         (0.0, 1.0, 0.3),     # Bias toward forking when energy surplus
    "signal_drive":            (0.0, 1.0, 0.2),     # Bias toward broadcasting

    # ── Evolvable I/O dimensions ──────────────────────────────────────
    "broadcast_width":         (1, 16, 4),           # Active broadcast channels (rest zeroed)

    # ── Evolvable cortex architecture ─────────────────────────────────
    "cortex_reliance":         (0.0, 1.0, 0.5),      # Prob cortex fires when brain active
    "cortex_resolution":       (2, 6, 4),             # Bits per perceptual dimension in state hash

    # ── Evolvable memory ──────────────────────────────────────────────
    "memory_decay":            (0.80, 0.99, 0.95),    # Importance decay rate per tick
    "memory_social_weight":    (0.0, 2.0, 0.5),       # Social presence importance boost

    # ── Evolvable macro discovery ─────────────────────────────────────
    "macro_capacity":          (5, 50, 20),            # Max compound actions per agent
    "macro_pattern_length":    (2, 8, 5),              # Max length of discovered patterns
}

# ── Starting agent energy ────────────────────────────────────────────────────
INITIAL_ENERGY_FRACTION = 0.9

# ── Drives ───────────────────────────────────────────────────────────────────
LETHAL_ENTROPY = 100.0
BASE_ENTROPY_PER_TICK = 0.1
ENTROPY_AGE_FACTOR = 0.001

# ── Action costs ─────────────────────────────────────────────────────────────
ACTION_COSTS = {
    "move":     1.0,
    "harvest":  0.3,
    "transfer": 0.0,
    "signal":   0.2,
    "maintain": 1.5,
    "fork":     25.0,
    "observe":  0.1,
    "idle":     0.0,
    "attack":   2.0,
}

# ── Competition / Attack ────────────────────────────────────────────────────
ATTACK_ENABLED = True
ATTACK_STEAL_FRACTION = 0.3       # Fraction of target's energy stolen on success
ATTACK_DEFENSE_FACTOR = 0.5       # Defender keeps this fraction if they have more entropy resistance
ATTACK_INTENSITY_THRESHOLD = 0.5  # Minimum intensity to attempt attack

# ── Action parameters ────────────────────────────────────────────────────────
HARVEST_AMOUNT = 20.0
MAINTAIN_REDUCTION = 10.0
TRANSFER_MAX = 20.0
FORK_PARENT_ENERGY_CONTRIBUTION = 25.0
OFFSPRING_INITIAL_ENTROPY = 0.0

# ── Cortex ───────────────────────────────────────────────────────────────────
CORTEX_WEIGHT_INIT = 0.0
CORTEX_PRUNE_THRESHOLD = -2.0
CORTEX_DECAY_RATE = 0.001

# ── Movement (graph) ────────────────────────────────────────────────────────
# Instead of compass directions, agents choose neighbor by index.
# 4 movement actions map to neighbor indices modulo node degree.
NUM_MOVE_ACTIONS = 4

# ── Initial population ──────────────────────────────────────────────────────
INITIAL_AGENT_COUNT = 2

# ── Compound Actions (Self-Modification) ─────────────────────────────────────
MAX_COMPOUND_ACTIONS = 20
MAX_COMPOUND_LENGTH = 5
COMPOUND_SUCCESS_THRESHOLD = 3
COMPOUND_INHERIT_CHANCE = 0.6

# ── Episodic Memory ─────────────────────────────────────────────────────────
MEMORY_IMPORTANCE_DECAY = 0.95
MEMORY_MIN_IMPORTANCE = 0.05

# ── NEAT Brain (evolvable topology neural network) ──────────────────────────
BRAIN_ENABLED = True

# Metabolic cost per brain component per tick
NEURON_COST = 0.005               # Cost per active neuron per tick
CONNECTION_COST = 0.002           # Cost per active connection per tick
SENSORY_COST = 0.001              # Cost per active sensory input per tick
BROADCAST_COST = 0.003            # Cost per broadcast channel per tick

# ── Unstructured Communication (Phase 5) ────────────────────────────────────
# Instead of hardcoded signal encoding, broadcast channels are brain outputs.
# Agents evolve what information to encode and how to decode it.
BROADCAST_CHANNELS = 16           # Max broadcast output neurons (agents use broadcast_width)
UNSTRUCTURED_COMMS = True         # Use brain-driven broadcasts instead of fixed encoding

# NEAT mutation probabilities
NEAT_PROB_ADD_CONNECTION = 0.15   # Add a new connection between nodes
NEAT_PROB_ADD_NODE = 0.03         # Split a connection to add a hidden node
NEAT_PROB_MUTATE_WEIGHT = 0.80   # Perturb an existing connection weight
NEAT_PROB_TOGGLE_CONNECTION = 0.05 # Enable/disable a connection
NEAT_PROB_MUTATE_BIAS = 0.30     # Perturb a node bias
NEAT_PROB_MUTATE_ACTIVATION = 0.02 # Change a node's activation function

# NEAT weight mutation parameters
NEAT_WEIGHT_MUTATE_POWER = 0.5   # Std dev for weight perturbation
NEAT_WEIGHT_REPLACE_PROB = 0.1   # Probability of full weight replacement (vs perturbation)
NEAT_WEIGHT_RANGE = (-3.0, 3.0)  # Range for weight initialization
NEAT_BIAS_MUTATE_POWER = 0.3     # Std dev for bias perturbation
NEAT_BIAS_RANGE = (-3.0, 3.0)    # Range for bias initialization

# Speciation
NEAT_COMPAT_C1 = 1.0             # Coefficient for excess genes
NEAT_COMPAT_C2 = 1.0             # Coefficient for disjoint genes
NEAT_COMPAT_C3 = 0.4             # Coefficient for avg weight difference
NEAT_COMPAT_THRESHOLD = 3.0      # Distance threshold for speciation
NEAT_FITNESS_SHARING = True       # Divide fitness by species size

# Starting brain configuration
NEAT_INITIAL_CONNECTIONS = 25     # Random input->output connections at birth

# Legacy brain config (kept for backward compat during transition)
BRAIN_HIDDEN_SIZE = 24
BRAIN_LEARNING_RATE = 0.05
BRAIN_GAMMA = 0.9
BRAIN_BUFFER_SIZE = 300
BRAIN_TRAIN_BATCH = 24
BRAIN_TRAIN_EVERY = 5
BRAIN_EXPLORATION_DECAY = 0.002

# ── Continuous Action Space ──────────────────────────────────────────────────
# When enabled, brain outputs are interpreted as continuous intensities (0-1)
# instead of softmax probabilities.  Multiple actions can fire per tick.
CONTINUOUS_ACTIONS = True
ACTION_INTENSITY_THRESHOLD = 0.3  # Minimum output activation to fire an action
MAX_ACTIONS_PER_TICK = 3           # Cap on simultaneous actions per tick
FORK_INTENSITY_THRESHOLD = 0.7    # Fork requires high commitment
ACTION_INTENSITY_COST_SCALE = True # Scale energy costs by intensity

# ── Reward System (vestigial — kept for experience counting only) ────────────
# The NEAT brain evolves through natural selection, not reward-based learning.
# compute_reward has been removed.  Internal drives are evolvable genome traits.
# Only REWARD_BASELINE_ALPHA remains for exploration decay tracking.
REWARD_BASELINE_ALPHA = 0.05      # Exponential moving average rate for baseline

# ── Persistence ──────────────────────────────────────────────────────────────
DB_PATH = os.path.join(DATA_DIR, "simulation.db")
CHECKPOINT_DIR = os.path.join(DATA_DIR, "checkpoints")
MILESTONE_DIR = os.path.join(DATA_DIR, "milestones")
CHECKPOINT_KEEP = 10
CHECKPOINT_COMPRESS = True
MILESTONE_EVERY = 10_000          # Save a milestone checkpoint every N ticks (never deleted)

# ── DB Compaction ────────────────────────────────────────────────────────────
DB_PRUNE_EVERY = 500              # Run pruning every N ticks
DB_PRUNE_AFTER_TICKS = 5_000     # Keep full detail for last N ticks; prune older

# ── Indefinite Running ──────────────────────────────────────────────────────
EXTINCTION_SAFEGUARD = True       # Auto-spawn mutants when population drops to 1
DEAD_AGENT_PURGE_EVERY = 200      # Purge dead agents from memory every N ticks
DEAD_AGENT_KEEP_RECENT = 50       # Keep N recently-dead for logging
