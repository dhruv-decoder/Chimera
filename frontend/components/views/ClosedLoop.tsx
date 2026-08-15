"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import { Panel, Metric, Loader, Tag, Fade } from "@/components/ui";
import { HardeningCurve, BarList } from "@/components/charts";

const AGENTS = [
  { n: 1, label: "Recon", c: "#8b8cf0", d: "RAG-grounded ideation proposes novel variants (gpt-oss-120b)" },
  { n: 2, label: "Red team", c: "#ff5c49", d: "Evolutionary search tunes each attack to evade the live model" },
  { n: 3, label: "Attack", c: "#ff5c49", d: "Generates the evasive stream and measures the breach" },
  { n: 4, label: "Blue team", c: "#2ed6a6", d: "Retrains on the misses and measures the recovery" },
] as const;

function AgentPipeline({ orchestration, trace }: { orchestration?: string; trace?: string[] }) {
  const [open, setOpen] = useState(false);
  return (
    <Panel title="Multi-agent orchestration"
      right={orchestration === "langgraph" ? <Tag tone="agentic">LangGraph · live</Tag> : undefined}
      hint="A compiled LangGraph StateGraph: four agents pass shared state and the graph cycles until the round budget is spent.">
      <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
        {AGENTS.map((a, i) => (
          <div key={a.label} className="relative rounded-xl border p-4" style={{ borderColor: `${a.c}44`, background: `${a.c}0d` }}>
            <div className="flex items-center gap-2.5">
              <span className="grid h-6 w-6 place-items-center rounded-lg text-xs font-semibold" style={{ background: `${a.c}22`, color: a.c }}>{a.n}</span>
              <span className="text-sm font-semibold text-mist-100">{a.label}</span>
            </div>
            <p className="mt-2 text-[12px] leading-relaxed text-mist-400">{a.d}</p>
            {i < AGENTS.length - 1 && (
              <span className="absolute -right-2 top-1/2 z-10 hidden -translate-y-1/2 text-mist-600 lg:block">→</span>
            )}
          </div>
        ))}
      </div>
      <div className="mt-3 flex items-center gap-2 text-[12px] text-mist-500">
        <span className="text-defense">↻</span> the graph loops recon → red_team → attack → blue_team each round
      </div>
      {trace?.length ? (
        <div className="mt-3">
          <button onClick={() => setOpen(!open)} className="text-[12px] text-mist-400 hover:text-mist-200">
            {open ? "▾ hide" : "▸ show"} execution trace ({trace.length} steps)
          </button>
          {open && (
            <div className="mt-2 max-h-48 overflow-y-auto rounded-lg border border-white/[0.06] bg-ink-950/60 p-3 font-mono text-[11px] leading-relaxed text-mist-400">
              {trace.map((line, i) => (
                <div key={i}><span className="text-mist-600">$</span> {line}</div>
              ))}
            </div>
          )}
        </div>
      ) : null}
    </Panel>
  );
}

export function ClosedLoop() {
  const { data, loading } = useAsync(() => api.loop(), []);
  const [round, setRound] = useState(1);

  if (loading) return <Loader label="Loading loop report" />;
  if (!data || !data.rounds?.length)
    return <Panel><p className="text-sm text-mist-400">No loop report yet. Run <code className="font-mono text-mist-200">python scripts/run_loop.py</code>.</p></Panel>;

  const curve = data.hardening_curve;
  const last = curve[curve.length - 1];
  const r = data.rounds.find((x) => x.round === round) || data.rounds[0];
  const vectors = Object.keys(r.pre_per_vector);

  return (
    <div className="space-y-5">
      <Fade>
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-lg font-semibold tracking-tight text-mist-100">Closed-loop console</h2>
          <Tag tone="defense">the winning view</Tag>
        </div>
        <p className="mt-1.5 max-w-3xl text-sm leading-relaxed text-mist-400">
          Four AI agents evolve evasive fraud against the current detector, measure the breach, retrain, and
          measure the recovery - then cycle. This is the feedback loop that turns the system&apos;s own attacks
          into a stronger defence, and the one chart that proves it closes.
        </p>
      </Fade>

      <AgentPipeline orchestration={(data.meta as any)?.orchestration} trace={data.trace} />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Metric label="baseline recall" better="higher" value={`${(data.baseline_recall * 100).toFixed(1)}%`} sub="fraud caught before any attack" />
        <Metric label="deepest breach" tone="threat" value={`${(Math.min(...data.rounds.map((x) => x.pre_recall)) * 100).toFixed(1)}%`} sub="worst point - most fraud slipped through" />
        <Metric label="hardened recall" tone="defense" better="higher" value={`${(last.post_recall * 100).toFixed(1)}%`} sub="after retraining on the misses" />
        <Metric label="operating threshold" value={last.threshold.toFixed(3)} sub="fixed, conservative (~1% FPR)" />
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.5fr_1fr]">
        <Panel title="Hardening curve" hint="Red dashed = fraud slipping past as the attacker evolves (lower is worse). Green = the same detector after we retrain on the misses (higher is better).">
          <HardeningCurve data={curve} />
        </Panel>
        <Panel title="Rounds" hint="Select a round to inspect.">
          <div className="space-y-2">
            {data.rounds.map((x) => (
              <button key={x.round} onClick={() => setRound(x.round)}
                className={`w-full rounded-lg border p-3 text-left transition-colors ${
                  round === x.round ? "border-defense/30 bg-defense/5" : "border-white/[0.06] hover:border-white/15"
                }`}>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-mist-100">Round {x.round}</span>
                  <span className="stat text-xs"><span className="text-threat">{(x.pre_recall * 100).toFixed(0)}%</span>
                    <span className="text-mist-600"> → </span>
                    <span className="text-defense">{(x.post_recall * 100).toFixed(0)}%</span></span>
                </div>
              </button>
            ))}
          </div>
        </Panel>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Panel title={`Round ${r.round} · per-vector recall (before retraining)`} hint="How much of each attack was still caught while the red team was evading. Green = held up, red = broke through.">
          <BarList
            items={vectors.map((v) => ({ label: v, value: r.pre_per_vector[v] }))}
            tone={(v) => (v > 0.7 ? "#2ed6a6" : v > 0.35 ? "#f5b544" : "#ff5c49")}
          />
        </Panel>
        <Panel title={`Round ${r.round} · red-team ideation`} hint="RAG-grounded variants proposed from the evasive parameters.">
          <div className="max-h-[320px] space-y-2 overflow-y-auto">
            {r.ideation?.length ? r.ideation.map((idea, i) => (
              <div key={i} className="panel p-3">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-agentic">{idea.attack}</span>
                  <Tag tone="agentic">{idea.mode}</Tag>
                </div>
                <div className="mt-1 text-[13px] font-medium text-mist-100">{idea.variant}</div>
                <p className="mt-0.5 text-[11px] leading-relaxed text-mist-500">{idea.twist}</p>
              </div>
            )) : <p className="text-sm text-mist-500">No ideation recorded.</p>}
          </div>
        </Panel>
      </div>
    </div>
  );
}
