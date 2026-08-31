"use client";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import { Panel, Metric, Loader, Fade, Tag } from "@/components/ui";
import { Curve, BarList } from "@/components/charts";

export function Detection() {
  const { data, loading } = useAsync(() => api.metrics(), []);
  if (loading) return <Loader label="Loading detection report" />;
  if (!data || !data.supervised) return <Panel><p className="text-sm text-mist-400">No eval report. Run <code className="font-mono text-mist-200">python scripts/train.py</code>.</p></Panel>;

  const s = data.supervised;
  const c = s.confusion;
  const op = data.operating_point;
  const pv = Object.entries(data.per_vector_recall).map(([label, v]) => ({ label, value: v.recall, note: `${v.n}` }));
  const imp = data.global_importance.slice(0, 12);
  const maxImp = Math.max(...imp.map((i) => i.importance), 1);

  return (
    <div className="space-y-5">
      <Fade>
        <div>
          <h2 className="text-lg font-semibold tracking-tight text-mist-100">Detection & explainability</h2>
          <p className="mt-1 max-w-2xl text-sm text-mist-400">
            A LightGBM gradient-boosting classifier plus an unsupervised novelty channel (isolation forest +
            PCA reconstruction) fit on legitimate traffic. Metrics are on a held-out test split of {data.n_test.toLocaleString()} events.
          </p>
        </div>
      </Fade>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
        <Metric label="ROC-AUC" tone="defense" better="higher" value={s.roc_auc.toFixed(4)} />
        <Metric label="PR-AUC" tone="defense" better="higher" value={s.pr_auc.toFixed(4)} />
        <Metric label="precision" better="higher" value={s.precision.toFixed(3)} />
        <Metric label="recall" better="higher" value={s.recall.toFixed(3)} />
        <Metric label="F1" better="higher" value={s.f1.toFixed(3)} />
        <Metric label="FPR" tone="warn" better="lower" value={`${(s.fpr * 100).toFixed(3)}%`} />
      </div>

      <Fade>
        <div className="panel flex gap-3 border-defense/15 p-4">
          <span className="mt-0.5 text-defense">ⓘ</span>
          <p className="text-[13px] leading-relaxed text-mist-300">
            <span className="font-medium text-mist-100">The scores that matter are adversarial.</span>{" "}
            In-distribution metrics sit near ceiling because first-generation campaigns carry loud structural
            signatures. The detector is judged on the harder tests: recall under live evasion (the{" "}
            <span className="text-defense">Closed Loop</span>) and recovery of a vector never seen in training
            (the novelty table below). Deepfake authorised-push payment stays the hardest vector by design.
          </p>
        </div>
      </Fade>

      {op && (
        <Panel title="Operating point - cost-aware" hint="What a fraud desk signs off: value recovered and the review workload it costs.">
          <div className="grid gap-4 sm:grid-cols-4">
            <OpStat v={`${(op.cost_optimal.value_detected_rate * 100).toFixed(1)}%`} k="fraud value caught" d="share of fraudulent $ recovered" tone="defense" />
            <OpStat v={`${op.cost_optimal.alerts_per_10k}`} k="alerts / 10k txns" d="review / step-up workload" />
            <OpStat v={s.value_detected_rate != null ? `${(s.value_detected_rate * 100).toFixed(1)}%` : "-"} k="value detected @ maxF1" d="amount-weighted recall" />
            <OpStat v={op.cost_optimal.threshold.toFixed(3)} k="cost-optimal threshold" d="min expected loss + review" />
          </div>
        </Panel>
      )}

      <div className="grid gap-5 lg:grid-cols-3">
        <Panel title="ROC curve" hint={`AUC ${s.roc_auc.toFixed(4)} · closer to the top-left corner is better`}>
          <Curve points={data.curves.roc} diagonal color="#2ed6a6" xlabel="false positive rate" ylabel="fraud caught (TPR)" />
        </Panel>
        <Panel title="Precision - Recall" hint={`AUC ${s.pr_auc.toFixed(4)} · closer to the top-right corner is better`}>
          <Curve points={data.curves.pr} color="#8b8cf0" xlabel="recall (fraud caught)" ylabel="precision" />
        </Panel>
        <Panel title="Confusion @ operating point" hint={`threshold ${s.threshold.toFixed(3)}`}>
          <div className="grid grid-cols-2 gap-2">
            <Cell label="true positive" value={c.tp} tone="defense" />
            <Cell label="false negative" value={c.fn} tone="threat" />
            <Cell label="false positive" value={c.fp} tone="warn" />
            <Cell label="true negative" value={c.tn} tone="default" />
          </div>
          <p className="mt-3 text-[11px] leading-relaxed text-mist-500">
            {c.fp} false positives on {(c.fp + c.tn).toLocaleString()} good transactions -             FPR at 90% recall is {(s.fpr_at_90_recall * 100).toFixed(3)}%.
          </p>
        </Panel>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Panel title="Per-vector recall" hint="Share of each attack type caught on the test set (higher is better). Deepfake push (DF-APP) is hardest by design.">
          <BarList items={pv} tone={(v) => (v > 0.85 ? "#2ed6a6" : v > 0.6 ? "#f5b544" : "#ff5c49")} />
        </Panel>
        <Panel title="What the model relies on" hint="How much each signal drives decisions (bigger = more influential). Device, agent-identity, velocity and graph signals lead.">
          <BarList items={imp.map((i) => ({ label: i.feature, value: i.importance }))} tone="#5ea0ff" max={maxImp}
            format={(v) => `${Math.round(v)}`} />
        </Panel>
      </div>

      {data.leave_one_out && (
        <Panel title="Catching attacks the model has never seen"
          hint="We remove one attack type entirely from training, then score it. Higher % = more of that unseen attack still caught. This is the answer to 'novel, emerging' - and where the agent-hijack vector shines.">
          <div className="mb-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-mist-500">
            <span><span className="text-mist-300">supervised</span> = trained model alone</span>
            <span><span className="text-agentic">novelty</span> = anomaly channel + agent-identity features</span>
            <span><span className="text-defense">blended</span> = combined</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-mist-500">
                <tr className="[&>th]:px-3 [&>th]:py-2 [&>th]:font-medium">
                  <th>unseen attack</th><th>supervised</th><th>novelty</th><th>blended</th>
                </tr>
              </thead>
              <tbody className="font-mono">
                {data.leave_one_out.map((r) => {
                  const star = r.vector === "AGENT-HIJACK";
                  return (
                    <tr key={r.vector} className={`border-t border-white/[0.05] [&>td]:px-3 [&>td]:py-2 ${star ? "bg-agentic/[0.06]" : ""}`}>
                      <td className={star ? "text-agentic" : "text-mist-200"}>{r.vector}{star && <span className="ml-1.5 text-[9px] uppercase tracking-wider text-agentic">new vector</span>}</td>
                      <td className={r.supervised_recall < 0.5 ? "text-threat" : "text-mist-300"}>{(r.supervised_recall * 100).toFixed(0)}%</td>
                      <td className="text-agentic">{(r.novelty_recall * 100).toFixed(0)}%</td>
                      <td className="text-defense">{(r.blended_recall * 100).toFixed(0)}%</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Panel>
      )}
    </div>
  );
}

function OpStat({ v, k, d, tone = "default" }: { v: string; k: string; d: string; tone?: "defense" | "default" }) {
  return (
    <div>
      <div className="label">{k}</div>
      <div className={`stat mt-1 text-2xl font-semibold ${tone === "defense" ? "text-defense" : "text-mist-100"}`}>{v}</div>
      <div className="mt-1 text-[11px] text-mist-500">{d}</div>
    </div>
  );
}

function Cell({ label, value, tone }: { label: string; value: number; tone: "defense" | "threat" | "warn" | "default" }) {
  const map = { defense: "text-defense", threat: "text-threat", warn: "text-warn", default: "text-mist-300" } as const;
  return (
    <div className="panel p-3">
      <div className="label">{label}</div>
      <div className={`stat mt-1 text-xl font-semibold ${map[tone]}`}>{value.toLocaleString()}</div>
    </div>
  );
}
