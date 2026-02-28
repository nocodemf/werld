"use client";

import type { SimulationData } from "@/hooks/use-simulation";
import { BookOpen, Clock, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";

export default function StorySection({ data }: { data: SimulationData }) {
  const { storyChapters, overview } = data;
  const [expandedChapter, setExpandedChapter] = useState<number | null>(
    storyChapters.length > 0 ? storyChapters[storyChapters.length - 1].chapter : null
  );

  // Sort chapters newest-first for display, but keep option to read chronologically
  const [chronological, setChronological] = useState(false);
  const sortedChapters = chronological
    ? [...storyChapters]
    : [...storyChapters].reverse();

  const ticksPerChapter = 50000;
  const currentChapter = Math.floor(overview.currentTick / ticksPerChapter);
  const progressInChapter =
    ((overview.currentTick % ticksPerChapter) / ticksPerChapter) * 100;

  return (
    <div>
      {/* Header */}
      <div className="mb-5">
        <h2 className="text-lg font-semibold text-foreground">
          The Story So Far
        </h2>
        <p className="text-sm text-muted-foreground">
          A chronicle of this civilisation&apos;s journey — a new chapter is
          written every {ticksPerChapter.toLocaleString()} ticks
        </p>
      </div>

      {/* Progress to next chapter */}
      <div className="bg-card border border-border rounded-xl p-5 mb-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm font-medium text-foreground">
              Progress to Chapter {currentChapter + 1}
            </span>
          </div>
          <span className="text-sm font-mono tabular-nums text-muted-foreground">
            Tick {overview.currentTick.toLocaleString()}
          </span>
        </div>
        <div className="w-full bg-muted rounded-full h-2">
          <div
            className="bg-gradient-to-r from-indigo-400 to-violet-500 h-2 rounded-full transition-all duration-500"
            style={{ width: `${progressInChapter}%` }}
          />
        </div>
        <div className="flex items-center justify-between mt-2 text-[11px] text-muted-foreground">
          <span>
            {Math.floor(overview.currentTick % ticksPerChapter)} /{" "}
            {ticksPerChapter} ticks
          </span>
          <span>{storyChapters.length} chapters written</span>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm text-muted-foreground">
            {storyChapters.length === 0
              ? "No chapters yet — the first chapter will be written at tick 1,000"
              : `${storyChapters.length} chapter${storyChapters.length !== 1 ? "s" : ""}`}
          </span>
        </div>
        {storyChapters.length > 1 && (
          <button
            onClick={() => setChronological(!chronological)}
            className="text-[11px] text-muted-foreground hover:text-foreground transition-colors px-2 py-1 rounded cursor-pointer"
          >
            {chronological ? "Newest first ↓" : "Read in order ↑"}
          </button>
        )}
      </div>

      {/* Chapters */}
      {storyChapters.length === 0 ? (
        <div className="bg-card border border-border rounded-xl p-10 text-center">
          <BookOpen className="w-10 h-10 text-muted-foreground/30 mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">
            The story hasn&apos;t begun yet. The first chapter will be written
            once the simulation reaches tick {ticksPerChapter.toLocaleString()}.
          </p>
          <p className="text-[11px] text-muted-foreground/60 mt-2">
            Chapters are auto-generated summaries of what happened during each
            epoch of {ticksPerChapter.toLocaleString()} ticks.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {sortedChapters.map((ch) => {
            const isExpanded = expandedChapter === ch.chapter;
            const isLatest =
              ch.chapter === storyChapters[storyChapters.length - 1].chapter;

            return (
              <div
                key={ch.chapter}
                className={`bg-card border rounded-xl transition-all ${
                  isLatest
                    ? "border-indigo-200 ring-1 ring-indigo-100"
                    : "border-border"
                }`}
              >
                {/* Chapter header */}
                <button
                  onClick={() =>
                    setExpandedChapter(isExpanded ? null : ch.chapter)
                  }
                  className="w-full flex items-center justify-between px-5 py-4 cursor-pointer group"
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold ${
                        isLatest
                          ? "bg-indigo-50 text-indigo-600"
                          : "bg-muted text-muted-foreground"
                      }`}
                    >
                      {ch.chapter + 1}
                    </div>
                    <div className="text-left">
                      <div className="text-sm font-medium text-foreground group-hover:text-indigo-600 transition-colors">
                        {ch.title}
                      </div>
                      <div className="text-[11px] text-muted-foreground">
                        Ticks {ch.tickStart.toLocaleString()} –{" "}
                        {ch.tickEnd.toLocaleString()}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {isLatest && (
                      <span className="text-[10px] font-medium text-indigo-500 bg-indigo-50 px-2 py-0.5 rounded-full">
                        Latest
                      </span>
                    )}
                    {isExpanded ? (
                      <ChevronUp className="w-4 h-4 text-muted-foreground" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-muted-foreground" />
                    )}
                  </div>
                </button>

                {/* Chapter content */}
                {isExpanded && (
                  <div className="px-5 pb-5 pt-0">
                    <div className="border-t border-border pt-4">
                      <div className="prose prose-sm max-w-none">
                        {ch.content.split("\n\n").map((paragraph, i) => (
                          <p
                            key={i}
                            className="text-[13px] leading-relaxed text-foreground/80 mb-3 last:mb-0"
                          >
                            {paragraph}
                          </p>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

