"use client";

import type { SimulationData } from "@/hooks/use-simulation";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { InfoTip, TitleWithTip } from "@/components/ui/info-tip";

// ── Shared chart styling ─────────────────────────────────────────────────

const TOOLTIP_STYLE = {
  backgroundColor: "#fff",
  border: "1px solid #e5e7eb",
  borderRadius: "8px",
  fontSize: 12,
  boxShadow: "0 4px 6px -1px rgba(0,0,0,0.05)",
};

// ── Metric Card ──────────────────────────────────────────────────────────

function Metric({
  label,
  value,
  sub,
  color,
  tip,
}: {
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
  tip?: string;
}) {
  return (
    <div className="bg-card border border-border rounded-xl px-4 py-3.5">
      <div className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1">
        {label}
        {tip && <InfoTip text={tip} />}
      </div>
      <div
        className="mt-1 text-xl font-semibold tabular-nums"
        style={{ color }}
      >
        {value}
      </div>
      {sub && (
        <div className="mt-0.5 text-[11px] text-muted-foreground">{sub}</div>
      )}
    </div>
  );
}

// ── Event item ───────────────────────────────────────────────────────────

const EVENT_STYLE: Record<string, { label: string; color: string }> = {
  birth: { label: "Birth", color: "#059669" },
  death: { label: "Death", color: "#dc2626" },
  macro_discovered: { label: "Invention", color: "#d97706" },
};

// ── Section ──────────────────────────────────────────────────────────────

export default function OverviewSection({ data }: { data: SimulationData }) {
  const { overview, fullHistory, recentEvents } = data;

  // Compute per-tick births/deaths from cumulative data
  const popHistory = fullHistory.map((p, i) => {
    const prev = i > 0 ? fullHistory[i - 1] : p;
    return {
      tick: p.tick,
      population: p.population,
      births: p.total_births - prev.total_births,
      deaths: p.total_deaths - prev.total_deaths,
    };
  });

  // Only show birth/death/macro events
  const keyEvents = recentEvents.filter(
    (e) => e.event_type !== "brain_decision"
  );

  return (
    <div>
      {/* Section title */}
      <div className="mb-5">
        <h2 className="text-lg font-semibold text-foreground">Overview</h2>
        <p className="text-sm text-muted-foreground">
          A real-time snapshot of this agent civilisation — how many are alive, how healthy they are, and how far they&apos;ve evolved
        </p>
      </div>

      {/* Metrics grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-3">
        <Metric
          label="Tick"
          value={overview.currentTick.toLocaleString()}
          sub="Simulation time"
          tip="Each tick is one step in the simulation. Every tick, all agents perceive their surroundings, make a decision, and act."
        />
        <Metric
          label="Population"
          value={overview.population}
          sub={`${overview.totalBirths}B / ${overview.totalDeaths}D`}
          color="#059669"
          tip="Number of agents currently alive. B = total births ever, D = total deaths ever."
        />
        <Metric
          label="Avg Energy"
          value={overview.avgEnergy.toFixed(1)}
          color="#d97706"
          tip="Average energy across all living agents. Energy is like food — agents harvest it from the world and spend it to act. At zero energy, they die."
        />
        <Metric
          label="Avg Entropy"
          value={overview.avgEntropy.toFixed(1)}
          color="#dc2626"
          tip="Average entropy (decay) across all living agents. Entropy increases with age and represents physical deterioration. At 100, they die."
        />
        <Metric
          label="Max Generation"
          value={overview.maxGeneration}
          sub={`Avg age: ${overview.avgAge.toFixed(0)}`}
          color="#7c3aed"
          tip="The deepest family tree. Generation 0 = original agents. Each offspring is one generation deeper than its parents."
        />
        <Metric
          label="Substrate"
          value={`${(overview.substrateEnergy / 1000).toFixed(1)}k`}
          sub="Total energy"
          color="#0d9488"
          tip="Total energy stored in the world's 800 nodes. This is the 'food supply' — it regenerates over time and agents harvest from it."
        />
      </div>

      {/* Second row of metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-3 mt-3">
        <Metric
          label="Avg Cortex"
          value={overview.avgCortexSize.toFixed(0)}
          sub="Associations"
          color="#4f46e5"
          tip="Average number of learned situation→action associations per agent. The cortex is a fast-learning memory that helps agents make quick decisions."
        />
        <Metric
          label="Inventions"
          value={overview.totalMacros}
          sub="Compound behaviors"
          color="#d97706"
          tip="Number of 'motor patterns' discovered — sequences of actions that agents chain together into efficient routines, like a learned skill."
        />
        <Metric
          label="Signals"
          value={overview.totalSignalDeliveries.toLocaleString()}
          sub="Total deliveries"
          color="#0891b2"
          tip="Total signal messages delivered between agents. Agents can broadcast signals using evolved neural channels — the meaning of these signals emerges through evolution."
        />
      </div>

      {/* Population chart */}
      <div className="mt-6 bg-card border border-border rounded-xl p-5">
        <div className="text-sm font-medium text-foreground mb-3">
          Population
        </div>
        <div className="h-[200px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={popHistory}>
              <defs>
                <linearGradient id="ov-pop" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#059669" stopOpacity={0.15} />
                  <stop offset="100%" stopColor="#059669" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
              <XAxis
                dataKey="tick"
                tick={{ fontSize: 10, fill: "#9ca3af" }}
                stroke="#e5e7eb"
                tickFormatter={(v) => v.toLocaleString()}
              />
              <YAxis
                tick={{ fontSize: 10, fill: "#9ca3af" }}
                stroke="#e5e7eb"
                allowDecimals={false}
              />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                labelFormatter={(v) => `Tick ${Number(v).toLocaleString()}`}
              />
              <Area
                type="monotone"
                dataKey="population"
                stroke="#059669"
                fill="url(#ov-pop)"
                strokeWidth={1.5}
                name="Population"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recent events */}
      <div className="mt-5 bg-card border border-border rounded-xl p-5">
        <div className="text-sm font-medium text-foreground mb-3">
          Recent Events
        </div>
        <div className="space-y-1 max-h-[240px] overflow-y-auto">
          {keyEvents.length === 0 && (
            <div className="text-sm text-muted-foreground py-4 text-center">
              No events yet
            </div>
          )}
          {keyEvents.slice(0, 20).map((e, i) => {
            const style = EVENT_STYLE[e.event_type] ?? {
              label: e.event_type,
              color: "#6b7280",
            };
            return (
              <div
                key={`${e.tick}-${e.agent_id}-${i}`}
                className="flex items-center gap-3 text-[12px] px-3 py-1.5 rounded-lg hover:bg-muted/40 transition-colors"
              >
                <span className="font-mono text-muted-foreground w-14 shrink-0 tabular-nums">
                  T{e.tick}
                </span>
                <span
                  className="text-[10px] font-medium uppercase tracking-wider w-16 shrink-0"
                  style={{ color: style.color }}
                >
                  {style.label}
                </span>
                <span className="font-mono text-foreground/70 w-10 shrink-0">
                  #{e.agent_id}
                </span>
                <span className="text-muted-foreground truncate">
                  {e.description}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

