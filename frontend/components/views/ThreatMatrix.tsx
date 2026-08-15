"use client";
import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api, Technique } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import { Fade, Loader, Tag } from "@/components/ui";

const TACTIC_ORDER = ["recon", "access", "setup", "execution", "cashout", "evasion"];

export function ThreatMatrix() {
  const { data, loading } = useAsync(() => api.taxonomy(), []);
  const [sel, setSel] = useState<Technique | null>(null);

  if (loading || !data) return <Loader label="Loading taxonomy" />;
  const byTactic = (t: string) => data.techniques.filter((x) => x.tactic === t);

  return (
    <div className="space-y-5">
      <Fade>
        <div>
          <h2 className="text-lg font-semibold tracking-tight text-mist-100">Payment-fraud technique matrix</h2>
          <p className="mt-1 max-w-3xl text-sm text-mist-400">
            An ATT&CK-style map of GenAI-era payment fraud across the six stages of the kill chain (columns).{" "}
            {data.techniques.filter((t) => t.simulated).length} of {data.techniques.length} techniques are simulated
            end-to-end; the rest are mapped for breadth and feed the ideation agent.
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[11px] text-mist-400">
            <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-defense" />simulated end-to-end</span>
            <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-white/20" />mapped for breadth</span>
            <span className="flex items-center gap-1.5"><SeverityDots n={4} /> financial impact</span>
            <span className="text-mist-600">click any technique for detail, sources and detection signatures</span>
          </div>
        </div>
      </Fade>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {TACTIC_ORDER.map((tactic, ci) => (
          <Fade key={tactic} delay={ci * 0.04}>
            <div className="flex h-full flex-col">
              <div className="mb-2.5 flex items-center gap-2 border-b border-white/[0.06] pb-2">
                <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-mist-200">{tactic}</span>
                <span className="stat text-[10px] text-mist-600">{byTactic(tactic).length}</span>
              </div>
              <div className="flex flex-col gap-2.5">
                {byTactic(tactic).map((t) => (
                  <button key={t.id} onClick={() => setSel(t)}
                    className={`group relative overflow-hidden rounded-xl border bg-white/[0.024] p-3.5 text-left transition-all duration-200 hover:-translate-y-0.5 hover:bg-white/[0.05] ${t.simulated ? "border-defense/25 hover:border-defense/50" : "border-white/[0.07] hover:border-white/20"}`}>
                    {t.simulated && <span className="absolute left-0 top-0 h-full w-[3px] bg-defense/50" />}
                    <div className="flex items-start justify-between gap-2">
                      <span className="text-[13px] font-semibold leading-snug text-mist-100">{t.name}</span>
                      {t.simulated
                        ? <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-defense" title="simulated" />
                        : <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-white/20" title="mapped" />}
                    </div>
                    <p className="mt-1.5 line-clamp-2 text-[11px] leading-snug text-mist-500">{t.summary}</p>
                    <div className="mt-2 flex items-center justify-between">
                      <span className="font-mono text-[10px] text-mist-500">{t.id}</span>
                      <SeverityDots n={t.severity} />
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </Fade>
        ))}
      </div>

      <AnimatePresence>
        {sel && <Drawer t={sel} onClose={() => setSel(null)} tacticDesc={data.tactics[sel.tactic]} />}
      </AnimatePresence>
    </div>
  );
}

function SeverityDots({ n }: { n: number }) {
  return (
    <span className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((i) => (
        <span key={i} className={`h-1 w-1 rounded-full ${i <= n ? "bg-threat/80" : "bg-white/10"}`} />
      ))}
    </span>
  );
}

function Drawer({ t, onClose, tacticDesc }: { t: Technique; onClose: () => void; tacticDesc: string }) {
  return (
    <motion.div className="fixed inset-0 z-30 flex justify-end bg-black/50 backdrop-blur-sm"
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose}>
      <motion.aside onClick={(e) => e.stopPropagation()}
        initial={{ x: 40, opacity: 0 }} animate={{ x: 0, opacity: 1 }} exit={{ x: 40, opacity: 0 }}
        transition={{ type: "spring", stiffness: 260, damping: 30 }}
        className="h-full w-full max-w-md overflow-y-auto border-l border-white/10 bg-ink-900 p-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs text-defense">{t.id}</span>
              {t.simulated ? <Tag tone="defense">simulated</Tag> : <Tag>mapped</Tag>}
            </div>
            <h3 className="mt-1 text-lg font-semibold tracking-tight text-mist-100">{t.name}</h3>
          </div>
          <button onClick={onClose} className="btn px-2 py-1 text-xs">esc</button>
        </div>

        <p className="mt-4 text-sm leading-relaxed text-mist-300">{t.summary}</p>

        <Section label="GenAI amplification">
          <p className="text-sm leading-relaxed text-mist-300">{t.genai_role}</p>
        </Section>
        <Section label="Kill chain">
          <div className="flex flex-wrap items-center gap-1.5">
            {t.kill_chain.map((k, i) => (
              <span key={i} className="flex items-center gap-1.5">
                <span className="chip">{k}</span>
                {i < t.kill_chain.length - 1 && <span className="text-mist-600">→</span>}
              </span>
            ))}
          </div>
        </Section>
        <Section label="Observable signatures">
          <ul className="space-y-1.5">
            {t.signatures.map((sig, i) => (
              <li key={i} className="flex gap-2 text-sm text-mist-300">
                <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-defense" />{sig}
              </li>
            ))}
          </ul>
        </Section>
        <Section label="Rails & channels">
          <div className="flex flex-wrap gap-1.5">
            {t.rails.map((r) => <Tag key={r}>{r}</Tag>)}
            {t.channels.map((c) => <Tag key={c} tone={c === "agent" ? "agentic" : "default"}>{c}</Tag>)}
          </div>
        </Section>
        <Section label="Intelligence sources">
          <ul className="space-y-1">
            {t.references.map((r, i) => (
              <li key={i}><a href={r} target="_blank" rel="noreferrer" className="break-all text-xs text-signal hover:underline">{r}</a></li>
            ))}
          </ul>
        </Section>
      </motion.aside>
    </motion.div>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mt-5 border-t border-white/[0.06] pt-4">
      <div className="label mb-2">{label}</div>
      {children}
    </div>
  );
}
