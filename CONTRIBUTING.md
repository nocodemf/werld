# Contributing to Werld

## Setup

```bash
git clone https://github.com/nocodemf/werld.git
cd werld
```

The simulation is pure Python (stdlib only) — no `pip install` needed.

```bash
python main.py --ticks 1000    # verify it runs
```

For the dashboard:

```bash
cd dashboard && npm install && npm run dev
```

Reads from `../data/simulation.db`, so run the simulation first.

## Development workflow

- **`config.py`** — Most tunable parameters live here. Start here for behavior changes.
- **`CLAUDE.md`** — Full technical reference: sensory channels, effectors, genome traits, architecture.
- **Python** — Type hints, `from __future__ import annotations`. Pure stdlib, no ML frameworks.
- **Dashboard** — Next.js 16, React 19, TypeScript, shadcn/ui, Recharts.

## Pull requests

1. Open an issue first if it's a big change — helps align on direction before you write code.
2. Branch from `main`, keep PRs focused.
3. Verify: `python main.py --ticks 500` runs clean and `cd dashboard && npm run build` succeeds.
4. Update `CLAUDE.md` if you change architecture, add systems, or modify the genome/sensory/effector layout.

## Good contributions

- **Bug fixes** — checkpoint compatibility, DB schema, simulation loop edge cases.
- **Tuning** — better defaults, new genome traits, substrate parameters. Explain the reasoning.
- **Dashboard** — new visualizations, better tooltips, performance.
- **Docs** — corrections, clarifications, examples.
- **Ideas that expand evolvability** — new latent sensory channels, additional effector dimensions, novel selection pressures. The design goal is maximum evolvable surface area.

## Out of scope (for now)

- Rewrites in another language.
- ML frameworks (PyTorch, TensorFlow, etc.) — the brain is NEAT, evolution is the optimizer.
- Hardcoded behavioral assumptions — if it doesn't evolve, it doesn't belong in the agent.

## Questions?

Open an issue.
