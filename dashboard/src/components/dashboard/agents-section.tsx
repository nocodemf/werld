"use client";

import { useState } from "react";
import type { SimulationData } from "@/hooks/use-simulation";
import { InfoTip, TitleWithTip } from "@/components/ui/info-tip";

type SortKey = "energy" | "entropy" | "age" | "cortex_size" | "generation" | "compound_actions";

const GENOME_TRAITS: { key: string; label: string; format: (v: number) => string }[] = [
  { key: "max_energy", label: "Max Energy", format: (v) => v.toFixed(0) },
  { key: "tick_cost", label: "Tick Cost", format: (v) => v.toFixed(2) },
  { key: "entropy_resistance", label: "Entropy Res.", format: (v) => v.toFixed(2) },
  { key: "sense_range", label: "Sense Range", format: (v) => v.toFixed(1) },
  { key: "learning_rate", label: "Learning Rate", format: (v) => v.toFixed(3) },
  { key: "exploration_factor", label: "Exploration", format: (v) => v.toFixed(2) },
  { key: "knowledge_transfer_strength", label: "Knowledge Transfer", format: (v) => v.toFixed(2) },
  { key: "mutation_rate", label: "Mutation Rate", format: (v) => v.toFixed(3) },
  { key: "fork_threshold", label: "Fork Threshold", format: (v) => v.toFixed(0) },
  { key: "signal_range", label: "Signal Range", format: (v) => v.toFixed(1) },
  { key: "signal_width", label: "Signal Width", format: (v) => v.toFixed(0) },
  { key: "cortex_capacity", label: "Cortex Capacity", format: (v) => v.toFixed(0) },
  { key: "memory_capacity", label: "Memory Capacity", format: (v) => v.toFixed(0) },
  // Evolvable internal drives (Phase A)
  { key: "harvest_drive", label: "Harvest Drive", format: (v) => v.toFixed(2) },
  { key: "maintain_drive", label: "Maintain Drive", format: (v) => v.toFixed(2) },
  { key: "explore_drive", label: "Explore Drive", format: (v) => v.toFixed(2) },
  { key: "social_drive", label: "Social Drive", format: (v) => v.toFixed(2) },
  { key: "reproduce_drive", label: "Reproduce Drive", format: (v) => v.toFixed(2) },
  { key: "signal_drive", label: "Signal Drive", format: (v) => v.toFixed(2) },
];

export default function AgentsSection({ data }: { data: SimulationData }) {
  const { agentSnapshots, recentEvents, overview } = data;
  const [sortKey, setSortKey] = useState<SortKey>("energy");
  const [sortAsc, setSortAsc] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<number | null>(null);

  const sorted = [...agentSnapshots].sort((a, b) => {
    const va = a[sortKey] ?? 0;
    const vb = b[sortKey] ?? 0;
    return sortAsc ? va - vb : vb - va;
  });

  const handleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(false);
    }
  };

  const selectedData = selectedAgent !== null
    ? agentSnapshots.find((a) => a.agent_id === selectedAgent)
    : null;

  // Only show birth/death/macro events
  const keyEvents = recentEvents.filter(
    (e) => e.event_type !== "brain_decision"
  );

  return (
    <div>
      <div className="mb-5">
        <div className="flex items-center gap-1.5">
          <h2 className="text-lg font-semibold text-foreground">Agents</h2>
          <InfoTip text="A roster of every living agent. Click any row to see its full genome — the genetic code that determines its traits, brain structure, and behavioral tendencies." />
        </div>
        <p className="text-sm text-muted-foreground">
          {overview.population} agents alive — click a row to inspect
        </p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* Agent table */}
        <div className="xl:col-span-2 bg-card border border-border rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-[12px]">
              <thead>
                <tr className="border-b border-border bg-muted/30">
                  <Th>ID</Th>
                  <ThSort
                    label="Gen"
                    active={sortKey === "generation"}
                    asc={sortAsc}
                    onClick={() => handleSort("generation")}
                  />
                  <ThSort
                    label="Age"
                    active={sortKey === "age"}
                    asc={sortAsc}
                    onClick={() => handleSort("age")}
                  />
                  <ThSort
                    label="Energy"
                    active={sortKey === "energy"}
                    asc={sortAsc}
                    onClick={() => handleSort("energy")}
                  />
                  <ThSort
                    label="Entropy"
                    active={sortKey === "entropy"}
                    asc={sortAsc}
                    onClick={() => handleSort("entropy")}
                  />
                  <Th>Node</Th>
                  <ThSort
                    label="Cortex"
                    active={sortKey === "cortex_size"}
                    asc={sortAsc}
                    onClick={() => handleSort("cortex_size")}
                  />
                  <Th>Memory</Th>
                  <ThSort
                    label="Macros"
                    active={sortKey === "compound_actions"}
                    asc={sortAsc}
                    onClick={() => handleSort("compound_actions")}
                  />
                  <Th>Parents</Th>
                </tr>
              </thead>
              <tbody>
                {sorted.length === 0 && (
                  <tr>
                    <td
                      colSpan={10}
                      className="text-center text-muted-foreground py-8"
                    >
                      No agent snapshots available
                    </td>
                  </tr>
                )}
                {sorted.map((a) => (
                  <tr
                    key={a.agent_id}
                    onClick={() => setSelectedAgent(a.agent_id === selectedAgent ? null : a.agent_id)}
                    className={`border-b border-border/50 cursor-pointer transition-colors ${
                      a.agent_id === selectedAgent
                        ? "bg-primary/[0.04]"
                        : "hover:bg-muted/30"
                    }`}
                  >
                    <td className="px-3 py-2 font-mono font-semibold text-foreground">
                      #{a.agent_id}
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium"
                        style={{
                          backgroundColor: genColor(a.generation).bg,
                          color: genColor(a.generation).fg,
                        }}
                      >
                        G{a.generation}
                      </span>
                    </td>
                    <td className="px-3 py-2 font-mono tabular-nums text-foreground/70">
                      {a.age.toLocaleString()}
                    </td>
                    <td className="px-3 py-2 font-mono tabular-nums">
                      <span style={{ color: energyColor(a.energy, a.genome.max_energy ?? 150) }}>
                        {a.energy.toFixed(0)}
                      </span>
                    </td>
                    <td className="px-3 py-2 font-mono tabular-nums">
                      <span style={{ color: a.entropy > 30 ? "#dc2626" : a.entropy > 10 ? "#d97706" : "#6b7280" }}>
                        {a.entropy.toFixed(0)}
                      </span>
                    </td>
                    <td className="px-3 py-2 font-mono tabular-nums text-muted-foreground">
                      {a.position}
                    </td>
                    <td className="px-3 py-2 font-mono tabular-nums text-indigo-600">
                      {a.cortex_size}
                    </td>
                    <td className="px-3 py-2 font-mono tabular-nums text-muted-foreground">
                      {a.memory_size}
                    </td>
                    <td className="px-3 py-2 font-mono tabular-nums text-orange-600">
                      {a.compound_actions}
                    </td>
                    <td className="px-3 py-2 font-mono text-muted-foreground text-[10px]">
                      {a.parent_a_id != null
                        ? `#${a.parent_a_id} × #${a.parent_b_id}`
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Side panel: detail or events */}
        <div className="space-y-4">
          {selectedData ? (
            <div className="bg-card border border-border rounded-xl p-5">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <div className="text-sm font-semibold text-foreground">
                    Agent #{selectedData.agent_id}
                  </div>
                  <div className="text-[11px] text-muted-foreground">
                    Generation {selectedData.generation} · Age{" "}
                    {selectedData.age.toLocaleString()}
                  </div>
                </div>
                <button
                  onClick={() => setSelectedAgent(null)}
                  className="text-[10px] text-muted-foreground hover:text-foreground cursor-pointer"
                >
                  ✕
                </button>
              </div>

              {/* Vitals */}
              <div className="grid grid-cols-2 gap-2 mb-4">
                <MiniStat label="Energy" value={selectedData.energy.toFixed(1)} color="#d97706" />
                <MiniStat label="Entropy" value={selectedData.entropy.toFixed(1)} color="#dc2626" />
                <MiniStat label="Node" value={String(selectedData.position)} color="#6b7280" />
                <MiniStat label="Cortex" value={String(selectedData.cortex_size)} color="#4f46e5" />
                <MiniStat label="Memory" value={String(selectedData.memory_size)} color="#6366f1" />
                <MiniStat label="Macros" value={String(selectedData.compound_actions)} color="#ea580c" />
              </div>

              {/* Genome */}
              <div className="text-[11px] font-medium text-foreground mb-2 uppercase tracking-wider">
                Genome
              </div>
              <div className="space-y-1 max-h-[300px] overflow-y-auto">
                {GENOME_TRAITS.map((trait) => {
                  const val = selectedData.genome?.[trait.key];
                  if (val === undefined) return null;
                  return (
                    <div
                      key={trait.key}
                      className="flex items-center justify-between text-[11px] px-2 py-1 rounded bg-muted/30"
                    >
                      <span className="text-muted-foreground">{trait.label}</span>
                      <span className="font-mono tabular-nums text-foreground/80">
                        {trait.format(val)}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="bg-card border border-border rounded-xl p-5">
              <div className="text-sm text-muted-foreground text-center py-4">
                Click an agent to inspect its details and genome
              </div>
            </div>
          )}

          {/* Event feed */}
          <div className="bg-card border border-border rounded-xl p-5">
            <TitleWithTip
              title="Recent Events"
              tip="A live log of births, deaths, and new inventions. Green = birth, red = death, orange = a new motor pattern was discovered."
              className="mb-3"
            />
            <div className="space-y-1 max-h-[280px] overflow-y-auto">
              {keyEvents.length === 0 && (
                <div className="text-[12px] text-muted-foreground py-4 text-center">
                  No events yet
                </div>
              )}
              {keyEvents.slice(0, 25).map((e, i) => (
                <div
                  key={`${e.tick}-${e.agent_id}-${i}`}
                  className="flex items-center gap-2 text-[11px] px-2 py-1 rounded hover:bg-muted/30 transition-colors"
                >
                  <span className="font-mono text-muted-foreground w-11 shrink-0 tabular-nums">
                    T{e.tick}
                  </span>
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{
                      backgroundColor:
                        e.event_type === "birth"
                          ? "#059669"
                          : e.event_type === "death"
                          ? "#dc2626"
                          : "#d97706",
                    }}
                  />
                  <span className="font-mono text-foreground/60 w-8 shrink-0">
                    #{e.agent_id}
                  </span>
                  <span className="text-muted-foreground truncate">
                    {e.description}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Helpers ──────────────────────────────────────────────────────────────

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="px-3 py-2.5 text-left text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
      {children}
    </th>
  );
}

function ThSort({
  label,
  active,
  asc,
  onClick,
}: {
  label: string;
  active: boolean;
  asc: boolean;
  onClick: () => void;
}) {
  return (
    <th
      onClick={onClick}
      className="px-3 py-2.5 text-left text-[10px] font-medium uppercase tracking-wider cursor-pointer select-none hover:text-foreground transition-colors"
      style={{ color: active ? "#111827" : "#9ca3af" }}
    >
      {label}
      {active && (
        <span className="ml-0.5 text-[8px]">{asc ? "▲" : "▼"}</span>
      )}
    </th>
  );
}

function MiniStat({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="bg-muted/30 rounded-lg px-3 py-2">
      <div className="text-[10px] text-muted-foreground uppercase tracking-wider">
        {label}
      </div>
      <div className="font-mono text-sm font-semibold tabular-nums" style={{ color }}>
        {value}
      </div>
    </div>
  );
}

function genColor(gen: number): { bg: string; fg: string } {
  const palette = [
    { bg: "#dcfce7", fg: "#16a34a" },
    { bg: "#dbeafe", fg: "#2563eb" },
    { bg: "#ede9fe", fg: "#7c3aed" },
    { bg: "#fef3c7", fg: "#d97706" },
    { bg: "#fce7f3", fg: "#db2777" },
    { bg: "#ccfbf1", fg: "#0d9488" },
    { bg: "#e0e7ff", fg: "#4f46e5" },
    { bg: "#fef9c3", fg: "#ca8a04" },
  ];
  return palette[gen % palette.length];
}

function energyColor(energy: number, maxEnergy: number): string {
  const ratio = energy / Math.max(maxEnergy, 1);
  if (ratio > 0.6) return "#059669";
  if (ratio > 0.3) return "#d97706";
  return "#dc2626";
}

