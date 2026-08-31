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
              A single-stage attack trips loud, obvious signals. A patient adversary chains stages so the
              cash-out inherits none of them. Here two attacks are linked end-to-end - and it is the one place a
              well-tuned chain can still slip past the <span className="text-mist-200">supervised</span> model.
              The point is what stops it anyway.
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
          <div className="mt-4 rounded-lg border border-warn/20 bg-warn/[0.04] p-3 text-xs leading-relaxed text-mist-400">
            <span className="font-medium text-mist-200">Read the rows honestly.</span> The first two use the
            shipped detector; the third is a detector <span className="text-mist-200">retrained</span> on the chain
            and scored on a <span className="text-mist-200">fresh</span> chained holdout. So the real before/after
            of retraining is the chained row versus it (supervised {pct(chains.chained.supervised_only)} →{" "}
            {pct(chains.chained_after_retrain.supervised_only)}), not against the easy single-stage{" "}
            {pct(chains.single_stage_cold.full_ensemble)}.
          </div>
        </Panel>
      </Fade>

      {/* The finding */}
      <Fade delay={0.25}>
        <Panel title="Why this is on-thesis, not a weakness">
          <p className="text-sm leading-relaxed text-mist-300">
            {chains.finding ??
              "The chain evades the supervised classifier; the novelty channel still catches it, and retraining restores the supervised channel."}
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <Takeaway
              tone="threat"
              title="Chaining is a genuine evasion"
              body={`The aged, low-signal cash-out strips the tenure and velocity cues a cold ring would trip - supervised recall collapses ${pct(chains.single_stage_cold.supervised_only)} → ${pct(chains.chained.supervised_only)}.`}
            />
            <Takeaway
              tone="defense"
              title="Two channels + the loop are the answer"
              body={`The novelty channel keeps it from going to zero (${pct(chains.chained.full_ensemble)}), and retraining lifts the supervised channel back to ${pct(chains.chained_after_retrain.supervised_only)}. The same lesson as the agent-hijack result, now on a multi-stage threat.`}
            />
          </div>
          <p className="mt-4 text-xs leading-relaxed text-mist-500">
            Marked <span className="text-warn">beta</span> because the chain is a scripted two-stage probe, not
            yet driven by the evolutionary evasion search - the honest status, stated plainly. It is isolated from
            the shipped pipeline and does not affect the headline numbers.
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
