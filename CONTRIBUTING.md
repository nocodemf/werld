# Contributing to Werld

Thanks for considering contributing. Here's how to get going.

## Setup

1. **Clone and install**

   ```bash
   git clone https://github.com/nocodemf/werld.git
   cd werld
   cd dashboard && npm install
   ```

   No Python deps — the sim uses stdlib only.

2. **Run the simulation**

   ```bash
   python main.py --ticks 1000
   ```

3. **Run the dashboard**

   ```bash
   cd dashboard && npm run dev
   ```

   The dashboard reads from `../data/simulation.db`. Run the sim first so there's data to show.

## Development workflow

- **Config** — Most tunable parameters live in `config.py`. Start there for behavior changes.
- **Architecture** — See `CLAUDE.md` for the full reference (sensory channels, effectors, genome traits, etc.).
- **Python** — We use type hints and `from __future__ import annotations`. No ML frameworks; keep it pure Python.
- **Dashboard** — Next.js 16, React 19, TypeScript, shadcn/ui, Recharts.

## Pull requests

1. Open an issue first if it's a big change — helps align on direction.
2. Branch from `main`, keep PRs focused.
3. Make sure the sim still runs (`python main.py --ticks 500`) and the dashboard builds (`cd dashboard && npm run build`).
4. Update `CLAUDE.md` if you change architecture or add new systems.

## What we're looking for

- **Bug fixes** — Especially around checkpoint compatibility, DB schema, or edge cases in the sim loop.
- **Config / tuning** — Better defaults, new genome traits, substrate params. Document why.
- **Dashboard** — New visualizations, clearer tooltips, performance improvements.
- **Docs** — Clarifications, examples, or corrections to `CLAUDE.md` and this file.

## What we're not looking for (right now)

- Rewrites in another language.
- Adding ML frameworks (PyTorch, etc.) — the brain is NEAT, no gradients.
- Hardcoding new behavioral assumptions — the design goal is evolvable, not engineered.

## Questions?

Open an issue. We'll get back to you.
