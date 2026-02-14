"""
Simulation — the master tick loop with persistence.

Orchestrates substrate (graph), agents, and all systems each tick.
Supports auto-save, state dumps, event logging, and resume from checkpoint.
Runs indefinitely until population = 0 or user interrupts.
"""

from __future__ import annotations

import json
import random
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

import config as cfg
from engine.substrate import Substrate, GraphNode
from agents.agent import Agent, reset_id_counter
from agents.genome import Genome
from agents.cortex import ACTION_NAMES, NUM_ACTIONS
from systems.actions import execute_action, interpret_effectors
from systems.signals import propagate_signals
from systems.forking import resolve_forks
from systems.entropy import apply_entropy_decay, collect_deaths
from utils.logger import SimLogger
from utils.events import TickEvents
from persistence.event_log import (
    log_event, log_birth, log_death, log_population_stats, log_agent_snapshot,
    log_comms_stats, log_signal_batch,
)
from persistence.state_store import save_checkpoint, save_milestone, get_latest_checkpoint
from persistence.db import prune_old_data
from persistence.story import generate_chapter, save_substrate_topology, STORY_CHAPTER_EVERY


class Simulation:
    """Top-level simulation controller with persistence."""

    def __init__(self, seed: Optional[int] = None) -> None:
        self.seed = seed if seed is not None else cfg.SEED
        self.rng = random.Random(self.seed)
        self.tick = 0

        reset_id_counter()

        # Build graph substrate
        self.substrate = Substrate(rng=random.Random(self.rng.random()))

        # Spawn initial agents on random nodes near each other
        self.agents: List[Agent] = []
        # Pick a starting node and its neighbor for the initial pair
        start_node = self.substrate.random_node_id()
        start_neighbors = self.substrate.nodes[start_node].neighbors
        second_node = start_neighbors[0] if start_neighbors else start_node

        spawn_nodes = [start_node, second_node]
        for i in range(cfg.INITIAL_AGENT_COUNT):
            genome = Genome.random(rng=random.Random(self.rng.random()))
            node_id = spawn_nodes[i % len(spawn_nodes)]
            agent = Agent(
                genome=genome,
                node_id=node_id,
                rng=random.Random(self.rng.random()),
                generation=0,
            )
            self.agents.append(agent)

        # Log initial agents to lineage
        for agent in self.agents:
            log_birth(0, agent.id, -1, -1, 0, agent.genome.to_json())

        # Systems
        self.logger = SimLogger()
        self.events = TickEvents()
        self._last_signal_summary = None

        # Store substrate topology for dashboard world visualization
        save_substrate_topology(self.substrate)

    @classmethod
    def from_checkpoint(cls, path: str) -> "Simulation":
        """Resume a simulation from a checkpoint file."""
        from persistence.state_store import load_checkpoint, deserialise_rng
        from agents.memory import EpisodicMemory
        from agents.cortex import Cortex
        from agents.genome import (
            Genome, NodeGene, ConnectionGene,
            reset_innovation_counter,
        )
        from reasoning.neat_brain import NEATBrain

        data = load_checkpoint(path)

        sim = object.__new__(cls)
        sim.seed = data["seed"]
        sim.tick = data["tick"]
        sim.rng = deserialise_rng(data["rng_state"])
        sim.events = TickEvents()
        sim.logger = SimLogger()
        sim._last_signal_summary = None
        sim.logger.total_births = data["stats"]["total_births"]
        sim.logger.total_deaths = data["stats"]["total_deaths"]

        # Restore innovation counter
        innov_counter = data.get("innovation_counter", 0)
        innov_cache_raw = data.get("innovation_cache", {})
        innov_cache = {}
        for k, v in innov_cache_raw.items():
            parts = k.split(":")
            innov_cache[(int(parts[0]), int(parts[1]))] = v
        reset_innovation_counter(innov_counter, innov_cache)

        # Restore graph substrate
        sub_data = data["substrate"]
        sub_rng = random.Random(sim.rng.random())

        sim.substrate = object.__new__(Substrate)
        sim.substrate.rng = sub_rng
        sim.substrate.tick = sub_data["tick"]
        sim.substrate.num_nodes_count = sub_data["num_nodes"]
        sim.substrate.nodes = {}

        for nid_str, node_data in sub_data["nodes"].items():
            nid = int(nid_str)
            node = GraphNode(
                nid,
                energy=node_data["energy"],
                vis_x=node_data.get("vis_x", 0.0),
                vis_y=node_data.get("vis_y", 0.0),
            )
            node.neighbors = list(node_data["neighbors"])
            node.pheromone = node_data.get("pheromone", 0.0)
            sim.substrate.nodes[nid] = node

        # Restore agents
        reset_id_counter(data["next_agent_id"])
        sim.agents = []
        for a_data in data["agents"]:
            # Restore genome (handles both old-style and NEAT-style)
            genome_data = a_data["genome"]
            if isinstance(genome_data, dict) and "traits" in genome_data:
                # New NEAT-style genome
                import json as _json
                genome = Genome.from_json(_json.dumps(genome_data))
            elif isinstance(genome_data, dict):
                # Old-style: just traits dict
                genome = Genome(genome_data)
            else:
                genome = Genome({})

            agent_rng = deserialise_rng(a_data["rng_state"])

            agent = object.__new__(Agent)
            agent.id = a_data["id"]
            agent.genome = genome
            agent.rng = agent_rng
            agent.generation = a_data["generation"]
            agent.parent_ids = tuple(a_data["parent_ids"])

            # Restore state
            from agents.state import AgentState
            s = a_data["state"]
            agent.state = AgentState(
                energy=s["energy"],
                node_id=s.get("node_id", s.get("position", [0, 0])[0] if isinstance(s.get("position"), list) else 0),
                entropy=s["entropy"],
            )
            agent.state.age = s["age"]
            agent.state.alive = s["alive"]
            agent.state.inventory = s.get("inventory", 0.0)

            # Restore cortex (with genome-driven drive weights)
            c_data = a_data["cortex"]
            drive_traits = {
                k: genome.traits.get(k, cfg.GENOME_RANGES.get(k, (0, 1, 0.5))[2])
                for k in (
                    "harvest_drive", "maintain_drive", "explore_drive",
                    "social_drive", "reproduce_drive", "signal_drive",
                )
            }
            agent.cortex = Cortex(
                capacity=c_data["capacity"],
                learning_rate=c_data["learning_rate"],
                exploration_factor=c_data["exploration_factor"],
                rng=agent_rng,
                drive_weights=drive_traits,
            )
            agent.cortex.experience = c_data["experience"]
            for key_str, w in c_data["weights"].items():
                sh, aid = key_str.split(":")
                agent.cortex.weights[(int(sh), int(aid))] = w

            # Restore memory (with evolvable decay and social weight)
            agent.memory = EpisodicMemory.deserialise(
                a_data.get("memory", []),
                int(genome.traits.get("memory_capacity", 40)),
                decay_rate=genome.traits.get("memory_decay", 0.95),
                social_weight=genome.traits.get("memory_social_weight", 0.5),
            )

            # Restore compound actions
            agent.compound_actions = {}
            for name, ca_data in a_data.get("compound_actions", {}).items():
                agent.compound_actions[name] = {
                    "sequence": ca_data["sequence"],
                    "success_count": ca_data["success_count"],
                    "discovered_tick": ca_data.get("discovered_tick", 0),
                }

            # Restore NEAT brain
            agent.brain = None
            if cfg.BRAIN_ENABLED:
                brain_data = a_data.get("brain")
                if brain_data and brain_data.get("type") == "neat":
                    # NEAT brain — restore from genome topology
                    from agents.agent import NUM_SENSORY_INPUTS, NUM_OUTPUTS
                    from reasoning.neat_brain import setup_initial_brain
                    if not genome.node_genes:
                        setup_initial_brain(genome, NUM_SENSORY_INPUTS, NUM_OUTPUTS, agent_rng)
                    agent.brain = NEATBrain.deserialise(brain_data, genome, agent_rng)
                elif brain_data:
                    # Legacy NativeBrain — create a fresh NEAT brain for this agent
                    from agents.agent import NUM_SENSORY_INPUTS, NUM_OUTPUTS
                    from reasoning.neat_brain import setup_initial_brain
                    if not genome.node_genes:
                        setup_initial_brain(genome, NUM_SENSORY_INPUTS, NUM_OUTPUTS, agent_rng)
                    agent.brain = NEATBrain(genome, agent_rng)
                else:
                    # No brain data — create fresh
                    from agents.agent import NUM_SENSORY_INPUTS, NUM_OUTPUTS
                    from reasoning.neat_brain import setup_initial_brain
                    if not genome.node_genes:
                        setup_initial_brain(genome, NUM_SENSORY_INPUTS, NUM_OUTPUTS, agent_rng)
                    agent.brain = NEATBrain(genome, agent_rng)

            # Sequence tracker
            from systems.evolution import SequenceTracker
            agent.sequence_tracker = SequenceTracker()

            # Brain state tracking
            agent._last_state_features = None
            agent._last_action_id = -1
            from agents.agent import NUM_BROADCAST
            agent._broadcast_buffer = [0.0] * NUM_BROADCAST

            sim.agents.append(agent)

        # Store substrate topology for dashboard world visualization
        save_substrate_topology(sim.substrate)

        print(f"  Resumed from checkpoint: tick {sim.tick}, {len(sim.agents)} agents")
        return sim

    def alive_agents(self) -> List[Agent]:
        return [a for a in self.agents if a.alive]

    def population(self) -> int:
        return len(self.alive_agents())

    # ── Main loop ────────────────────────────────────────────────────────

    def run(self, max_ticks: int = 0) -> None:
        """Run the simulation.  max_ticks=0 means run indefinitely."""
        tick_count = 0

        try:
            while True:
                self.tick += 1
                tick_count += 1
                self.events.clear()

                if max_ticks > 0 and tick_count > max_ticks:
                    break

                # 1. Substrate update
                self.substrate.update()

                alive = self.alive_agents()
                if not alive:
                    self.logger.extinction(self.tick)
                    self._save_and_log(alive)
                    return

                # 2-4. Agent tick cycle
                self._tick_agents(alive)

                # 5. System resolution
                self._resolve_systems(alive)

                # 6. Collect deaths
                newly_dead = [a for a in alive if not a.alive]
                if newly_dead:
                    for a in newly_dead:
                        cause = "energy depletion" if a.state.energy <= 0 else "entropy overload"
                        self.events.deaths.append(
                            f"Agent-{a.id} DIED: {cause} (age={a.state.age}, gen={a.generation})"
                        )
                        log_death(self.tick, a.id, cause, a.state.age, a.generation)

                # 7. Logging
                alive_after = self.alive_agents()
                if self.tick % cfg.LOG_EVERY == 0:
                    self.logger.tick_header(
                        self.tick, len(alive_after), self.substrate.total_energy(),
                    )
                    self.logger.agent_actions(alive_after)
                    if self.events.signals:
                        self.logger.events(self.events.signals)
                    if self.events.births:
                        self.logger.birth_report(self.events.births)
                    if self.events.deaths:
                        self.logger.death_report(self.events.deaths)

                # Periodic summary
                if self.tick % cfg.STATE_DUMP_EVERY == 0:
                    comms_info = None
                    ss = self._last_signal_summary
                    if ss and ss.signals_sent > 0:
                        comms_info = {
                            "sent": ss.signals_sent,
                            "delivered": ss.total_deliveries,
                            "senders": len(ss.unique_senders),
                            "receivers": len(ss.unique_receivers),
                            "avg_dist": ss.avg_distance,
                        }
                    self.logger.summary(self.tick, self.agents, comms_info)
                    self._log_stats(alive_after)
                    self.logger.state_dump(self.tick, self.agents, self.substrate)

                # Auto-save
                if self.tick % cfg.AUTO_SAVE_EVERY == 0:
                    path = save_checkpoint(self)
                    self.logger.checkpoint_saved(path, self.tick)

                # Milestone checkpoint (never deleted)
                if self.tick % cfg.MILESTONE_EVERY == 0:
                    mpath = save_milestone(self)
                    print(f"  [MILESTONE] Saved milestone at tick {self.tick}: {mpath}")

                # Story chapter generation
                if self.tick % STORY_CHAPTER_EVERY == 0 and self.tick > 0:
                    chapter = generate_chapter(self.tick)
                    if chapter:
                        print(f"  [STORY] New chapter written for tick {self.tick}")

                # DB pruning
                if self.tick % cfg.DB_PRUNE_EVERY == 0:
                    deleted = prune_old_data(self.tick)
                    if deleted > 0:
                        print(f"  [PRUNE] Deleted {deleted} old DB rows")

                # Dead agent memory purge
                if self.tick % cfg.DEAD_AGENT_PURGE_EVERY == 0:
                    self._purge_dead_agents()

                # Extinction safeguard
                if cfg.EXTINCTION_SAFEGUARD and len(alive_after) <= 1 and alive_after:
                    self._spawn_safeguard_mutant(alive_after[0])

                # Extinction check
                if not alive_after:
                    if cfg.EXTINCTION_SAFEGUARD:
                        self._spawn_fresh_pair()
                        print(f"  [SAFEGUARD] Population extinct — spawned fresh pair")
                    else:
                        self.logger.extinction(self.tick)
                        self._save_and_log(alive_after)
                        return

        except KeyboardInterrupt:
            self.logger.interrupted(self.tick, self.agents)
            path = save_checkpoint(self)
            self.logger.checkpoint_saved(path, self.tick)
            print("  State saved. Resume with: python3 main.py --resume")

    # ── Agent tick cycle ─────────────────────────────────────────────────

    def _tick_agents(self, alive: List[Agent]) -> None:
        """Run perceive → decide → act → learn for each agent.

        Uses the continuous effector interface: the brain produces a vector
        of muscle activations, and interpret_effectors() resolves them all
        simultaneously into world effects.
        """
        for agent in alive:
            agent.tick_upkeep()
            if not agent.alive:
                continue

            perception = agent.perceive(self.substrate, self.agents)

            # Drives before action
            drive_before = agent.state.drive_vector(agent.genome.traits["max_energy"])

            # Decide — returns continuous effector outputs
            state_hash, effector_outputs, brain_reason = agent.decide(perception, self.tick)

            # Log brain decision if it happened
            if brain_reason:
                log_event(self.tick, "brain_decision", agent.id, brain_reason,
                          {"effectors": effector_outputs[:7], "continuous": True})

            # Act — interpret all effectors simultaneously
            action_desc = interpret_effectors(
                agent, effector_outputs, self.substrate, self.agents, perception,
            )
            agent.state.last_action = action_desc

            # Pheromone deposition — agents leave traces on visited nodes
            if agent.alive and cfg.PHEROMONE_ENABLED:
                energy_frac = agent.state.energy / max(agent.genome.traits["max_energy"], 1.0)
                self.substrate.deposit_agent_pheromone(agent.state.node_id, energy_frac)

            # Drives after action
            drive_after = agent.state.drive_vector(agent.genome.traits["max_energy"])

            # Learn
            if agent.alive:
                old_compound_count = len(agent.compound_actions)
                agent.learn(
                    state_hash, effector_outputs, drive_before, drive_after,
                    self.tick, action_desc, perception,
                )
                # Report new compound action discoveries
                if len(agent.compound_actions) > old_compound_count:
                    for name, ca in list(agent.compound_actions.items())[-1:]:
                        self.logger.compound_discovery(agent.id, name, ca["sequence"])
                        log_event(self.tick, "macro_discovered", agent.id,
                                  f"Discovered macro {name}", {"sequence": ca["sequence"]})

                agent.cortex.decay_unused()

    # ── System resolution ────────────────────────────────────────────────

    def _resolve_systems(self, alive: List[Agent]) -> None:
        """Run all post-action systems."""
        # Signals
        signal_strings, signal_event_objs, signal_summary = propagate_signals(
            alive, self.substrate,
        )
        self.events.signals.extend(signal_strings)
        self._last_signal_summary = signal_summary

        # Log comms stats periodically
        if self.tick % cfg.STATE_DUMP_EVERY == 0 and signal_summary.signals_sent > 0:
            # Average signal channels (generic — works for both structured and unstructured)
            num_ch = max(cfg.BROADCAST_CHANNELS if cfg.UNSTRUCTURED_COMMS else 3, 3)
            avg_channels = [0.0] * num_ch
            if signal_event_objs:
                n = len(signal_event_objs)
                for evt in signal_event_objs:
                    for ch in range(min(len(evt.vector), num_ch)):
                        avg_channels[ch] += evt.vector[ch]
                for ch in range(num_ch):
                    avg_channels[ch] /= n

            log_comms_stats(
                self.tick,
                signals_sent=signal_summary.signals_sent,
                signals_received=signal_summary.signals_received,
                unique_senders=len(signal_summary.unique_senders),
                unique_receivers=len(signal_summary.unique_receivers),
                avg_distance=signal_summary.avg_distance,
                total_deliveries=signal_summary.total_deliveries,
                avg_signal_energy=avg_channels[0] if len(avg_channels) > 0 else 0.0,
                avg_signal_entropy=avg_channels[1] if len(avg_channels) > 1 else 0.0,
                avg_signal_resource=avg_channels[2] if len(avg_channels) > 2 else 0.0,
            )

        # Log signal events periodically
        if self.tick % cfg.STATE_DUMP_EVERY == 0:
            log_signal_batch(self.tick, signal_event_objs)

        # Forking
        new_agents, fork_events = resolve_forks(alive, self.substrate, self.rng)
        self.events.births.extend(fork_events)
        for child in new_agents:
            self.agents.append(child)
            p_ids = child.parent_ids
            log_birth(
                self.tick, child.id,
                p_ids[0] if len(p_ids) > 0 else -1,
                p_ids[1] if len(p_ids) > 1 else -1,
                child.generation, child.genome.to_json(),
            )

        # Entropy
        entropy_events = apply_entropy_decay(alive)
        self.events.deaths.extend(entropy_events)

        # Clear action results
        for agent in alive:
            agent.state.last_action_result = None

    # ── Persistence helpers ──────────────────────────────────────────────

    def _save_and_log(self, alive: List[Agent]) -> None:
        """Final save on extinction or shutdown."""
        path = save_checkpoint(self)
        self.logger.checkpoint_saved(path, self.tick)
        self._log_stats(alive)

    def _purge_dead_agents(self) -> None:
        """Remove long-dead agents from memory to prevent unbounded growth."""
        if len(self.agents) <= cfg.DEAD_AGENT_KEEP_RECENT:
            return
        alive = []
        dead = []
        for a in self.agents:
            if a.alive:
                alive.append(a)
            else:
                dead.append(a)
        # Keep only the most recently dead
        dead.sort(key=lambda a: a.state.age, reverse=True)
        keep_dead = dead[:cfg.DEAD_AGENT_KEEP_RECENT]
        self.agents = alive + keep_dead

    def _spawn_safeguard_mutant(self, survivor: Agent) -> None:
        """Spawn a random mutant near the sole survivor to prevent extinction."""
        genome = Genome.random(rng=random.Random(self.rng.random()))
        neighbors = self.substrate.nodes[survivor.state.node_id].neighbors
        node_id = neighbors[0] if neighbors else survivor.state.node_id
        child = Agent(
            genome=genome,
            node_id=node_id,
            rng=random.Random(self.rng.random()),
            generation=0,
        )
        self.agents.append(child)
        log_birth(self.tick, child.id, -1, -1, 0, child.genome.to_json())
        self.events.births.append(
            f"[SAFEGUARD] Agent-{child.id} spawned near survivor Agent-{survivor.id}"
        )

    def _spawn_fresh_pair(self) -> None:
        """Spawn two fresh agents at a random location after total extinction."""
        start_node = self.substrate.random_node_id()
        neighbors = self.substrate.nodes[start_node].neighbors
        second_node = neighbors[0] if neighbors else start_node
        for nid in [start_node, second_node]:
            genome = Genome.random(rng=random.Random(self.rng.random()))
            agent = Agent(
                genome=genome,
                node_id=nid,
                rng=random.Random(self.rng.random()),
                generation=0,
            )
            self.agents.append(agent)
            log_birth(self.tick, agent.id, -1, -1, 0, agent.genome.to_json())

    def _log_stats(self, alive: List[Agent]) -> None:
        """Log population statistics and brain stats to the database."""
        if not alive:
            log_population_stats(
                self.tick, 0, self.logger.total_births, self.logger.total_deaths,
                0, 0, 0, 0, 0, self.substrate.total_energy(),
            )
            return

        avg_energy = sum(a.energy for a in alive) / len(alive)
        avg_entropy = sum(a.state.entropy for a in alive) / len(alive)
        avg_age = sum(a.state.age for a in alive) / len(alive)
        max_gen = max(a.generation for a in alive)
        avg_cortex = sum(a.cortex.num_associations() for a in alive) / len(alive)

        log_population_stats(
            self.tick, len(alive), self.logger.total_births, self.logger.total_deaths,
            avg_energy, avg_entropy, avg_age, max_gen, avg_cortex,
            self.substrate.total_energy(),
        )

        # Log brain stats
        self._log_brain_stats(alive)

        # Log speciation
        self._log_speciation(alive)

        # Snapshot each agent
        for a in alive:
            log_agent_snapshot(self.tick, a.snapshot_dict())

    def _log_brain_stats(self, alive: List[Agent]) -> None:
        """Log NEAT brain complexity metrics."""
        brains = [a for a in alive if a.brain is not None]
        if not brains:
            return
        from persistence.db import get_connection
        conn = get_connection()
        avg_n = sum(a.brain.num_active_nodes for a in brains) / len(brains)
        avg_c = sum(a.brain.num_active_connections for a in brains) / len(brains)
        max_n = max(a.brain.num_active_nodes for a in brains)
        max_c = max(a.brain.num_active_connections for a in brains)
        avg_cost = sum(a.brain.metabolic_cost for a in brains) / len(brains)
        conn.execute(
            "INSERT OR REPLACE INTO brain_stats VALUES (?,?,?,?,?,?)",
            (self.tick, avg_n, avg_c, max_n, max_c, avg_cost),
        )
        conn.commit()

    def _log_speciation(self, alive: List[Agent]) -> None:
        """Classify agents into species and log stats."""
        if not alive or not cfg.BRAIN_ENABLED:
            return
        from persistence.db import get_connection

        # Simple speciation: group agents by genome compatibility
        species: Dict[int, List[Agent]] = {}
        representatives: List[Tuple[int, "Genome"]] = []  # (species_id, representative_genome)
        next_species_id = 0

        for agent in alive:
            placed = False
            for sp_id, rep_genome in representatives:
                dist = agent.genome.compatibility_distance(rep_genome)
                if dist < cfg.NEAT_COMPAT_THRESHOLD:
                    species[sp_id].append(agent)
                    placed = True
                    break
            if not placed:
                sp_id = next_species_id
                next_species_id += 1
                species[sp_id] = [agent]
                representatives.append((sp_id, agent.genome))

        # Log species stats
        conn = get_connection()
        for sp_id, members in species.items():
            avg_fit = sum(a.energy for a in members) / len(members)
            avg_bn = sum(
                a.brain.num_active_nodes for a in members if a.brain
            ) / max(1, sum(1 for a in members if a.brain))
            avg_bc = sum(
                a.brain.num_active_connections for a in members if a.brain
            ) / max(1, sum(1 for a in members if a.brain))
            conn.execute(
                "INSERT OR REPLACE INTO species_stats VALUES (?,?,?,?,?,?)",
                (self.tick, sp_id, len(members), avg_fit, int(avg_bn), int(avg_bc)),
            )
        conn.commit()
