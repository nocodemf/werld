"use client";

import type { SimulationData } from "@/hooks/use-simulation";
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ComposedChart,
  Bar,
} from "recharts";
import { TitleWithTip } from "@/components/ui/info-tip";

const TT = {
  backgroundColor: "#fff",
  border: "1px solid #e5e7eb",
  borderRadius: "8px",
  fontSize: 12,
  boxShadow: "0 4px 6px -1px rgba(0,0,0,0.05)",
};

export default function BrainSection({
  data,
}: {
  data: SimulationData;
}) {
  const { brainHistory, agentSnapshots, latestSpecies } = data;

  // Summary stats from latest brain history point
  const latest = brainHistory.length > 0 ? brainHistory[brainHistory.length - 1] : null;

  // Brain node/connection distribution from live agents
  const brainDistData = agentSnapshots
    .filter((a) => a.genome?.brain_nodes != null)
    .map((a) => ({
      id: a.agent_id,
      nodes: a.genome?.brain_nodes ?? 0,
      conns: a.genome?.brain_connections ?? 0,
    }));

  // Metabolic cost over time
  const costData = brainHistory.map((p) => ({
    tick: p.tick,
    avgCost: p.avgMetabolicCost,
    avgNodes: p.avgNodes,
    avgConns: p.avgConnections,
  }));

  // Complexity growth rate (nodes per 100 ticks)
  const growthRate =
    brainHistory.length > 10
      ? (
          (brainHistory[brainHistory.length - 1].avgNodes -
            brainHistory[Math.max(0, brainHistory.length - 11)].avgNodes) /
          10
        ).toFixed(2)
      : "—";

  return (
    <div>
      <div className="mb-5">
        <h2 className="text-lg font-semibold text-foreground">
          Brain Complexity
        </h2>
        <p className="text-sm text-muted-foreground">
          Each agent has a neural network brain that evolves over generations. Brains can grow new neurons and connections — but bigger brains cost more energy to run
        </p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-5">
        <StatBox
          label="Avg Neurons"
          value={latest ? latest.avgNodes.toFixed(1) : "—"}
          sub="Per brain"
          color="#4f46e5"
        />
        <StatBox
          label="Max Neurons"
          value={latest ? latest.maxNodes.toString() : "—"}
          sub="Most complex brain"
          color="#7c3aed"
        />
        <StatBox
          label="Avg Connections"
          value={latest ? latest.avgConnections.toFixed(1) : "—"}
          sub="Per brain"
          color="#0891b2"
        />
        <StatBox
          label="Max Connections"
          value={latest ? latest.maxConnections.toString() : "—"}
          sub="Most wired brain"
          color="#0d9488"
        />
        <StatBox
          label="Avg Cost"
          value={latest ? latest.avgMetabolicCost.toFixed(3) : "—"}
          sub="Energy/tick"
          color="#d97706"
        />
        <StatBox
          label="Growth Rate"
          value={growthRate}
          sub="Nodes/sample"
          color="#059669"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Brain topology over time */}
        <div className="bg-card border border-border rounded-xl p-5">
          <TitleWithTip
            title="Brain Topology Growth"
            tip="Average brain size over time. Neurons are processing units, connections are wires between them. More = smarter (but more expensive to run)."
            className="mb-1"
          />
          <div className="text-[11px] text-muted-foreground mb-3">
            Average neuron and connection count over time
          </div>
          <div className="h-[280px]">
            {brainHistory.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={brainHistory}>
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
                  <Line
                    type="monotone"
                    dataKey="avgNodes"
                    stroke="#4f46e5"
                    strokeWidth={1.5}
                    dot={false}
                    name="Avg Neurons"
                  />
                  <Line
                    type="monotone"
                    dataKey="avgConnections"
                    stroke="#0891b2"
                    strokeWidth={1.5}
                    dot={false}
                    name="Avg Connections"
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
                No brain data yet
              </div>
            )}
          </div>
        </div>

        {/* Max topology over time */}
        <div className="bg-card border border-border rounded-xl p-5">
          <TitleWithTip
            title="Peak Brain Complexity"
            tip="The most complex brain alive at each point. This shows the frontier of neural evolution — the smartest (or at least largest) brains that exist."
            className="mb-1"
          />
          <div className="text-[11px] text-muted-foreground mb-3">
            Maximum neuron and connection counts over time
          </div>
          <div className="h-[280px]">
            {brainHistory.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={brainHistory}>
                  <defs>
                    <linearGradient id="brain-max-n" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#7c3aed" stopOpacity={0.15} />
                      <stop offset="100%" stopColor="#7c3aed" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="brain-max-c" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#0d9488" stopOpacity={0.15} />
                      <stop offset="100%" stopColor="#0d9488" stopOpacity={0} />
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
                    dataKey="maxNodes"
                    stroke="#7c3aed"
                    fill="url(#brain-max-n)"
                    strokeWidth={1.5}
                    name="Max Neurons"
                  />
                  <Area
                    type="monotone"
                    dataKey="maxConnections"
                    stroke="#0d9488"
                    fill="url(#brain-max-c)"
                    strokeWidth={1.5}
                    name="Max Connections"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
                No brain data yet
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Metabolic cost */}
      <div className="bg-card border border-border rounded-xl p-5 mt-4">
        <TitleWithTip
          title="Brain Metabolic Cost"
          tip="Bigger brains burn more energy per tick. This creates a trade-off: smarter agents can find more food, but they also need more to survive. Evolution finds the balance."
          className="mb-1"
        />
        <div className="text-[11px] text-muted-foreground mb-3">
          Average energy cost of running brains over time
        </div>
        <div className="h-[220px]">
          {costData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={costData}>
                <defs>
                  <linearGradient id="cost-g" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#d97706" stopOpacity={0.15} />
                    <stop offset="100%" stopColor="#d97706" stopOpacity={0} />
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
                  dataKey="avgCost"
                  stroke="#d97706"
                  fill="url(#cost-g)"
                  strokeWidth={1.5}
                  name="Avg Brain Cost"
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
              No metabolic cost data yet
            </div>
          )}
        </div>
      </div>

      {/* Species brain comparison */}
      {latestSpecies.length > 0 && (
        <div className="bg-card border border-border rounded-xl p-5 mt-4">
          <TitleWithTip
            title="Species Brain Comparison"
            tip="Different species evolve different brain sizes. Bars show neurons and connections; the line shows fitness (energy). Bigger brains don't always mean more successful species."
            className="mb-1"
          />
          <div className="text-[11px] text-muted-foreground mb-3">
            Brain topology differences between species
          </div>
          <div className="h-[220px]">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart
                data={latestSpecies.map((sp) => ({
                  name: `S${sp.speciesId}`,
                  nodes: sp.avgBrainNodes,
                  conns: sp.avgBrainConns,
                  fitness: sp.avgFitness,
                }))}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                <XAxis
                  dataKey="name"
                  tick={{ fontSize: 10, fill: "#9ca3af" }}
                  stroke="#e5e7eb"
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
                <Tooltip contentStyle={TT} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar
                  yAxisId="left"
                  dataKey="nodes"
                  fill="#4f46e5"
                  fillOpacity={0.6}
                  name="Avg Neurons"
                  barSize={20}
                />
                <Bar
                  yAxisId="left"
                  dataKey="conns"
                  fill="#0891b2"
                  fillOpacity={0.6}
                  name="Avg Connections"
                  barSize={20}
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="fitness"
                  stroke="#d97706"
                  strokeWidth={2}
                  dot={{ fill: "#d97706", r: 3 }}
                  name="Avg Fitness"
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
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

