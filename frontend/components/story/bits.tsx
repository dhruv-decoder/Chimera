"use client";
import { animate, motion, useInView, useMotionValue, useTransform } from "framer-motion";
import { ReactNode, useEffect, useRef, useState } from "react";

const EASE = [0.22, 1, 0.36, 1] as const;

/** Fade + rise into view once. */
export function Reveal({ children, delay = 0, y = 14, className = "" }: {
  children: ReactNode; delay?: number; y?: number; className?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-12% 0px" }}
      transition={{ duration: 0.7, delay, ease: EASE }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

/** Count up to `value` when scrolled into view. */
export function Counter({ value, decimals = 0, prefix = "", suffix = "", className = "" }: {
  value: number; decimals?: number; prefix?: string; suffix?: string; className?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-10% 0px" });
  const mv = useMotionValue(0);
  const [txt, setTxt] = useState("0");
  useEffect(() => {
    if (!inView) return;
    const controls = animate(mv, value, { duration: 1.4, ease: EASE });
    const unsub = mv.on("change", (v) => setTxt(v.toFixed(decimals)));
    return () => { controls.stop(); unsub(); };
  }, [inView, value, decimals, mv]);
  return (
    <span ref={ref} className={className}>
      {prefix}{txt}{suffix}
    </span>
  );
}

/** The living loop: identify -> generate -> defend, with a traveling pulse. */
export function LoopDiagram({ size = 320 }: { size?: number }) {
  const nodes = [
    { a: -90, label: "Identify", c: "#8b8cf0" },
    { a: 30, label: "Generate", c: "#ff5c49" },
    { a: 150, label: "Defend", c: "#2ed6a6" },
  ];
  const R = size / 2 - 44;
  const cx = size / 2;
  const cy = size / 2;
  const pt = (deg: number) => [cx + R * Math.cos((deg * Math.PI) / 180), cy + R * Math.sin((deg * Math.PI) / 180)];
  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="w-full max-w-[360px]">
      <defs>
        <linearGradient id="loopring" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#8b8cf0" />
          <stop offset="50%" stopColor="#ff5c49" />
          <stop offset="100%" stopColor="#2ed6a6" />
        </linearGradient>
      </defs>
      <circle cx={cx} cy={cy} r={R} fill="none" stroke="url(#loopring)" strokeWidth={1.4} opacity={0.5} strokeDasharray="2 6" />
      <motion.circle
        cx={cx} cy={cy} r={R} fill="none" stroke="url(#loopring)" strokeWidth={2.4}
        strokeLinecap="round" strokeDasharray={`${2 * Math.PI * R * 0.16} ${2 * Math.PI * R}`}
        animate={{ rotate: 360 }} transition={{ duration: 7, repeat: Infinity, ease: "linear" }}
        style={{ transformOrigin: "50% 50%" }}
      />
      {nodes.map((n, i) => {
        const [x, y] = pt(n.a);
        const [nx, ny] = pt(nodes[(i + 1) % 3].a);
        return (
          <g key={n.label}>
            <line x1={x} y1={y} x2={nx} y2={ny} stroke="rgba(255,255,255,0.10)" strokeWidth={1} />
          </g>
        );
      })}
      {nodes.map((n) => {
        const [x, y] = pt(n.a);
        return (
          <g key={n.label}>
            <circle cx={x} cy={y} r={26} fill="#0d0f14" stroke={n.c} strokeWidth={1.3} />
            <circle cx={x} cy={y} r={5} fill={n.c} />
            <text x={x} y={y + 42} fill="#aeb4c2" fontSize={12} textAnchor="middle" className="font-medium">
              {n.label}
            </text>
          </g>
        );
      })}
      <text x={cx} y={cy - 4} fill="#e8eaf0" fontSize={13} textAnchor="middle" className="font-mono">closed</text>
      <text x={cx} y={cy + 13} fill="#6b7280" fontSize={11} textAnchor="middle" className="font-mono">loop</text>
    </svg>
  );
}

/** Horizontal recall bars that animate to a target when scrolled into view. */
export function RecallBars({ items }: { items: { label: string; value: number; tone?: string }[] }) {
  return (
    <div className="space-y-3">
      {items.map((it, i) => (
        <div key={it.label} className="grid grid-cols-[112px_1fr_46px] items-center gap-3">
          <div className="truncate font-mono text-[11px] text-mist-400" title={it.label}>{it.label}</div>
          <div className="h-2 overflow-hidden rounded-full bg-white/[0.06]">
            <motion.div
              className="h-2 rounded-full"
              style={{ background: it.tone || "#2ed6a6" }}
              initial={{ width: 0 }}
              whileInView={{ width: `${Math.round(it.value * 100)}%` }}
              viewport={{ once: true }}
              transition={{ duration: 0.9, delay: i * 0.05, ease: EASE }}
            />
          </div>
          <div className="stat text-right text-[11px] text-mist-200">{Math.round(it.value * 100)}%</div>
        </div>
      ))}
    </div>
  );
}

export function useParallax(scrollYProgress: any, range: [number, number]) {
  return useTransform(scrollYProgress, [0, 1], range);
}
