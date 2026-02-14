"""
State Store — save and restore full simulation state.

Uses JSON checkpoints for complete state serialisation so the simulation
can be stopped and resumed from any checkpoint.

Checkpoints are optionally gzip-compressed (~90% space saving) and
automatically rotated to keep only the last CHECKPOINT_KEEP files.

The substrate is now a graph (not a grid), so serialisation stores
nodes with their energy and neighbor lists.
"""

from __future__ import annotations

import gzip
import json
import os
import random
from typing import Dict, Any, List, Optional, TYPE_CHECKING

import config as cfg

if TYPE_CHECKING:
    from engine.simulation import Simulation


def save_checkpoint(sim: "Simulation") -> str:
    """Serialise the entire simulation state to a checkpoint file."""
    os.makedirs(cfg.CHECKPOINT_DIR, exist_ok=True)

    # Serialize innovation counter state
    from agents.genome import get_innovation_state
    innov_counter, innov_cache = get_innovation_state()
    innov_cache_ser = {f"{k[0]}:{k[1]}": v for k, v in innov_cache.items()}

    state = {
        "tick": sim.tick,
        "seed": sim.seed,
        "rng_state": _serialise_rng(sim.rng),
        "next_agent_id": _get_next_id(),
        "substrate": _serialise_substrate(sim.substrate),
        "agents": [_serialise_agent(a) for a in sim.agents],
        "stats": {
            "total_births": sim.logger.total_births,
            "total_deaths": sim.logger.total_deaths,
        },
        "innovation_counter": innov_counter,
        "innovation_cache": innov_cache_ser,
    }

    payload = json.dumps(state, separators=(",", ":"))

    if getattr(cfg, "CHECKPOINT_COMPRESS", True):
        path = os.path.join(cfg.CHECKPOINT_DIR, f"tick_{sim.tick:08d}.json.gz")
        with gzip.open(path, "wt", encoding="utf-8", compresslevel=6) as f:
            f.write(payload)
    else:
        path = os.path.join(cfg.CHECKPOINT_DIR, f"tick_{sim.tick:08d}.json")
        with open(path, "w") as f:
            f.write(payload)

    _rotate_checkpoints()
    return path


def save_milestone(sim: "Simulation") -> str:
    """Save a milestone checkpoint that is never automatically deleted."""
    os.makedirs(cfg.MILESTONE_DIR, exist_ok=True)

    from agents.genome import get_innovation_state
    innov_counter, innov_cache = get_innovation_state()
    innov_cache_ser = {f"{k[0]}:{k[1]}": v for k, v in innov_cache.items()}

    state = {
        "tick": sim.tick,
        "seed": sim.seed,
        "rng_state": _serialise_rng(sim.rng),
        "next_agent_id": _get_next_id(),
        "substrate": _serialise_substrate(sim.substrate),
        "agents": [_serialise_agent(a) for a in sim.agents if a.alive],
        "stats": {
            "total_births": sim.logger.total_births,
            "total_deaths": sim.logger.total_deaths,
        },
        "innovation_counter": innov_counter,
        "innovation_cache": innov_cache_ser,
    }

    payload = json.dumps(state, separators=(",", ":"))
    path = os.path.join(cfg.MILESTONE_DIR, f"milestone_{sim.tick:08d}.json.gz")
    with gzip.open(path, "wt", encoding="utf-8", compresslevel=6) as f:
        f.write(payload)
    return path


def load_checkpoint(path: str) -> Dict[str, Any]:
    """Load a checkpoint file (gzipped or plain) and return the raw state dict."""
    if path.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)
    else:
        with open(path, "r") as f:
            return json.load(f)


def get_latest_checkpoint() -> Optional[str]:
    """Find the most recent checkpoint file, if any."""
    if not os.path.exists(cfg.CHECKPOINT_DIR):
        return None
    files = sorted(
        [
            f
            for f in os.listdir(cfg.CHECKPOINT_DIR)
            if f.endswith(".json") or f.endswith(".json.gz")
        ],
        reverse=True,
    )
    if not files:
        return None
    return os.path.join(cfg.CHECKPOINT_DIR, files[0])


# ── Rotation ────────────────────────────────────────────────────────────────


def _rotate_checkpoints() -> None:
    """Delete old checkpoints, keeping only the last CHECKPOINT_KEEP."""
    keep = getattr(cfg, "CHECKPOINT_KEEP", 3)
    if not os.path.exists(cfg.CHECKPOINT_DIR):
        return
    files = sorted(
        [
            f
            for f in os.listdir(cfg.CHECKPOINT_DIR)
            if f.endswith(".json") or f.endswith(".json.gz")
        ]
    )
    if len(files) <= keep:
        return
    for f in files[: len(files) - keep]:
        try:
            os.remove(os.path.join(cfg.CHECKPOINT_DIR, f))
        except OSError:
            pass


# ── Serialisation helpers ────────────────────────────────────────────────────


def _get_next_id() -> int:
    from agents.agent import _next_id
    return _next_id


def _serialise_rng(rng: random.Random) -> list:
    """Serialise Random state to a JSON-compatible list."""
    state = rng.getstate()
    return [state[0], list(state[1]), state[2]]


def deserialise_rng(data: list) -> random.Random:
    """Restore a Random from serialised state."""
    rng = random.Random()
    rng.setstate((data[0], tuple(data[1]), data[2]))
    return rng


def _serialise_substrate(substrate) -> Dict[str, Any]:
    """Serialise graph substrate to dict."""
    nodes_data = {}
    for nid, node in substrate.nodes.items():
        node_data = {
            "energy": round(node.energy, 2),
            "neighbors": node.neighbors,
            "vis_x": round(node.vis_x, 2),
            "vis_y": round(node.vis_y, 2),
        }
        if hasattr(node, "pheromone") and node.pheromone > 0.001:
            node_data["pheromone"] = round(node.pheromone, 4)
        nodes_data[str(nid)] = node_data
    return {
        "num_nodes": len(substrate.nodes),
        "tick": substrate.tick,
        "nodes": nodes_data,
    }


def _serialise_agent(agent) -> Dict[str, Any]:
    """Serialise a single agent to dict."""
    cortex_weights = {}
    for (sh, aid), w in agent.cortex.weights.items():
        cortex_weights[f"{sh}:{aid}"] = w

    memories = []
    if hasattr(agent, "memory") and agent.memory is not None:
        memories = agent.memory.serialise()

    compound = {}
    if hasattr(agent, "compound_actions"):
        for name, ca in agent.compound_actions.items():
            compound[name] = {
                "sequence": ca["sequence"],
                "success_count": ca["success_count"],
                "discovered_tick": ca.get("discovered_tick", 0),
            }

    brain_data = None
    if hasattr(agent, "brain") and agent.brain is not None:
        brain_data = agent.brain.serialise()

    # Serialize the full genome (traits + NEAT topology)
    import json as _json
    genome_data = _json.loads(agent.genome.to_json())

    return {
        "id": agent.id,
        "generation": agent.generation,
        "parent_ids": list(agent.parent_ids),
        "genome": genome_data,
        "state": {
            "energy": agent.state.energy,
            "entropy": agent.state.entropy,
            "age": agent.state.age,
            "node_id": agent.state.node_id,
            "alive": agent.state.alive,
            "inventory": agent.state.inventory,
        },
        "cortex": {
            "weights": cortex_weights,
            "experience": agent.cortex.experience,
            "capacity": agent.cortex.capacity,
            "learning_rate": agent.cortex.learning_rate,
            "exploration_factor": agent.cortex.exploration_factor,
        },
        "memory": memories,
        "compound_actions": compound,
        "brain": brain_data,
        "rng_state": _serialise_rng(agent.rng),
    }
