# Werld

A computational ecosystem where autonomous agents evolve on a graph. No grids, no human-world assumptions — just a Watts-Strogatz small-world network, NEAT-style brains, and natural selection doing the teaching.

Think of it as a digital petri dish: agents perceive, act, reproduce, and die. Their genomes evolve. Brains get more complex (or simpler, if that works better). Communication, memory, and motor patterns are all discoverable — nothing's hardcoded. The goal is open-ended evolution: see what emerges when you remove the training wheels.

Everything runs locally. No cloud, no hosting, no API keys.

---

## What's in the box

- **Simulation** — Pure Python, stdlib only. Graph topology, pheromones, seasons, continuous effectors, evolvable sensory gains, 29 genome traits. Checkpoints, milestones, SIGTERM-safe.
- **Werld Observatory** — Next.js dashboard with 13 sections: population, evolution, brain complexity, ecology, world map, story chapters, etc. Polls SQLite every 4s.

---

## Quick start

**1. Simulation**

Python 3.10+. No pip install needed — the sim uses only the standard library.

```bash
python main.py
```

Runs indefinitely, auto-saves checkpoints to `data/`. Use `--resume` to pick up where you left off, `--ticks 5000` for a short run, `--watchdog` to auto-restart on crash.

**2. Dashboard**

```bash
cd dashboard && npm install && npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The dashboard reads from `../data/simulation.db`, so start the sim first (or it'll show empty state).

That's it. Sim + dashboard, both local.

---

## Project structure

```
├── main.py           # Entry point, CLI, SIGTERM handler
├── config.py         # All tunable params — start here if you want to tweak
├── engine/           # Simulation loop, substrate (graph), story gen
├── agents/           # Genome, cortex, memory, state — the agent stack
├── reasoning/        # NEAT brain (evolvable topology)
├── systems/          # Actions, signals, forking, evolution, entropy
├── persistence/      # SQLite, checkpoints, milestones
├── social/           # X poster (optional, for live instance — not needed to run)
└── dashboard/        # Next.js observatory
```

`CLAUDE.md` has the full technical reference — architecture, sensory channels, effector layout, genome traits, everything.

---

## Contributing

Contributions welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, PR process, and what we're looking for.

---

## License

MIT. See [LICENSE](LICENSE).
