"use client";

import type { SimulationData } from "@/hooks/use-simulation";
import { useMemo, useState, useRef, useEffect, useCallback } from "react";

// ── Color helpers ─────────────────────────────────────────────────────────

function energyColor(energy: number, maxEnergy = 150): string {
  const ratio = Math.min(energy / maxEnergy, 1);
  // Green spectrum: pale → vivid
  const g = Math.round(120 + ratio * 135);
  const r = Math.round(220 - ratio * 180);
  const b = Math.round(160 - ratio * 80);
  return `rgb(${r},${g},${b})`;
}

function generationColor(gen: number, maxGen: number): string {
  if (maxGen <= 0) return "#6366f1";
  const ratio = Math.min(gen / maxGen, 1);
  // Indigo → Amber gradient
  const r = Math.round(99 + ratio * 156);
  const g = Math.round(102 - ratio * 13);
  const b = Math.round(241 - ratio * 178);
  return `rgb(${r},${g},${b})`;
}

// ── Main Component ────────────────────────────────────────────────────────

type ViewMode = "agents" | "energy" | "density";

export default function WorldMapSection({
  data,
}: {
  data: SimulationData;
}) {
  const { substrateTopology, agentPositions, nodeEnergyData, overview } = data;
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("agents");
  const [hoveredNode, setHoveredNode] = useState<number | null>(null);
  const [zoom, setZoom] = useState(1);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const isDragging = useRef(false);
  const lastMouse = useRef({ x: 0, y: 0 });

  // Build agent count per node lookup
  const agentsByNode = useMemo(() => {
    const map = new Map<number, typeof agentPositions>();
    for (const agent of agentPositions) {
      const arr = map.get(agent.nodeId) || [];
      arr.push(agent);
      map.set(agent.nodeId, arr);
    }
    return map;
  }, [agentPositions]);

  // Node energy lookup
  const nodeEnergy = useMemo(() => {
    const map = new Map<number, { energy: number; agentCount: number }>();
    for (const d of nodeEnergyData) {
      map.set(d.nodeId, { energy: d.energy, agentCount: d.agentCount });
    }
    return map;
  }, [nodeEnergyData]);

  // Max generation for color scaling
  const maxGen = overview.maxGeneration || 1;

  // Node positions lookup
  const nodePositions = useMemo(() => {
    if (!substrateTopology) return new Map<number, { x: number; y: number; degree: number }>();
    const map = new Map<number, { x: number; y: number; degree: number }>();
    for (const n of substrateTopology.nodes) {
      map.set(n.id, { x: n.x, y: n.y, degree: n.degree });
    }
    return map;
  }, [substrateTopology]);

  // Draw canvas
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !substrateTopology) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const W = rect.width;
    const H = rect.height;

    ctx.clearRect(0, 0, W, H);

    // Compute node positions with viewport transform
    const nodes = substrateTopology.nodes;
    if (nodes.length === 0) return;

    // Find bounds
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (const n of nodes) {
      minX = Math.min(minX, n.x);
      maxX = Math.max(maxX, n.x);
      minY = Math.min(minY, n.y);
      maxY = Math.max(maxY, n.y);
    }

    const rangeX = maxX - minX || 1;
    const rangeY = maxY - minY || 1;
    const padding = 40;
    const scaleX = (W - padding * 2) / rangeX;
    const scaleY = (H - padding * 2) / rangeY;
    const scale = Math.min(scaleX, scaleY) * zoom;
    const cx = W / 2 + panOffset.x;
    const cy = H / 2 + panOffset.y;
    const midX = (minX + maxX) / 2;
    const midY = (minY + maxY) / 2;

    const toScreen = (x: number, y: number): [number, number] => [
      cx + (x - midX) * scale,
      cy + (y - midY) * scale,
    ];

    // Pre-compute screen positions
    const screenPos = new Map<number, [number, number]>();
    for (const n of nodes) {
      screenPos.set(n.id, toScreen(n.x, n.y));
    }

    // Draw edges (very thin, subtle)
    ctx.strokeStyle = "rgba(0,0,0,0.04)";
    ctx.lineWidth = 0.5;
    ctx.beginPath();
    for (const [a, b] of substrateTopology.edges) {
      const posA = screenPos.get(a);
      const posB = screenPos.get(b);
      if (posA && posB) {
        ctx.moveTo(posA[0], posA[1]);
        ctx.lineTo(posB[0], posB[1]);
      }
    }
    ctx.stroke();

    // Draw nodes
    for (const n of nodes) {
      const pos = screenPos.get(n.id);
      if (!pos) continue;
      const [sx, sy] = pos;

      // Skip nodes outside viewport
      if (sx < -20 || sx > W + 20 || sy < -20 || sy > H + 20) continue;

      const agents = agentsByNode.get(n.id);
      const hasAgents = agents && agents.length > 0;
      const ne = nodeEnergy.get(n.id);

      let radius: number;
      let fillColor: string;

      switch (viewMode) {
        case "agents": {
          radius = hasAgents ? 3 + Math.min(agents!.length * 1.5, 8) : 1.5;
          fillColor = hasAgents
            ? generationColor(
                agents![0].generation,
                maxGen
              )
            : "rgba(0,0,0,0.06)";
          break;
        }
        case "energy": {
          const agentEnergy = hasAgents
            ? agents!.reduce((s, a) => s + a.energy, 0) / agents!.length
            : 0;
          radius = hasAgents ? 3 + Math.min(agents!.length * 1.5, 8) : 1.5;
          fillColor = hasAgents ? energyColor(agentEnergy) : "rgba(0,0,0,0.06)";
          break;
        }
        case "density": {
          const count = ne?.agentCount ?? 0;
          radius = 1.5 + count * 2;
          fillColor =
            count > 0
              ? `rgba(99, 102, 241, ${Math.min(0.2 + count * 0.15, 0.9)})`
              : "rgba(0,0,0,0.06)";
          break;
        }
      }

      ctx.beginPath();
      ctx.arc(sx, sy, radius, 0, Math.PI * 2);
      ctx.fillStyle = fillColor;
      ctx.fill();

      // Highlight hovered node
      if (hoveredNode === n.id) {
        ctx.strokeStyle = "#4f46e5";
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    }

    // Draw agent indicators (small bright dots on top)
    if (viewMode === "agents") {
      for (const [nodeId, agents] of agentsByNode) {
        const pos = screenPos.get(nodeId);
        if (!pos) continue;
        const [sx, sy] = pos;
        if (sx < -20 || sx > W + 20 || sy < -20 || sy > H + 20) continue;

        // Draw each agent as a small dot offset from center
        const count = agents.length;
        if (count <= 3) {
          agents.forEach((a, i) => {
            const angle = (i / Math.max(count, 1)) * Math.PI * 2 - Math.PI / 2;
            const offset = count > 1 ? 4 : 0;
            const ax = sx + Math.cos(angle) * offset;
            const ay = sy + Math.sin(angle) * offset;
            ctx.beginPath();
            ctx.arc(ax, ay, 2.5, 0, Math.PI * 2);
            ctx.fillStyle = generationColor(a.generation, maxGen);
            ctx.fill();
            ctx.strokeStyle = "#fff";
            ctx.lineWidth = 0.8;
            ctx.stroke();
          });
        }
      }
    }
  }, [substrateTopology, agentsByNode, nodeEnergy, viewMode, hoveredNode, zoom, panOffset, maxGen]);

  useEffect(() => {
    draw();
  }, [draw]);

  // Handle resize
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const obs = new ResizeObserver(() => draw());
    obs.observe(canvas);
    return () => obs.disconnect();
  }, [draw]);

  // Mouse handlers for pan
  const handleMouseDown = (e: React.MouseEvent) => {
    isDragging.current = true;
    lastMouse.current = { x: e.clientX, y: e.clientY };
  };
  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging.current) {
      const dx = e.clientX - lastMouse.current.x;
      const dy = e.clientY - lastMouse.current.y;
      setPanOffset((prev) => ({ x: prev.x + dx, y: prev.y + dy }));
      lastMouse.current = { x: e.clientX, y: e.clientY };
    }
  };
  const handleMouseUp = () => {
    isDragging.current = false;
  };
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    setZoom((prev) => Math.max(0.3, Math.min(5, prev - e.deltaY * 0.001)));
  };

  if (!substrateTopology) {
    return (
      <div>
        <div className="mb-5">
          <h2 className="text-lg font-semibold text-foreground">World Map</h2>
          <p className="text-sm text-muted-foreground">
            Visualisation of the agent world
          </p>
        </div>
        <div className="bg-card border border-border rounded-xl p-10 text-center">
          <p className="text-sm text-muted-foreground">
            No topology data available yet. The world map will appear once the
            simulation starts.
          </p>
        </div>
      </div>
    );
  }

  const totalAgents = agentPositions.length;
  const occupiedNodes = agentsByNode.size;
  const occupancyPct =
    substrateTopology.numNodes > 0
      ? ((occupiedNodes / substrateTopology.numNodes) * 100).toFixed(1)
      : "0";

  return (
    <div>
      {/* Header */}
      <div className="mb-5">
        <h2 className="text-lg font-semibold text-foreground">World Map</h2>
        <p className="text-sm text-muted-foreground">
          The agent world — {substrateTopology.numNodes} nodes connected by{" "}
          {substrateTopology.numEdges.toLocaleString()} links
        </p>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        <StatBox
          label="Nodes"
          value={substrateTopology.numNodes.toLocaleString()}
          sub="Total in world"
          color="#6366f1"
        />
        <StatBox
          label="Connections"
          value={substrateTopology.numEdges.toLocaleString()}
          sub="Between nodes"
          color="#0891b2"
        />
        <StatBox
          label="Agents Placed"
          value={`${totalAgents} on ${occupiedNodes}`}
          sub={`${occupancyPct}% nodes occupied`}
          color="#059669"
        />
        <StatBox
          label="Avg Degree"
          value={
            substrateTopology.numNodes > 0
              ? (
                  (substrateTopology.numEdges * 2) /
                  substrateTopology.numNodes
                ).toFixed(1)
              : "—"
          }
          sub="Connections per node"
          color="#d97706"
        />
      </div>

      {/* View mode toggle */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-[11px] text-muted-foreground font-medium">
          View:
        </span>
        {(
          [
            { id: "agents", label: "Agents", desc: "Colored by generation" },
            { id: "energy", label: "Energy", desc: "Colored by agent energy" },
            { id: "density", label: "Density", desc: "Agent clustering" },
          ] as const
        ).map((mode) => (
          <button
            key={mode.id}
            onClick={() => setViewMode(mode.id)}
            className={`text-[11px] px-3 py-1.5 rounded-lg transition-colors cursor-pointer ${
              viewMode === mode.id
                ? "bg-foreground/[0.08] text-foreground font-medium"
                : "text-muted-foreground hover:text-foreground hover:bg-foreground/[0.03]"
            }`}
            title={mode.desc}
          >
            {mode.label}
          </button>
        ))}
        <div className="flex-1" />
        <button
          onClick={() => {
            setZoom(1);
            setPanOffset({ x: 0, y: 0 });
          }}
          className="text-[11px] text-muted-foreground hover:text-foreground px-2 py-1 cursor-pointer"
        >
          Reset view
        </button>
      </div>

      {/* Canvas map */}
      <div className="bg-card border border-border rounded-xl overflow-hidden">
        <canvas
          ref={canvasRef}
          className="w-full cursor-grab active:cursor-grabbing"
          style={{ height: 520 }}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onWheel={handleWheel}
        />
      </div>

      {/* Legend */}
      <div className="mt-3 flex items-center gap-6 text-[11px] text-muted-foreground">
        {viewMode === "agents" && (
          <>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-full bg-indigo-500 inline-block" />
              Gen 0 (early)
            </div>
            <div className="flex items-center gap-1.5">
              <span
                className="w-3 h-3 rounded-full inline-block"
                style={{ backgroundColor: generationColor(maxGen, maxGen) }}
              />
              Gen {maxGen} (latest)
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-black/10 inline-block" />
              Empty node
            </div>
          </>
        )}
        {viewMode === "energy" && (
          <>
            <div className="flex items-center gap-1.5">
              <span
                className="w-3 h-3 rounded-full inline-block"
                style={{ backgroundColor: energyColor(0) }}
              />
              Low energy
            </div>
            <div className="flex items-center gap-1.5">
              <span
                className="w-3 h-3 rounded-full inline-block"
                style={{ backgroundColor: energyColor(150) }}
              />
              High energy
            </div>
          </>
        )}
        {viewMode === "density" && (
          <>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-full bg-indigo-200 inline-block" />
              Few agents
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-full bg-indigo-600 inline-block" />
              Many agents
            </div>
          </>
        )}
        <span className="ml-auto">
          Scroll to zoom · Drag to pan
        </span>
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

