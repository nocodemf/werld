# Werld

An open-ended artificial life simulation. Autonomous agents evolve on a graph — no grid, no reward function, no hardcoded behaviors. Natural selection is the only teacher.

Agents have NEAT-style neural networks that grow their own topology, 64-channel sensory systems with latent slots that evolution can discover, continuous motor effectors, episodic memory, and 29 genome traits — all evolvable. The simulation runs in pure Python (stdlib only) with a Next.js observatory dashboard.

The interesting constraint: nothing about how agents should behave is specified. No loss function. No reward signal. No behavioral templates. Agents that survive long enough to reproduce pass their genes on. Everything else — brain architecture, sensory processing, drives, communication protocols, motor patterns — emerges or doesn't.

---

## Quick start

**Simulation** (Python 3.10+, no dependencies)

```bash
python main.py
```

Runs indefinitely. Checkpoints auto-save to `data/`. Resume with `--resume`, short run with `--ticks 5000`, auto-restart on crash with `--watchdog`.

**Dashboard** (Node.js 20+)

```bash
cd dashboard && npm install && npm run dev
```

Opens at [localhost:3000](http://localhost:3000). Reads from `../data/simulation.db` — start the sim first.

---

## What's in here

**Simulation** — Pure Python, stdlib only. Agents live on a Watts-Strogatz small-world graph (800 nodes) with pheromone trails and seasonal energy cycles. Each tick: perceive (BFS neighborhood scan) -> decide (NEAT forward pass) -> act (continuous effectors) -> learn (cortex reinforcement + memory). Reproduction is sexual crossover with NEAT gene alignment.

**Observatory** — Next.js dashboard with 13 sections: population dynamics, brain complexity, species evolution, world map, story chapters, ecology, communication analysis, agent inspector, and more. Polls SQLite every 4 seconds.

---

## Design decisions worth knowing about

**No reward function.** The NEAT brain has a vestigial `compute_reward()` that returns 0.0. Weights evolve through selection, not gradient descent.

**Latent sensory channels.** Channels 45-63 start with near-zero gain (0.01). They're invisible to the brain until evolution upregulates the gain. The sensory field can expand without changing I/O dimensionality — agents don't need to "know" the channels exist for evolution to discover them.

**Everything costs energy.** Each neuron, each connection, each active broadcast channel, each deviation from default sensory gain — all have metabolic cost deducted every tick. Complexity must earn its keep.

**The cortex is optional.** `cortex_reliance` is a genome trait (0-1). Agents can evolve to be pure NEAT-brain creatures or keep a fast associative reflex system as backup. Evolution decides.

**Communication is unstructured.** Up to 16 broadcast channels with brain-controlled content. No semantic encoding is imposed — if meaning emerges, it's because selection found it useful.

**Motor patterns self-discover.** Repeated beneficial effector sequences get promoted to compound actions and become heritable. The capacity and max pattern length are themselves evolvable.

---

## Project structure

```
├── main.py           # Entry point, CLI, SIGTERM handler
├── config.py         # All tunable parameters — start here
├── engine/           # Simulation loop, graph substrate, story generation
├── agents/           # Genome (29 traits), cortex, memory, state
├── reasoning/        # NEAT brain (evolvable topology neural network)
├── systems/          # Actions, signals, forking, evolution, entropy
├── persistence/      # SQLite, checkpoints, milestones
└── dashboard/        # Next.js observatory (13 sections)
```

`CLAUDE.md` is the full technical reference — every sensory channel, effector, genome trait, and architectural decision documented.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The short version: open an issue first for big changes, branch from `main`, make sure `python main.py --ticks 500` and `cd dashboard && npm run build` still work.

We're interested in: bug fixes, better defaults, new visualizations, and ideas that expand the scope for open-ended evolution — without injecting human behavioral assumptions.

---

## License

MIT. See [LICENSE](LICENSE).
