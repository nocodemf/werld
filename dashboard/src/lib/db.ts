import Database from "better-sqlite3";
import path from "path";

const DB_PATH = path.resolve(process.cwd(), "..", "data", "simulation.db");

let _db: Database.Database | null = null;
let _dbOpenedAt = 0;
const DB_TTL = 10_000; // re-open every 10s to pick up file changes

function getDb(): Database.Database {
  const now = Date.now();
  if (_db && now - _dbOpenedAt > DB_TTL) {
    try { _db.close(); } catch { /* ignore */ }
    _db = null;
  }
  if (!_db) {
    _db = new Database(DB_PATH, { readonly: true, fileMustExist: true });
    _db.pragma("journal_mode = WAL");
    _dbOpenedAt = now;
  }
  return _db;
}

// ── Action name mapping (legacy discrete actions) ─────────────────────────
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

// ── Effector channel colors (continuous motor interface) ─────────────────────
const EFFECTOR_COLORS: Record<string, string> = {
  Locomotion: "#3b82f6",
  Harvest: "#059669",
  Transfer: "#d97706",
  Attack: "#dc2626",
  Maintenance: "#7c3aed",
  Reproduction: "#db2777",
  Signal: "#0891b2",
};

// ── Types ────────────────────────────────────────────────────────────────

export interface OverviewStats {
  currentTick: number;
  population: number;
  totalBirths: number;
  totalDeaths: number;
  avgEnergy: number;
  avgEntropy: number;
  avgAge: number;
  maxGeneration: number;
  avgCortexSize: number;
  substrateEnergy: number;
  totalMacros: number;
  totalSignalDeliveries: number;
}

export interface FullHistoryPoint {
  tick: number;
  population: number;
  avg_energy: number;
  avg_entropy: number;
  avg_age: number;
  avg_cortex_size: number;
  substrate_energy: number;
  max_generation: number;
  total_births: number;
  total_deaths: number;
}

export interface ActionCount {
  actionId: number;
  actionName: string;
  count: number;
}

export interface EffectorActivity {
  name: string;
  avgActivation: number;
  color: string;
}

export interface EffectorHistoryPoint {
  tick: number;
  locomotion: number;
  harvest: number;
  social: number;
  maintenance: number;
  reproduction: number;
  signal: number;
}

export interface CommsPoint {
  tick: number;
  signalsSent: number;
  signalsDelivered: number;
  uniqueSenders: number;
  uniqueReceivers: number;
  avgDistance: number;
  avgSignalEnergy: number;
  avgSignalEntropy: number;
  avgSignalResource: number;
}

export interface GenerationBucket {
  generation: number;
  count: number;
  alive: number;
  dead: number;
  avgLifespan: number;
}

export interface SignalEvent {
  tick: number;
  senderId: number;
  receiverId: number;
  vector: number[];
  distance: number;
  senderEnergy: number;
  senderEntropy: number;
}

export interface MacroDiscovery {
  tick: number;
  agentId: number;
  sequence: number[];
}

export interface AgentSnapshot {
  agent_id: number;
  energy: number;
  entropy: number;
  age: number;
  position: number;
  generation: number;
  cortex_size: number;
  memory_size: number;
  compound_actions: number;
  genome: Record<string, number>;
  parent_a_id: number | null;
  parent_b_id: number | null;
  born_tick: number | null;
}

export interface EventInfo {
  tick: number;
  event_type: string;
  agent_id: number;
  description: string;
}

export interface BrainStatsPoint {
  tick: number;
  avgNodes: number;
  avgConnections: number;
  maxNodes: number;
  maxConnections: number;
  avgMetabolicCost: number;
}

export interface SpeciesPoint {
  tick: number;
  speciesId: number;
  count: number;
  avgFitness: number;
  avgBrainNodes: number;
  avgBrainConns: number;
}

export interface SpeciesSummary {
  speciesId: number;
  currentCount: number;
  avgFitness: number;
  avgBrainNodes: number;
  avgBrainConns: number;
}

export interface EcologyPoint {
  tick: number;
  population: number;
  births: number;
  deaths: number;
  avgEnergy: number;
  avgEntropy: number;
  substrateEnergy: number;
  numSpecies: number;
}

// ── Query functions ──────────────────────────────────────────────────────

export function getOverview(): OverviewStats {
  const db = getDb();

  const latest = db
    .prepare("SELECT * FROM population_stats ORDER BY tick DESC LIMIT 1")
    .get() as Record<string, number> | undefined;

  if (!latest) {
    return {
      currentTick: 0,
      population: 0,
      totalBirths: 0,
      totalDeaths: 0,
      avgEnergy: 0,
      avgEntropy: 0,
      avgAge: 0,
      maxGeneration: 0,
      avgCortexSize: 0,
      substrateEnergy: 0,
      totalMacros: 0,
      totalSignalDeliveries: 0,
    };
  }

  const macros = db
    .prepare(
      "SELECT COUNT(*) as c FROM events WHERE event_type='macro_discovered'"
    )
    .get() as { c: number };
  const signals = db
    .prepare(
      "SELECT COALESCE(SUM(total_deliveries), 0) as c FROM comms_stats"
    )
    .get() as { c: number };

  return {
    currentTick: latest.tick,
    population: latest.population,
    totalBirths: latest.total_births ?? 0,
    totalDeaths: latest.total_deaths ?? 0,
    avgEnergy: latest.avg_energy ?? 0,
    avgEntropy: latest.avg_entropy ?? 0,
    avgAge: latest.avg_age ?? 0,
    maxGeneration: latest.max_generation ?? 0,
    avgCortexSize: latest.avg_cortex_size ?? 0,
    substrateEnergy: latest.substrate_energy ?? 0,
    totalMacros: macros?.c ?? 0,
    totalSignalDeliveries: signals?.c ?? 0,
  };
}

export function getFullHistory(limit = 300): FullHistoryPoint[] {
  const db = getDb();
  const rows = db
    .prepare(
      `SELECT tick, population, avg_energy, avg_entropy, avg_age,
              avg_cortex_size, substrate_energy, max_generation,
              total_births, total_deaths
       FROM population_stats
       ORDER BY tick DESC LIMIT ?`
    )
    .all(limit) as FullHistoryPoint[];
  return rows.reverse();
}

export function getActionDistribution(recentTicks = 500): ActionCount[] {
  const db = getDb();
  const currentTick = (
    db.prepare("SELECT MAX(tick) as t FROM events").get() as { t: number }
  )?.t ?? 0;

  const rows = db
    .prepare(
      `SELECT json_extract(data, '$.action_id') as action_id, COUNT(*) as cnt
       FROM events
       WHERE event_type='brain_decision' AND data IS NOT NULL
         AND tick > ?
       GROUP BY action_id
       ORDER BY cnt DESC`
    )
    .all(currentTick - recentTicks) as { action_id: number; cnt: number }[];

  return rows.map((r) => ({
    actionId: r.action_id,
    actionName: ACTION_NAMES[r.action_id] ?? `macro_${r.action_id}`,
    count: r.cnt,
  }));
}

export function getCommsHistory(limit = 150): CommsPoint[] {
  const db = getDb();
  const rows = db
    .prepare(`SELECT * FROM comms_stats ORDER BY tick DESC LIMIT ?`)
    .all(limit) as Record<string, number>[];

  return rows.reverse().map((r) => ({
    tick: r.tick,
    signalsSent: r.signals_sent,
    signalsDelivered: r.total_deliveries ?? r.signals_received ?? 0,
    uniqueSenders: r.unique_senders,
    uniqueReceivers: r.unique_receivers,
    avgDistance: r.avg_distance,
    avgSignalEnergy: r.avg_signal_energy ?? 0,
    avgSignalEntropy: r.avg_signal_entropy ?? 0,
    avgSignalResource: r.avg_signal_resource ?? 0,
  }));
}

export function getGenerationDistribution(): GenerationBucket[] {
  const db = getDb();
  const rows = db
    .prepare(
      `SELECT
         generation,
         COUNT(*) as total,
         SUM(CASE WHEN died_tick IS NULL THEN 1 ELSE 0 END) as alive,
         SUM(CASE WHEN died_tick IS NOT NULL THEN 1 ELSE 0 END) as dead,
         AVG(CASE WHEN died_tick IS NOT NULL THEN died_tick - born_tick ELSE NULL END) as avg_lifespan
       FROM lineage
       GROUP BY generation
       ORDER BY generation`
    )
    .all() as Record<string, number>[];

  return rows.map((r) => ({
    generation: r.generation,
    count: r.total,
    alive: r.alive,
    dead: r.dead,
    avgLifespan: r.avg_lifespan ?? 0,
  }));
}

export function getRecentSignals(limit = 60): SignalEvent[] {
  const db = getDb();
  const rows = db
    .prepare(
      `SELECT tick, agent_id, data FROM events
       WHERE event_type='signal_sent' AND data IS NOT NULL
       ORDER BY tick DESC LIMIT ?`
    )
    .all(limit) as { tick: number; agent_id: number; data: string }[];

  return rows.map((r) => {
    const d = JSON.parse(r.data);
    return {
      tick: r.tick,
      senderId: r.agent_id,
      receiverId: d.receiver_id,
      vector: d.vector ?? [],
      distance: d.distance ?? 0,
      senderEnergy: d.sender_energy ?? 0,
      senderEntropy: d.sender_entropy ?? 0,
    };
  });
}

export function getAgentSnapshots(): AgentSnapshot[] {
  const db = getDb();
  const maxTick = (
    db.prepare("SELECT MAX(tick) as t FROM snapshots").get() as { t: number }
  )?.t;
  if (!maxTick) return [];

  const rows = db
    .prepare(
      `SELECT s.agent_id, s.energy, s.entropy, s.age, s.node_id as position,
              s.generation, s.cortex_size, s.memory_size, s.compound_actions,
              s.genome,
              l.parent_a_id, l.parent_b_id, l.born_tick
       FROM snapshots s
       LEFT JOIN lineage l ON s.agent_id = l.child_id
       WHERE s.tick = ? AND s.alive = 1
       ORDER BY s.energy DESC`
    )
    .all(maxTick) as Record<string, unknown>[];

  return rows.map((r) => ({
    agent_id: r.agent_id as number,
    energy: r.energy as number,
    entropy: r.entropy as number,
    age: r.age as number,
    position: r.position as number,
    generation: r.generation as number,
    cortex_size: r.cortex_size as number,
    memory_size: (r.memory_size as number) ?? 0,
    compound_actions: (r.compound_actions as number) ?? 0,
    genome: r.genome ? JSON.parse(r.genome as string) : {},
    parent_a_id: (r.parent_a_id as number) ?? null,
    parent_b_id: (r.parent_b_id as number) ?? null,
    born_tick: (r.born_tick as number) ?? null,
  }));
}

export function getRecentMacros(limit = 30): MacroDiscovery[] {
  const db = getDb();
  const rows = db
    .prepare(
      `SELECT tick, agent_id, data FROM events
       WHERE event_type='macro_discovered' AND data IS NOT NULL
       ORDER BY tick DESC LIMIT ?`
    )
    .all(limit) as { tick: number; agent_id: number; data: string }[];

  return rows.map((r) => {
    const d = JSON.parse(r.data);
    return {
      tick: r.tick,
      agentId: r.agent_id,
      sequence: d.sequence ?? [],
    };
  });
}

export function getRecentEvents(limit = 50): EventInfo[] {
  const db = getDb();
  const rows = db
    .prepare(
      `SELECT tick, event_type, agent_id, description
       FROM events
       WHERE event_type IN ('birth', 'death', 'macro_discovered', 'brain_decision')
       ORDER BY tick DESC, rowid DESC LIMIT ?`
    )
    .all(limit) as EventInfo[];
  return rows;
}

// ── Effector activity queries (continuous motor interface) ─────────────────

export function getEffectorActivity(recentTicks = 500): EffectorActivity[] {
  const db = getDb();
  const currentTick = (
    db.prepare("SELECT MAX(tick) as t FROM events").get() as { t: number }
  )?.t ?? 0;

  try {
    const row = db
      .prepare(
        `SELECT
          AVG(json_extract(data, '$.effectors[1]')) as locomotion,
          AVG(json_extract(data, '$.effectors[2]')) as harvest,
          AVG(CASE WHEN json_extract(data, '$.effectors[3]') > 0
               THEN json_extract(data, '$.effectors[3]') ELSE 0 END) as social_pos,
          AVG(CASE WHEN json_extract(data, '$.effectors[3]') < 0
               THEN ABS(json_extract(data, '$.effectors[3]')) ELSE 0 END) as social_neg,
          AVG(json_extract(data, '$.effectors[4]')) as maintenance,
          AVG(json_extract(data, '$.effectors[5]')) as reproduction,
          AVG(json_extract(data, '$.effectors[6]')) as signal_ch,
          COUNT(*) as cnt
        FROM events
        WHERE event_type='brain_decision' AND data IS NOT NULL
          AND json_extract(data, '$.effectors') IS NOT NULL
          AND tick > ?`
      )
      .get(currentTick - recentTicks) as Record<string, number> | undefined;

    if (!row || !row.cnt) return [];

    return [
      { name: "Locomotion", avgActivation: row.locomotion ?? 0, color: EFFECTOR_COLORS["Locomotion"] },
      { name: "Harvest", avgActivation: row.harvest ?? 0, color: EFFECTOR_COLORS["Harvest"] },
      { name: "Transfer", avgActivation: row.social_pos ?? 0, color: EFFECTOR_COLORS["Transfer"] },
      { name: "Attack", avgActivation: row.social_neg ?? 0, color: EFFECTOR_COLORS["Attack"] },
      { name: "Maintenance", avgActivation: row.maintenance ?? 0, color: EFFECTOR_COLORS["Maintenance"] },
      { name: "Reproduction", avgActivation: row.reproduction ?? 0, color: EFFECTOR_COLORS["Reproduction"] },
      { name: "Signal", avgActivation: row.signal_ch ?? 0, color: EFFECTOR_COLORS["Signal"] },
    ].sort((a, b) => b.avgActivation - a.avgActivation);
  } catch {
    return [];
  }
}

export function getEffectorHistory(recentTicks = 2000): EffectorHistoryPoint[] {
  const db = getDb();
  const currentTick = (
    db.prepare("SELECT MAX(tick) as t FROM events").get() as { t: number }
  )?.t ?? 0;

  const startTick = Math.max(0, currentTick - recentTicks);
  const binSize = Math.max(1, Math.floor(recentTicks / 100));

  try {
    const rows = db
      .prepare(
        `SELECT
          (tick / ?) * ? as tick_bin,
          AVG(json_extract(data, '$.effectors[1]')) as locomotion,
          AVG(json_extract(data, '$.effectors[2]')) as harvest,
          AVG(json_extract(data, '$.effectors[3]')) as social,
          AVG(json_extract(data, '$.effectors[4]')) as maintenance,
          AVG(json_extract(data, '$.effectors[5]')) as reproduction,
          AVG(json_extract(data, '$.effectors[6]')) as signal_ch
        FROM events
        WHERE event_type='brain_decision' AND data IS NOT NULL
          AND json_extract(data, '$.effectors') IS NOT NULL
          AND tick > ?
        GROUP BY tick_bin
        ORDER BY tick_bin`
      )
      .all(binSize, binSize, startTick) as Record<string, number>[];

    return rows.map((r) => ({
      tick: r.tick_bin,
      locomotion: r.locomotion ?? 0,
      harvest: r.harvest ?? 0,
      social: r.social ?? 0,
      maintenance: r.maintenance ?? 0,
      reproduction: r.reproduction ?? 0,
      signal: r.signal_ch ?? 0,
    }));
  } catch {
    return [];
  }
}

// ── Phase 6: Evolution & Brain Complexity queries ─────────────────────────

export function getBrainHistory(limit = 300): BrainStatsPoint[] {
  const db = getDb();
  try {
    const rows = db
      .prepare(
        `SELECT tick, avg_nodes, avg_connections, max_nodes, max_connections, avg_metabolic_cost
         FROM brain_stats ORDER BY tick DESC LIMIT ?`
      )
      .all(limit) as Record<string, number>[];
    return rows.reverse().map((r) => ({
      tick: r.tick,
      avgNodes: r.avg_nodes ?? 0,
      avgConnections: r.avg_connections ?? 0,
      maxNodes: r.max_nodes ?? 0,
      maxConnections: r.max_connections ?? 0,
      avgMetabolicCost: r.avg_metabolic_cost ?? 0,
    }));
  } catch {
    return [];
  }
}

export function getSpeciesHistory(limit = 300): SpeciesPoint[] {
  const db = getDb();
  try {
    const rows = db
      .prepare(
        `SELECT tick, species_id, count, avg_fitness, avg_brain_nodes, avg_brain_conns
         FROM species_stats ORDER BY tick DESC LIMIT ?`
      )
      .all(limit) as Record<string, number>[];
    return rows.reverse().map((r) => ({
      tick: r.tick,
      speciesId: r.species_id,
      count: r.count ?? 0,
      avgFitness: r.avg_fitness ?? 0,
      avgBrainNodes: r.avg_brain_nodes ?? 0,
      avgBrainConns: r.avg_brain_conns ?? 0,
    }));
  } catch {
    return [];
  }
}

export function getLatestSpecies(): SpeciesSummary[] {
  const db = getDb();
  try {
    const maxTick = (
      db.prepare("SELECT MAX(tick) as t FROM species_stats").get() as { t: number }
    )?.t;
    if (!maxTick) return [];
    const rows = db
      .prepare(
        `SELECT species_id, count, avg_fitness, avg_brain_nodes, avg_brain_conns
         FROM species_stats WHERE tick = ? ORDER BY count DESC`
      )
      .all(maxTick) as Record<string, number>[];
    return rows.map((r) => ({
      speciesId: r.species_id,
      currentCount: r.count ?? 0,
      avgFitness: r.avg_fitness ?? 0,
      avgBrainNodes: r.avg_brain_nodes ?? 0,
      avgBrainConns: r.avg_brain_conns ?? 0,
    }));
  } catch {
    return [];
  }
}

// ── Story chapters query ──────────────────────────────────────────────────

export interface StoryChapter {
  chapter: number;
  tickStart: number;
  tickEnd: number;
  title: string;
  content: string;
}

export function getStoryChapters(): StoryChapter[] {
  const db = getDb();
  try {
    const rows = db
      .prepare(
        `SELECT chapter, tick_start, tick_end, title, content
         FROM story_chapters ORDER BY chapter ASC`
      )
      .all() as Record<string, unknown>[];

    return rows.map((r) => ({
      chapter: r.chapter as number,
      tickStart: r.tick_start as number,
      tickEnd: r.tick_end as number,
      title: r.title as string,
      content: r.content as string,
    }));
  } catch {
    return [];
  }
}

// ── Substrate topology query ──────────────────────────────────────────────

export interface SubstrateTopology {
  nodes: { id: number; x: number; y: number; degree: number }[];
  edges: [number, number][];
  numNodes: number;
  numEdges: number;
}

export interface AgentPosition {
  agentId: number;
  nodeId: number;
  energy: number;
  entropy: number;
  generation: number;
  speciesId?: number;
}

export function getSubstrateTopology(): SubstrateTopology | null {
  const db = getDb();
  try {
    const row = db
      .prepare(
        `SELECT value FROM simulation_meta WHERE key = 'substrate_topology'`
      )
      .get() as { value: string } | undefined;

    if (!row) return null;
    const data = JSON.parse(row.value);
    return {
      nodes: data.nodes ?? [],
      edges: data.edges ?? [],
      numNodes: data.num_nodes ?? 0,
      numEdges: data.num_edges ?? 0,
    };
  } catch {
    return null;
  }
}

export function getAgentPositions(): AgentPosition[] {
  const db = getDb();
  try {
    const maxTick = (
      db.prepare("SELECT MAX(tick) as t FROM snapshots").get() as { t: number }
    )?.t;
    if (!maxTick) return [];

    const rows = db
      .prepare(
        `SELECT s.agent_id, s.node_id, s.energy, s.entropy, s.generation
         FROM snapshots s
         WHERE s.tick = ? AND s.alive = 1`
      )
      .all(maxTick) as Record<string, number>[];

    return rows.map((r) => ({
      agentId: r.agent_id,
      nodeId: r.node_id,
      energy: r.energy ?? 0,
      entropy: r.entropy ?? 0,
      generation: r.generation ?? 0,
    }));
  } catch {
    return [];
  }
}

// ── Node energy data for world map ────────────────────────────────────────

export interface NodeEnergyData {
  nodeId: number;
  energy: number;
  agentCount: number;
}

export function getNodeEnergyData(): NodeEnergyData[] {
  // This is derived from agent snapshots — we count agents per node
  const db = getDb();
  try {
    const maxTick = (
      db.prepare("SELECT MAX(tick) as t FROM snapshots").get() as { t: number }
    )?.t;
    if (!maxTick) return [];

    const rows = db
      .prepare(
        `SELECT node_id, COUNT(*) as agent_count, AVG(energy) as avg_energy
         FROM snapshots
         WHERE tick = ? AND alive = 1
         GROUP BY node_id`
      )
      .all(maxTick) as Record<string, number>[];

    return rows.map((r) => ({
      nodeId: r.node_id,
      energy: r.avg_energy ?? 0,
      agentCount: r.agent_count ?? 0,
    }));
  } catch {
    return [];
  }
}

export function getEcologyHistory(limit = 300): EcologyPoint[] {
  const db = getDb();
  try {
    // Join population_stats with species count per tick
    const rows = db
      .prepare(
        `SELECT p.tick, p.population, p.total_births, p.total_deaths,
                p.avg_energy, p.avg_entropy, p.substrate_energy,
                COALESCE(s.num_species, 0) as num_species
         FROM population_stats p
         LEFT JOIN (
           SELECT tick, COUNT(DISTINCT species_id) as num_species
           FROM species_stats GROUP BY tick
         ) s ON p.tick = s.tick
         ORDER BY p.tick DESC LIMIT ?`
      )
      .all(limit) as Record<string, number>[];

    const result = rows.reverse();
    return result.map((r, i) => {
      const prev = i > 0 ? result[i - 1] : r;
      return {
        tick: r.tick,
        population: r.population ?? 0,
        births: (r.total_births ?? 0) - (prev.total_births ?? 0),
        deaths: (r.total_deaths ?? 0) - (prev.total_deaths ?? 0),
        avgEnergy: r.avg_energy ?? 0,
        avgEntropy: r.avg_entropy ?? 0,
        substrateEnergy: r.substrate_energy ?? 0,
        numSpecies: r.num_species ?? 0,
      };
    });
  } catch {
    return [];
  }
}
