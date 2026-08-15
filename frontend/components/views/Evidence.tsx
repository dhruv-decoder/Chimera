"use client";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import { Panel, Metric, Bar, Fade, Loader, Tag } from "@/components/ui";

const pct = (x?: number, d = 0) => (x == null ? " - " : `${(x * 100).toFixed(d)}%`);
const f = (x?: number, d = 2) => (x == null ? " - " : x.toFixed(d));

export function Evidence() {
  const v = useAsync(() => api.validation(), []);
  const ext = v.data?.external;
  const gnn = v.data?.gnn;
  const pit = v.data?.point_in_time;
  const rig = v.data?.rigor;
  const bench = v.data?.benchmark;

  const chains = v.data?.attack_chains;
  const seeds = rig?.stability_across_seeds;
  const abl = rig?.component_ablation || {};
  const lat = rig?.latency;
  const loopReal = bench?.closed_loop_on_real;
  const baselines = bench?.baselines || {};
  // order baselines by pr_auc, tag Chimera
  const rows = Object.entries(baselines)
    .map(([k, m]) => ({ name: k, pr: m.pr_auc, mine: k.toLowerCase().includes("chimera") }))
    .sort((a, b) => b.pr - a.pr);
  const maxPr = Math.max(0.001, ...rows.map((r) => r.pr));

  if (v.loading) return <Loader label="Loading validation" />;

  return (
    <div className="space-y-6">
      <Fade>
        <div className="panel relative overflow-hidden p-7">
          <div className="absolute right-0 top-0 h-40 w-40 animate-pulseSoft rounded-full bg-signal/10 blur-3xl" />
          <div className="relative">
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <Tag tone="defense">real fraud data</Tag>
              <Tag tone="agentic">graph neural network</Tag>
              <Tag tone="warn">evaluation rigor</Tag>
            </div>
            <h1 className="max-w-3xl text-2xl font-semibold leading-tight tracking-tight text-mist-100 sm:text-[28px]">
              Validated beyond the synthetic benchmark.
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-mist-400">
              The same detector, unchanged, on a real public fraud dataset; a graph
              neural network that proves structure matters; and the audits a fraud-ML
              reviewer would run. Every number here is precomputed and reproducible
              from <code className="font-mono text-mist-300">scripts/</code>.
            </p>
          </div>
        </div>
      </Fade>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Fade delay={0.05}>
          <Metric label="Real ULB · ROC-AUC" tone="defense" better="higher"
            value={f(ext?.supervised?.roc_auc)} sub="same ensemble, real card fraud" />
        </Fade>
        <Fade delay={0.1}>
          <Metric label="Real ULB · PR-AUC" tone="defense" better="higher"
            value={f(ext?.supervised?.pr_auc)} sub="in line with published baselines" />
        </Fade>
        <Fade delay={0.15}>
          <Metric label="GNN ring PR-AUC" tone="agentic" better="higher"
            value={`${f(gnn?.gradient_boosting?.pr_auc)} → ${f(gnn?.graphsage_gnn?.pr_auc, 3)}`}
            sub={gnn?.graphsage_inductive
              ? `+${f(gnn?.pr_auc_lift)} vs boosting · holds inductively (${f(gnn.graphsage_inductive.pr_auc, 3)}, no leakage)`
              : `+${f(gnn?.pr_auc_lift)} over gradient boosting (simulated rings)`} />
        </Fade>
        <Fade delay={0.2}>
          <Metric label="Point-in-time · PR-AUC" better="higher"
            value={f(pit?.causal?.pr_auc, 3)}
            sub={`vs ${f(pit?.batch?.pr_auc, 3)} batch · no look-ahead`} />
        </Fade>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
        <Panel title="Baselines on real fraud (ULB, held-out)"
          hint="Standard models vs Chimera's ensemble. Competitive, not superior - the contribution is the loop, not a better static classifier.">
          <div className="space-y-3">
            {rows.map((r) => (
              <div key={r.name} className="grid grid-cols-[130px_1fr_48px] items-center gap-3">
                <span className={`truncate text-xs ${r.mine ? "text-agentic" : "text-mist-400"}`}>{r.name.replace(" (two-channel)", "")}</span>
                <Bar value={r.pr / maxPr} tone={r.mine ? "agentic" : "signal"} />
                <span className="stat text-right text-xs text-mist-300">{f(r.pr)}</span>
              </div>
            ))}
          </div>
          <p className="mt-4 text-xs leading-relaxed text-mist-500">
            {ext ? `${ext.n.toLocaleString()} real transactions · ${ext.n_fraud} fraud (${(ext.fraud_rate * 100).toFixed(3)}%). ` : ""}
            PR-AUC shown (the right metric under heavy imbalance).
          </p>
        </Panel>

        <Panel title="The loop transfers to real fraud"
          hint="Perturb real ULB fraud toward the legit distribution (evasion), then retrain on the evasive samples.">
          <div className="space-y-4">
            <LoopStep label="Baseline recall" value={loopReal?.baseline_recall} tone="defense" />
            <LoopStep label="Under evasion" value={loopReal?.under_evasion} tone="threat" />
            <LoopStep label="After retrain" value={loopReal?.after_retrain} tone="defense" />
          </div>
          <p className="mt-4 text-xs leading-relaxed text-mist-500">
            {loopReal
              ? `Recall drops ${pct(loopReal.baseline_recall)} → ${pct(loopReal.under_evasion)} under evasion, then recovers to ${pct(loopReal.after_retrain)} at the same operating threshold. The methodology does not depend on the synthetic simulator.`
              : "run scripts/benchmark_baselines.py to populate."}
          </p>
        </Panel>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.15fr_1fr]">
        <Panel title="Evaluation rigor"
          hint="The audits a fraud-ML reviewer would ask for. All reproducible; artifacts in data/artifacts/.">
          <div className="space-y-3">
            <RigorRow name="Point-in-time (no look-ahead)"
              detail={`Structural features rebuilt causally. PR-AUC ${f(pit?.batch?.pr_auc, 3)} → ${f(pit?.causal?.pr_auc, 3)}, recall ${f(pit?.batch?.recall, 3)} → ${f(pit?.causal?.recall, 3)}. Not a leakage artifact.`} />
            <RigorRow name="Stability across seeds"
              detail={seeds ? `${seeds.seeds.length} seeds: ROC-AUC ${f(seeds.roc_auc.mean)} ±${f(seeds.roc_auc.std, 3)}, recall ${f(seeds.recall.mean, 3)} ±${f(seeds.recall.std, 3)}. Not seed-dependent.` : " - "} />
            <RigorRow name="Component ablation"
              detail={`Held-out PR-AUC ${f(abl["event+velocity"]?.pr_auc)} (event+velocity) → ${f(abl["+ graph"]?.pr_auc, 3)} once graph features are added. The graph is the decisive lift.`} />
            <RigorRow name="Throughput (single-process CPU)"
              detail={lat ? `${(lat.generation_events_per_sec / 1000).toFixed(1)}k events/s generated · ${(lat.feature_build_events_per_sec / 1000).toFixed(1)}k/s features · ${(lat.inference_events_per_sec / 1000).toFixed(1)}k/s scored.` : " - "} />
          </div>
        </Panel>

        <Panel title="Datasets · benchmarks · models"
          hint="What this evidence is built on, and where to reproduce it.">
          <div className="space-y-3">
            <RefRow tone="defense" name="ULB Credit-Card Fraud"
              detail="284,807 real European card transactions, 492 fraud. Kaggle mlg-ulb/creditcardfraud (OpenML 1597)." />
            <RefRow tone="agentic" name="gpt-oss-120b / 20b (open-weight)"
              detail="OpenAI open models via Groq, drive the RAG ideation agent." />
            <RefRow tone="signal" name="LightGBM · GraphSAGE · IsolationForest+PCA"
              detail="Gradient boosting + a 2-layer GNN (PyTorch) + a novelty channel. Baselines: LogReg, RandomForest, XGBoost." />
            <RefRow tone="warn" name="Reproduce"
              detail="make validate · make gnn · scripts/rigor.py · notebooks/external_benchmark.ipynb." />
          </div>
        </Panel>
      </div>

      {chains && (
        <Panel title="Combined attack chains"
          right={<span className="chip border border-warn/30 bg-warn/5 text-warn">beta</span>}
          hint="A synthetic-identity bust-out ages accounts that then run a low-observability cash-out. Does chaining evade, and does the loop recover? Recall on the stage-2 fraud at a matched 1% alert budget.">
          <div className="space-y-2.5">
            <div className="grid grid-cols-[1.4fr_1fr_1fr] items-center gap-3 text-[11px] text-mist-500">
              <span>scenario</span><span className="text-right">supervised only</span><span className="text-right">full ensemble</span>
            </div>
            <ChainRow label="single-stage (cold)" sup={chains.single_stage_cold.supervised_only} full={chains.single_stage_cold.full_ensemble} />
            <ChainRow label="chained (aged bust-out)" sup={chains.chained.supervised_only} full={chains.chained.full_ensemble} evaded />
            <ChainRow label="chained, after retrain" sup={chains.chained_after_retrain.supervised_only} full={chains.chained_after_retrain.full_ensemble} />
          </div>
          <p className="mt-4 text-xs leading-relaxed text-mist-500">
            Chaining evades the supervised classifier ({pct(chains.single_stage_cold.supervised_only)} → {pct(chains.chained.supervised_only)}); the novelty channel is the safety net ({pct(chains.chained.full_ensemble)}), and retraining lifts both channels. The last row is a fresh holdout scored by the retrained detector, so the honest before/after is the chained row vs it (not the easy single-stage 100%). The two-channel design and the loop both earn their keep against a multi-stage threat.
          </p>
        </Panel>
      )}
    </div>
  );
}

function ChainRow({ label, sup, full, evaded }: { label: string; sup: number; full: number; evaded?: boolean }) {
  return (
    <div className="grid grid-cols-[1.4fr_1fr_1fr] items-center gap-3">
      <span className="text-xs text-mist-300">{label}</span>
      <span className={`stat text-right text-sm ${evaded ? "text-threat" : "text-mist-200"}`}>{pct(sup)}</span>
      <span className="stat text-right text-sm text-defense">{pct(full)}</span>
    </div>
  );
}

function LoopStep({ label, value, tone }: { label: string; value?: number; tone: "defense" | "threat" }) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="text-mist-400">{label}</span>
        <span className={`stat ${tone === "threat" ? "text-threat" : "text-defense"}`}>{pct(value)}</span>
      </div>
      <Bar value={value ?? 0} tone={tone} height={8} />
    </div>
  );
}

function RigorRow({ name, detail }: { name: string; detail: string }) {
  return (
    <div className="flex gap-3">
      <div className="mt-1 h-2 w-2 shrink-0 rounded-full bg-defense" />
      <div>
        <div className="text-sm font-medium text-mist-100">{name}</div>
        <div className="text-xs leading-relaxed text-mist-500">{detail}</div>
      </div>
    </div>
  );
}

function RefRow({ tone, name, detail }: { tone: "defense" | "agentic" | "signal" | "warn"; name: string; detail: string }) {
  const c = { defense: "bg-defense", agentic: "bg-agentic", signal: "bg-signal", warn: "bg-warn" }[tone];
  return (
    <div className="flex gap-3">
      <div className={`mt-1 h-2 w-2 shrink-0 rounded-full ${c}`} />
      <div>
        <div className="text-sm font-medium text-mist-100">{name}</div>
        <div className="text-xs leading-relaxed text-mist-500">{detail}</div>
      </div>
    </div>
  );
}
