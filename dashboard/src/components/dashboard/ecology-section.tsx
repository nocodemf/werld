"use client";

import type { SimulationData } from "@/hooks/use-simulation";
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  ComposedChart,
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

export default function EcologySection({
  data,
}: {
  data: SimulationData;
}) {
  const { ecologyHistory, fullHistory, overview, commsHistory } = data;

  // Compute derived metrics
  const energyRatio = fullHistory.map((p) => ({
    tick: p.tick,
    agentEnergy: p.avg_energy * p.population,
    substrateEnergy: p.substrate_energy,
    ratio:
      p.substrate_energy > 0
        ? ((p.avg_energy * p.population) / p.substrate_energy) * 100
        : 0,
  }));

  // Birth/death rate over time
  const birthDeathData = ecologyHistory.map((p) => ({
    tick: p.tick,
    births: p.births,
    deaths: p.deaths,
    net: p.births - p.deaths,
  }));

  // Species diversity over time
  const diversityData = ecologyHistory.map((p) => ({
    tick: p.tick,
    numSpecies: p.numSpecies,
    population: p.population,
    speciesPerCapita: p.population > 0 ? p.numSpecies / p.population : 0,
  }));

  // Energy flow: substrate vs agent energy
  const energyFlow = fullHistory.map((p) => ({
    tick: p.tick,
    substratePer1k: p.substrate_energy / 1000,
    agentTotal: p.avg_energy * p.population,
    avgEnergy: p.avg_energy,
    avgEntropy: p.avg_entropy,
  }));

  // Summary
  const latestPop = overview.population;
  const birthRate =
    ecologyHistory.length > 5
      ? (
          ecologyHistory.slice(-5).reduce((s, p) => s + p.births, 0) / 5
        ).toFixed(1)
      : "—";
  const deathRate =
    ecologyHistory.length > 5
      ? (
          ecologyHistory.slice(-5).reduce((s, p) => s + p.deaths, 0) / 5
        ).toFixed(1)
      : "—";
  const latestSpecies =
    ecologyHistory.length > 0
      ? ecologyHistory[ecologyHistory.length - 1].numSpecies
      : 0;
  const carryingCapacity =
    fullHistory.length > 0
      ? Math.max(...fullHistory.map((p) => p.population))
      : 0;
  const signalDensity =
    commsHistory.length > 0
      ? commsHistory[commsHistory.length - 1].signalsDelivered
      : 0;

  return (
    <div>
      <div className="mb-5">
        <h2 className="text-lg font-semibold text-foreground">Ecology</h2>
        <p className="text-sm text-muted-foreground">
          The big picture — how energy flows through the world, how populations rise and fall, and whether the ecosystem is healthy
        </p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-5">
        <StatBox
          label="Population"
          value={latestPop.toString()}
          sub="Living agents"
          color="#059669"
        />
        <StatBox
          label="Birth Rate"
          value={birthRate}
          sub="Per sample (recent)"
          color="#3b82f6"
        />
        <StatBox
          label="Death Rate"
          value={deathRate}
          sub="Per sample (recent)"
          color="#dc2626"
        />
        <StatBox
          label="Species"
          value={latestSpecies.toString()}
          sub="Genetic clusters"
          color="#7c3aed"
        />
        <StatBox
          label="Peak Pop"
          value={carryingCapacity.toString()}
          sub="Historical max"
          color="#d97706"
        />
        <StatBox
          label="Signal Traffic"
          value={signalDensity.toLocaleString()}
          sub="Last sample"
          color="#0891b2"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Population & Species Diversity */}
        <div className="bg-card border border-border rounded-xl p-5">
          <TitleWithTip
            title="Population & Diversity"
            tip="Green area = total living agents. Purple line = number of distinct species. More species means greater genetic diversity — the civilisation is branching into different survival strategies."
            className="mb-1"
          />
          <div className="text-[11px] text-muted-foreground mb-3">
            Population count and species diversity over time
          </div>
          <div className="h-[280px]">
            {diversityData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={diversityData}>
                  <defs>
                    <linearGradient id="eco-pop" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#059669" stopOpacity={0.12} />
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
                    yAxisId="left"
                    tick={{ fontSize: 10, fill: "#9ca3af" }}
                    stroke="#e5e7eb"
                    allowDecimals={false}
                  />
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    tick={{ fontSize: 10, fill: "#9ca3af" }}
                    stroke="#e5e7eb"
                    allowDecimals={false}
                  />
                  <Tooltip
                    contentStyle={TT}
                    labelFormatter={(v) => `Tick ${Number(v).toLocaleString()}`}
                  />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Area
                    yAxisId="left"
                    type="monotone"
                    dataKey="population"
                    stroke="#059669"
                    fill="url(#eco-pop)"
                    strokeWidth={1.5}
                    name="Population"
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="numSpecies"
                    stroke="#7c3aed"
                    strokeWidth={2}
                    dot={false}
                    name="Species Count"
                  />
                </ComposedChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
                No ecology data yet
              </div>
            )}
          </div>
        </div>

        {/* Birth/Death dynamics */}
        <div className="bg-card border border-border rounded-xl p-5">
          <TitleWithTip
            title="Birth & Death Dynamics"
            tip="Green bars = births, red bars = deaths, blue line = net change. When the line is above zero, the population is growing. Below zero, it's shrinking."
            className="mb-1"
          />
          <div className="text-[11px] text-muted-foreground mb-3">
            Per-sample births, deaths, and net growth
          </div>
          <div className="h-[280px]">
            {birthDeathData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={birthDeathData}>
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
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar
                    dataKey="births"
                    fill="#059669"
                    fillOpacity={0.6}
                    name="Births"
                    barSize={6}
                  />
                  <Bar
                    dataKey="deaths"
                    fill="#dc2626"
                    fillOpacity={0.5}
                    name="Deaths"
                    barSize={6}
                  />
                  <Line
                    type="monotone"
                    dataKey="net"
                    stroke="#3b82f6"
                    strokeWidth={1.5}
                    dot={false}
                    name="Net Growth"
                  />
                </ComposedChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
                No birth/death data yet
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
        {/* Energy Flow */}
        <div className="bg-card border border-border rounded-xl p-5">
          <TitleWithTip
            title="Energy Flow"
            tip="Teal line = total energy in the world (food supply). Orange line = average energy per agent. If the food supply drops while agent energy rises, agents are successfully harvesting."
            className="mb-1"
          />
          <div className="text-[11px] text-muted-foreground mb-3">
            Substrate energy vs average agent energy
          </div>
          <div className="h-[240px]">
            {energyFlow.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={energyFlow}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                  <XAxis
                    dataKey="tick"
                    tick={{ fontSize: 10, fill: "#9ca3af" }}
                    stroke="#e5e7eb"
                    tickFormatter={(v) => v.toLocaleString()}
                  />
                  <YAxis
                    yAxisId="left"
                    tick={{ fontSize: 10, fill: "#9ca3af" }}
                    stroke="#e5e7eb"
                  />
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    tick={{ fontSize: 10, fill: "#9ca3af" }}
                    stroke="#e5e7eb"
                  />
                  <Tooltip
                    contentStyle={TT}
                    labelFormatter={(v) => `Tick ${Number(v).toLocaleString()}`}
                  />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="substratePer1k"
                    stroke="#0d9488"
                    strokeWidth={1.5}
                    dot={false}
                    name="Substrate (×1k)"
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="avgEnergy"
                    stroke="#d97706"
                    strokeWidth={1.5}
                    dot={false}
                    name="Avg Agent Energy"
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
                No energy data yet
              </div>
            )}
          </div>
        </div>

        {/* Entropy pressure */}
        <div className="bg-card border border-border rounded-xl p-5">
          <TitleWithTip
            title="Homeostasis Pressure"
            tip="Orange = energy (good), red = entropy/decay (bad). Agents need to keep energy high and entropy low. Rising entropy means the population is aging faster than it can maintain itself."
            className="mb-1"
          />
          <div className="text-[11px] text-muted-foreground mb-3">
            Average energy and entropy (lower entropy = healthier)
          </div>
          <div className="h-[240px]">
            {energyFlow.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={energyFlow}>
                  <defs>
                    <linearGradient id="eco-energy" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#d97706" stopOpacity={0.12} />
                      <stop offset="100%" stopColor="#d97706" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="eco-entropy" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#dc2626" stopOpacity={0.12} />
                      <stop offset="100%" stopColor="#dc2626" stopOpacity={0} />
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
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Area
                    type="monotone"
                    dataKey="avgEnergy"
                    stroke="#d97706"
                    fill="url(#eco-energy)"
                    strokeWidth={1.5}
                    name="Avg Energy"
                  />
                  <Area
                    type="monotone"
                    dataKey="avgEntropy"
                    stroke="#dc2626"
                    fill="url(#eco-entropy)"
                    strokeWidth={1.5}
                    name="Avg Entropy"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
                No homeostasis data yet
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Extraction ratio (how efficiently agents use the substrate) */}
      <div className="bg-card border border-border rounded-xl p-5 mt-4">
        <TitleWithTip
          title="Extraction Efficiency"
          tip="What percentage of the world's energy agents have managed to harvest. Higher = agents are better at finding and gathering food. Very high might mean they're depleting the world."
          className="mb-1"
        />
        <div className="text-[11px] text-muted-foreground mb-3">
          Agent energy as % of world energy — higher = better foraging
        </div>
        <div className="h-[200px]">
          {energyRatio.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={energyRatio}>
                <defs>
                  <linearGradient id="eco-ratio" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.12} />
                    <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
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
                  tickFormatter={(v) => `${v.toFixed(1)}%`}
                />
                <Tooltip
                  contentStyle={TT}
                  labelFormatter={(v) => `Tick ${Number(v).toLocaleString()}`}
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  formatter={(value: any) => [`${Number(value).toFixed(2)}%`, "Extraction %"]}
                />
                <Area
                  type="monotone"
                  dataKey="ratio"
                  stroke="#3b82f6"
                  fill="url(#eco-ratio)"
                  strokeWidth={1.5}
                  name="Extraction %"
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
              No extraction data yet
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatBox({
  label,
  value,
  sub,
  color,
}: {
  label: string;
  value: string;
  sub: string;
  color: string;
}) {
  return (
    <div className="bg-card border border-border rounded-xl px-4 py-3.5">
      <div className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
        {label}
      </div>
      <div className="text-xl font-semibold tabular-nums mt-1" style={{ color }}>
        {value}
      </div>
      <div className="text-[11px] text-muted-foreground mt-0.5">{sub}</div>
    </div>
  );
}

