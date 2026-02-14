"""
Genome — heritable blueprint for an agent.

Two-part genome:
  1. Traits: flat numeric vector (tick_cost, sense_range, etc.)
     Governs physical capacities and learning parameters.
  2. NEAT topology: node genes + connection genes
     Encodes the brain's neural network structure.

On forking, both parts undergo crossover and mutation independently.
NEAT crossover uses the global innovation number to align connection genes.

Key evolvable traits:
  - knowledge_transfer: how much brain weight offspring inherit (0=blank, 1=full copy)
"""

from __future__ import annotations

import json
import math
import random
from typing import Dict, List, Optional, Tuple, Any

import config as cfg

# ── Trait names ──────────────────────────────────────────────────────────────
TRAIT_NAMES = list(cfg.GENOME_RANGES.keys())
INTEGER_TRAITS = {
    "signal_width", "cortex_capacity", "memory_capacity", "sense_range", "signal_range",
    "broadcast_width", "cortex_resolution", "macro_capacity", "macro_pattern_length",
}

# ── Global innovation counter ───────────────────────────────────────────────
# Tracks every new structural mutation ever created across the entire population.
# This enables meaningful crossover between agents with different topologies.
_innovation_counter: int = 0
_innovation_cache: Dict[Tuple[int, int], int] = {}  # (from_node, to_node) -> innovation


def next_innovation(from_node: int, to_node: int) -> int:
    """Get or create a global innovation number for a connection."""
    global _innovation_counter
    key = (from_node, to_node)
    if key in _innovation_cache:
        return _innovation_cache[key]
    _innovation_counter += 1
    _innovation_cache[key] = _innovation_counter
    return _innovation_counter


def reset_innovation_counter(value: int = 0, cache: Optional[Dict] = None) -> None:
    """Reset the global innovation counter (for checkpoint restore)."""
    global _innovation_counter, _innovation_cache
    _innovation_counter = value
    _innovation_cache = cache if cache is not None else {}


def get_innovation_state() -> Tuple[int, Dict[Tuple[int, int], int]]:
    """Get current innovation state for serialization."""
    return _innovation_counter, dict(_innovation_cache)


# ── Available activation functions ──────────────────────────────────────────
ACTIVATIONS = ("tanh", "relu", "sigmoid", "sin", "step", "identity")


def apply_activation(name: str, x: float) -> float:
    """Apply an activation function by name."""
    if name == "tanh":
        return math.tanh(x)
    elif name == "relu":
        return max(0.0, x)
    elif name == "sigmoid":
        return 1.0 / (1.0 + math.exp(-max(-500.0, min(500.0, x))))
    elif name == "sin":
        return math.sin(x)
    elif name == "step":
        return 1.0 if x > 0.0 else 0.0
    elif name == "identity":
        return x
    return math.tanh(x)


# ── Node gene ───────────────────────────────────────────────────────────────

class NodeGene:
    """A single neuron in the NEAT brain."""
    __slots__ = ("node_id", "node_type", "activation", "bias")

    def __init__(
        self,
        node_id: int,
        node_type: str = "hidden",    # "input", "hidden", "output"
        activation: str = "tanh",
        bias: float = 0.0,
    ) -> None:
        self.node_id = node_id
        self.node_type = node_type
        self.activation = activation
        self.bias = bias

    def copy(self) -> "NodeGene":
        return NodeGene(self.node_id, self.node_type, self.activation, self.bias)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.node_id,
            "type": self.node_type,
            "act": self.activation,
            "bias": round(self.bias, 6),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "NodeGene":
        return cls(d["id"], d["type"], d["act"], d["bias"])


# ── Connection gene ─────────────────────────────────────────────────────────

class ConnectionGene:
    """A single wire in the NEAT brain."""
    __slots__ = ("innovation", "from_node", "to_node", "weight", "enabled")

    def __init__(
        self,
        innovation: int,
        from_node: int,
        to_node: int,
        weight: float = 0.0,
        enabled: bool = True,
    ) -> None:
        self.innovation = innovation
        self.from_node = from_node
        self.to_node = to_node
        self.weight = weight
        self.enabled = enabled

    def copy(self) -> "ConnectionGene":
        return ConnectionGene(
            self.innovation, self.from_node, self.to_node, self.weight, self.enabled,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "innov": self.innovation,
            "from": self.from_node,
            "to": self.to_node,
            "w": round(self.weight, 6),
            "on": self.enabled,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ConnectionGene":
        return cls(d["innov"], d["from"], d["to"], d["w"], d["on"])


# ── NEAT Genome ─────────────────────────────────────────────────────────────

class Genome:
    """
    Full agent genome: evolvable traits + NEAT brain topology + sensory genes.

    The trait system governs physical capacities and learning parameters.
    The NEAT topology encodes the brain's structure.
    Sensory genes (gains + offsets) control how each input channel is perceived.
    """
    __slots__ = ("traits", "node_genes", "connection_genes", "sensory_gains", "sensory_offsets")

    def __init__(
        self,
        traits: Dict[str, float],
        node_genes: Optional[Dict[int, NodeGene]] = None,
        connection_genes: Optional[Dict[int, ConnectionGene]] = None,
        sensory_gains: Optional[List[float]] = None,
        sensory_offsets: Optional[List[float]] = None,
    ) -> None:
        self.traits: Dict[str, float] = dict(traits)
        self.node_genes: Dict[int, NodeGene] = node_genes if node_genes is not None else {}
        self.connection_genes: Dict[int, ConnectionGene] = connection_genes if connection_genes is not None else {}
        # Evolvable sensory processing: one gain+offset per input channel.
        # gain=1.0, offset=0.0 means raw perception passthrough.
        # These evolve so different species "tune" their senses differently.
        self.sensory_gains: List[float] = sensory_gains if sensory_gains is not None else []
        self.sensory_offsets: List[float] = sensory_offsets if sensory_offsets is not None else []

    # ── Convenience accessors ─────────────────────────────────────────────

    def __getattr__(self, name: str) -> float:
        if name in ("traits", "node_genes", "connection_genes", "sensory_gains", "sensory_offsets"):
            raise AttributeError
        try:
            return self.traits[name]
        except KeyError:
            raise AttributeError(f"Genome has no trait '{name}'")

    def __repr__(self) -> str:
        inner = ", ".join(f"{k}={v:.2f}" for k, v in self.traits.items())
        return f"Genome({inner}, nodes={len(self.node_genes)}, conns={len(self.connection_genes)})"

    @property
    def num_nodes(self) -> int:
        return len(self.node_genes)

    @property
    def num_connections(self) -> int:
        return sum(1 for c in self.connection_genes.values() if c.enabled)

    def to_json(self) -> str:
        data: Dict[str, Any] = {
            "traits": self.traits,
            "nodes": [n.to_dict() for n in self.node_genes.values()],
            "connections": [c.to_dict() for c in self.connection_genes.values()],
        }
        if self.sensory_gains:
            data["sensory_gains"] = [round(g, 6) for g in self.sensory_gains]
        if self.sensory_offsets:
            data["sensory_offsets"] = [round(o, 6) for o in self.sensory_offsets]
        return json.dumps(data)

    @classmethod
    def from_json(cls, s: str) -> "Genome":
        d = json.loads(s)
        # Handle old-style genomes (just traits dict)
        if "traits" not in d:
            return cls(d)
        traits = d["traits"]
        nodes = {n["id"]: NodeGene.from_dict(n) for n in d.get("nodes", [])}
        conns = {c["innov"]: ConnectionGene.from_dict(c) for c in d.get("connections", [])}
        sensory_gains = d.get("sensory_gains", [])
        sensory_offsets = d.get("sensory_offsets", [])
        return cls(traits, nodes, conns, sensory_gains, sensory_offsets)

    def clone(self) -> "Genome":
        nodes = {nid: ng.copy() for nid, ng in self.node_genes.items()}
        conns = {inn: cg.copy() for inn, cg in self.connection_genes.items()}
        return Genome(
            dict(self.traits), nodes, conns,
            list(self.sensory_gains), list(self.sensory_offsets),
        )

    # ── Factory: random viable genome ────────────────────────────────────

    @classmethod
    def random(
        cls,
        rng: Optional[random.Random] = None,
        num_inputs: int = 0,
        num_outputs: int = 0,
    ) -> "Genome":
        """
        Create a genome with random traits and a minimal NEAT brain.

        If num_inputs/num_outputs are 0, input/output nodes are NOT created
        here — they will be set up by the NEATBrain constructor which knows
        the actual sensory field and action space sizes.
        """
        rng = rng or random.Random()
        traits: Dict[str, float] = {}
        for name, (lo, hi, _default) in cfg.GENOME_RANGES.items():
            traits[name] = rng.uniform(lo, hi)
        for t in INTEGER_TRAITS:
            if t in traits:
                traits[t] = round(traits[t])

        node_genes: Dict[int, NodeGene] = {}
        connection_genes: Dict[int, ConnectionGene] = {}

        if num_inputs > 0 and num_outputs > 0:
            # Create input nodes (ids 0..num_inputs-1)
            for i in range(num_inputs):
                node_genes[i] = NodeGene(i, "input", "identity", 0.0)
            # Create output nodes (ids num_inputs..num_inputs+num_outputs-1)
            for i in range(num_outputs):
                nid = num_inputs + i
                node_genes[nid] = NodeGene(nid, "output", "tanh", 0.0)

            # Random sparse connections (input -> output)
            input_ids = list(range(num_inputs))
            output_ids = list(range(num_inputs, num_inputs + num_outputs))
            num_initial = min(cfg.NEAT_INITIAL_CONNECTIONS, num_inputs * num_outputs)
            possible = [(inp, out) for inp in input_ids for out in output_ids]
            rng.shuffle(possible)
            for inp, out in possible[:num_initial]:
                inn = next_innovation(inp, out)
                w = rng.uniform(*cfg.NEAT_WEIGHT_RANGE)
                connection_genes[inn] = ConnectionGene(inn, inp, out, w, True)

        # Sensory genes: slight variation around neutral (gain=1.0, offset=0.0)
        sensory_gains = [rng.gauss(1.0, 0.1) for _ in range(num_inputs)] if num_inputs > 0 else []
        sensory_offsets = [rng.gauss(0.0, 0.05) for _ in range(num_inputs)] if num_inputs > 0 else []

        return cls(traits, node_genes, connection_genes, sensory_gains, sensory_offsets)

    # ── NEAT Crossover ───────────────────────────────────────────────────

    @classmethod
    def crossover(
        cls,
        parent_a: "Genome",
        parent_b: "Genome",
        fitness_a: float = 0.0,
        fitness_b: float = 0.0,
        rng: Optional[random.Random] = None,
    ) -> "Genome":
        """
        Create a child genome by NEAT-style crossover.

        Traits: per-trait random selection + gaussian mutation (as before).
        NEAT topology: align by innovation number, pick from fitter parent
        for disjoint/excess genes, random for matching genes.
        """
        rng = rng or random.Random()

        # ── Trait crossover (unchanged) ────────────────────────────────
        mutation_rate = (
            parent_a.traits.get("mutation_rate", 0.05) +
            parent_b.traits.get("mutation_rate", 0.05)
        ) / 2.0

        child_traits: Dict[str, float] = {}
        for name in TRAIT_NAMES:
            val_a = parent_a.traits.get(name)
            val_b = parent_b.traits.get(name)
            if val_a is None and val_b is None:
                lo, hi, default = cfg.GENOME_RANGES[name]
                child_traits[name] = default
                continue
            if val_a is None:
                value = val_b
            elif val_b is None:
                value = val_a
            else:
                value = val_a if rng.random() < 0.5 else val_b
            lo, hi, _ = cfg.GENOME_RANGES[name]
            noise = rng.gauss(0, mutation_rate * (hi - lo))
            child_traits[name] = max(lo, min(hi, value + noise))

        for t in INTEGER_TRAITS:
            if t in child_traits:
                lo, _, _ = cfg.GENOME_RANGES[t]
                child_traits[t] = max(int(lo), round(child_traits[t]))

        # ── NEAT topology crossover ────────────────────────────────────
        # Determine fitter parent
        if fitness_a > fitness_b:
            fitter, weaker = parent_a, parent_b
        elif fitness_b > fitness_a:
            fitter, weaker = parent_b, parent_a
        else:
            # Equal fitness — pick randomly
            if rng.random() < 0.5:
                fitter, weaker = parent_a, parent_b
            else:
                fitter, weaker = parent_b, parent_a

        child_connections: Dict[int, ConnectionGene] = {}

        all_innovations = set(fitter.connection_genes.keys()) | set(weaker.connection_genes.keys())
        for inn in all_innovations:
            in_fitter = inn in fitter.connection_genes
            in_weaker = inn in weaker.connection_genes
            if in_fitter and in_weaker:
                # Matching gene: random pick
                if rng.random() < 0.5:
                    child_connections[inn] = fitter.connection_genes[inn].copy()
                else:
                    child_connections[inn] = weaker.connection_genes[inn].copy()
                # If either parent has it disabled, 75% chance it stays disabled
                if (not fitter.connection_genes[inn].enabled or
                        not weaker.connection_genes[inn].enabled):
                    child_connections[inn].enabled = rng.random() > 0.75
            elif in_fitter:
                # Disjoint/excess: inherit from fitter
                child_connections[inn] = fitter.connection_genes[inn].copy()
            # else: disjoint/excess from weaker — skip

        # Collect all node IDs referenced by child connections
        needed_node_ids: set = set()
        for cg in child_connections.values():
            needed_node_ids.add(cg.from_node)
            needed_node_ids.add(cg.to_node)

        # Also include all input and output nodes from fitter parent
        child_nodes: Dict[int, NodeGene] = {}
        for nid, ng in fitter.node_genes.items():
            if ng.node_type in ("input", "output") or nid in needed_node_ids:
                child_nodes[nid] = ng.copy()

        # Add any missing nodes from weaker parent (for inherited connections)
        for nid in needed_node_ids:
            if nid not in child_nodes:
                if nid in weaker.node_genes:
                    child_nodes[nid] = weaker.node_genes[nid].copy()
                elif nid in fitter.node_genes:
                    child_nodes[nid] = fitter.node_genes[nid].copy()

        # ── Sensory gene crossover ─────────────────────────────────────
        num_sensory = max(len(parent_a.sensory_gains), len(parent_b.sensory_gains))
        child_gains: List[float] = []
        child_offsets: List[float] = []
        for i in range(num_sensory):
            ga = parent_a.sensory_gains[i] if i < len(parent_a.sensory_gains) else 1.0
            gb = parent_b.sensory_gains[i] if i < len(parent_b.sensory_gains) else 1.0
            oa = parent_a.sensory_offsets[i] if i < len(parent_a.sensory_offsets) else 0.0
            ob = parent_b.sensory_offsets[i] if i < len(parent_b.sensory_offsets) else 0.0
            # Crossover: random pick from parents + small mutation
            g = ga if rng.random() < 0.5 else gb
            o = oa if rng.random() < 0.5 else ob
            g += rng.gauss(0, mutation_rate * 0.3)
            o += rng.gauss(0, mutation_rate * 0.1)
            child_gains.append(max(0.01, min(5.0, g)))  # Gain clamped to [0.01, 5.0]
            child_offsets.append(max(-2.0, min(2.0, o)))  # Offset clamped to [-2.0, 2.0]

        return cls(child_traits, child_nodes, child_connections, child_gains, child_offsets)

    # ── NEAT Mutations ───────────────────────────────────────────────────

    def mutate(self, rng: Optional[random.Random] = None) -> None:
        """
        Apply NEAT mutations in-place.
        Called after crossover during forking.
        """
        rng = rng or random.Random()

        # Weight mutations (most common)
        if rng.random() < cfg.NEAT_PROB_MUTATE_WEIGHT:
            self._mutate_weights(rng)

        # Bias mutations
        if rng.random() < cfg.NEAT_PROB_MUTATE_BIAS:
            self._mutate_biases(rng)

        # Structural: add connection
        if rng.random() < cfg.NEAT_PROB_ADD_CONNECTION:
            self._mutate_add_connection(rng)

        # Structural: add node
        if rng.random() < cfg.NEAT_PROB_ADD_NODE:
            self._mutate_add_node(rng)

        # Toggle a connection
        if rng.random() < cfg.NEAT_PROB_TOGGLE_CONNECTION:
            self._mutate_toggle_connection(rng)

        # Change activation function
        if rng.random() < cfg.NEAT_PROB_MUTATE_ACTIVATION:
            self._mutate_activation(rng)

        # Sensory gene mutations (at same rate as weight mutations)
        if rng.random() < cfg.NEAT_PROB_MUTATE_WEIGHT:
            self._mutate_sensory(rng)

    def _mutate_weights(self, rng: random.Random) -> None:
        """Perturb or replace weights on all enabled connections."""
        for cg in self.connection_genes.values():
            if not cg.enabled:
                continue
            if rng.random() < cfg.NEAT_WEIGHT_REPLACE_PROB:
                cg.weight = rng.uniform(*cfg.NEAT_WEIGHT_RANGE)
            else:
                cg.weight += rng.gauss(0, cfg.NEAT_WEIGHT_MUTATE_POWER)
                cg.weight = max(cfg.NEAT_WEIGHT_RANGE[0],
                                min(cfg.NEAT_WEIGHT_RANGE[1], cg.weight))

    def _mutate_biases(self, rng: random.Random) -> None:
        """Perturb biases on non-input nodes."""
        for ng in self.node_genes.values():
            if ng.node_type == "input":
                continue
            ng.bias += rng.gauss(0, cfg.NEAT_BIAS_MUTATE_POWER)
            ng.bias = max(cfg.NEAT_BIAS_RANGE[0], min(cfg.NEAT_BIAS_RANGE[1], ng.bias))

    def _mutate_add_connection(self, rng: random.Random) -> None:
        """Add a connection between two previously unconnected nodes."""
        if not self.node_genes:
            return
        node_ids = list(self.node_genes.keys())
        # Track existing connections
        existing = {(cg.from_node, cg.to_node) for cg in self.connection_genes.values()}

        # Try up to 20 times to find a valid new connection
        for _ in range(20):
            from_id = rng.choice(node_ids)
            to_id = rng.choice(node_ids)
            if from_id == to_id:
                continue
            # Don't connect to input nodes
            if self.node_genes[to_id].node_type == "input":
                continue
            # Don't connect from output nodes (let evolution discover this via hidden nodes)
            # Actually, we do allow output->hidden and output->output for recurrence
            if (from_id, to_id) in existing:
                continue
            inn = next_innovation(from_id, to_id)
            w = rng.uniform(*cfg.NEAT_WEIGHT_RANGE)
            self.connection_genes[inn] = ConnectionGene(inn, from_id, to_id, w, True)
            return

    def _mutate_add_node(self, rng: random.Random) -> None:
        """Split an existing connection: A->B becomes A->N->B."""
        enabled = [cg for cg in self.connection_genes.values() if cg.enabled]
        if not enabled:
            return
        cg = rng.choice(enabled)
        cg.enabled = False

        # Create new hidden node
        new_id = max(self.node_genes.keys()) + 1 if self.node_genes else 0
        act = rng.choice(ACTIVATIONS)
        self.node_genes[new_id] = NodeGene(new_id, "hidden", act, 0.0)

        # A -> N with weight 1.0 (to preserve the old signal initially)
        inn1 = next_innovation(cg.from_node, new_id)
        self.connection_genes[inn1] = ConnectionGene(inn1, cg.from_node, new_id, 1.0, True)

        # N -> B with the old weight
        inn2 = next_innovation(new_id, cg.to_node)
        self.connection_genes[inn2] = ConnectionGene(inn2, new_id, cg.to_node, cg.weight, True)

    def _mutate_toggle_connection(self, rng: random.Random) -> None:
        """Toggle the enabled state of a random connection."""
        if not self.connection_genes:
            return
        cg = rng.choice(list(self.connection_genes.values()))
        cg.enabled = not cg.enabled

    def _mutate_activation(self, rng: random.Random) -> None:
        """Change the activation function of a random hidden node."""
        hidden = [ng for ng in self.node_genes.values() if ng.node_type == "hidden"]
        if not hidden:
            return
        ng = rng.choice(hidden)
        ng.activation = rng.choice(ACTIVATIONS)

    def _mutate_sensory(self, rng: random.Random) -> None:
        """Perturb sensory gains and offsets."""
        for i in range(len(self.sensory_gains)):
            if rng.random() < 0.3:  # Per-channel mutation probability
                self.sensory_gains[i] += rng.gauss(0, 0.15)
                self.sensory_gains[i] = max(0.01, min(5.0, self.sensory_gains[i]))
        for i in range(len(self.sensory_offsets)):
            if rng.random() < 0.2:
                self.sensory_offsets[i] += rng.gauss(0, 0.05)
                self.sensory_offsets[i] = max(-2.0, min(2.0, self.sensory_offsets[i]))

    # ── NEAT compatibility distance (for speciation) ─────────────────────

    def compatibility_distance(self, other: "Genome") -> float:
        """
        Compute the NEAT compatibility distance between two genomes.
        Used for speciation: agents within a threshold are the same species.
        """
        if not self.connection_genes and not other.connection_genes:
            return 0.0

        innovs_a = set(self.connection_genes.keys())
        innovs_b = set(other.connection_genes.keys())
        matching = innovs_a & innovs_b
        all_innovs = innovs_a | innovs_b

        if not all_innovs:
            return 0.0

        max_a = max(innovs_a) if innovs_a else 0
        max_b = max(innovs_b) if innovs_b else 0
        max_innov = max(max_a, max_b)

        excess = 0
        disjoint = 0
        for inn in all_innovs - matching:
            if inn > min(max_a, max_b):
                excess += 1
            else:
                disjoint += 1

        weight_diff = 0.0
        if matching:
            for inn in matching:
                weight_diff += abs(
                    self.connection_genes[inn].weight - other.connection_genes[inn].weight
                )
            weight_diff /= len(matching)

        n = max(len(innovs_a), len(innovs_b), 1)
        return (
            cfg.NEAT_COMPAT_C1 * excess / n +
            cfg.NEAT_COMPAT_C2 * disjoint / n +
            cfg.NEAT_COMPAT_C3 * weight_diff
        )
