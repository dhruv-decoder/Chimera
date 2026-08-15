"use client";
import { motion } from "framer-motion";

const AXIS = "rgba(255,255,255,0.10)";
const GRID = "rgba(255,255,255,0.05)";

// ---- Hardening curve: pre-retrain vs post-retrain recall across rounds ----
export function HardeningCurve({
  data, width = 640, height = 260,
}: {
  data: { round: number; pre_recall: number; post_recall: number }[];
  width?: number; height?: number;
}) {
  const pad = { l: 30, r: 26, t: 24, b: 34 };
  const W = width - pad.l - pad.r;
  const H = height - pad.t - pad.b;
  const xs = data.map((d) => d.round);
  const maxX = Math.max(...xs, 1);
  const x = (r: number) => pad.l + (r / maxX) * W;
  const y = (v: number) => pad.t + (1 - v) * H;
  const line = (key: "pre_recall" | "post_recall") =>
    data.map((d, i) => `${i === 0 ? "M" : "L"} ${x(d.round)} ${y(d[key])}`).join(" ");
  const pct = (v: number) => `${Math.round(v * 100)}%`;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full">
      {[0, 0.5, 1].map((g) => (
        <g key={g}>
          <line x1={pad.l} x2={width - pad.r} y1={y(g)} y2={y(g)} stroke={GRID} />
          <text x={pad.l - 6} y={y(g) + 3} fill="#6b7280" fontSize={10} textAnchor="end" className="font-mono">
            {(g * 100).toFixed(0)}
          </text>
        </g>
      ))}
      {xs.map((r, i) => (
        <text key={r} x={x(r)} y={height - 10} fill="#6b7280" fontSize={10} textAnchor="middle" className="font-mono">
          round {r}
        </text>
      ))}
      <text x={pad.l} y={12} fill="#8a909f" fontSize={9.5}>recall % (higher is better)</text>
      {/* post-retrain (defense) */}
      <motion.path d={line("post_recall")} fill="none" stroke="#2ed6a6" strokeWidth={2.5}
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1 }} />
      {/* pre-retrain (attack breach) */}
      <motion.path d={line("pre_recall")} fill="none" stroke="#ff5c49" strokeWidth={2.5}
        strokeDasharray="5 4" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1, delay: 0.2 }} />
      {data.map((d, i) => {
        const anchor = i === 0 ? "start" : i === data.length - 1 ? "end" : "middle";
        const same = Math.abs(d.post_recall - d.pre_recall) < 0.02;
        return (
          <g key={d.round}>
            <circle cx={x(d.round)} cy={y(d.post_recall)} r={3.5} fill="#2ed6a6" />
            <circle cx={x(d.round)} cy={y(d.pre_recall)} r={3.5} fill="#ff5c49" />
            <text x={x(d.round)} y={y(d.post_recall) - 8} fill="#2ed6a6" fontSize={10} fontWeight={600} textAnchor={anchor} className="font-mono">{pct(d.post_recall)}</text>
            {!same && (
              <text x={x(d.round)} y={y(d.pre_recall) + 15} fill="#ff5c49" fontSize={10} fontWeight={600} textAnchor={anchor} className="font-mono">{pct(d.pre_recall)}</text>
            )}
          </g>
        );
      })}
    </svg>
  );
}

// ---- ROC / PR curve ----
export function Curve({
  points, width = 320, height = 240, color = "#2ed6a6", diagonal = false, xlabel, ylabel,
}: {
  points: [number, number][]; width?: number; height?: number; color?: string;
  diagonal?: boolean; xlabel?: string; ylabel?: string;
}) {
  const pad = { l: 34, r: 12, t: 12, b: 28 };
  const W = width - pad.l - pad.r;
  const H = height - pad.t - pad.b;
  const x = (v: number) => pad.l + v * W;
  const y = (v: number) => pad.t + (1 - v) * H;
  const d = points.map((p, i) => `${i === 0 ? "M" : "L"} ${x(p[0])} ${y(p[1])}`).join(" ");
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full">
      {[0, 0.5, 1].map((g) => (
        <line key={`h${g}`} x1={pad.l} x2={width - pad.r} y1={y(g)} y2={y(g)} stroke={GRID} />
      ))}
      {[0, 0.5, 1].map((g) => (
        <line key={`v${g}`} x1={x(g)} x2={x(g)} y1={pad.t} y2={height - pad.b} stroke={GRID} />
      ))}
      {diagonal && <line x1={x(0)} y1={y(0)} x2={x(1)} y2={y(1)} stroke={AXIS} strokeDasharray="3 3" />}
      <motion.path d={d} fill="none" stroke={color} strokeWidth={2}
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.9 }} />
      {xlabel && <text x={pad.l + W / 2} y={height - 4} fill="#6b7280" fontSize={9} textAnchor="middle">{xlabel}</text>}
      {ylabel && <text x={10} y={pad.t + 6} fill="#6b7280" fontSize={9}>{ylabel}</text>}
    </svg>
  );
}

// ---- Horizontal bar list (per-vector recall, feature importance) ----
export function BarList({
  items, tone = "#2ed6a6", format = (v) => `${(v * 100).toFixed(0)}%`, max = 1,
}: {
  items: { label: string; value: number; note?: string }[];
  tone?: string | ((v: number) => string); format?: (v: number) => string; max?: number;
}) {
  return (
    <div className="space-y-2.5">
      {items.map((it, i) => {
        const color = typeof tone === "function" ? tone(it.value) : tone;
        return (
          <div key={it.label} className="grid grid-cols-[130px_1fr_52px] items-center gap-3">
            <div className="truncate font-mono text-xs text-mist-300" title={it.label}>{it.label}</div>
            <div className="h-2 overflow-hidden rounded-full bg-white/[0.06]">
              <motion.div className="h-2 rounded-full" style={{ background: color }}
                initial={{ width: 0 }} animate={{ width: `${(it.value / max) * 100}%` }}
                transition={{ duration: 0.7, delay: i * 0.03, ease: [0.22, 1, 0.36, 1] }} />
            </div>
            <div className="stat text-right text-xs text-mist-200">{format(it.value)}</div>
          </div>
        );
      })}
    </div>
  );
}
