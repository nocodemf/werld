"""
Logger — CLI narration and state dumps.

Prints structured output each tick and periodically writes human-readable
state dumps to disk for inspection while the simulation runs.
"""

from __future__ import annotations

import os
import time
from typing import List, Optional, TYPE_CHECKING

import config as cfg

if TYPE_CHECKING:
    from agents.agent import Agent
    from engine.substrate import Substrate


class SimLogger:
    """Structured CLI output + file-based state dumps."""

    def __init__(self, verbose: bool = cfg.VERBOSE) -> None:
        self.verbose = verbose
        self.total_births = 0
        self.total_deaths = 0
        self._start_time = time.time()

    def tick_header(
        self,
        tick: int,
        population: int,
        substrate_energy: float,
    ) -> None:
        elapsed = time.time() - self._start_time
        tps = tick / elapsed if elapsed > 0 else 0
        print(
            f"\n=== Tick {tick} | Pop: {population} | "
            f"Substrate: {substrate_energy:.0f}e | "
            f"B:{self.total_births} D:{self.total_deaths} | "
            f"{tps:.1f} t/s ==="
        )

    def agent_actions(self, agents: List[Agent]) -> None:
        if not self.verbose:
            return
        for agent in agents:
            if agent.alive:
                print(f"  {agent.status_line()}")

    def events(self, event_lines: List[str]) -> None:
        for line in event_lines:
            print(f"  -- {line}")

    def death_report(self, death_events: List[str]) -> None:
        for line in death_events:
            self.total_deaths += 1
            print(f"  ** {line}")

    def birth_report(self, birth_events: List[str]) -> None:
        for line in birth_events:
            self.total_births += 1
            print(f"  ++ {line}")

    def compound_discovery(self, agent_id: int, name: str, sequence: list) -> None:
        from agents.cortex import ACTION_NAMES
        seq_desc = " -> ".join(ACTION_NAMES.get(a, f"a{a}") for a in sequence)
        print(f"  ~~ Agent-{agent_id} discovered macro '{name}': [{seq_desc}]")

    def brain_decision(self, agent_id: int, info: str) -> None:
        print(f"  >> Agent-{agent_id} brain: {info}")

    def extinction(self, tick: int) -> None:
        elapsed = time.time() - self._start_time
        print(f"\n{'='*60}")
        print(f"  EXTINCTION at tick {tick} ({elapsed:.0f}s elapsed)")
        print(f"  Total births: {self.total_births}")
        print(f"  Total deaths: {self.total_deaths}")
        print(f"{'='*60}")

    def summary(self, tick: int, agents: List[Agent], comms_info: Optional[dict] = None) -> None:
        alive = [a for a in agents if a.alive]
        if not alive:
            return

        avg_energy = sum(a.energy for a in alive) / len(alive)
        avg_entropy = sum(a.state.entropy for a in alive) / len(alive)
        avg_age = sum(a.state.age for a in alive) / len(alive)
        max_gen = max(a.generation for a in alive)
        avg_cortex = sum(a.cortex.num_associations() for a in alive) / len(alive)
        avg_memory = sum(len(a.memory) for a in alive) / len(alive)
        total_macros = sum(len(a.compound_actions) for a in alive)
        total_brain_exp = sum(a.brain.total_experiences if a.brain else 0 for a in alive)
        total_brain_trains = sum(getattr(a.brain, 'total_trains', 0) if a.brain else 0 for a in alive)
        elapsed = time.time() - self._start_time

        print(f"\n--- Summary at tick {tick} ({elapsed:.0f}s) ---")
        print(f"  Alive: {len(alive)} | Births: {self.total_births} | Deaths: {self.total_deaths}")
        print(f"  Avg energy: {avg_energy:.1f} | Avg entropy: {avg_entropy:.1f} | Avg age: {avg_age:.0f}")
        print(f"  Max gen: {max_gen} | Avg cortex: {avg_cortex:.0f} | Avg memory: {avg_memory:.0f}")
        print(f"  Total macros: {total_macros} | Brain exp: {total_brain_exp} | Brain trains: {total_brain_trains}")
        if comms_info:
            print(f"  Signals: {comms_info['sent']} sent → {comms_info['delivered']} delivered | "
                  f"Senders: {comms_info['senders']} | Receivers: {comms_info['receivers']} | "
                  f"Avg hops: {comms_info['avg_dist']:.1f}")

    def checkpoint_saved(self, path: str, tick: int) -> None:
        print(f"  [SAVE] Checkpoint saved at tick {tick}: {os.path.basename(path)}")

    def state_dump(self, tick: int, agents: List[Agent], substrate) -> None:
        """Write a human-readable state dump to disk."""
        os.makedirs(cfg.DATA_DIR, exist_ok=True)
        dump_path = os.path.join(cfg.DATA_DIR, "latest_state.txt")

        alive = [a for a in agents if a.alive]
        elapsed = time.time() - self._start_time

        lines = [
            f"{'='*70}",
            f"WERLD — STATE DUMP (Graph Topology)",
            f"Tick: {tick} | Elapsed: {elapsed:.0f}s | Population: {len(alive)}",
            f"Births: {self.total_births} | Deaths: {self.total_deaths}",
            f"Graph: {substrate.num_nodes()} nodes, avg degree {substrate.avg_degree():.1f}",
            f"Substrate Energy: {substrate.total_energy():.0f}",
            f"{'='*70}",
            "",
        ]

        for agent in alive:
            s = agent.state
            g = agent.genome.traits
            node = substrate.node(s.node_id)
            lines.append(f"--- Agent-{agent.id} (gen {agent.generation}, age {s.age}) ---")
            lines.append(f"  Energy: {s.energy:.1f}/{g['max_energy']:.0f} | Entropy: {s.entropy:.1f}")
            lines.append(f"  Node: {s.node_id} (degree {node.degree}, energy {node.energy:.1f})")
            lines.append(f"  Cortex: {agent.cortex.num_associations()} assoc, {agent.cortex.experience} exp")
            lines.append(f"  Memory: {len(agent.memory)} episodes")
            lines.append(f"  Macros: {len(agent.compound_actions)}")
            if agent.brain:
                wm = agent.brain.weight_magnitude()
                lines.append(
                    f"  Brain: {agent.brain.total_experiences} exp, "
                    f"{getattr(agent.brain, 'total_trains', 0)} trains, weight_mag={wm:.1f}, "
                    f"baseline={agent.brain.reward_baseline:.3f}"
                )
            lines.append(f"  Genome: tick_cost={g['tick_cost']:.2f} sense={g['sense_range']:.0f} "
                         f"max_e={g['max_energy']:.0f} ent_res={g['entropy_resistance']:.2f} "
                         f"lr={g['learning_rate']:.3f} explore={g['exploration_factor']:.2f} "
                         f"cult={g.get('cultural_transfer', 0):.2f} "
                         f"kt={g.get('knowledge_transfer', 0.5):.2f}")
            if agent.compound_actions:
                from agents.cortex import ACTION_NAMES
                for name, ca in agent.compound_actions.items():
                    seq_desc = " -> ".join(ACTION_NAMES.get(a, f"a{a}") for a in ca["sequence"])
                    lines.append(f"    Macro '{name}': [{seq_desc}] (used {ca['success_count']}x)")
            lines.append("")

        with open(dump_path, "w") as f:
            f.write("\n".join(lines))

    def interrupted(self, tick: int, agents: List[Agent]) -> None:
        print(f"\n\n{'='*60}")
        print(f"  Simulation interrupted at tick {tick}")
        self.summary(tick, agents)
        print(f"{'='*60}")
