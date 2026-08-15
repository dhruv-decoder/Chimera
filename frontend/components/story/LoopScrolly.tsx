"use client";
import { motion, useMotionValueEvent, useScroll } from "framer-motion";
import { useRef, useState } from "react";

type Pt = { round: number; pre_recall: number; post_recall: number };

const clamp = (n: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, n));

function caption(step: number, curve: Pt[]) {
  const r = curve[step];
  const pre = Math.round((r?.pre_recall ?? 0) * 100);
  const post = Math.round((r?.post_recall ?? 0) * 100);
  if (step === 0)
    return { k: "Baseline", t: `A static detector catches ${post}% of the fraud it was trained on. Good - against fraud that holds still.` };
  if (step === 1)
    return { k: `Round 1 · breach`, t: `The red team evolves evasive campaigns against the live model. Recall falls to ${pre}%. Nearly half the fraud now walks straight through.` };
  if (step === 2 && curve.length <= 3)
    return { k: `Round ${r.round} · hardened`, t: `Retrain on exactly what broke through. Recall recovers to ${post}%.` };
  if (step === 2)
    return { k: `Round ${r.round}`, t: `Retrain on what broke through; the red team probes the hardened model again. Breach ${pre}%, recovered ${post}%.` };
  return { k: `Round ${r.round} · converged`, t: `The attacker can no longer find easy evasion. Pre-retrain recall stays at ${pre}%. The defense has learned to generalise across the adversary's moves.` };
}

export function LoopScrolly({ curve }: { curve: Pt[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] });
  const [step, setStep] = useState(0);
  const n = curve.length;
  useMotionValueEvent(scrollYProgress, "change", (v) => {
    setStep(clamp(Math.floor(v * n), 0, n - 1));
  });

  const cap = caption(step, curve);
  const r = curve[step];

  // chart geometry
  const W = 620, H = 340, pad = { l: 46, r: 20, t: 24, b: 34 };
  const iw = W - pad.l - pad.r, ih = H - pad.t - pad.b;
  const maxX = Math.max(n - 1, 1);
  const x = (i: number) => pad.l + (i / maxX) * iw;
  const y = (v: number) => pad.t + (1 - v) * ih;
  const shown = curve.slice(0, step + 1);
  const path = (key: "pre_recall" | "post_recall") =>
    shown.map((d, i) => `${i === 0 ? "M" : "L"} ${x(i)} ${y(d[key])}`).join(" ");

  return (
    <section ref={ref} style={{ height: `${n * 92}vh` }} className="relative">
      <div className="sticky top-0 flex min-h-screen items-center">
        <div className="mx-auto grid w-full max-w-6xl gap-10 px-6 lg:grid-cols-[1.15fr_1fr] lg:items-center">
          {/* chart */}
          <div className="panel p-6">
            <div className="mb-3 flex items-center justify-between">
              <span className="label">Adversarial hardening curve</span>
              <span className="stat text-[11px] text-mist-500">round {r?.round ?? 0} / {curve[n - 1]?.round}</span>
            </div>
            <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
              {[0, 0.5, 1].map((g) => (
                <g key={g}>
                  <line x1={pad.l} x2={W - pad.r} y1={y(g)} y2={y(g)} stroke="rgba(255,255,255,0.05)" />
                  <text x={pad.l - 6} y={y(g) + 3} fill="#4b5261" fontSize={10} textAnchor="end" className="font-mono">{g * 100}</text>
                </g>
              ))}
              <text x={pad.l} y={12} fill="#8a909f" fontSize={10}>recall % (higher is better)</text>
              {curve.map((d, i) => (
                <text key={i} x={x(i)} y={H - 10} fill="#4b5261" fontSize={10} textAnchor="middle" className="font-mono">round {d.round}</text>
              ))}
              {/* value labels on points */}
              {shown.map((d, i) => {
                const anchor = i === 0 ? "start" : i === shown.length - 1 ? "end" : "middle";
                const same = Math.abs(d.post_recall - d.pre_recall) < 0.02;
                return (
                  <g key={`lbl${i}`}>
                    <text x={x(i)} y={y(d.post_recall) - 8} fill="#2ed6a6" fontSize={10} fontWeight={600} textAnchor={anchor} className="font-mono">{Math.round(d.post_recall * 100)}%</text>
                    {!same && <text x={x(i)} y={y(d.pre_recall) + 15} fill="#ff5c49" fontSize={10} fontWeight={600} textAnchor={anchor} className="font-mono">{Math.round(d.pre_recall * 100)}%</text>}
                  </g>
                );
              })}
              {/* breach band from post to pre at active round */}
              {r && step > 0 && (
                <motion.rect
                  x={x(step) - 16} width={32}
                  y={y(Math.max(r.pre_recall, r.post_recall))}
                  height={Math.abs(y(r.pre_recall) - y(r.post_recall))}
                  fill="rgba(255,92,73,0.10)"
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                />
              )}
              <motion.path key={`post${step}`} d={path("post_recall")} fill="none" stroke="#2ed6a6" strokeWidth={2.6}
                initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.7 }} />
              <motion.path key={`pre${step}`} d={path("pre_recall")} fill="none" stroke="#ff5c49" strokeWidth={2.6}
                strokeDasharray="5 4" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.7, delay: 0.1 }} />
              {shown.map((d, i) => (
                <g key={i}>
                  <circle cx={x(i)} cy={y(d.post_recall)} r={3.5} fill="#2ed6a6" />
                  <circle cx={x(i)} cy={y(d.pre_recall)} r={3.5} fill="#ff5c49" />
                </g>
              ))}
            </svg>
            <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1 text-[11px]">
              <span className="flex items-center gap-2 text-threat"><span className="inline-block h-0 w-5 border-t-2 border-dashed border-threat" />fraud slipping past (before retrain)</span>
              <span className="flex items-center gap-2 text-defense"><span className="inline-block h-[2px] w-5 bg-defense" />fraud caught (after retrain)</span>
            </div>
          </div>

          {/* caption */}
          <div>
            <div className="mb-4 flex gap-1.5">
              {curve.map((_, i) => (
                <span key={i} className={`h-1 flex-1 rounded-full transition-colors duration-300 ${i <= step ? "bg-defense" : "bg-white/10"}`} />
              ))}
            </div>
            <motion.div key={step} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
              <div className="label text-defense">{cap.k}</div>
              <div className="mt-3 flex items-baseline gap-3">
                <span className="stat text-4xl font-semibold text-threat">{Math.round((r?.pre_recall ?? 0) * 100)}%</span>
                <span className="text-mist-500">→</span>
                <span className="stat text-4xl font-semibold text-defense">{Math.round((r?.post_recall ?? 0) * 100)}%</span>
              </div>
              <p className="mt-4 max-w-md text-[15px] leading-relaxed text-mist-300">{cap.t}</p>
            </motion.div>
            <p className="mt-8 text-[12px] text-mist-600">Scroll to advance the rounds ↓</p>
          </div>
        </div>
      </div>
    </section>
  );
}
