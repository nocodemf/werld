"use client";

import type { SimulationData } from "@/hooks/use-simulation";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { TitleWithTip } from "@/components/ui/info-tip";

const TT = {
  backgroundColor: "#fff",
  border: "1px solid #e5e7eb",
  borderRadius: "8px",
  fontSize: 12,
  boxShadow: "0 4px 6px -1px rgba(0,0,0,0.05)",
};

export default function PopulationSection({ data }: { data: SimulationData }) {
  const { fullHistory, generationDist, overview } = data;

  const popData = fullHistory.map((p, i) => {
    const prev = i > 0 ? fullHistory[i - 1] : p;
    return {
      tick: p.tick,
      population: p.population,
      births: p.total_births - prev.total_births,
      deaths: p.total_deaths - prev.total_deaths,
    };
  });

  return (
    <div>
      <div className="mb-5">
        <h2 className="text-lg font-semibold text-foreground">Population</h2>
        <p className="text-sm text-muted-foreground">
          How many agents are alive, how fast they&apos;re reproducing, and how deep the family trees go
        </p>
      </div>

      {/* Summary bar */}
      <div className="grid grid-cols-4 gap-3 mb-5">
        <Stat label="Total Born" value={overview.totalBirths} color="#3b82f6" />
        <Stat
          label="Total Died"
          value={overview.totalDeaths}
          color="#ef4444"
        />
        <Stat label="Alive" value={overview.population} color="#059669" />
        <Stat
          label="Max Generation"
          value={overview.maxGeneration}
          color="#7c3aed"
        />
      </div>

      {/* Population over time */}
      <div className="bg-card border border-border rounded-xl p-5">
        <TitleWithTip
          title="Population Over Time"
          tip="The green area shows how many agents are alive at each point. Blue spikes are births (new agents), red spikes are deaths."
          className="mb-1"
        />
        <div className="text-[11px] text-muted-foreground mb-3">
          With per-tick births and deaths
        </div>
        <div className="h-[280px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={popData}>
              <defs>
                <linearGradient id="pop-g" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#059669" stopOpacity={0.12} />
                  <stop offset="100%" stopColor="#059669" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="birth-g" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.12} />
                  <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="death-g" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#ef4444" stopOpacity={0.12} />
                  <stop offset="100%" stopColor="#ef4444" stopOpacity={0} />
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
                contentStyle={TT}
                labelFormatter={(v) => `Tick ${Number(v).toLocaleString()}`}
              />
              <Legend
                wrapperStyle={{ fontSize: 11 }}
                iconType="plainline"
                iconSize={12}
              />
              <Area
                type="monotone"
                dataKey="population"
                stroke="#059669"
                fill="url(#pop-g)"
                strokeWidth={1.5}
                name="Population"
              />
              <Area
                type="monotone"
                dataKey="births"
                stroke="#3b82f6"
                fill="url(#birth-g)"
                strokeWidth={1}
                name="Births"
              />
              <Area
                type="monotone"
                dataKey="deaths"
                stroke="#ef4444"
                fill="url(#death-g)"
                strokeWidth={1}
                name="Deaths"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Generations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
        <div className="bg-card border border-border rounded-xl p-5">
          <TitleWithTip
            title="Generation Distribution"
            tip="Each bar is a generation (G0 = original agents, G1 = their children, etc). Green = still alive, grey = died. Taller later bars mean successful reproduction."
            className="mb-1"
          />
          <div className="text-[11px] text-muted-foreground mb-3">
            Alive vs dead by generation
          </div>
          <div className="h-[240px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={generationDist}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                <XAxis
                  dataKey="generation"
                  tick={{ fontSize: 10, fill: "#9ca3af" }}
                  stroke="#e5e7eb"
                />
                <YAxis
                  tick={{ fontSize: 10, fill: "#9ca3af" }}
                  stroke="#e5e7eb"
                  allowDecimals={false}
                />
                <Tooltip contentStyle={TT} />
                <Legend
                  wrapperStyle={{ fontSize: 11 }}
                  iconType="square"
                  iconSize={8}
                />
                <Bar
                  dataKey="alive"
                  stackId="a"
                  fill="#059669"
                  name="Alive"
                  radius={[0, 0, 0, 0]}
                />
                <Bar
                  dataKey="dead"
                  stackId="a"
                  fill="#d1d5db"
                  name="Dead"
                  radius={[2, 2, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Max generation over time */}
        <div className="bg-card border border-border rounded-xl p-5">
          <TitleWithTip
            title="Max Generation Over Time"
            tip="How deep the deepest family tree goes. A rising line means agents are successfully reproducing across multiple generations — the civilisation is sustaining itself."
            className="mb-1"
          />
          <div className="text-[11px] text-muted-foreground mb-3">
            Evolutionary progress
          </div>
          <div className="h-[240px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={fullHistory}>
                <defs>
                  <linearGradient id="gen-g" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#7c3aed" stopOpacity={0.12} />
                    <stop offset="100%" stopColor="#7c3aed" stopOpacity={0} />
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
                  contentStyle={TT}
                  labelFormatter={(v) => `Tick ${Number(v).toLocaleString()}`}
                />
                <Area
                  type="stepAfter"
                  dataKey="max_generation"
                  stroke="#7c3aed"
                  fill="url(#gen-g)"
                  strokeWidth={1.5}
                  name="Max Generation"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Avg age over time */}
      <div className="bg-card border border-border rounded-xl p-5 mt-4">
        <TitleWithTip
          title="Average Age Over Time"
          tip="How long agents are living on average. A rising trend means agents are getting better at surviving — they're evolving more effective strategies."
          className="mb-1"
        />
        <div className="text-[11px] text-muted-foreground mb-3">
          Longevity trends across the population
        </div>
        <div className="h-[200px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={fullHistory}>
              <defs>
                <linearGradient id="age-g" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#6366f1" stopOpacity={0.12} />
                  <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
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
              />
              <Tooltip
                contentStyle={TT}
                labelFormatter={(v) => `Tick ${Number(v).toLocaleString()}`}
              />
              <Area
                type="monotone"
                dataKey="avg_age"
                stroke="#6366f1"
                fill="url(#age-g)"
                strokeWidth={1.5}
                name="Avg Age"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

// ── Helper ───────────────────────────────────────────────────────────────

function Stat({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className="bg-card border border-border rounded-xl px-4 py-3">
      <div className="text-[11px] text-muted-foreground uppercase tracking-wider font-medium">
        {label}
      </div>
      <div
        className="text-lg font-semibold tabular-nums mt-0.5"
        style={{ color }}
      >
        {value.toLocaleString()}
      </div>
    </div>
  );
}

