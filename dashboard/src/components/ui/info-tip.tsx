"use client";

import { useState, useRef, useEffect } from "react";
import { HelpCircle } from "lucide-react";

interface InfoTipProps {
  text: string;
  className?: string;
}

/**
 * A small (?) icon that shows a plain-English tooltip on hover.
 * Used to explain technical concepts throughout the dashboard.
 */
export function InfoTip({ text, className = "" }: InfoTipProps) {
  const [show, setShow] = useState(false);
  const [position, setPosition] = useState<"above" | "below">("above");
  const triggerRef = useRef<HTMLSpanElement>(null);
  const tipRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (show && triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      // If too close to top of viewport, show below
      setPosition(rect.top < 120 ? "below" : "above");
    }
  }, [show]);

  return (
    <span
      ref={triggerRef}
      className={`relative inline-flex items-center ${className}`}
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
    >
      <HelpCircle className="w-3 h-3 text-muted-foreground/50 hover:text-muted-foreground cursor-help transition-colors" />
      {show && (
        <div
          ref={tipRef}
          className={`absolute z-50 w-56 px-3 py-2 text-[11px] leading-relaxed text-foreground/80 bg-white border border-border rounded-lg shadow-lg ${
            position === "above"
              ? "bottom-full mb-1.5 left-1/2 -translate-x-1/2"
              : "top-full mt-1.5 left-1/2 -translate-x-1/2"
          }`}
        >
          {text}
        </div>
      )}
    </span>
  );
}

/**
 * A chart/card title with built-in tooltip.
 */
export function TitleWithTip({
  title,
  tip,
  className = "",
}: {
  title: string;
  tip: string;
  className?: string;
}) {
  return (
    <div className={`flex items-center gap-1.5 ${className}`}>
      <span className="text-sm font-medium text-foreground">{title}</span>
      <InfoTip text={tip} />
    </div>
  );
}

