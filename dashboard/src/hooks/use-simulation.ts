"use client";

import { useState, useEffect, useCallback, useRef } from "react";

// ── Types ────────────────────────────────────────────────────────────────

export interface SimulationData {
  overview: {
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
  };
  fullHistory: {
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
  }[];
  actionDistribution: {
    actionId: number;
    actionName: string;
    count: number;
  }[];
  commsHistory: {
    tick: number;
    signalsSent: number;
    signalsDelivered: number;
    uniqueSenders: number;
    uniqueReceivers: number;
    avgDistance: number;
    avgSignalEnergy: number;
    avgSignalEntropy: number;
    avgSignalResource: number;
  }[];
  generationDist: {
    generation: number;
    count: number;
    alive: number;
    dead: number;
    avgLifespan: number;
  }[];
  recentSignals: {
    tick: number;
    senderId: number;
    receiverId: number;
    vector: number[];
    distance: number;
    senderEnergy: number;
    senderEntropy: number;
  }[];
  agentSnapshots: {
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
  }[];
  recentMacros: {
    tick: number;
    agentId: number;
    sequence: number[];
  }[];
  recentEvents: {
    tick: number;
    event_type: string;
    agent_id: number;
    description: string;
  }[];
  brainHistory: {
    tick: number;
    avgNodes: number;
    avgConnections: number;
    maxNodes: number;
    maxConnections: number;
    avgMetabolicCost: number;
  }[];
  speciesHistory: {
    tick: number;
    speciesId: number;
    count: number;
    avgFitness: number;
    avgBrainNodes: number;
    avgBrainConns: number;
  }[];
  latestSpecies: {
    speciesId: number;
    currentCount: number;
    avgFitness: number;
    avgBrainNodes: number;
    avgBrainConns: number;
  }[];
  ecologyHistory: {
    tick: number;
    population: number;
    births: number;
    deaths: number;
    avgEnergy: number;
    avgEntropy: number;
    substrateEnergy: number;
    numSpecies: number;
  }[];
  effectorActivity: {
    name: string;
    avgActivation: number;
    color: string;
  }[];
  effectorHistory: {
    tick: number;
    locomotion: number;
    harvest: number;
    social: number;
    maintenance: number;
    reproduction: number;
    signal: number;
  }[];
  storyChapters: {
    chapter: number;
    tickStart: number;
    tickEnd: number;
    title: string;
    content: string;
  }[];
  substrateTopology: {
    nodes: { id: number; x: number; y: number; degree: number }[];
    edges: [number, number][];
    numNodes: number;
    numEdges: number;
  } | null;
  agentPositions: {
    agentId: number;
    nodeId: number;
    energy: number;
    entropy: number;
    generation: number;
  }[];
  nodeEnergyData: {
    nodeId: number;
    energy: number;
    agentCount: number;
  }[];
  timestamp: number;
}

// ── Hook ─────────────────────────────────────────────────────────────────

export function useSimulation(refreshInterval = 4000) {
  const [data, setData] = useState<SimulationData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [paused, setPaused] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch("/api/simulation", { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      if (json.error) throw new Error(json.error);
      setData(json);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    if (!paused) {
      intervalRef.current = setInterval(fetchData, refreshInterval);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchData, refreshInterval, paused]);

  return { data, error, loading, paused, setPaused, refresh: fetchData };
}
