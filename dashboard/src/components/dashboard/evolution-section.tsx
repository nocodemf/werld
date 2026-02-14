"use client";

import type { SimulationData } from "@/hooks/use-simulation";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  LineChart,
  Line,
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

// Distinct colors for up to 12 species
const SPECIES_COLORS = [
  "#3b82f6", "#059669", "#d97706", "#dc2626", "#7c3aed",
  "#0891b2", "#db2777", "#ea580c", "#6366f1", "#84cc16",
  "#f43f5e", "#14b8a6",
];

export default function EvolutionSection({
  data,
}: {
  data: SimulationData;
}) {
  const { generationDist, speciesHistory, latestSpecies } = data;

  // ── Species stacked area: transform species history into per-tick stacked data
  const speciesStackData = buildSpeciesStack(speciesHistory);
  const allSpeciesIds = Array.from(
    new Set(speciesHistory.map((s) => s.speciesId))
  ).sort((a, b) => a - b);

  // ── Generation distribution
  const genData = generationDist.map((g) => ({
    gen: `G${g.generation}`,
    alive: g.alive,
    dead: g.dead,
    avgLifespan: Math.round(g.avgLifespan),
  }));

  // Summary stats
  const totalSpecies = latestSpecies.length;
  const maxGen = generationDist.length > 0
    ? Math.max(...generationDist.map((g) => g.generation))
    : 0;
  const dominantSpecies = latestSpecies.length > 0
    ? latestSpecies.reduce((a, b) => (a.currentCount > b.currentCount ? a : b))
    : null;
  const avgLifespan = generationDist.length > 0
    ? generationDist
        .filter((g) => g.avgLifespan > 0)
        .reduce((s, g) => s + g.avgLifespan, 0) /
      Math.max(1, generationDist.filter((g) => g.avgLifespan > 0).length)
    : 0;

  return (
    <div>
      <div className="mb-5">
        <h2 className="text-lg font-semibold text-foreground">Evolution</h2>
        <p className="text-sm text-muted-foreground">
          How the population is branching into different species, how deep the family trees go, and which species are thriving
        </p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
        <StatBox
          label="Species"
          value={totalSpecies.toString()}
          sub="Currently active"
          color="#7c3aed"
        />
        <StatBox
          label="Max Generation"
          value={maxGen.toString()}
          sub="Deepest lineage"
          color="#059669"
        />
        <StatBox
          label="Dominant Species"
          value={
            dominantSpecies
              ? `S${dominantSpecies.speciesId} (${dominantSpecies.currentCount})`
              : "—"
          }
          sub="Largest group"
          color="#3b82f6"
        />
        <StatBox
          label="Avg Lifespan"
          value={avgLifespan.toFixed(0)}
          sub="Ticks (dead agents)"
          color="#d97706"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Species over time (stacked area) */}
        <div className="bg-card border border-border rounded-xl p-5">
          <TitleWithTip
            title="Species Population"
            tip="Each colour is a different species. Species form naturally when groups of agents become genetically distinct from each other. Dominant colours mean one species is outcompeting others."
            className="mb-1"
          />
          <div className="text-[11px] text-muted-foreground mb-3">
            Population by species over time
          </div>
          <div className="h-[280px]">
            {speciesStackData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={speciesStackData}>
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
                  {allSpeciesIds.slice(0, 12).map((sid, i) => (
                    <Area
                      key={sid}
                      type="monotone"
                      dataKey={`s${sid}`}
                      stackId="species"
                      stroke={SPECIES_COLORS[i % SPECIES_COLORS.length]}
                      fill={SPECIES_COLORS[i % SPECIES_COLORS.length]}
                      fillOpacity={0.3}
                      strokeWidth={1}
                      name={`Species ${sid}`}
                    />
                  ))}
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
                No species data yet
              </div>
            )}
          </div>
        </div>

        {/* Generation distribution */}
        <div className="bg-card border border-border rounded-xl p-5">
          <TitleWithTip
            title="Generation Distribution"
            tip="Each bar is a generation — G0 are the original agents, G1 are their children, etc. Green = still alive, grey = died. More bars to the right means deeper evolutionary lineages."
            className="mb-1"
          />
          <div className="text-[11px] text-muted-foreground mb-3">
            Alive vs dead agents per generation
          </div>
          <div className="h-[280px]">
            {genData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={genData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                  <XAxis
                    dataKey="gen"
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
                  />
                  <Bar
                    dataKey="alive"
                    stackId="gen"
                    fill="#059669"
                    fillOpacity={0.7}
                    name="Alive"
                    radius={[0, 0, 0, 0]}
                  />
                  <Bar
                    dataKey="dead"
                    stackId="gen"
                    fill="#9ca3af"
                    fillOpacity={0.4}
                    name="Dead"
                    radius={[2, 2, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
                No generation data yet
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Current species table */}
      <div className="bg-card border border-border rounded-xl p-5 mt-4">
        <TitleWithTip
          title="Active Species"
          tip="All species currently alive. Members = population count. Fitness = average energy (higher is better). Brain Nodes/Conns show how complex their neural networks are."
          className="mb-1"
        />
        <div className="text-[11px] text-muted-foreground mb-3">
          Current species with brain characteristics
        </div>
        <div className="max-h-[300px] overflow-y-auto">
          {latestSpecies.length === 0 ? (
            <div className="text-sm text-muted-foreground py-6 text-center">
              No species data yet
            </div>
          ) : (
            <table className="w-full text-[12px]">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-2 px-3 font-medium text-muted-foreground">Species</th>
                  <th className="text-right py-2 px-3 font-medium text-muted-foreground">Members</th>
                  <th className="text-right py-2 px-3 font-medium text-muted-foreground">Avg Fitness</th>
                  <th className="text-right py-2 px-3 font-medium text-muted-foreground">Brain Nodes</th>
                  <th className="text-right py-2 px-3 font-medium text-muted-foreground">Brain Conns</th>
                </tr>
              </thead>
              <tbody>
                {latestSpecies.map((sp, i) => (
                  <tr
                    key={sp.speciesId}
                    className="border-b border-border/50 hover:bg-muted/30 transition-colors"
                  >
                    <td className="py-2 px-3">
                      <div className="flex items-center gap-2">
                        <span
                          className="w-2 h-2 rounded-full shrink-0"
                          style={{
                            backgroundColor: SPECIES_COLORS[i % SPECIES_COLORS.length],
                          }}
                        />
                        <span className="font-mono">S{sp.speciesId}</span>
                      </div>
                    </td>
                    <td className="text-right py-2 px-3 font-mono tabular-nums">
                      {sp.currentCount}
                    </td>
                    <td className="text-right py-2 px-3 font-mono tabular-nums">
                      {sp.avgFitness.toFixed(1)}
                    </td>
                    <td className="text-right py-2 px-3 font-mono tabular-nums">
                      {sp.avgBrainNodes}
                    </td>
                    <td className="text-right py-2 px-3 font-mono tabular-nums">
                      {sp.avgBrainConns}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Species fitness over time */}
      {speciesHistory.length > 0 && (
        <div className="bg-card border border-border rounded-xl p-5 mt-4">
          <TitleWithTip
            title="Species Fitness Trajectories"
            tip="How well each species is doing over time. Fitness = average energy. Rising lines mean a species is getting better at surviving. Species that drop off may be going extinct."
            className="mb-1"
          />
          <div className="text-[11px] text-muted-foreground mb-3">
            Average fitness (energy) by species over time
          </div>
          <div className="h-[240px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={buildSpeciesFitnessData(speciesHistory)}>
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
                {allSpeciesIds.slice(0, 8).map((sid, i) => (
                  <Line
                    key={sid}
                    type="monotone"
                    dataKey={`f${sid}`}
                    stroke={SPECIES_COLORS[i % SPECIES_COLORS.length]}
                    strokeWidth={1.5}
                    dot={false}
                    name={`S${sid} fitness`}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function buildSpeciesStack(
  speciesHistory: SimulationData["speciesHistory"]
): Record<string, number>[] {
  const tickMap = new Map<number, Record<string, number>>();
  for (const sp of speciesHistory) {
    if (!tickMap.has(sp.tick)) {
      tickMap.set(sp.tick, { tick: sp.tick });
    }
    const entry = tickMap.get(sp.tick)!;
    entry[`s${sp.speciesId}`] = sp.count;
  }
  return Array.from(tickMap.values()).sort((a, b) => a.tick - b.tick);
}

function buildSpeciesFitnessData(
  speciesHistory: SimulationData["speciesHistory"]
): Record<string, number>[] {
  const tickMap = new Map<number, Record<string, number>>();
  for (const sp of speciesHistory) {
    if (!tickMap.has(sp.tick)) {
      tickMap.set(sp.tick, { tick: sp.tick });
    }
    const entry = tickMap.get(sp.tick)!;
    entry[`f${sp.speciesId}`] = sp.avgFitness;
  }
  return Array.from(tickMap.values()).sort((a, b) => a.tick - b.tick);
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

