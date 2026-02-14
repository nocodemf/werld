"""
Substrate — a graph-based resource network.

Agents live on nodes in a graph.  There is no grid, no compass, no
2-D space.  Connectivity IS the physics: some nodes have many links
(hubs), some have few (periphery).  Distance is measured in hops.

The initial topology is a Watts-Strogatz small-world graph:
  - Mostly local connections (clusters)
  - Some long-range shortcuts (bridging)
  - Properties similar to real computational networks

This is the computational world.  Agents navigate it, extract energy
from nodes, and discover its structure through exploration.
"""

from __future__ import annotations

import math
import random
from collections import deque
from typing import List, Tuple, Optional, Dict, Set, Any

import config as cfg


class GraphNode:
    """A single node in the resource graph with pheromone support."""

    __slots__ = ("id", "energy", "neighbors", "vis_x", "vis_y", "pheromone")

    def __init__(self, node_id: int, energy: float = 0.0,
                 vis_x: float = 0.0, vis_y: float = 0.0) -> None:
        self.id: int = node_id
        self.energy: float = energy
        self.neighbors: List[int] = []   # IDs of connected nodes
        self.vis_x: float = vis_x        # For dashboard visualization only
        self.vis_y: float = vis_y
        self.pheromone: float = 0.0      # Chemical trace left by agents

    @property
    def degree(self) -> int:
        return len(self.neighbors)

    def regenerate(self, regen_rate: float = -1.0) -> None:
        """Add passive energy regeneration, capped at max."""
        rate = regen_rate if regen_rate >= 0.0 else cfg.ENERGY_REGEN_RATE
        self.energy = min(self.energy + rate, cfg.ENERGY_MAX_PER_NODE)

    def extract(self, amount: float) -> float:
        """Remove up to *amount* energy from this node; return actual extracted."""
        extracted = min(amount, self.energy)
        self.energy = max(self.energy - extracted, cfg.ENERGY_MIN_PER_NODE)
        return extracted

    def deposit_pheromone(self, amount: float) -> None:
        """Deposit pheromone on this node, capped at max."""
        self.pheromone = min(self.pheromone + amount, cfg.PHEROMONE_MAX)

    def decay_pheromone(self) -> None:
        """Decay pheromone by the configured rate."""
        self.pheromone *= (1.0 - cfg.PHEROMONE_DECAY_RATE)
        if self.pheromone < 0.001:
            self.pheromone = 0.0

    def __repr__(self) -> str:
        return f"Node({self.id}, e={self.energy:.1f}, ph={self.pheromone:.2f}, deg={self.degree})"


class Substrate:
    """Graph-based resource network.  No grids, no coordinates."""

    def __init__(
        self,
        num_nodes: int = cfg.SUBSTRATE_NUM_NODES,
        avg_degree: int = cfg.SUBSTRATE_AVG_DEGREE,
        rewire_prob: float = cfg.SUBSTRATE_REWIRE_PROB,
        rng: Optional[random.Random] = None,
    ) -> None:
        self.rng = rng or random.Random()
        self.tick: int = 0
        self.num_nodes_count: int = num_nodes
        self.nodes: Dict[int, GraphNode] = {}

        self._build_small_world(num_nodes, avg_degree, rewire_prob)

    # ── Graph generation ──────────────────────────────────────────────────

    def _build_small_world(self, n: int, k: int, p: float) -> None:
        """
        Generate a Watts-Strogatz small-world graph.

        1. Arrange N nodes in a ring
        2. Connect each to K/2 nearest neighbors on each side
        3. Rewire each edge with probability P (creates shortcuts)
        4. Assign random energy to a fraction of nodes
        """
        half_k = max(1, k // 2)

        # Create nodes arranged in a circle (for visualization layout)
        for i in range(n):
            angle = 2.0 * math.pi * i / n
            # Map to a 100x100 visualization space
            vis_x = 50.0 + 45.0 * math.cos(angle)
            vis_y = 50.0 + 45.0 * math.sin(angle)

            energy = 0.0
            if self.rng.random() < cfg.ENERGY_SEED_DENSITY:
                energy = self.rng.uniform(*cfg.ENERGY_SEED_RANGE)

            self.nodes[i] = GraphNode(i, energy, vis_x, vis_y)

        # Step 2: Ring lattice — connect to nearest neighbors
        for i in range(n):
            for j in range(1, half_k + 1):
                right = (i + j) % n
                left = (i - j) % n
                self._add_edge(i, right)
                self._add_edge(i, left)

        # Step 3: Rewire edges with probability p
        for i in range(n):
            neighbors_copy = list(self.nodes[i].neighbors)
            for old_neighbor in neighbors_copy:
                if self.rng.random() < p:
                    # Pick a random new target (not self, not already connected)
                    attempts = 0
                    while attempts < 20:
                        new_target = self.rng.randint(0, n - 1)
                        if (new_target != i and
                                new_target not in self.nodes[i].neighbors):
                            self._remove_edge(i, old_neighbor)
                            self._add_edge(i, new_target)
                            break
                        attempts += 1

        # Sort each node's neighbor list for deterministic traversal
        for node in self.nodes.values():
            node.neighbors.sort()

        # Verify connectivity — if disconnected, add bridges
        self._ensure_connected(n)

    def _add_edge(self, a: int, b: int) -> None:
        """Add an undirected edge between nodes a and b."""
        if b not in self.nodes[a].neighbors:
            self.nodes[a].neighbors.append(b)
        if a not in self.nodes[b].neighbors:
            self.nodes[b].neighbors.append(a)

    def _remove_edge(self, a: int, b: int) -> None:
        """Remove an undirected edge between nodes a and b."""
        if b in self.nodes[a].neighbors:
            self.nodes[a].neighbors.remove(b)
        if a in self.nodes[b].neighbors:
            self.nodes[b].neighbors.remove(a)

    def _ensure_connected(self, n: int) -> None:
        """If graph is disconnected, bridge the components."""
        visited: Set[int] = set()
        components: List[List[int]] = []

        for start in range(n):
            if start in visited:
                continue
            component: List[int] = []
            queue = deque([start])
            while queue:
                node = queue.popleft()
                if node in visited:
                    continue
                visited.add(node)
                component.append(node)
                for neighbor in self.nodes[node].neighbors:
                    if neighbor not in visited:
                        queue.append(neighbor)
            components.append(component)

        # Bridge disconnected components
        for i in range(1, len(components)):
            # Connect a random node from this component to a random node in component 0
            a = self.rng.choice(components[0])
            b = self.rng.choice(components[i])
            self._add_edge(a, b)
            components[0].extend(components[i])

    # ── Accessors ────────────────────────────────────────────────────────

    def node(self, node_id: int) -> GraphNode:
        """Return the node with the given ID."""
        return self.nodes[node_id]

    def neighbor_nodes(self, node_id: int, hops: int = 1) -> List[GraphNode]:
        """
        Return all nodes within `hops` graph distance (excluding the node itself).
        Uses BFS.
        """
        if hops <= 0:
            return []

        visited: Set[int] = {node_id}
        frontier: List[int] = [node_id]
        result: List[GraphNode] = []

        for _ in range(hops):
            next_frontier: List[int] = []
            for nid in frontier:
                for neighbor_id in self.nodes[nid].neighbors:
                    if neighbor_id not in visited:
                        visited.add(neighbor_id)
                        next_frontier.append(neighbor_id)
                        result.append(self.nodes[neighbor_id])
            frontier = next_frontier

        return result

    def graph_distance(self, a_id: int, b_id: int, max_dist: int = 20) -> int:
        """
        BFS shortest path distance between two nodes.
        Returns max_dist+1 if not reachable within max_dist hops.
        """
        if a_id == b_id:
            return 0

        visited: Set[int] = {a_id}
        frontier: List[int] = [a_id]

        for dist in range(1, max_dist + 1):
            next_frontier: List[int] = []
            for nid in frontier:
                for neighbor_id in self.nodes[nid].neighbors:
                    if neighbor_id == b_id:
                        return dist
                    if neighbor_id not in visited:
                        visited.add(neighbor_id)
                        next_frontier.append(neighbor_id)
            frontier = next_frontier
            if not frontier:
                break

        return max_dist + 1

    def nodes_within_range(self, start_id: int, max_hops: int) -> Dict[int, int]:
        """
        BFS from start_id.  Returns {node_id: distance} for all nodes
        within max_hops (excluding start).
        """
        visited: Dict[int, int] = {start_id: 0}
        frontier: List[int] = [start_id]

        for dist in range(1, max_hops + 1):
            next_frontier: List[int] = []
            for nid in frontier:
                for neighbor_id in self.nodes[nid].neighbors:
                    if neighbor_id not in visited:
                        visited[neighbor_id] = dist
                        next_frontier.append(neighbor_id)
            frontier = next_frontier
            if not frontier:
                break

        # Remove start node from result
        visited.pop(start_id, None)
        return visited

    def random_node_id(self) -> int:
        """Return a random node ID."""
        return self.rng.choice(list(self.nodes.keys()))

    def move_agent(self, from_node: int, direction: int) -> int:
        """
        Move from `from_node` in `direction`.
        Direction maps to neighbor index: neighbors[direction % degree].
        Returns the destination node ID.
        """
        node = self.nodes[from_node]
        if not node.neighbors:
            return from_node  # Stuck (shouldn't happen in connected graph)
        target_idx = direction % len(node.neighbors)
        return node.neighbors[target_idx]

    def vis_pos(self, node_id: int) -> Tuple[float, float]:
        """Return visualization coordinates for a node."""
        node = self.nodes[node_id]
        return (node.vis_x, node.vis_y)

    # ── Per-tick update ──────────────────────────────────────────────────

    def update(self) -> None:
        """
        Advance the substrate by one tick.
        - Regenerate energy (with seasonal modulation)
        - Decay pheromones
        """
        self.tick += 1

        # Seasonal modulation of regeneration rate
        regen_rate = cfg.ENERGY_REGEN_RATE
        if cfg.SEASONS_ENABLED:
            # Sinusoidal cycle: regen varies from (1-amp)*base to (1+amp)*base
            phase = 2.0 * math.pi * self.tick / max(cfg.SEASON_PERIOD, 1)
            season_factor = 1.0 + cfg.SEASON_AMPLITUDE * math.sin(phase)
            regen_rate *= max(0.0, season_factor)

        for node in self.nodes.values():
            node.regenerate(regen_rate)
            if cfg.PHEROMONE_ENABLED:
                node.decay_pheromone()

    def season_phase(self) -> float:
        """Return current season phase as a 0-1 value (0=winter, 0.5=summer)."""
        if not cfg.SEASONS_ENABLED:
            return 0.5
        phase = (self.tick % max(cfg.SEASON_PERIOD, 1)) / max(cfg.SEASON_PERIOD, 1)
        return phase

    def season_regen_multiplier(self) -> float:
        """Return current seasonal regeneration multiplier."""
        if not cfg.SEASONS_ENABLED:
            return 1.0
        phase = 2.0 * math.pi * self.tick / max(cfg.SEASON_PERIOD, 1)
        return max(0.0, 1.0 + cfg.SEASON_AMPLITUDE * math.sin(phase))

    def deposit_agent_pheromone(self, node_id: int, energy_fraction: float = 0.5) -> None:
        """
        Deposit pheromone on a node from an agent visit.
        If PHEROMONE_ENERGY_SCALE, deposit proportional to agent's energy fraction.
        """
        if not cfg.PHEROMONE_ENABLED:
            return
        amount = cfg.PHEROMONE_DEPOSIT_RATE
        if cfg.PHEROMONE_ENERGY_SCALE:
            amount *= max(0.1, energy_fraction)
        self.nodes[node_id].deposit_pheromone(amount)

    def pheromone_at(self, node_id: int) -> float:
        """Return pheromone level at a node."""
        return self.nodes[node_id].pheromone if cfg.PHEROMONE_ENABLED else 0.0

    # ── Aggregate stats ──────────────────────────────────────────────────

    def total_energy(self) -> float:
        return sum(node.energy for node in self.nodes.values())

    def num_nodes(self) -> int:
        return len(self.nodes)

    def avg_degree(self) -> float:
        if not self.nodes:
            return 0.0
        return sum(n.degree for n in self.nodes.values()) / len(self.nodes)

    def snapshot(self) -> Dict[str, Any]:
        """Return a lightweight dict summarising the substrate state."""
        return {
            "tick": self.tick,
            "total_energy": round(self.total_energy(), 1),
            "num_nodes": self.num_nodes(),
            "avg_degree": round(self.avg_degree(), 2),
        }

    def __repr__(self) -> str:
        return (
            f"Substrate(nodes={self.num_nodes()}, "
            f"avg_deg={self.avg_degree():.1f}, "
            f"energy={self.total_energy():.0f})"
        )
