"use client";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import { Panel, Metric, Bar, Fade, Loader, Tag } from "@/components/ui";

const pct = (x?: number, d = 0) => (x == null ? " - " : `${(x * 100).toFixed(d)}%`);

export function AttackChains() {
  const v = useAsync(() => api.validation(), []);
  const chains = v.data?.attack_chains;

  if (v.loading) return <Loader label="Loading attack chains" />;
  if (!chains)
    return (
      <Panel>
        <p className="text-sm text-mist-400">
          No chain report yet. Run <code className="font-mono text-mist-200">make chains</code> (or{" "}
          <code className="font-mono text-mist-200">python scripts/attack_chains.py</code>) to populate.
        </p>
      </Panel>
    );

  const supDrop = chains.single_stage_cold.supervised_only - chains.chained.supervised_only;

  return (
    <div className="space-y-6">
      <Fade>
        <div className="panel relative overflow-hidden p-7">
          <div className="absolute right-0 top-0 h-40 w-40 animate-pulseSoft rounded-full bg-threat/10 blur-3xl" />
          <div className="relative">
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <Tag tone="threat">multi-stage campaign</Tag>
              <span className="chip border border-warn/40 bg-warn/10 font-semibold text-warn">BETA</span>
            </div>
            <h1 className="max-w-3xl text-2xl font-semibold leading-tight tracking-tight text-mist-100 sm:text-[28px]">
              Real fraud is rarely one technique. It is a chain.
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-mist-400">
              A single-stage attack trips loud, obvious signals. A patient adversary chains stages so the final
              cash-out carries none of them. Chimera links two techniques end to end and measures whether the
              defence holds against the combined campaign.
            </p>
          </div>
        </div>
      </Fade>

      {/* Two-stage kill chain */}
      <Fade delay={0.05}>
        <Panel title="The chain" hint="Two attacks, linked. Stage 2 is scored - it is the transaction the bank actually sees.">
          <div className="grid items-stretch gap-3 sm:grid-cols-[1fr_auto_1fr]">
            <Stage
              n={1}
              tone="agentic"
              name="Synthetic-identity bust-out"
              body="Fabricated identities open low-KYC accounts and age quietly, building a benign history over weeks - no fraud signal to trip yet."
            />
            <div className="flex items-center justify-center text-2xl text-mist-600 sm:px-1" aria-hidden>
              →
            </div>
            <Stage
              n={2}
              tone="threat"
              name="Low-observability authorised-push cash-out"
              body="Those aged accounts now run an authorised-push-style cash-out to ordinary payees. No young-account tenure, no velocity burst - the usual cues are gone."
            />
          </div>
          <p className="mt-4 text-xs leading-relaxed text-mist-500">
            {chains.note ??
              "Recall on the stage-2 fraud, reported for the supervised classifier alone vs the full two-channel ensemble, at a matched ~1% legit alert budget."}
          </p>
        </Panel>
      </Fade>

      {/* Headline metrics */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
        <Fade delay={0.1}>
          <Metric
            label="supervised recall, chained"
            tone="threat"
            better="higher"
            value={pct(chains.chained.supervised_only)}
            sub={`down from ${pct(chains.single_stage_cold.supervised_only)} single-stage (−${pct(supDrop)})`}
          />
        </Fade>
        <Fade delay={0.15}>
          <Metric
            label="novelty channel holds it"
            tone="defense"
            better="higher"
            value={pct(chains.chained.full_ensemble)}
            sub="the safety net when the classifier is blind"
          />
        </Fade>
        <Fade delay={0.2}>
          <Metric
            label="after retrain (fresh holdout)"
            tone="defense"
            better="higher"
            value={pct(chains.chained_after_retrain.supervised_only)}
            sub="supervised channel restored by the loop"
          />
        </Fade>
      </div>

      {/* Evasion + recovery table */}
      <Fade delay={0.2}>
        <Panel
          title="Does chaining evade - and does the loop recover?"
          right={<span className="chip border border-warn/30 bg-warn/5 text-warn">beta</span>}
          hint="Recall on stage-2 fraud at a matched ~1% alert budget. Red = the supervised model going blind.">
          <div className="space-y-2.5">
            <div className="grid grid-cols-[1.5fr_1fr_1fr] items-center gap-3 text-[11px] text-mist-500">
              <span>scenario</span>
              <span className="text-right">supervised only</span>
              <span className="text-right">full ensemble</span>
            </div>
            <ChainRow
              label="single-stage (cold accounts)"
              sup={chains.single_stage_cold.supervised_only}
              full={chains.single_stage_cold.full_ensemble}
            />
            <ChainRow
              label="chained (aged bust-out)"
              sup={chains.chained.supervised_only}
              full={chains.chained.full_ensemble}
              evaded
            />
            <ChainRow
              label="chained, after retrain"
              sup={chains.chained_after_retrain.supervised_only}
              full={chains.chained_after_retrain.full_ensemble}
            />
          </div>
          <p className="mt-4 text-xs leading-relaxed text-mist-500">
            Rows 1 and 2 use the deployed detector; row 3 is retrained on the chain and evaluated on a held-out
            chained sample. Retraining lifts supervised recall from {pct(chains.chained.supervised_only)} to{" "}
            {pct(chains.chained_after_retrain.supervised_only)}.
          </p>
        </Panel>
      </Fade>

      {/* The result */}
      <Fade delay={0.25}>
        <Panel title="What the chain proves">
          <p className="text-sm leading-relaxed text-mist-300">
            {chains.finding ??
              "Chaining strips the account-tenure and velocity signals a single-stage ring trips, and supervised recall collapses. The novelty channel contains the attack, and one retraining cycle restores the supervised channel."}
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <Takeaway
              tone="threat"
              title="Chaining defeats the supervised model"
              body={`The aged, low-signal cash-out removes the tenure and velocity cues a cold ring trips, and supervised recall falls ${pct(chains.single_stage_cold.supervised_only)} → ${pct(chains.chained.supervised_only)}.`}
            />
            <Takeaway
              tone="defense"
              title="The architecture holds"
              body={`The novelty channel contains it at ${pct(chains.chained.full_ensemble)}, and one retraining cycle restores supervised recall to ${pct(chains.chained_after_retrain.supervised_only)} - the same result as the agent-hijack defence, now against a multi-stage campaign.`}
            />
          </div>
          <p className="mt-4 text-xs leading-relaxed text-mist-500">
            Beta: a scripted two-stage probe, run in isolation from the production pipeline. Driving it directly
            from the evolutionary evasion search is the next iteration.
          </p>
        </Panel>
      </Fade>
    </div>
  );
}

function Stage({ n, tone, name, body }: { n: number; tone: "agentic" | "threat"; name: string; body: string }) {
  const c = tone === "agentic" ? "#8b8cf0" : "#ff5c49";
  return (
    <div className="rounded-xl border p-4" style={{ borderColor: `${c}44`, background: `${c}0d` }}>
      <div className="flex items-center gap-2.5">
        <span
          className="grid h-6 w-6 place-items-center rounded-lg text-xs font-semibold"
          style={{ background: `${c}22`, color: c }}>
          {n}
        </span>
        <span className="text-sm font-semibold text-mist-100">{name}</span>
      </div>
      <p className="mt-2 text-[12px] leading-relaxed text-mist-400">{body}</p>
    </div>
  );
}

function ChainRow({ label, sup, full, evaded }: { label: string; sup: number; full: number; evaded?: boolean }) {
  return (
    <div className="grid grid-cols-[1.5fr_1fr_1fr] items-center gap-3">
      <span className="text-xs text-mist-300">{label}</span>
      <div className="flex items-center justify-end gap-2">
        <div className="hidden w-16 sm:block">
          <Bar value={sup} tone={evaded ? "threat" : "signal"} height={6} />
        </div>
        <span className={`stat w-10 text-right text-sm ${evaded ? "text-threat" : "text-mist-200"}`}>{pct(sup)}</span>
      </div>
      <div className="flex items-center justify-end gap-2">
        <div className="hidden w-16 sm:block">
          <Bar value={full} tone="defense" height={6} />
        </div>
        <span className="stat w-10 text-right text-sm text-defense">{pct(full)}</span>
      </div>
    </div>
  );
}

function Takeaway({ tone, title, body }: { tone: "threat" | "defense"; title: string; body: string }) {
  const c = tone === "threat" ? "border-threat/20 bg-threat/[0.04]" : "border-defense/20 bg-defense/[0.04]";
  const t = tone === "threat" ? "text-threat" : "text-defense";
  return (
    <div className={`rounded-lg border p-3 ${c}`}>
      <div className={`text-xs font-semibold ${t}`}>{title}</div>
      <p className="mt-1 text-[12px] leading-relaxed text-mist-400">{body}</p>
    </div>
  );
}
