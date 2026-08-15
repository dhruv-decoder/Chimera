"use client";
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api, LabResult, LabEvent, Ideation } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import { Panel, Metric, Loader, Tag, RiskPill, Fade } from "@/components/ui";

export function AttackLab() {
  const tax = useAsync(() => api.taxonomy(), []);
  const params = useAsync(() => api.attackParams(), []);
  const [attack, setAttack] = useState<string>("");
  const [intensity, setIntensity] = useState(1.5);
  const [knobs, setKnobs] = useState<Record<string, number>>({});
  const [result, setResult] = useState<LabResult | null>(null);
  const [idea, setIdea] = useState<Ideation | null>(null);
  const [busy, setBusy] = useState(false);
  const [openRow, setOpenRow] = useState<string | null>(null);

  useEffect(() => {
    if (tax.data && !attack) setAttack(tax.data.attack_ids[0]);
  }, [tax.data, attack]);

  const spec = params.data?.[attack];
  useEffect(() => {
    if (spec) setKnobs(Object.fromEntries(Object.entries(spec).map(([k, v]) => [k, v.default])));
  }, [attack, spec]);

  async function launch() {
    setBusy(true); setResult(null); setIdea(null);
    try {
      const [r, i] = await Promise.all([
        api.attackLab(attack, intensity, knobs),
        api.ideation(attack, knobs),
      ]);
      setResult(r); setIdea(i);
    } finally { setBusy(false); }
  }

  if (tax.loading || !tax.data) return <Loader label="Loading" />;

  return (
    <div className="space-y-5">
      <Fade>
        <div>
          <h2 className="text-lg font-semibold tracking-tight text-mist-100">Attack Lab</h2>
          <p className="mt-1 max-w-3xl text-sm text-mist-400">
            Run a fraud campaign against the trained detector and watch it score every transaction live. Then tune
            the evasion knobs to try to slip past it - the same levers the red-team agent optimises.
          </p>
          <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
            <span className="chip"><span className="text-defense">1</span> pick an attack</span>
            <span className="chip"><span className="text-defense">2</span> (optional) tune evasion knobs</span>
            <span className="chip"><span className="text-defense">3</span> launch and read the result</span>
          </div>
        </div>
      </Fade>

      <div className="grid gap-5 lg:grid-cols-[320px_1fr]">
        {/* control column */}
        <div className="space-y-4">
          <Panel title="Campaign">
            <label className="label">vector</label>
            <div className="mt-2 grid grid-cols-2 gap-1.5">
              {tax.data.attack_ids.map((a) => (
                <button key={a} onClick={() => setAttack(a)}
                  className={`rounded-md border px-2 py-1.5 text-left font-mono text-[11px] transition-colors ${
                    attack === a ? "border-threat/40 bg-threat/10 text-threat" : "border-white/[0.07] text-mist-400 hover:border-white/20"
                  }`}>{a}</button>
              ))}
            </div>

            <div className="mt-4">
              <div className="flex items-center justify-between">
                <label className="label">intensity</label>
                <span className="stat text-xs text-mist-300">{intensity.toFixed(1)}×</span>
              </div>
              <input type="range" min={0.5} max={3} step={0.1} value={intensity}
                onChange={(e) => setIntensity(+e.target.value)}
                className="mt-2 w-full accent-threat" />
            </div>

            <button onClick={launch} disabled={busy}
              className="btn btn-accent mt-4 w-full justify-center">
              {busy ? "running detector…" : "▸ Launch campaign"}
            </button>
          </Panel>

          {spec && (
            <Panel title="Evasion knobs" hint="Shape parameters the adversary tunes to lower risk.">
              <div className="space-y-3">
                {Object.entries(spec).filter(([k]) => !["n_rings","n_campaigns","n_agents","n_victims","n_identities","cards_per_device","purchases_per_agent"].includes(k)).slice(0, 6).map(([k, v]) => (
                  <div key={k}>
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[11px] text-mist-300">{k}</span>
                      <span className="stat text-[11px] text-mist-400">{(knobs[k] ?? v.default).toFixed(2)}</span>
                    </div>
                    <input type="range" min={v.min} max={v.max} step={(v.max - v.min) / 100}
                      value={knobs[k] ?? v.default}
                      onChange={(e) => setKnobs({ ...knobs, [k]: +e.target.value })}
                      className="mt-1 w-full accent-agentic" />
                    <p className="mt-0.5 text-[10px] leading-tight text-mist-600">{v.desc}</p>
                  </div>
                ))}
              </div>
            </Panel>
          )}
        </div>

        {/* result column */}
        <div className="space-y-4">
          {busy && <Panel><Loader label="Simulating + scoring" /></Panel>}
          {result && (
            <>
              <ResultBanner attack={attack} r={result.summary} />
              <div className="grid grid-cols-3 gap-3">
                <Metric label="caught" tone="defense" value={Math.round(result.summary.recall * result.summary.n_fraud)} sub={`of ${result.summary.n_fraud} fraud events`} />
                <Metric label="missed" tone="threat" value={result.summary.n_fraud - Math.round(result.summary.recall * result.summary.n_fraud)} sub="slipped through" />
                <Metric label="false positives" better="lower" tone="warn" value={`${(result.summary.fp_rate * 100).toFixed(1)}%`} sub={`${result.summary.false_positives}/${result.summary.n_legit_shown} legit flagged`} />
              </div>

              {idea && <IdeationCard idea={idea} />}

              <Panel title="Live event stream" hint="Each row is one transaction the detector just scored, riskiest first. Click any row to see the exact reason codes.">
                <div className="mb-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[11px] text-mist-400">
                  <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-threat" />flagged as fraud (risk &ge; {result.threshold.toFixed(3)})</span>
                  <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-mist-500" />allowed</span>
                  <span className="flex items-center gap-1.5"><span className="text-warn">&#9670;</span>misclassified</span>
                  <span className="text-mist-600">agent channel shown in violet</span>
                </div>
                <EventTable events={result.events} threshold={result.threshold} openRow={openRow} setOpenRow={setOpenRow} />
              </Panel>
            </>
          )}
          {!result && !busy && (
            <Panel>
              <div className="grid place-items-center gap-3 py-14 text-center">
                <div className="text-2xl">&#9654;</div>
                <div className="max-w-md text-sm text-mist-300">Pick an attack on the left and press <span className="text-defense">Launch campaign</span>.</div>
                <div className="max-w-md text-[13px] leading-relaxed text-mist-500">
                  The detector scores a fresh simulated stream in real time. You will see how much of the attack it
                  catches, which events slipped through, and - for any transaction - the exact features that drove
                  the decision. Try <span className="font-mono text-mist-300">AGENT-HIJACK</span>, then raise its
                  <span className="font-mono text-mist-300"> attestation_prob</span> knob and relaunch to watch recall fall.
                </div>
              </div>
            </Panel>
          )}
        </div>
      </div>
    </div>
  );
}

function ResultBanner({ attack, r }: { attack: string; r: { recall: number; n_fraud: number } }) {
  const pct = Math.round(r.recall * 100);
  const caught = Math.round(r.recall * r.n_fraud);
  const good = r.recall >= 0.7;
  const accent = good ? "text-defense" : "text-threat";
  return (
    <div className={`panel relative overflow-hidden p-5 ${good ? "border-defense/25" : "border-threat/30"}`}>
      <div className={`absolute -right-10 -top-10 h-32 w-32 rounded-full blur-3xl ${good ? "bg-defense/10" : "bg-threat/10"}`} />
      <div className="relative flex flex-wrap items-center gap-x-6 gap-y-2">
        <div>
          <div className="label">detection recall</div>
          <div className={`stat text-5xl font-semibold ${accent}`}>{pct}%</div>
        </div>
        <div className="max-w-lg text-sm leading-relaxed text-mist-300">
          The detector caught <span className={`font-semibold ${accent}`}>{caught} of {r.n_fraud}</span>{" "}
          <span className="font-mono text-mist-200">{attack}</span> events.{" "}
          {good
            ? "Its structural and identity signatures hold up here."
            : "A large share slipped through - tune it further, or this is a vector the closed loop must harden."}
        </div>
      </div>
    </div>
  );
}

function IdeationCard({ idea }: { idea: Ideation }) {
  return (
    <div className="panel border-agentic/20 p-4">
      <div className="flex items-center gap-2">
        <Tag tone="agentic">red-team ideation</Tag>
        <span className="stat text-[10px] text-mist-500">{idea.mode}</span>
      </div>
      <div className="mt-2 text-sm font-medium text-mist-100">{idea.variant_name}</div>
      <p className="mt-1 text-xs leading-relaxed text-mist-400">{idea.novel_twist}</p>
      {idea.observable_footprint?.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {idea.observable_footprint.slice(0, 5).map((f, i) => <span key={i} className="chip">{f}</span>)}
        </div>
      )}
    </div>
  );
}

function EventTable({ events, threshold, openRow, setOpenRow }: {
  events: LabEvent[]; threshold: number; openRow: string | null; setOpenRow: (id: string | null) => void;
}) {
  const rows = [...events].sort((a, b) => b.risk - a.risk).slice(0, 60);
  return (
    <div className="max-h-[460px] overflow-y-auto">
      <table className="w-full text-left text-xs">
        <thead className="sticky top-0 bg-ink-850 text-mist-500">
          <tr className="[&>th]:px-2 [&>th]:py-2 [&>th]:font-medium">
            <th>risk</th><th>amount</th><th>rail</th><th>channel</th><th>auth</th><th>truth</th>
          </tr>
        </thead>
        <tbody className="font-mono">
          {rows.map((e, i) => {
            const flagged = e.risk >= threshold;
            const correct = flagged === (e.is_fraud === 1);
            return (
              <>
                <motion.tr key={e.txn_id} onClick={() => setOpenRow(openRow === e.txn_id ? null : e.txn_id)}
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: Math.min(i * 0.01, 0.3) }}
                  className={`cursor-pointer border-t border-white/[0.04] [&>td]:px-2 [&>td]:py-1.5 hover:bg-white/[0.03] ${
                    e.is_fraud ? "bg-threat/[0.03]" : ""
                  }`}>
                  <td><RiskPill risk={e.risk} threshold={threshold} /></td>
                  <td className="text-mist-200">${e.amount.toLocaleString()}</td>
                  <td className="text-mist-400">{e.rail}</td>
                  <td className={e.channel === "agent" ? "text-agentic" : "text-mist-400"}>{e.channel}</td>
                  <td className="text-mist-400">{e.auth_method}</td>
                  <td>
                    <span className={`${e.is_fraud ? "text-threat" : "text-mist-500"}`}>
                      {e.is_fraud ? e.vector : "legit"}
                    </span>
                    {!correct && <span className="ml-1 text-warn" title="misclassified">◆</span>}
                  </td>
                </motion.tr>
                <AnimatePresence>
                  {openRow === e.txn_id && e.explanation && (
                    <motion.tr initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                      <td colSpan={6} className="bg-ink-900/60 px-3 py-3">
                        <div className="mb-2 flex gap-4 text-[11px] text-mist-500">
                          <span>supervised <span className="text-mist-200">{e.supervised_prob.toFixed(3)}</span></span>
                          <span>novelty <span className="text-mist-200">{e.novelty_score.toFixed(3)}</span></span>
                          <span>tenure <span className="text-mist-200">{e.account_age_days.toFixed(0)}d</span></span>
                          <span>new payee <span className="text-mist-200">{e.is_new_counterparty ? "yes" : "no"}</span></span>
                        </div>
                        <div className="space-y-1.5">
                          {e.explanation.map((x, j) => (
                            <div key={j} className="grid grid-cols-[160px_1fr_60px] items-center gap-2">
                              <span className="truncate text-[11px] text-mist-300">{x.feature}</span>
                              <div className="relative h-1.5 rounded-full bg-white/[0.06]">
                                <div className="absolute left-1/2 h-1.5 rounded-full"
                                  style={{
                                    width: `${Math.min(50, Math.abs(x.contribution) * 12)}%`,
                                    background: x.contribution > 0 ? "#ff5c49" : "#2ed6a6",
                                    transform: x.contribution > 0 ? "none" : "translateX(-100%)",
                                  }} />
                              </div>
                              <span className="stat text-right text-[11px] text-mist-400">{x.value}</span>
                            </div>
                          ))}
                        </div>
                      </td>
                    </motion.tr>
                  )}
                </AnimatePresence>
              </>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
