"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import { Wordmark } from "@/components/brand";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import { Overview } from "@/components/views/Overview";
import { ThreatMatrix } from "@/components/views/ThreatMatrix";
import { AttackLab } from "@/components/views/AttackLab";
import { ClosedLoop } from "@/components/views/ClosedLoop";
import { GraphView } from "@/components/views/GraphView";
import { Detection } from "@/components/views/Detection";
import { Evidence } from "@/components/views/Evidence";

const NAV = [
  { id: "overview", label: "Overview", pillar: "", view: Overview },
  { id: "threats", label: "Threat Matrix", pillar: "Identify", view: ThreatMatrix },
  { id: "lab", label: "Attack Lab", pillar: "Generate", view: AttackLab },
  { id: "loop", label: "Closed Loop", pillar: "Adapt", view: ClosedLoop },
  { id: "graph", label: "Network Graph", pillar: "Generate", view: GraphView },
  { id: "detect", label: "Detection", pillar: "Defend", view: Detection },
  { id: "evidence", label: "Validation", pillar: "Evidence", view: Evidence },
] as const;

export function Console({ initial = "overview", onExit }: { initial?: string; onExit: () => void }) {
  const [active, setActive] = useState<string>(initial);
  const health = useAsync(() => api.health(), []);
  const Active = (NAV.find((n) => n.id === active) || NAV[0]).view;

  return (
    <div className="relative z-10 min-h-screen">
      <header className="sticky top-0 z-30 border-b border-white/[0.06] bg-ink-950/75 backdrop-blur-md">
        <div className="mx-auto max-w-[1360px] px-5 lg:px-8">
          <div className="flex items-center justify-between py-3">
            <button onClick={onExit} className="flex items-center gap-3 text-left" title="Back to overview story">
              <Wordmark />
            </button>
            <div className="flex items-center gap-3">
              <span className="hidden items-center gap-2 text-[11px] text-mist-500 sm:flex">
                <span className={`h-1.5 w-1.5 rounded-full ${health.data?.detector_loaded ? "bg-defense" : "bg-warn"} ${health.loading ? "animate-blink" : ""}`} />
                {health.data?.detector_loaded ? "detector online" : health.loading ? "connecting" : "offline"}
              </span>
              <button onClick={onExit} className="btn py-2 text-xs">← Story</button>
            </div>
          </div>
          {/* tab rail */}
          <nav className="flex gap-1 overflow-x-auto pb-2">
            {NAV.map((n) => (
              <button
                key={n.id}
                onClick={() => setActive(n.id)}
                className={`group relative flex shrink-0 items-center gap-2 rounded-lg px-3.5 py-2 text-sm transition-colors ${
                  active === n.id ? "text-mist-100" : "text-mist-400 hover:text-mist-200"
                }`}
              >
                <span>{n.label}</span>
                {n.pillar && (
                  <span className={`text-[10px] uppercase tracking-wider ${active === n.id ? "text-defense" : "text-mist-600"}`}>
                    {n.pillar}
                  </span>
                )}
                {active === n.id && (
                  <motion.span layoutId="tabpill" className="absolute inset-0 -z-10 rounded-lg bg-white/[0.06] ring-1 ring-white/[0.06]" transition={{ type: "spring", stiffness: 400, damping: 32 }} />
                )}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-[1360px] px-5 py-7 lg:px-8">
        <motion.div key={active} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}>
          <Active />
        </motion.div>
      </main>
    </div>
  );
}
