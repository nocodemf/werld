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
} from "recharts";
import { TitleWithTip } from "@/components/ui/info-tip";

const TT = {
  backgroundColor: "#fff",
  border: "1px solid #e5e7eb",
  borderRadius: "8px",
  fontSize: 12,
  boxShadow: "0 4px 6px -1px rgba(0,0,0,0.05)",
};

export default function ResourcesSection({ data }: { data: SimulationData }) {
  const { fullHistory, overview, agentSnapshots } = data;

  // Energy distribution among agents
  const energyBuckets = computeBuckets(
    agentSnapshots.map((a) => a.energy),
    6
  );
  const entropyBuckets = computeBuckets(
    agentSnapshots.map((a) => a.entropy),
    6
  );

  return (
    <div>
      <div className="mb-5">
        <h2 className="text-lg font-semibold text-foreground">Resources</h2>
        <p className="text-sm text-muted-foreground">
          The world&apos;s food supply, how agents are using it, and the physical decay they face over time
        </p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-4 gap-3 mb-5">
        <StatBox
          label="Avg Energy"
          value={overview.avgEnergy.toFixed(1)}
          color="#d97706"
        />
        <StatBox
          label="Avg Entropy"
          value={overview.avgEntropy.toFixed(1)}
          color="#dc2626"
        />
        <StatBox
          label="Substrate Energy"
          value={`${(overview.substrateEnergy / 1000).toFixed(1)}k`}
          color="#0d9488"
        />
        <StatBox
          label="Avg Age"
          value={overview.avgAge.toFixed(0)}
          color="#6366f1"
        />
      </div>

      {/* Energy & Entropy over time */}
      <div className="bg-card border border-border rounded-xl p-5">
        <TitleWithTip
          title="Energy & Entropy Trends"
          tip="Energy (orange) is like health/food — more is better. Entropy (red) is physical decay — it rises with age and kills at 100. Age (dashed) shows how long agents live."
          className="mb-1"
        />
        <div className="text-[11px] text-muted-foreground mb-3">
          Population averages over time
        </div>
        <div className="h-[260px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={fullHistory}>
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
              <Legend
                wrapperStyle={{ fontSize: 11 }}
                iconType="plainline"
                iconSize={12}
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="avg_energy"
                stroke="#d97706"
                strokeWidth={1.5}
                dot={false}
                name="Avg Energy"
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="avg_entropy"
                stroke="#dc2626"
                strokeWidth={1.5}
                dot={false}
                name="Avg Entropy"
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="avg_age"
                stroke="#6366f1"
                strokeWidth={1}
                dot={false}
                strokeDasharray="4 4"
                name="Avg Age"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Substrate energy */}
      <div className="bg-card border border-border rounded-xl p-5 mt-4">
        <TitleWithTip
          title="Substrate Energy"
          tip="The total 'food' available across all 800 nodes in the world. It regenerates naturally and fluctuates with seasons. When agents harvest, it drops."
          className="mb-1"
        />
        <div className="text-[11px] text-muted-foreground mb-3">
          Total energy available in the world graph
        </div>
        <div className="h-[200px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={fullHistory}>
              <defs>
                <linearGradient id="sub-g" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#0d9488" stopOpacity={0.12} />
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
                tickFormatter={(v) =>
                  `${(Number(v) / 1000).toFixed(0)}k`
                }
              />
              <Tooltip
                contentStyle={TT}
                labelFormatter={(v) => `Tick ${Number(v).toLocaleString()}`}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                formatter={(v: any) => [
                  `${Number(v).toLocaleString()}`,
                  "Substrate Energy",
                ]}
              />
              <Area
                type="monotone"
                dataKey="substrate_energy"
                stroke="#0d9488"
                fill="url(#sub-g)"
                strokeWidth={1.5}
                name="Substrate Energy"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Distribution histograms */}
      {agentSnapshots.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
          <DistributionPanel
            title="Energy Distribution"
            sub="Current energy levels across agents"
            data={energyBuckets}
            color="#d97706"
          />
          <DistributionPanel
            title="Entropy Distribution"
            sub="Current entropy levels across agents"
            data={entropyBuckets}
            color="#dc2626"
          />
        </div>
      )}
    </div>
  );
}

// ── Helpers ──────────────────────────────────────────────────────────────

function StatBox({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
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
        {value}
      </div>
    </div>
  );
}

function computeBuckets(
  values: number[],
  numBuckets: number
): { range: string; count: number }[] {
  if (values.length === 0) return [];
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (min === max) return [{ range: `${min.toFixed(0)}`, count: values.length }];
  const step = (max - min) / numBuckets;
  const buckets: { range: string; count: number }[] = [];
  for (let i = 0; i < numBuckets; i++) {
    const lo = min + i * step;
    const hi = lo + step;
    const count = values.filter(
      (v) => v >= lo && (i === numBuckets - 1 ? v <= hi : v < hi)
    ).length;
    buckets.push({
      range: `${lo.toFixed(0)}-${hi.toFixed(0)}`,
      count,
    });
  }
  return buckets;
}

function DistributionPanel({
  title,
  sub,
  data,
  color,
}: {
  title: string;
  sub: string;
  data: { range: string; count: number }[];
  color: string;
}) {
  return (
    <div className="bg-card border border-border rounded-xl p-5">
      <div className="text-sm font-medium text-foreground mb-1">{title}</div>
      <div className="text-[11px] text-muted-foreground mb-3">{sub}</div>
      <div className="space-y-1.5">
        {data.map((d) => {
          const maxCount = Math.max(...data.map((b) => b.count), 1);
          const pct = (d.count / maxCount) * 100;
          return (
            <div key={d.range} className="flex items-center gap-2 text-[11px]">
              <span className="font-mono text-muted-foreground w-20 shrink-0 text-right tabular-nums">
                {d.range}
              </span>
              <div className="flex-1 h-4 bg-muted/50 rounded overflow-hidden">
                <div
                  className="h-full rounded transition-all"
                  style={{
                    width: `${Math.max(pct, 2)}%`,
                    backgroundColor: `${color}30`,
                    borderRight: `2px solid ${color}`,
                  }}
                />
              </div>
              <span className="font-mono text-foreground/70 w-6 tabular-nums">
                {d.count}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

