"""
NEATBrain — evolvable-topology neural network for agents.

The brain's structure is encoded in the agent's genome (node genes +
connection genes).  It starts minimal and evolves structural complexity
through mutation and crossover.

Key properties:
  - Variable topology: number of neurons and connections evolve
  - Recurrent connections: allowed, giving agents working memory
  - Persistent activations: node values carry between ticks
  - Metabolic cost: proportional to brain complexity
  - No backprop: the brain topology evolves via natural selection,
    not gradient descent.  Weights evolve through mutation.

Pure Python, zero dependencies.  Data structures designed for future
GPU portability (flat lists -> sparse tensors).
"""

from __future__ import annotations

import math
import random
from collections import deque
from typing import Dict, List, Optional, Set, Tuple, Any

import config as cfg
from agents.genome import Genome, NodeGene, ConnectionGene, apply_activation


class NEATBrain:
    """
    A neural network whose topology is defined by a Genome.

    The brain evaluates inputs through the genome's connection graph,
    producing output activations that drive behavior.  Activations
    persist between ticks, enabling temporal dynamics and recurrence.
    """

    __slots__ = (
        "genome",
        "activations",          # Current activation values per node
        "_eval_order",          # Cached topological order for evaluation
        "_recurrent_nodes",     # Set of nodes that have recurrent inputs
        "_input_ids",           # Ordered list of input node IDs
        "_output_ids",          # Ordered list of output node IDs
        "_adjacency",           # from_node -> [(to_node, weight)]
        "_incoming",            # to_node -> [(from_node, weight)]
        "rng",
        "visited_states",       # Novelty tracking
        "max_visited",
        "reward_baseline",
        "total_experiences",
    )

    def __init__(self, genome: Genome, rng: Optional[random.Random] = None) -> None:
        self.genome = genome
        self.rng = rng or random.Random()
        self.activations: Dict[int, float] = {}
        self._eval_order: List[int] = []
        self._recurrent_nodes: Set[int] = set()
        self._input_ids: List[int] = []
        self._output_ids: List[int] = []
        self._adjacency: Dict[int, List[Tuple[int, float]]] = {}

        # Novelty tracking
        self.visited_states: Set[int] = set()
        self.max_visited: int = 2000
        self.reward_baseline: float = 0.0
        self.total_experiences: int = 0

        self._rebuild()

    def _rebuild(self) -> None:
        """Rebuild evaluation order and incoming adjacency from genome."""
        nodes = self.genome.node_genes
        conns = self.genome.connection_genes

        # Classify nodes
        self._input_ids = sorted(
            nid for nid, ng in nodes.items() if ng.node_type == "input"
        )
        self._output_ids = sorted(
            nid for nid, ng in nodes.items() if ng.node_type == "output"
        )

        # Initialize activations for any new nodes
        for nid in nodes:
            if nid not in self.activations:
                self.activations[nid] = 0.0

        # Build forward adjacency (for topological sort)
        self._adjacency = {}
        for cg in conns.values():
            if not cg.enabled:
                continue
            if cg.from_node not in nodes or cg.to_node not in nodes:
                continue
            if cg.from_node not in self._adjacency:
                self._adjacency[cg.from_node] = []
            self._adjacency[cg.from_node].append((cg.to_node, cg.weight))

        # Build incoming adjacency (for forward pass): to_node -> [(from_node, weight)]
        self._incoming: Dict[int, List[Tuple[int, float]]] = {}
        for cg in conns.values():
            if not cg.enabled:
                continue
            if cg.from_node not in nodes or cg.to_node not in nodes:
                continue
            if cg.to_node not in self._incoming:
                self._incoming[cg.to_node] = []
            self._incoming[cg.to_node].append((cg.from_node, cg.weight))

        # Compute evaluation order via topological sort
        self._eval_order, self._recurrent_nodes = self._topological_sort()

    def _topological_sort(self) -> Tuple[List[int], Set[int]]:
        """
        Kahn-style topological sort of non-input nodes.
        Nodes that participate in cycles use previous tick's activation
        (marked as recurrent).
        """
        nodes = self.genome.node_genes
        non_input = [nid for nid in nodes if nodes[nid].node_type != "input"]

        # Build in-degree from enabled connections (only non-input targets)
        in_degree: Dict[int, int] = {nid: 0 for nid in non_input}
        for cg in self.genome.connection_genes.values():
            if not cg.enabled:
                continue
            if cg.to_node in in_degree and cg.from_node in nodes:
                # Don't count inputs (they're always available)
                if nodes[cg.from_node].node_type != "input":
                    in_degree[cg.to_node] += 1

        order: List[int] = []
        queue = deque(nid for nid, deg in in_degree.items() if deg == 0)
        visited_set: Set[int] = set()

        while queue:
            nid = queue.popleft()
            if nid in visited_set:
                continue
            visited_set.add(nid)
            order.append(nid)

            # Reduce in-degree of successors
            for to_nid, _ in self._adjacency.get(nid, []):
                if to_nid in in_degree:
                    in_degree[to_nid] -= 1
                    if in_degree[to_nid] <= 0 and to_nid not in visited_set:
                        queue.append(to_nid)

        # Any remaining nodes are in cycles — mark them as recurrent
        recurrent: Set[int] = set()
        for nid in non_input:
            if nid not in visited_set:
                recurrent.add(nid)
                order.append(nid)

        return order, recurrent

    # ── Forward pass ─────────────────────────────────────────────────────

    def forward(self, inputs: List[float]) -> List[float]:
        """
        Evaluate the network for one tick.

        Recurrent connections (cycles) use the PREVIOUS tick's activation
        value, which is already stored in self.activations.  Non-recurrent
        nodes are evaluated in topological order so their inputs are fresh.

        Args:
            inputs: Values for input nodes (length must match _input_ids).

        Returns:
            Output node activations (length matches _output_ids).
        """
        nodes = self.genome.node_genes

        # Set input node activations
        for i, nid in enumerate(self._input_ids):
            if i < len(inputs):
                self.activations[nid] = inputs[i]
            else:
                self.activations[nid] = 0.0

        # Evaluate non-input nodes in topological order
        for nid in self._eval_order:
            ng = nodes.get(nid)
            if ng is None or ng.node_type == "input":
                continue

            # Sum weighted inputs from incoming connections
            total = ng.bias
            for from_nid, weight in self._incoming.get(nid, []):
                total += self.activations.get(from_nid, 0.0) * weight

            self.activations[nid] = apply_activation(ng.activation, total)

        # Collect output values
        return [self.activations.get(nid, 0.0) for nid in self._output_ids]

    # ── Action selection ─────────────────────────────────────────────────

    def choose_action(
        self,
        inputs: List[float],
        num_primitive_actions: int,
        num_compound_actions: int = 0,
        exploration_rate: float = 0.2,
    ) -> int:
        """
        Choose an action from brain outputs.
        Uses epsilon-greedy with softmax for exploitation.
        """
        total_actions = num_primitive_actions + num_compound_actions

        # Epsilon-greedy: explore randomly sometimes
        if self.rng.random() < exploration_rate:
            return self.rng.randint(0, total_actions - 1)

        # Get brain outputs
        outputs = self.forward(inputs)

        # Extend outputs for compound actions
        while len(outputs) < total_actions:
            outputs.append(self.rng.gauss(0, 0.1))

        # Softmax selection over available actions
        scores = outputs[:total_actions]
        probs = _softmax(scores)
        r = self.rng.random()
        cumulative = 0.0
        for i, p in enumerate(probs):
            cumulative += p
            if r <= cumulative:
                return i
        return total_actions - 1

    # ── Continuous outputs (for Phase 3) ─────────────────────────────────

    def get_continuous_outputs(self, inputs: List[float]) -> List[float]:
        """
        Get raw output activations for continuous action interpretation.
        Used by Phase 3+ continuous action space.
        """
        return self.forward(inputs)

    # ── Novelty tracking ─────────────────────────────────────────────────

    def check_novelty(self, state: List[float]) -> bool:
        """Check if a state is novel (never seen before)."""
        state_hash = hash(tuple(round(f, 1) for f in state))
        if state_hash not in self.visited_states:
            self.visited_states.add(state_hash)
            if len(self.visited_states) > self.max_visited:
                self.visited_states.pop()
            return True
        return False

    def record_experience(self, reward: float = 0.0) -> None:
        """Record an experience.  Reward baseline is kept for exploration decay only."""
        alpha = cfg.REWARD_BASELINE_ALPHA
        self.reward_baseline = self.reward_baseline * (1.0 - alpha) + reward * alpha
        self.total_experiences += 1

    # ── Brain metrics ────────────────────────────────────────────────────

    @property
    def num_active_nodes(self) -> int:
        return len(self.genome.node_genes)

    @property
    def num_active_connections(self) -> int:
        return sum(1 for c in self.genome.connection_genes.values() if c.enabled)

    @property
    def metabolic_cost(self) -> float:
        """Energy cost per tick for running this brain.

        Includes sensory acuity cost: agents that evolve extreme
        sensory sensitivity pay more energy.  Only gains significantly
        different from 1.0 contribute to the cost.

        Broadcast cost: proportional to active broadcast channels
        (broadcast_width genome trait).  Unused channels are free.
        """
        base = (
            self.num_active_nodes * cfg.NEURON_COST +
            self.num_active_connections * cfg.CONNECTION_COST
        )
        # Sensory cost: proportional to total deviation from neutral gain
        sensory_excess = 0.0
        for g in self.genome.sensory_gains:
            sensory_excess += abs(g - 1.0)  # Neutral gain is 1.0
        sensory_cost = sensory_excess * cfg.SENSORY_COST
        # Broadcast cost: only active channels count
        active_bw = int(self.genome.traits.get("broadcast_width", 4))
        broadcast_cost = active_bw * cfg.BROADCAST_COST
        return base + sensory_cost + broadcast_cost

    def weight_magnitude(self) -> float:
        """Total absolute weight magnitude — measures complexity."""
        total = 0.0
        for cg in self.genome.connection_genes.values():
            if cg.enabled:
                total += abs(cg.weight)
        for ng in self.genome.node_genes.values():
            total += abs(ng.bias)
        return total

    # ── Serialization ────────────────────────────────────────────────────

    def serialise(self) -> Dict[str, Any]:
        """Serialize brain state for checkpointing."""
        return {
            "type": "neat",
            "activations": {str(k): round(v, 6) for k, v in self.activations.items()},
            "reward_baseline": self.reward_baseline,
            "total_experiences": self.total_experiences,
            "visited_count": len(self.visited_states),
        }

    @classmethod
    def deserialise(
        cls,
        data: Dict[str, Any],
        genome: Genome,
        rng: random.Random,
    ) -> "NEATBrain":
        """Restore a NEAT brain from serialized data."""
        brain = cls(genome, rng)
        if "activations" in data:
            for k, v in data["activations"].items():
                brain.activations[int(k)] = v
        brain.reward_baseline = data.get("reward_baseline", 0.0)
        brain.total_experiences = data.get("total_experiences", 0)
        return brain

    def __repr__(self) -> str:
        return (
            f"NEATBrain(nodes={self.num_active_nodes}, "
            f"conns={self.num_active_connections}, "
            f"cost={self.metabolic_cost:.3f})"
        )


# ── Utility functions ────────────────────────────────────────────────────────

def _softmax(scores: List[float]) -> List[float]:
    """Softmax over a list of scores."""
    if not scores:
        return []
    max_s = max(scores)
    exps = [math.exp(min(s - max_s, 20.0)) for s in scores]
    total = sum(exps)
    if total == 0:
        n = len(scores)
        return [1.0 / n] * n
    return [e / total for e in exps]


def compute_reward(**_kwargs: Any) -> float:
    """
    DEPRECATED: compute_reward is vestigial.

    The NEAT brain evolves through natural selection, not reward-based learning.
    Internal drives are now evolvable genome traits (harvest_drive, maintain_drive, etc.)
    rather than an engineered reward function.

    This stub remains only for backward compatibility with any code that still
    calls it.  It returns 0.0 — the brain's record_experience() only increments
    the experience counter for exploration decay.
    """
    return 0.0


def setup_initial_brain(genome: Genome, num_inputs: int, num_outputs: int, rng: random.Random) -> None:
    """
    Initialize a genome's NEAT topology with input and output nodes
    and random sparse connections.  Called when creating a brand new agent.
    """
    from agents.genome import next_innovation

    # Create input nodes
    for i in range(num_inputs):
        genome.node_genes[i] = NodeGene(i, "input", "identity", 0.0)

    # Create output nodes
    for i in range(num_outputs):
        nid = num_inputs + i
        genome.node_genes[nid] = NodeGene(nid, "output", "tanh", 0.0)

    # Random sparse connections
    input_ids = list(range(num_inputs))
    output_ids = list(range(num_inputs, num_inputs + num_outputs))
    possible = [(inp, out) for inp in input_ids for out in output_ids]
    rng.shuffle(possible)
    num_initial = min(cfg.NEAT_INITIAL_CONNECTIONS, len(possible))
    for inp, out in possible[:num_initial]:
        inn = next_innovation(inp, out)
        w = rng.uniform(*cfg.NEAT_WEIGHT_RANGE)
        genome.connection_genes[inn] = ConnectionGene(inn, inp, out, w, True)

