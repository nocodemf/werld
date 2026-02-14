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
  Cell,
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

// ── Effector channel names & colors ──────────────────────────────────────

const EFFECTOR_CHANNEL_COLORS: Record<string, string> = {
  locomotion: "#3b82f6",
  harvest: "#059669",
  social: "#d97706",
  maintenance: "#7c3aed",
  reproduction: "#db2777",
  signal: "#0891b2",
};

// Legacy action names for macro sequence display
const ACTION_NAMES: Record<number, string> = {
  0: "move_0",
  1: "move_1",
  2: "move_2",
  3: "move_3",
  4: "harvest",
  5: "transfer",
  6: "signal",
  7: "maintain",
  8: "fork",
  9: "observe",
  10: "idle",
  11: "attack",
};

const ACTION_COLORS: Record<string, string> = {
  move_0: "#3b82f6",
  move_1: "#60a5fa",
  move_2: "#93c5fd",
  move_3: "#2563eb",
  harvest: "#059669",
  transfer: "#d97706",
  signal: "#0891b2",
  maintain: "#7c3aed",
  fork: "#db2777",
  observe: "#6366f1",
  idle: "#9ca3af",
  attack: "#dc2626",
  macros: "#ea580c",
};

export default function IntelligenceSection({
  data,
}: {
  data: SimulationData;
}) {
  const {
    fullHistory,
    actionDistribution,
    effectorActivity,
    effectorHistory,
    recentMacros,
    overview,
  } = data;

  // Use effector data if available, fall back to legacy action distribution
  const hasEffectorData = effectorActivity && effectorActivity.length > 0;
  const hasEffectorHistory = effectorHistory && effectorHistory.length > 0;

  // Legacy action chart data (fallback)
  const primitives = actionDistribution.filter((d) => d.actionId <= 11);
  const macroTotal = actionDistribution
    .filter((d) => d.actionId > 11)
    .reduce((sum, d) => sum + d.count, 0);
  const total = actionDistribution.reduce((sum, d) => sum + d.count, 0) || 1;

  const actionData = [
    ...primitives.map((d) => ({
      name: d.actionName,
      count: d.count,
      pct: ((d.count / total) * 100).toFixed(1),
    })),
    ...(macroTotal > 0
      ? [
          {
            name: "macros",
            count: macroTotal,
            pct: ((macroTotal / total) * 100).toFixed(1),
          },
        ]
      : []),
  ].sort((a, b) => b.count - a.count);

  // Peak effector activation
  const peakEffector =
    hasEffectorData && effectorActivity.length > 0
      ? effectorActivity[0]
      : null;

  return (
    <div>
      <div className="mb-5">
        <h2 className="text-lg font-semibold text-foreground">Intelligence</h2>
        <p className="text-sm text-muted-foreground">
          How agents learn, what actions they take, and what new behaviours they&apos;ve invented on their own
        </p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-3 mb-5">
        <StatBox
          label="Avg Cortex Size"
          value={overview.avgCortexSize.toFixed(0)}
          sub="Learned associations"
          color="#4f46e5"
        />
        <StatBox
          label="Inventions"
          value={overview.totalMacros.toString()}
          sub="Motor patterns discovered"
          color="#ea580c"
        />
        <StatBox
          label={hasEffectorData ? "Dominant Effector" : "Brain Decisions"}
          value={
            hasEffectorData && peakEffector
              ? peakEffector.name
              : actionDistribution
                  .reduce((s, d) => s + d.count, 0)
                  .toLocaleString()
          }
          sub={
            hasEffectorData && peakEffector
              ? `Avg activation: ${peakEffector.avgActivation.toFixed(3)}`
              : "Last 500 ticks"
          }
          color={
            hasEffectorData && peakEffector ? peakEffector.color : "#0891b2"
          }
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Effector activity OR legacy action distribution */}
        <div className="bg-card border border-border rounded-xl p-5">
          <TitleWithTip
            title={hasEffectorData ? "Effector Activity" : "Action Distribution"}
            tip={hasEffectorData
              ? "Each bar is a 'muscle' the agent can use: locomotion (moving), harvest (eating), social (interacting), maintenance (self-repair), reproduction (making offspring), and signal (broadcasting). Longer bars = agents use that action more."
              : "What actions agents are choosing most often. Taller bars = more popular actions. This reveals the dominant survival strategy of the population."}
            className="mb-1"
          />
          <div className="text-[11px] text-muted-foreground mb-3">
            {hasEffectorData
              ? "Average continuous activation per effector channel (last 500 ticks)"
              : "Brain decisions over last 500 ticks"}
          </div>
          <div className="h-[280px]">
            {hasEffectorData ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={effectorActivity} layout="vertical">
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="#f3f4f6"
                    horizontal={false}
                  />
                  <XAxis
                    type="number"
                    domain={[0, "auto"]}
                    tick={{ fontSize: 10, fill: "#9ca3af" }}
                    stroke="#e5e7eb"
                    tickFormatter={(v: any) => Number(v).toFixed(2)}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    tick={{ fontSize: 11, fill: "#6b7280" }}
                    stroke="#e5e7eb"
                    width={90}
                  />
                  <Tooltip
                    contentStyle={TT}
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    formatter={(value: any) => [
                      Number(value).toFixed(4),
                      "Avg Activation",
                    ]}
                  />
                  <Bar
                    dataKey="avgActivation"
                    radius={[0, 4, 4, 0]}
                    barSize={18}
                  >
                    {effectorActivity.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={actionData} layout="vertical">
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="#f3f4f6"
                    horizontal={false}
                  />
                  <XAxis
                    type="number"
                    tick={{ fontSize: 10, fill: "#9ca3af" }}
                    stroke="#e5e7eb"
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    tick={{ fontSize: 11, fill: "#6b7280" }}
                    stroke="#e5e7eb"
                    width={65}
                  />
                  <Tooltip
                    contentStyle={TT}
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    formatter={(value: any, _: any, props: any) => [
                      `${Number(value).toLocaleString()} (${props?.payload?.pct ?? 0}%)`,
                      "Count",
                    ]}
                  />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={16}>
                    {actionData.map((entry, i) => (
                      <Cell
                        key={i}
                        fill={ACTION_COLORS[entry.name] ?? "#9ca3af"}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Effector history OR cortex growth */}
        <div className="bg-card border border-border rounded-xl p-5">
          <TitleWithTip
            title={hasEffectorHistory ? "Effector Activation Over Time" : "Cortex Growth"}
            tip={hasEffectorHistory
              ? "How each 'muscle' usage changes over time. Shifting patterns mean the population is evolving new behavioural strategies — e.g. switching from harvesting to reproducing."
              : "How many situation→action associations agents have learned. More = agents have a richer repertoire of responses. This is their fast 'instinct' memory."}
            className="mb-1"
          />
          <div className="text-[11px] text-muted-foreground mb-3">
            {hasEffectorHistory
              ? "How effector channel usage evolves"
              : "Average learned associations over time"}
          </div>
          <div className="h-[280px]">
            {hasEffectorHistory ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={effectorHistory}>
                  <defs>
                    {Object.entries(EFFECTOR_CHANNEL_COLORS).map(
                      ([key, color]) => (
                        <linearGradient
                          key={key}
                          id={`eff-${key}`}
                          x1="0"
                          y1="0"
                          x2="0"
                          y2="1"
                        >
                          <stop
                            offset="0%"
                            stopColor={color}
                            stopOpacity={0.15}
                          />
                          <stop
                            offset="100%"
                            stopColor={color}
                            stopOpacity={0}
                          />
                        </linearGradient>
                      )
                    )}
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                  <XAxis
                    dataKey="tick"
                    tick={{ fontSize: 10, fill: "#9ca3af" }}
                    stroke="#e5e7eb"
                    tickFormatter={(v: any) => Number(v).toLocaleString()}
                  />
                  <YAxis
                    tick={{ fontSize: 10, fill: "#9ca3af" }}
                    stroke="#e5e7eb"
                    tickFormatter={(v: any) => Number(v).toFixed(2)}
                  />
                  <Tooltip
                    contentStyle={TT}
                    labelFormatter={(v: any) =>
                      `Tick ${Number(v).toLocaleString()}`
                    }
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    formatter={(value: any) => [Number(value).toFixed(4)]}
                  />
                  <Legend
                    wrapperStyle={{ fontSize: 10, paddingTop: 4 }}
                    iconSize={8}
                    iconType="circle"
                  />
                  {Object.entries(EFFECTOR_CHANNEL_COLORS).map(
                    ([key, color]) => (
                      <Area
                        key={key}
                        type="monotone"
                        dataKey={key}
                        stroke={color}
                        fill={`url(#eff-${key})`}
                        strokeWidth={1.5}
                        name={key.charAt(0).toUpperCase() + key.slice(1)}
                        dot={false}
                      />
                    )
                  )}
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={fullHistory}>
                  <defs>
                    <linearGradient id="cortex-g" x1="0" y1="0" x2="0" y2="1">
                      <stop
                        offset="0%"
                        stopColor="#4f46e5"
                        stopOpacity={0.12}
                      />
                      <stop
                        offset="100%"
                        stopColor="#4f46e5"
                        stopOpacity={0}
                      />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                  <XAxis
                    dataKey="tick"
                    tick={{ fontSize: 10, fill: "#9ca3af" }}
                    stroke="#e5e7eb"
                    tickFormatter={(v: any) => Number(v).toLocaleString()}
                  />
                  <YAxis
                    tick={{ fontSize: 10, fill: "#9ca3af" }}
                    stroke="#e5e7eb"
                  />
                  <Tooltip
                    contentStyle={TT}
                    labelFormatter={(v: any) =>
                      `Tick ${Number(v).toLocaleString()}`
                    }
                  />
                  <Area
                    type="monotone"
                    dataKey="avg_cortex_size"
                    stroke="#4f46e5"
                    fill="url(#cortex-g)"
                    strokeWidth={1.5}
                    name="Avg Cortex"
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* Cortex growth (shown alongside effector data) */}
      {hasEffectorHistory && (
        <div className="bg-card border border-border rounded-xl p-5 mt-4">
          <TitleWithTip
            title="Cortex Growth"
            tip="The cortex is a fast-learning memory bank — it stores which actions worked in which situations. More associations = smarter decisions without needing the full neural network."
            className="mb-1"
          />
          <div className="text-[11px] text-muted-foreground mb-3">
            Average learned associations over time
          </div>
          <div className="h-[200px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={fullHistory}>
                <defs>
                  <linearGradient id="cortex-g2" x1="0" y1="0" x2="0" y2="1">
                    <stop
                      offset="0%"
                      stopColor="#4f46e5"
                      stopOpacity={0.12}
                    />
                    <stop
                      offset="100%"
                      stopColor="#4f46e5"
                      stopOpacity={0}
                    />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                <XAxis
                  dataKey="tick"
                  tick={{ fontSize: 10, fill: "#9ca3af" }}
                  stroke="#e5e7eb"
                  tickFormatter={(v: any) => Number(v).toLocaleString()}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: "#9ca3af" }}
                  stroke="#e5e7eb"
                />
                <Tooltip
                  contentStyle={TT}
                  labelFormatter={(v: any) =>
                    `Tick ${Number(v).toLocaleString()}`
                  }
                />
                <Area
                  type="monotone"
                  dataKey="avg_cortex_size"
                  stroke="#4f46e5"
                  fill="url(#cortex-g2)"
                  strokeWidth={1.5}
                  name="Avg Cortex"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Motor pattern discoveries (macros) */}
      <div className="bg-card border border-border rounded-xl p-5 mt-4">
        <TitleWithTip
          title="Motor Pattern Discoveries"
          tip="Agents sometimes chain multiple actions together into routines — like 'harvest then move then harvest'. These are invented by agents, not programmed. Each row shows who discovered what and when."
          className="mb-1"
        />
        <div className="text-[11px] text-muted-foreground mb-3">
          Evolved compound effector sequences (behavioral inventions)
        </div>
        <div className="max-h-[300px] overflow-y-auto">
          {recentMacros.length === 0 ? (
            <div className="text-sm text-muted-foreground py-6 text-center">
              No motor patterns discovered yet
            </div>
          ) : (
            <div className="space-y-1.5">
              {recentMacros.map((m, i) => (
                <div
                  key={`${m.tick}-${m.agentId}-${i}`}
                  className="flex items-center gap-3 text-[12px] px-3 py-2 rounded-lg bg-muted/30"
                >
                  <span className="font-mono text-muted-foreground w-14 shrink-0 tabular-nums">
                    T{m.tick}
                  </span>
                  <span className="font-mono text-foreground/70 w-12 shrink-0">
                    #{m.agentId}
                  </span>
                  <div className="flex items-center gap-1 flex-wrap">
                    {m.sequence.map((actionId, j) => {
                      const name = ACTION_NAMES[actionId] ?? `m${actionId}`;
                      return (
                        <span key={j} className="flex items-center">
                          {j > 0 && (
                            <span className="text-muted-foreground mx-0.5 text-[10px]">
                              →
                            </span>
                          )}
                          <span
                            className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium"
                            style={{
                              backgroundColor: `${ACTION_COLORS[name] ?? "#9ca3af"}15`,
                              color: ACTION_COLORS[name] ?? "#6b7280",
                            }}
                          >
                            {name}
                          </span>
                        </span>
                      );
                    })}
                  </div>
                </div>
              ))}
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
      <div
        className="text-xl font-semibold tabular-nums mt-1"
        style={{ color }}
      >
        {value}
      </div>
      <div className="text-[11px] text-muted-foreground mt-0.5">{sub}</div>
    </div>
  );
}
