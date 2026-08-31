"use client";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import { Panel, Metric, Fade, Loader, Tag } from "@/components/ui";
import { HardeningCurve } from "@/components/charts";

export function Overview() {
  const metrics = useAsync(() => api.metrics(), []);
  const loop = useAsync(() => api.loop(), []);
  const meta = useAsync(() => api.simMeta(), []);

  const s = metrics.data?.supervised;
  const curve = loop.data?.hardening_curve;
  // Show the round with the deepest breach - that is where the loop earns its keep.
  const lastRound = curve && curve.length
    ? curve.reduce((a, b) => (b.pre_recall < a.pre_recall ? b : a))
    : undefined;

  return (
    <div className="space-y-6">
      <Fade>
        <div className="panel relative overflow-hidden p-7">
          <div className="absolute right-0 top-0 h-40 w-40 animate-pulseSoft rounded-full bg-defense/10 blur-3xl" />
          <div className="relative">
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <Tag tone="defense">closed-loop red team / blue team</Tag>
              <Tag tone="agentic">GenAI-era fraud</Tag>
            </div>
            <h1 className="max-w-3xl text-2xl font-semibold leading-tight tracking-tight text-mist-100 sm:text-[28px]">
              Discover emerging payment fraud, simulate it at fidelity, and harden a detector on what it misses.
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-mist-400">
              An AI red team evolves evasive fraud against a live detector across card-not-present,
              real-time account-to-account, and agentic-commerce rails. Every attack it discovers
              becomes training data for the defence - a single feedback loop across all three pillars.
            </p>
          </div>
        </div>
      </Fade>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Fade delay={0.05}><Metric label="ROC-AUC" tone="defense" better="higher" value={s ? s.roc_auc.toFixed(4) : " - "} sub="ranks fraud above legit" /></Fade>
        <Fade delay={0.1}><Metric label="PR-AUC" tone="defense" better="higher" value={s ? s.pr_auc.toFixed(4) : " - "} sub="precision under 1.4% fraud rate" /></Fade>
        <Fade delay={0.15}><Metric label="F1 @ max-F1" better="higher" value={s ? s.f1.toFixed(3) : " - "} sub={s ? `precision ${s.precision.toFixed(3)} · recall ${s.recall.toFixed(3)}` : ""} /></Fade>
        <Fade delay={0.2}><Metric label="FPR @ operating point" tone="warn" better="lower" value={s ? `${(s.fpr * 100).toFixed(3)}%` : " - "} sub={s && s.confusion ? `${s.confusion.fp} of ${(s.confusion.fp + s.confusion.tn).toLocaleString()} good txns flagged` : "good customers wrongly flagged"} /></Fade>
      </div>

      <Fade delay={0.25}>
        <div className="panel flex gap-3 border-defense/15 p-4">
          <span className="mt-0.5 text-defense">ⓘ</span>
          <p className="text-[13px] leading-relaxed text-mist-300">
            <span className="font-medium text-mist-100">Why these numbers look perfect - and why that is not the point.</span>{" "}
            First-generation campaigns carry loud structural signatures, so a strong model scores near-perfect
            in-distribution. The two honest tests are how the detector holds up when the red team evolves evasion
            (the <span className="text-defense">Closed Loop</span> below) and how it recovers a vector it has never
            seen (<span className="text-defense">Detection</span>); on real public fraud the same ensemble scores a
            credible ROC 0.95 (<span className="text-defense">Validation</span>). One vector, deepfake authorised
            push, stays hard by design.
          </p>
        </div>
      </Fade>

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <Panel title="Adversarial hardening curve"
          hint="Each round the red team evolves evasion (recall drops); retraining on the new samples recovers it.">
          {loop.loading ? <Loader label="Loading loop" /> : curve ? (
            <>
              <HardeningCurve data={curve} />
              <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1 text-xs">
                <span className="flex items-center gap-2 text-threat"><span className="h-[2px] w-5 bg-threat" style={{ borderTop: "2px dashed" }} />fraud slipping past (before retrain)</span>
                <span className="flex items-center gap-2 text-defense"><span className="h-[2px] w-5 bg-defense" />fraud caught (after retrain)</span>
              </div>
            </>
          ) : <p className="text-sm text-mist-500">Run <code className="font-mono text-mist-300">scripts/run_loop.py</code> to populate.</p>}
        </Panel>

        <Panel title="Pillars" hint="One system, three responsibilities.">
          <div className="space-y-3">
            <PillarRow color="agentic" name="Identify" desc={`${meta.data ? Object.keys(meta.data.per_vector || {}).length : " - "} simulated vectors, mapped to an ATT&CK-style matrix + RAG intel`} />
            <PillarRow color="threat" name="Generate" desc={meta.data ? `${meta.data.n_total?.toLocaleString()} events · ${(meta.data.fraud_rate * 100).toFixed(2)}% fraud · hard negatives injected` : "realistic multi-rail simulation"} />
            <PillarRow color="defense" name="Defend" desc="LightGBM + novelty channel (isolation forest + PCA) with per-event SHAP reason codes" />
            <div className="panel mt-1 p-3">
              <div className="label mb-1">Loop outcome · worst round</div>
              <div className="stat text-sm text-mist-200">
                {lastRound ? (
                  <>attack got recall down to <span className="text-threat">{(lastRound.pre_recall * 100).toFixed(1)}%</span> → retrain recovered to <span className="text-defense">{(lastRound.post_recall * 100).toFixed(1)}%</span></>
                ) : " - "}
              </div>
            </div>
          </div>
        </Panel>
      </div>
    </div>
  );
}

function PillarRow({ color, name, desc }: { color: "agentic" | "threat" | "defense"; name: string; desc: string }) {
  const c = { agentic: "bg-agentic", threat: "bg-threat", defense: "bg-defense" }[color];
  return (
    <div className="flex gap-3">
      <div className={`mt-1 h-2 w-2 shrink-0 rounded-full ${c}`} />
      <div>
        <div className="text-sm font-medium text-mist-100">{name}</div>
        <div className="text-xs leading-relaxed text-mist-500">{desc}</div>
      </div>
    </div>
  );
}
