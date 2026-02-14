"use client";

import { useState } from "react";
import { useSimulation, type SimulationData } from "@/hooks/use-simulation";
import OverviewSection from "@/components/dashboard/overview-section";
import PopulationSection from "@/components/dashboard/population-section";
import IntelligenceSection from "@/components/dashboard/intelligence-section";
import ResourcesSection from "@/components/dashboard/resources-section";
import CommunicationSection from "@/components/dashboard/communication-section";
import AgentsSection from "@/components/dashboard/agents-section";
import EvolutionSection from "@/components/dashboard/evolution-section";
import BrainSection from "@/components/dashboard/brain-section";
import EcologySection from "@/components/dashboard/ecology-section";
import StorySection from "@/components/dashboard/story-section";
import WorldMapSection from "@/components/dashboard/world-map-section";
import WelcomeSection from "@/components/dashboard/welcome-section";
import MethodsSection from "@/components/dashboard/methods-section";
import {
  LayoutDashboard,
  Users,
  Brain,
  Zap,
  Radio,
  Activity,
  Dna,
  Network,
  TreePine,
  BookOpen,
  Globe,
  Pause,
  Play,
  Home,
  FlaskConical,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ── Navigation ───────────────────────────────────────────────────────────

type Section =
  | "welcome"
  | "methods"
  | "overview"
  | "story"
  | "world"
  | "population"
  | "evolution"
  | "brain"
  | "intelligence"
  | "ecology"
  | "resources"
  | "communication"
  | "agents";

const NAV_ITEMS: {
  id: Section;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  separator?: boolean;
}[] = [
  { id: "welcome", label: "Welcome", icon: Home },
  { id: "methods", label: "Methods", icon: FlaskConical, separator: true },
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "story", label: "Story", icon: BookOpen },
  { id: "world", label: "World Map", icon: Globe, separator: true },
  { id: "population", label: "Population", icon: Users },
  { id: "evolution", label: "Evolution", icon: Dna },
  { id: "brain", label: "Brain", icon: Network },
  { id: "intelligence", label: "Intelligence", icon: Brain },
  { id: "ecology", label: "Ecology", icon: TreePine },
  { id: "resources", label: "Resources", icon: Zap },
  { id: "communication", label: "Comms", icon: Radio },
  { id: "agents", label: "Agents", icon: Activity },
];

// ── Page ─────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const [section, setSection] = useState<Section>("welcome");
  const { data, error, loading, paused, setPaused } = useSimulation(4000);

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <div className="text-lg font-medium text-foreground">
            Loading simulation data…
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Connecting to database
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <div className="text-center max-w-md">
          <div className="text-lg font-medium text-red-600">
            Connection Error
          </div>
          <p className="text-sm text-muted-foreground mt-1">{error}</p>
          <p className="text-xs text-muted-foreground/60 mt-4">
            Ensure the simulation is running and <code className="font-mono text-xs bg-muted px-1 py-0.5 rounded">../data/simulation.db</code> exists.
          </p>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* ── Sidebar ─────────────────────────────────────────── */}
      <aside className="w-52 border-r border-border bg-card flex flex-col shrink-0">
        {/* Logo */}
        <div className="px-5 py-5 border-b border-border">
          <h1 className="text-[13px] font-semibold tracking-[0.08em] text-foreground uppercase">
            Agentic Life
          </h1>
          <p className="text-[11px] text-muted-foreground mt-0.5">
            Observatory
          </p>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-3 space-y-0.5">
          {NAV_ITEMS.map((item) => (
            <div key={item.id}>
              <button
                onClick={() => setSection(item.id)}
                className={cn(
                  "w-full flex items-center gap-2.5 px-3 py-[7px] rounded-lg text-[13px] transition-colors cursor-pointer",
                  section === item.id
                    ? "bg-foreground/[0.05] text-foreground font-medium"
                    : "text-muted-foreground hover:text-foreground hover:bg-foreground/[0.03]"
                )}
              >
                <item.icon className="w-[15px] h-[15px]" />
                {item.label}
              </button>
              {item.separator && (
                <div className="my-2 border-t border-border/50" />
              )}
            </div>
          ))}
        </nav>

        {/* Status */}
        <div className="px-4 py-4 border-t border-border">
          <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
            <span className="relative flex h-1.5 w-1.5">
              <span
                className={cn(
                  "absolute inline-flex h-full w-full rounded-full opacity-75",
                  paused
                    ? "bg-amber-400"
                    : "bg-emerald-400 animate-ping"
                )}
              />
              <span
                className={cn(
                  "relative inline-flex rounded-full h-1.5 w-1.5",
                  paused ? "bg-amber-500" : "bg-emerald-500"
                )}
              />
            </span>
            {paused ? "Paused" : "Live"}
          </div>
          <div className="mt-1.5 font-mono text-[11px] text-foreground tabular-nums">
            Tick {data.overview.currentTick.toLocaleString()}
          </div>
          <div className="font-mono text-[11px] text-muted-foreground tabular-nums">
            {data.overview.population} agents
          </div>
          <button
            onClick={() => setPaused(!paused)}
            className="mt-3 flex items-center gap-1.5 text-[11px] text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
          >
            {paused ? (
              <Play className="w-3 h-3" />
            ) : (
              <Pause className="w-3 h-3" />
            )}
            {paused ? "Resume" : "Pause"} updates
          </button>
        </div>
      </aside>

      {/* ── Main content ────────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-[1440px] mx-auto px-6 py-6">
          <SectionRenderer section={section} data={data} />
        </div>
      </main>
    </div>
  );
}

// ── Section router ───────────────────────────────────────────────────────

function SectionRenderer({
  section,
  data,
}: {
  section: Section;
  data: SimulationData;
}) {
  switch (section) {
    case "welcome":
      return <WelcomeSection />;
    case "methods":
      return <MethodsSection />;
    case "overview":
      return <OverviewSection data={data} />;
    case "story":
      return <StorySection data={data} />;
    case "world":
      return <WorldMapSection data={data} />;
    case "population":
      return <PopulationSection data={data} />;
    case "evolution":
      return <EvolutionSection data={data} />;
    case "brain":
      return <BrainSection data={data} />;
    case "intelligence":
      return <IntelligenceSection data={data} />;
    case "ecology":
      return <EcologySection data={data} />;
    case "resources":
      return <ResourcesSection data={data} />;
    case "communication":
      return <CommunicationSection data={data} />;
    case "agents":
      return <AgentsSection data={data} />;
  }
}
