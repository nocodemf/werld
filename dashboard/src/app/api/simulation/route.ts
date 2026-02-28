import { NextResponse } from "next/server";
import {
  getOverview,
  getFullHistory,
  getActionDistribution,
  getCommsHistory,
  getGenerationDistribution,
  getRecentSignals,
  getAgentSnapshots,
  getRecentMacros,
  getRecentEvents,
  getBrainHistory,
  getSpeciesHistory,
  getLatestSpecies,
  getEcologyHistory,
  getEffectorActivity,
  getEffectorHistory,
  getStoryChapters,
  getSubstrateTopology,
  getAgentPositions,
  getNodeEnergyData,
  getSimulationStartTime,
} from "@/lib/db";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export async function GET() {
  try {
    const overview = getOverview();
    const fullHistory = getFullHistory(300);
    const actionDistribution = getActionDistribution(500);
    const commsHistory = getCommsHistory(150);
    const generationDist = getGenerationDistribution();
    const recentSignals = getRecentSignals(60);
    const agentSnapshots = getAgentSnapshots();
    const recentMacros = getRecentMacros(25);
    const recentEvents = getRecentEvents(50);
    const brainHistory = getBrainHistory(300);
    const speciesHistory = getSpeciesHistory(300);
    const latestSpecies = getLatestSpecies();
    const ecologyHistory = getEcologyHistory(300);
    const effectorActivity = getEffectorActivity(500);
    const effectorHistory = getEffectorHistory(2000);
    const storyChapters = getStoryChapters();
    const substrateTopology = getSubstrateTopology();
    const agentPositions = getAgentPositions();
    const nodeEnergyData = getNodeEnergyData();
    const simulationStartTime = getSimulationStartTime();

    return NextResponse.json({
      overview,
      fullHistory,
      actionDistribution,
      commsHistory,
      generationDist,
      recentSignals,
      agentSnapshots,
      recentMacros,
      recentEvents,
      brainHistory,
      speciesHistory,
      latestSpecies,
      ecologyHistory,
      effectorActivity,
      effectorHistory,
      storyChapters,
      substrateTopology,
      agentPositions,
      nodeEnergyData,
      simulationStartTime,
      timestamp: Date.now(),
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
