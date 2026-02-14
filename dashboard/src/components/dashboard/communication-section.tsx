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

function decodeSignal(v: number[]): string {
  if (v.length < 4) return "—";
  const parts: string[] = [];
  if (v[0] > 0.7) parts.push("STRONG");
  else if (v[0] < 0.2) parts.push("STARVING");
  else parts.push("OK");

  if (v[1] > 0.2) parts.push("AGING");
  else parts.push("YOUNG");

  if (v[2] > 0.2) parts.push("FOOD");
  else if (v[2] < 0.05) parts.push("BARREN");

  if (v[3] > 0.8) parts.push("CROWDED");
  else if (v[3] < 0.3) parts.push("ALONE");

  return parts.join(" · ");
}

export default function CommunicationSection({
  data,
}: {
  data: SimulationData;
}) {
  const { commsHistory, recentSignals, overview } = data;

  // Signal type distribution
  const typeCounts: Record<string, number> = {};
  for (const sig of recentSignals) {
    const decoded = decodeSignal(sig.vector);
    typeCounts[decoded] = (typeCounts[decoded] ?? 0) + 1;
  }
  const sortedTypes = Object.entries(typeCounts).sort((a, b) => b[1] - a[1]);
  const totalSigs = recentSignals.length;

  return (
    <div>
      <div className="mb-5">
        <h2 className="text-lg font-semibold text-foreground">
          Communication
        </h2>
        <p className="text-sm text-muted-foreground">
          Agents can broadcast signals to nearby neighbours. The content of these signals is evolved — we don&apos;t know what they mean, only that agents are choosing to send them
        </p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-4 gap-3 mb-5">
        <StatBox
          label="Total Deliveries"
          value={overview.totalSignalDeliveries.toLocaleString()}
          color="#0891b2"
        />
        <StatBox
          label="Recent Signals"
          value={totalSigs.toString()}
          color="#06b6d4"
        />
        <StatBox
          label="Avg Distance"
          value={
            commsHistory.length > 0
              ? commsHistory[commsHistory.length - 1].avgDistance.toFixed(1)
              : "—"
          }
          color="#0d9488"
        />
        <StatBox
          label="Message Types"
          value={sortedTypes.length.toString()}
          color="#7c3aed"
        />
      </div>

      {/* Signal activity chart */}
      <div className="bg-card border border-border rounded-xl p-5">
        <TitleWithTip
          title="Signal Activity Over Time"
          tip="How much 'talking' is happening. Delivered = messages that reached another agent. Senders/Receivers = how many unique agents are participating."
          className="mb-1"
        />
        <div className="text-[11px] text-muted-foreground mb-3">
          Deliveries and unique participants
        </div>
        <div className="h-[240px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={commsHistory}>
              <defs>
                <linearGradient id="sig-g" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#0891b2" stopOpacity={0.12} />
                  <stop offset="100%" stopColor="#0891b2" stopOpacity={0} />
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
                dataKey="signalsDelivered"
                stroke="#0891b2"
                fill="url(#sig-g)"
                strokeWidth={1.5}
                name="Delivered"
              />
              <Area
                type="monotone"
                dataKey="uniqueSenders"
                stroke="#7c3aed"
                fill="none"
                strokeWidth={1}
                strokeDasharray="4 4"
                name="Unique Senders"
              />
              <Area
                type="monotone"
                dataKey="uniqueReceivers"
                stroke="#059669"
                fill="none"
                strokeWidth={1}
                strokeDasharray="4 4"
                name="Unique Receivers"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
        {/* Signal decoder */}
        <div className="bg-card border border-border rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <TitleWithTip
              title="Signal Decoder"
              tip="A live feed of recent broadcasts. Each row shows: when it was sent, who sent it, who received it, how far it travelled, and our best guess at what the signal 'means' based on its values."
            />
            <span className="relative flex h-1.5 w-1.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-cyan-500" />
            </span>
          </div>
          <div className="max-h-[320px] overflow-y-auto space-y-1">
            {recentSignals.length === 0 && (
              <div className="text-sm text-muted-foreground py-6 text-center">
                No signals detected yet
              </div>
            )}
            {recentSignals.slice(0, 30).map((sig, i) => (
              <div
                key={`${sig.tick}-${sig.senderId}-${i}`}
                className="flex items-center gap-2 text-[11px] font-mono px-2.5 py-1.5 rounded-lg bg-muted/30"
              >
                <span className="text-muted-foreground w-11 shrink-0 tabular-nums">
                  T{sig.tick}
                </span>
                <span className="text-cyan-600 w-10 shrink-0">
                  #{sig.senderId}
                </span>
                <span className="text-muted-foreground text-[10px]">→</span>
                <span className="text-violet-600 w-10 shrink-0">
                  #{sig.receiverId}
                </span>
                <span className="text-muted-foreground/60 w-8 shrink-0 text-[10px]">
                  d={sig.distance}
                </span>
                <span className="text-foreground/60 truncate text-[10px]">
                  {decodeSignal(sig.vector)}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Message distribution */}
        <div className="bg-card border border-border rounded-xl p-5">
          <TitleWithTip
            title="Message Distribution"
            tip="Groups decoded signals by type and shows how common each kind is. Agents don't intend these categories — we assign labels based on signal values to help us see patterns."
            className="mb-1"
          />
          <div className="text-[11px] text-muted-foreground mb-3">
            Decoded signal content breakdown
          </div>
          {sortedTypes.length === 0 ? (
            <div className="text-sm text-muted-foreground py-6 text-center">
              No signal data available
            </div>
          ) : (
            <div className="space-y-2 max-h-[320px] overflow-y-auto">
              {sortedTypes.map(([msg, count]) => {
                const pct = totalSigs > 0 ? (count / totalSigs) * 100 : 0;
                return (
                  <div key={msg} className="flex items-center gap-3">
                    <span className="font-mono text-[11px] text-foreground/70 w-40 shrink-0 truncate">
                      {msg}
                    </span>
                    <div className="flex-1 h-3 bg-muted/50 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: `${Math.max(pct, 2)}%`,
                          backgroundColor: "#0891b250",
                        }}
                      />
                    </div>
                    <span className="font-mono text-[10px] text-muted-foreground w-16 shrink-0 text-right tabular-nums">
                      {count} ({pct.toFixed(0)}%)
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Signal content averages chart */}
      {commsHistory.length > 0 && (
        <div className="bg-card border border-border rounded-xl p-5 mt-4">
          <TitleWithTip
            title="Average Signal Content"
            tip="Each signal has multiple numeric channels (like radio frequencies). This shows the average value of each channel over time. Convergence to specific values may indicate emerging 'language' patterns."
            className="mb-1"
          />
          <div className="text-[11px] text-muted-foreground mb-3">
            Mean signal channel values over time
          </div>
          <div className="h-[200px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={commsHistory}>
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
                  domain={[0, 1]}
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
                  dataKey="avgSignalEnergy"
                  stroke="#d97706"
                  fill="none"
                  strokeWidth={1.5}
                  name="Energy (ch0)"
                />
                <Area
                  type="monotone"
                  dataKey="avgSignalEntropy"
                  stroke="#dc2626"
                  fill="none"
                  strokeWidth={1.5}
                  name="Entropy (ch1)"
                />
                <Area
                  type="monotone"
                  dataKey="avgSignalResource"
                  stroke="#059669"
                  fill="none"
                  strokeWidth={1.5}
                  name="Resource (ch2)"
                />
              </AreaChart>
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

