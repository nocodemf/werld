"""
Forking — reproduction with NEAT-style brain evolution.

When two agents fork:
  1. Each parent contributes energy
  2. Genomes cross over with NEAT-style topology alignment
  3. Child genome is mutated (weight, bias, structural, activation)
  4. Cortex weights are partially inherited (cultural_transfer trait)
  5. NEAT brain topology is inherited from the genome (no separate brain inheritance)
  6. Compound actions can be inherited (with mutation)

Brain inheritance is now implicit: the child's genome contains the
evolved topology, which the NEATBrain constructor uses directly.
"""

from __future__ import annotations

import random
from typing import List, Tuple, Dict, Any, TYPE_CHECKING

import config as cfg
from agents.genome import Genome
from agents.cortex import Cortex, NUM_ACTIONS
from agents.agent import Agent
from agents.memory import EpisodicMemory
from systems.evolution import CompoundAction, mutate_compound_action

if TYPE_CHECKING:
    from engine.substrate import Substrate


def resolve_forks(
    agents: List[Agent],
    substrate: "Substrate",
    rng: random.Random,
) -> Tuple[List[Agent], List[str]]:
    """
    Process all fork requests from this tick.
    Returns (new_agents, event_descriptions).
    """
    new_agents: List[Agent] = []
    events: List[str] = []
    used_ids: set = set()

    for agent in agents:
        if not agent.alive:
            continue
        result = agent.state.last_action_result
        if not isinstance(result, dict) or result.get("type") != "fork_request":
            continue
        if agent.id in used_ids:
            continue

        partner_id = result["partner_id"]
        partner = None
        for other in agents:
            if other.id == partner_id and other.alive and other.id not in used_ids:
                partner = other
                break

        if partner is None:
            continue

        if agent.energy < cfg.FORK_PARENT_ENERGY_CONTRIBUTION:
            continue
        if partner.energy < cfg.FORK_PARENT_ENERGY_CONTRIBUTION:
            continue

        # Execute fork
        agent.state.spend_energy(cfg.FORK_PARENT_ENERGY_CONTRIBUTION)
        partner.state.spend_energy(cfg.FORK_PARENT_ENERGY_CONTRIBUTION)

        # Create offspring genome via NEAT crossover
        child_genome = Genome.crossover(
            agent.genome,
            partner.genome,
            fitness_a=agent.energy,
            fitness_b=partner.energy,
            rng=rng,
        )

        # Apply NEAT mutations to child genome
        child_genome.mutate(rng)

        # Create offspring on parent's node
        child_rng = random.Random(rng.random())
        child = Agent(
            genome=child_genome,
            node_id=agent.state.node_id,
            rng=child_rng,
            generation=max(agent.generation, partner.generation) + 1,
            parent_ids=(agent.id, partner.id),
        )

        # Override energy
        child.state.energy = cfg.FORK_PARENT_ENERGY_CONTRIBUTION * 2
        child.state.entropy = cfg.OFFSPRING_INITIAL_ENTROPY

        # Knowledge transfer: cortex (cultural_transfer trait)
        cultural_transfer = child_genome.traits.get("cultural_transfer", 0.4)
        # Extract evolvable drive weights from child genome for cortex
        drive_traits = {
            k: child_genome.traits.get(k, cfg.GENOME_RANGES.get(k, (0, 1, 0.5))[2])
            for k in (
                "harvest_drive", "maintain_drive", "explore_drive",
                "social_drive", "reproduce_drive", "signal_drive",
            )
        }
        child.cortex = Cortex.inherit(
            parent_a=agent.cortex,
            parent_b=partner.cortex,
            capacity=int(child_genome.traits["cortex_capacity"]),
            learning_rate=child_genome.traits["learning_rate"],
            exploration_factor=child_genome.traits["exploration_factor"],
            cultural_transfer=cultural_transfer,
            rng=child_rng,
            drive_weights=drive_traits,
            resolution=int(child_genome.traits.get("cortex_resolution", 4)),
        )

        # Brain is already created by the Agent constructor from the genome's topology.
        # No separate brain inheritance needed — it's encoded in the NEAT genome.

        # Inherit compound actions
        _inherit_compound_actions(child, agent, partner, child_rng)

        new_agents.append(child)
        used_ids.add(agent.id)
        used_ids.add(partner.id)

        brain_info = ""
        if child.brain:
            brain_info = (
                f", neat({child.brain.num_active_nodes}n/"
                f"{child.brain.num_active_connections}c,"
                f"cost={child.brain.metabolic_cost:.2f})"
            )
        events.append(
            f"Agent-{agent.id} + Agent-{partner.id} forked -> Agent-{child.id} "
            f"(gen {child.generation}) at node {child.state.node_id} "
            f"[cortex:{child.cortex.num_associations()}, "
            f"macros:{len(child.compound_actions)}{brain_info}]"
        )

    return new_agents, events


def _inherit_compound_actions(
    child: Agent,
    parent_a: Agent,
    parent_b: Agent,
    rng: random.Random,
) -> None:
    """Transfer compound actions from parents to child with mutation."""
    all_cas: Dict[str, Dict[str, Any]] = {}
    for name, ca_dict in parent_a.compound_actions.items():
        all_cas[f"a_{name}"] = ca_dict
    for name, ca_dict in parent_b.compound_actions.items():
        all_cas[f"b_{name}"] = ca_dict

    for name, ca_dict in all_cas.items():
        if rng.random() > cfg.COMPOUND_INHERIT_CHANCE:
            continue
        macro_cap = int(child.genome.traits.get("macro_capacity", cfg.MAX_COMPOUND_ACTIONS))
        if len(child.compound_actions) >= macro_cap:
            break

        ca = CompoundAction(
            name=name,
            sequence=list(ca_dict["sequence"]),
            success_count=0,
        )
        mutation_rate = child.genome.traits.get("mutation_rate", 0.05)
        max_ml = int(child.genome.traits.get("macro_pattern_length", cfg.MAX_COMPOUND_LENGTH))
        mutated = mutate_compound_action(ca, rng, mutation_rate, NUM_ACTIONS, max_length=max_ml)

        child.compound_actions[mutated.name] = {
            "sequence": mutated.sequence,
            "success_count": 0,
            "discovered_tick": mutated.discovered_tick,
        }
