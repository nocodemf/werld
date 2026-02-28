#!/usr/bin/env python3
"""
Werld — Entry Point

A tick-based simulation where computational entities emerge, survive,
communicate, evolve, and reproduce within a graph-based resource network.

Agents live on nodes in a graph — no grid, no spatial metaphors.
Distance is measured in hops.  The topology creates the physics.

Features:
  - Graph topology: agents traverse a small-world network
  - Multi-channel reward: energy + entropy + survival + novelty
  - Evolvable knowledge transfer: natural selection decides inheritance
  - Self-modification: agents discover compound action macros
  - Native brain: self-training neural network from random weights
  - Persistence: SQLite event log, gzipped checkpoints, auto-save

Usage:
    python3 main.py                    # Fresh start, run indefinitely
    python3 main.py --seed 42          # Fixed seed for reproducibility
    python3 main.py --resume           # Resume from latest checkpoint
    python3 main.py --ticks 500        # Run for 500 ticks then stop
    python3 main.py --quiet            # Suppress per-agent detail
    python3 main.py --no-brain         # Cortex-only (no neural net)
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
import time
import traceback

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config as cfg
from engine.simulation import Simulation
from persistence.state_store import save_checkpoint, get_latest_checkpoint
from persistence.db import get_connection, close_connection

# ── Global reference for signal handler ──────────────────────────────────────
_active_sim: Simulation | None = None


def _sigterm_handler(signum: int, frame) -> None:
    """Save checkpoint on SIGTERM then exit cleanly."""
    if _active_sim is not None:
        print(f"\n  [SIGTERM] Saving checkpoint at tick {_active_sim.tick}...")
        path = save_checkpoint(_active_sim)
        print(f"  [SIGTERM] Saved: {path}")
        close_connection()
    sys.exit(0)


def _build_or_resume(args) -> Simulation:
    """Build a fresh simulation or resume from a checkpoint."""
    if args.resume or args.checkpoint:
        checkpoint_path = args.checkpoint or get_latest_checkpoint()
        if checkpoint_path and os.path.exists(checkpoint_path):
            print(f"  Resuming from: {os.path.basename(checkpoint_path)}")
            return Simulation.from_checkpoint(checkpoint_path)
        else:
            print("  No checkpoint found, starting fresh.")
    return Simulation(seed=args.seed)


def main() -> None:
    global _active_sim

    parser = argparse.ArgumentParser(description="Werld Simulation")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--ticks", type=int, default=0, help="Max ticks (0=indefinite)")
    parser.add_argument("--quiet", action="store_true", help="Suppress per-agent output")
    parser.add_argument("--log-every", type=int, default=cfg.LOG_EVERY, help="Print every N ticks")
    parser.add_argument("--resume", action="store_true", help="Resume from latest checkpoint")
    parser.add_argument("--checkpoint", type=str, default=None, help="Resume from specific checkpoint file")
    parser.add_argument("--no-brain", action="store_true", help="Disable native brain (cortex-only)")
    parser.add_argument("--brain-hidden", type=int, default=None, help="Brain hidden layer size")
    parser.add_argument("--brain-lr", type=float, default=None, help="Brain learning rate")
    parser.add_argument("--watchdog", action="store_true", help="Auto-restart on crash (indefinite)")
    args = parser.parse_args()

    # Apply CLI overrides
    if args.quiet:
        cfg.VERBOSE = False
    if args.log_every:
        cfg.LOG_EVERY = args.log_every
    if args.no_brain:
        cfg.BRAIN_ENABLED = False
    if args.brain_hidden:
        cfg.BRAIN_HIDDEN_SIZE = args.brain_hidden
    if args.brain_lr:
        cfg.BRAIN_LEARNING_RATE = args.brain_lr

    # Ensure data directory exists
    os.makedirs(cfg.DATA_DIR, exist_ok=True)

    # Register SIGTERM handler
    signal.signal(signal.SIGTERM, _sigterm_handler)

    # Initialise database
    get_connection()

    # Banner
    print("=" * 60)
    print("  WERLD")
    print("  Autonomous agents on a graph topology")
    print("=" * 60)

    # Brain status
    brain_status = "disabled"
    if cfg.BRAIN_ENABLED:
        brain_status = f"enabled (hidden={cfg.BRAIN_HIDDEN_SIZE}, lr={cfg.BRAIN_LEARNING_RATE})"

    sim = _build_or_resume(args)
    _active_sim = sim

    print(f"  Seed: {sim.seed or 'random'}")
    print(f"  Graph: {sim.substrate.num_nodes()} nodes, avg degree {sim.substrate.avg_degree():.1f}")
    print(f"  Initial agents: {len(sim.agents)}")
    print(f"  Max ticks: {'indefinite' if args.ticks == 0 else args.ticks}")
    print(f"  Native brain: {brain_status}")
    print(f"  Reward: evolution-only (no engineered reward — drives are genome traits)")
    print(f"  Auto-save every: {cfg.AUTO_SAVE_EVERY} ticks")
    print(f"  Watchdog: {'ON' if args.watchdog else 'off'}")
    print(f"  Data dir: {cfg.DATA_DIR}")
    print("=" * 60)

    # Print initial agent genomes
    if sim.tick == 0:
        print("\n  Initial agents:")
        for agent in sim.agents:
            g = agent.genome.traits
            node = sim.substrate.node(agent.state.node_id)
            print(
                f"    Agent-{agent.id} at node {agent.state.node_id} (deg={node.degree}) | "
                f"tick_cost={g['tick_cost']:.2f} sense={g['sense_range']:.0f} "
                f"max_e={g['max_energy']:.0f} ent_res={g['entropy_resistance']:.2f} "
                f"explore={g['exploration_factor']:.2f} "
                f"kt={g.get('knowledge_transfer', 0.5):.2f}"
            )
    print()

    # Run (with optional watchdog retry)
    if args.watchdog:
        _run_with_watchdog(sim, args)
    else:
        try:
            sim.run(max_ticks=args.ticks)
        finally:
            close_connection()


def _run_with_watchdog(sim: Simulation, args) -> None:
    """Run with exponential backoff restart on crash."""
    global _active_sim
    backoff = 1  # seconds
    max_backoff = 60

    while True:
        try:
            sim.run(max_ticks=args.ticks)
            break  # Clean exit
        except KeyboardInterrupt:
            close_connection()
            break
        except Exception:
            traceback.print_exc()
            print(f"\n  [WATCHDOG] Crash detected. Saving checkpoint...")
            try:
                path = save_checkpoint(sim)
                print(f"  [WATCHDOG] Saved: {path}")
            except Exception:
                print("  [WATCHDOG] Failed to save checkpoint after crash")

            print(f"  [WATCHDOG] Restarting in {backoff}s...")
            time.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)

            # Resume from latest checkpoint
            checkpoint_path = get_latest_checkpoint()
            if checkpoint_path:
                try:
                    sim = Simulation.from_checkpoint(checkpoint_path)
                    _active_sim = sim
                    print(f"  [WATCHDOG] Resumed from {os.path.basename(checkpoint_path)}")
                except Exception:
                    print("  [WATCHDOG] Failed to resume, starting fresh")
                    sim = Simulation(seed=args.seed)
                    _active_sim = sim
            else:
                sim = Simulation(seed=args.seed)
                _active_sim = sim

    close_connection()


if __name__ == "__main__":
    main()
