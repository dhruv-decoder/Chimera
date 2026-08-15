"use client";
import { motion } from "framer-motion";
import { ReactNode } from "react";

export function Panel({ children, className = "", title, hint, right }: {
  children: ReactNode; className?: string; title?: string; hint?: string; right?: ReactNode;
}) {
  return (
    <div className={`panel p-5 ${className}`}>
      {(title || right) && (
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            {title && <h3 className="text-sm font-semibold tracking-tight text-mist-100">{title}</h3>}
            {hint && <p className="mt-0.5 text-xs text-mist-500">{hint}</p>}
          </div>
          {right}
        </div>
      )}
      {children}
    </div>
  );
}

export function Metric({ label, value, sub, tone = "default", better }: {
  label: string; value: ReactNode; sub?: ReactNode;
  tone?: "default" | "defense" | "threat" | "warn" | "agentic";
  better?: "higher" | "lower";
}) {
  const toneMap = {
    default: "text-mist-100", defense: "text-defense", threat: "text-threat",
    warn: "text-warn", agentic: "text-agentic",
  } as const;
  return (
    <div className="panel panel-hover p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="label">{label}</div>
        {better && (
          <span className="shrink-0 rounded-full bg-white/[0.05] px-1.5 py-0.5 text-[9px] font-medium tracking-wide text-mist-500">
            {better === "higher" ? "↑ higher better" : "↓ lower better"}
          </span>
        )}
      </div>
      <div className={`stat mt-1.5 text-2xl font-semibold ${toneMap[tone]}`}>{value}</div>
      {sub && <div className="mt-1 text-xs text-mist-500">{sub}</div>}
    </div>
  );
}

export function Bar({ value, tone = "defense", height = 6 }: {
  value: number; tone?: "defense" | "threat" | "warn" | "agentic" | "signal"; height?: number;
}) {
  const colors = {
    defense: "#2ed6a6", threat: "#ff5c49", warn: "#f5b544", agentic: "#8b8cf0", signal: "#5ea0ff",
  } as const;
  return (
    <div className="w-full overflow-hidden rounded-full bg-white/[0.06]" style={{ height }}>
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${Math.max(0, Math.min(100, value * 100))}%` }}
        transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
        style={{ height, background: colors[tone] }}
      />
    </div>
  );
}

export function RiskPill({ risk, threshold }: { risk: number; threshold: number }) {
  const flagged = risk >= threshold;
  return (
    <span
      className={`stat inline-flex items-center gap-1.5 rounded-md px-1.5 py-0.5 text-xs font-medium ${
        flagged ? "bg-threat/15 text-threat" : "bg-white/[0.05] text-mist-400"
      }`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${flagged ? "bg-threat" : "bg-mist-500"}`} />
      {risk.toFixed(3)}
    </span>
  );
}

export function Tag({ children, tone = "default" }: { children: ReactNode; tone?: "default" | "defense" | "threat" | "agentic" | "warn" }) {
  const map = {
    default: "border-white/10 text-mist-300",
    defense: "border-defense/30 text-defense bg-defense/5",
    threat: "border-threat/30 text-threat bg-threat/5",
    agentic: "border-agentic/30 text-agentic bg-agentic/5",
    warn: "border-warn/30 text-warn bg-warn/5",
  } as const;
  return <span className={`chip border ${map[tone]}`}>{children}</span>;
}

export function Loader({ label = "Computing" }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 text-sm text-mist-400">
      <div className="relative h-4 w-24 overflow-hidden rounded-full bg-white/[0.06]">
        <div className="absolute inset-y-0 w-1/3 animate-sweep rounded-full bg-defense/50" />
      </div>
      <span className="stat">{label}…</span>
    </div>
  );
}

export function Fade({ children, delay = 0 }: { children: ReactNode; delay?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}
