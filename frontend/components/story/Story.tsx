"use client";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import { Wordmark } from "@/components/brand";
import { Counter, LoopDiagram, RecallBars, Reveal } from "@/components/story/bits";
import { LoopScrolly } from "@/components/story/LoopScrolly";

type Launch = (view?: string) => void;

const DEFAULT_CURVE = [
  { round: 0, pre_recall: 0.729, post_recall: 0.729 },
  { round: 1, pre_recall: 0.192, post_recall: 0.829 },
  { round: 2, pre_recall: 0.337, post_recall: 0.996 },
  { round: 3, pre_recall: 0.996, post_recall: 0.991 },
];

export function Story({ onLaunch }: { onLaunch: Launch }) {
  const loop = useAsync(() => api.loop(), []);
  const metrics = useAsync(() => api.metrics(), []);
  const meta = useAsync(() => api.simMeta(), []);

  const curve = (loop.data?.hardening_curve as any) || DEFAULT_CURVE;
  const round1 = curve.find((c: any) => c.round === 1) || DEFAULT_CURVE[1];
  const s = metrics.data?.supervised;
  const loo = metrics.data?.leave_one_out?.find((r) => r.vector === "AGENT-HIJACK");
  const op = metrics.data?.operating_point?.cost_optimal;

  return (
    <div className="relative z-10">
      <StoryNav onLaunch={onLaunch} />
      <Hero onLaunch={onLaunch} r1={round1} />
      <HowItWorks />
      <Problem />
      <Threats onLaunch={onLaunch} />

      {/* The proof, told round by round */}
      <div id="proof" className="mx-auto max-w-6xl px-6">
        <Reveal className="mx-auto max-w-2xl pb-2 pt-12 text-center">
          <div className="label text-defense">The winning view · how to read this chart</div>
          <h2 className="display mt-3 text-display-sm">A static score measures yesterday. The hardening curve measures whether the loop actually closes.</h2>
          <p className="mx-auto mt-3 max-w-xl text-[13px] text-mist-500">
            Everyone can post an AUC. Almost no one shows their detector break under a live adversary and recover.
            This one chart is the whole thesis.
          </p>
          <p className="lede mx-auto mt-4 max-w-2xl text-[15px]">
            Scroll down. The <span className="font-medium text-threat">red line</span> is fraud slipping past the
            detector as the attacker evolves against it (falling = getting worse). The{" "}
            <span className="font-medium text-defense">green line</span> is the same detector after we retrain it
            on whatever broke through (rising = getting stronger).
          </p>
        </Reveal>
      </div>
      <LoopScrolly curve={curve} />

      <Agentic loo={loo} onLaunch={onLaunch} />
      <Feasibility s={s} op={op} meta={meta.data} />
      <TechStack />
      <FinalCTA onLaunch={onLaunch} />
      <Footer />
    </div>
  );
}

/* ----------------------------- nav ----------------------------- */
function StoryNav({ onLaunch }: { onLaunch: Launch }) {
  return (
    <header className="sticky top-0 z-30 border-b border-white/[0.06] bg-ink-950/70 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <Wordmark />
        <div className="flex items-center gap-3">
          <span className="chip hidden sm:inline-flex">Mastercard Innovation Challenge · GFF 2026</span>
          <button onClick={() => onLaunch("overview")} className="btn btn-accent py-2">
            Launch console <span aria-hidden>→</span>
          </button>
        </div>
      </div>
    </header>
  );
}

/* Primary call-to-action: a glowing button with a nudging arrow. */
function ConsoleCTA({ onLaunch, label, view = "overview" }: { onLaunch: Launch; label: string; view?: string }) {
  return (
    <button onClick={() => onLaunch(view)} className="group relative inline-flex items-center gap-2 overflow-hidden rounded-xl border border-defense/40 bg-defense/15 px-5 py-2.5 text-sm font-semibold text-defense transition-all hover:border-defense/70 hover:bg-defense/25 active:scale-[0.98]">
      <span className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-defense/20 to-transparent transition-transform duration-1000 group-hover:translate-x-full" />
      <span className="absolute inset-0 rounded-xl ring-1 ring-defense/30 animate-pulseSoft" />
      <span className="relative">{label}</span>
      <span aria-hidden className="relative transition-transform duration-300 group-hover:translate-x-1">→</span>
    </button>
  );
}

/* ----------------------------- hero ----------------------------- */
function Hero({ onLaunch, r1 }: { onLaunch: Launch; r1: any }) {
  const pre = Math.round(r1.pre_recall * 100);
  const post = Math.round(r1.post_recall * 100);
  return (
    <section className="relative overflow-hidden">
      <div className="mx-auto grid max-w-6xl items-center gap-10 px-6 pb-20 pt-16 lg:grid-cols-[1.15fr_0.85fr] lg:pt-24">
        <div>
          <Reveal>
            <div className="mb-5 flex flex-wrap items-center gap-2">
              <span className="chip border-defense/25 text-defense">closed-loop red team / blue team</span>
              <span className="chip border-agentic/25 text-agentic">GenAI-era payment fraud</span>
            </div>
          </Reveal>
          <Reveal delay={0.05}>
            <h1 className="display text-display-lg">
              Fraud that learns needs a defense that <span className="text-defense">learns back</span>.
            </h1>
          </Reveal>
          <Reveal delay={0.12}>
            <p className="lede mt-6 max-w-xl text-lg leading-relaxed">
              Chimera is one system that discovers emerging GenAI payment-fraud vectors, simulates them
              at fidelity across card, real-time A2A and agentic-commerce rails, and hardens a detector on
              exactly what breaks through. The attacks it generates become the training data for its own defense.
            </p>
          </Reveal>
          <Reveal delay={0.2}>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <ConsoleCTA onLaunch={onLaunch} label="Open the live console" />
              <a href="#proof" className="btn">See the loop close</a>
            </div>
          </Reveal>
          <Reveal delay={0.28}>
            <div className="mt-10 flex items-center gap-6">
              <div>
                <div className="stat text-3xl font-semibold text-threat">{pre}%</div>
                <div className="mt-1 text-xs text-mist-500">recall under live evasion</div>
              </div>
              <div className="h-8 w-px bg-white/10" />
              <div>
                <div className="stat text-3xl font-semibold text-defense">{post}%</div>
                <div className="mt-1 text-xs text-mist-500">after one retrain</div>
              </div>
              <div className="h-8 w-px bg-white/10" />
              <div>
                <div className="stat text-3xl font-semibold text-mist-100">9</div>
                <div className="mt-1 text-xs text-mist-500">simulated vectors</div>
              </div>
            </div>
          </Reveal>
        </div>
        <Reveal delay={0.2} className="hidden justify-center lg:flex">
          <div className="animate-float"><LoopDiagram /></div>
        </Reveal>
      </div>
      <Ticker />
    </section>
  );
}

const TICKER = [
  "Visa: 450%+ rise in dark-web “AI agent” chatter, H1 2026",
  "India: 524,121 mule accounts flagged, March 2026",
  "Visa: 25% rise in malicious bot-initiated payments",
  "Mastercard Agent Pay · Visa Trusted Agent Protocol - delegated agent credentials",
  "APP scams: the fraud the victim authorises themselves",
];
function Ticker() {
  const row = [...TICKER, ...TICKER];
  return (
    <div className="border-y border-white/[0.06] bg-white/[0.015] py-3">
      <div className="relative overflow-hidden">
        <div className="flex w-max animate-ticker gap-10 whitespace-nowrap pr-10">
          {row.map((t, i) => (
            <span key={i} className="flex items-center gap-3 text-[12px] text-mist-400">
              <span className="h-1 w-1 rounded-full bg-defense/70" />{t}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ----------------------------- problem ----------------------------- */
function Problem() {
  const cards = [
    { v: 450, suffix: "%+", c: "#8b8cf0", k: "AI-agent chatter", d: "Rise in dark-web posts mentioning “AI Agent” in six months (Visa). A brand-new, machine-speed attack surface.", src: "Visa" },
    { v: 524121, c: "#ff5c49", k: "mule accounts", d: "Suspected money-mule accounts flagged in India in a single month, March 2026. Real-time rails move funds in seconds.", src: "NPCI / MuleHunter.AI" },
    { v: 25, suffix: "%", c: "#f5b544", k: "malicious bot payments", d: "Rise in malicious bot-initiated transactions over six months as agentic checkout scales (Visa).", src: "Visa" },
  ];
  return (
    <section className="mx-auto max-w-6xl px-6 py-24">
      <Reveal className="max-w-3xl">
        <div className="label text-threat">The problem</div>
        <h2 className="display mt-3 text-display">GenAI made fraud fast, cheap, and adaptive. Static defenses decay the moment the attacker changes shape.</h2>
        <p className="lede mt-5 max-w-2xl">
          A model tuned on last quarter's fraud is a snapshot of a moving target. The challenge is not a better
          snapshot - it is a system that keeps up when an adversary evolves against it.
        </p>
      </Reveal>
      <div className="mt-12 grid gap-5 md:grid-cols-3">
        {cards.map((c, i) => (
          <Reveal key={c.k} delay={i * 0.08}>
            <div className="group relative h-full overflow-hidden rounded-2xl border border-white/[0.07] bg-white/[0.024] p-6 shadow-panel transition-all duration-300 hover:-translate-y-1 hover:border-white/15"
              style={{ boxShadow: "0 24px 64px -28px rgba(0,0,0,0.7)" }}>
              <span className="absolute inset-x-0 top-0 h-[3px]" style={{ background: `linear-gradient(90deg, ${c.c}, transparent)` }} />
              <div className="absolute -right-8 -top-8 h-28 w-28 rounded-full opacity-0 blur-2xl transition-opacity duration-500 group-hover:opacity-100" style={{ background: c.c }} />
              <div className="stat relative text-4xl font-semibold" style={{ color: c.c }}>
                <Counter value={c.v} suffix={c.suffix || ""} />
              </div>
              <div className="relative mt-1.5 text-[15px] font-medium text-mist-100">{c.k}</div>
              <p className="relative mt-3 text-sm leading-relaxed text-mist-400">{c.d}</p>
              <div className="relative mt-4 text-[11px] uppercase tracking-wider text-mist-600">source · {c.src}</div>
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

/* ----------------------- how it works (plain) ----------------------- */
function HowItWorks() {
  const steps = [
    {
      n: "1", c: "#8b8cf0", name: "Identify the attacks",
      d: "We catalogue how criminals use generative AI to attack payments - fake identities, deepfake scam calls, hijacked AI shopping agents, money-mule rings - as a structured threat map.",
    },
    {
      n: "2", c: "#ff5c49", name: "Generate them as data",
      d: "We turn each attack into realistic transactions on card, real-time transfer and agentic-checkout rails. Then an AI red team mutates them to slip past our own detector.",
    },
    {
      n: "3", c: "#2ed6a6", name: "Defend, then re-attack",
      d: "We train a fraud detector on that data, measure it honestly, and retrain it on whatever gets through. Repeat. Each loop makes the defence harder to beat.",
    },
  ];
  return (
    <section className="border-y border-white/[0.06] bg-white/[0.012]">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <Reveal className="mb-3 max-w-2xl">
          <div className="label text-defense">What this is</div>
          <h2 className="display mt-3 text-display-sm">A lab that builds payment-fraud attacks, then builds the defense that beats them - as one loop.</h2>
        </Reveal>
        <Reveal delay={0.05}>
          <p className="lede mb-10 max-w-2xl text-[15px]">
            Most fraud tools are graded once, against fixed data. Chimera keeps attacking its own detector so the
            defense has to keep improving. Three steps, run on repeat:
          </p>
        </Reveal>
        <div className="grid gap-5 md:grid-cols-3">
          {steps.map((p, i) => (
            <Reveal key={p.name} delay={i * 0.08}>
              <div className="panel h-full p-6">
                <div className="flex items-center gap-3">
                  <span className="grid h-7 w-7 place-items-center rounded-lg text-sm font-semibold" style={{ background: `${p.c}1a`, color: p.c }}>{p.n}</span>
                  <span className="text-base font-semibold text-mist-100">{p.name}</span>
                </div>
                <p className="mt-3 text-sm leading-relaxed text-mist-400">{p.d}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ----------------------------- threats ----------------------------- */
function Threats({ onLaunch }: { onLaunch: Launch }) {
  const items = [
    { tag: "NEW · 2026", c: "#8b8cf0", name: "Hijacked AI shopping agent", d: "A delegated agent credential is stolen and spends inside your mandate.", star: true },
    { tag: "agentic", c: "#8b8cf0", name: "Autonomous carding", d: "AI agents test stolen cards at machine speed on delegated tokens." },
    { tag: "real-time", c: "#ff5c49", name: "Deepfake scam transfer", d: "A cloned voice convinces the victim to authorise a push payment themselves." },
    { tag: "real-time", c: "#ff5c49", name: "Money-mule network", d: "Stolen funds fan out through many accounts within minutes to launder them." },
    { tag: "identity", c: "#5ea0ff", name: "Synthetic identity bust-out", d: "GenAI stitches fake identities, nurtures credit, then cashes out." },
    { tag: "access", c: "#5ea0ff", name: "Account takeover", d: "Bots stuff stolen credentials, then drain the account via card or transfer." },
    { tag: "long-con", c: "#f5b544", name: "Investment ('pig-butchering') scam", d: "A groomed victim makes escalating transfers to a fake platform." },
    { tag: "evasion", c: "#f5b544", name: "Structuring / velocity evasion", d: "Large sums split into many small transfers to stay under the radar." },
  ];
  return (
    <section className="mx-auto max-w-6xl px-6 py-24">
      <Reveal className="mb-3 max-w-2xl">
        <div className="label text-threat">The threats we simulate</div>
        <h2 className="display mt-3 text-display-sm">Nine attack types, each grounded in real 2026 fraud and mapped to the signals a bank can act on.</h2>
      </Reveal>
      <Reveal delay={0.05}>
        <p className="lede mb-9 max-w-2xl text-[15px]">
          Plain-language view of what the system generates and defends against. The full ATT&CK-style matrix,
          with sources and detection signatures, is in the console.
        </p>
      </Reveal>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {items.map((it, i) => (
          <Reveal key={it.name} delay={i * 0.04}>
            <div className={`group relative flex h-full flex-col overflow-hidden rounded-2xl border bg-white/[0.024] p-5 transition-all duration-300 hover:-translate-y-1 ${it.star ? "border-agentic/35 shadow-glow" : "border-white/[0.07] hover:border-white/15"}`}>
              <span className="absolute left-0 top-5 h-8 w-[3px] rounded-r" style={{ background: it.c }} />
              <div className="flex items-center justify-between">
                <span className="chip" style={{ color: it.c, borderColor: `${it.c}55`, background: `${it.c}12` }}>{it.tag}</span>
                <span className="h-2 w-2 rounded-full transition-transform duration-300 group-hover:scale-150" style={{ background: it.c }} />
              </div>
              <div className="mt-3 text-[15px] font-semibold text-mist-100">{it.name}</div>
              <p className="mt-1.5 text-[13px] leading-relaxed text-mist-500">{it.d}</p>
            </div>
          </Reveal>
        ))}
      </div>
      <Reveal delay={0.1}>
        <button onClick={() => onLaunch("threats")} className="btn mt-8 group">Open the full threat matrix <span aria-hidden className="transition-transform group-hover:translate-x-1">→</span></button>
      </Reveal>
    </section>
  );
}

/* ----------------------------- agentic frontier ----------------------------- */
function Agentic({ loo, onLaunch }: { loo?: { supervised_recall: number; novelty_recall: number }; onLaunch: Launch }) {
  const sup = Math.round((loo?.supervised_recall ?? 0.149) * 100);
  const nov = Math.round((loo?.novelty_recall ?? 1.0) * 100);
  return (
    <section className="mx-auto max-w-6xl px-6 py-24">
      <div className="grid gap-12 lg:grid-cols-[1fr_0.9fr] lg:items-center">
        <Reveal>
          <div className="label text-agentic">The 2026 frontier most teams will miss</div>
          <h2 className="display mt-3 text-display-sm">When an AI shopping agent is hijacked, it looks exactly like a legitimate one.</h2>
          <p className="lede mt-5 max-w-xl">
            Under Mastercard Agent Pay and Visa's Trusted Agent Protocol, a purchase can be initiated by a
            delegated agent credential. Stolen or replayed, that credential spends inside someone else's
            mandate - fast, automated, from reputable cloud, serving many principals. Velocity, device and
            cadence cannot tell it apart. Credential integrity can: a missing attestation, low directory trust,
            spend over the delegated cap.
          </p>
          <button onClick={() => onLaunch("detect")} className="btn mt-7">See it in Detection <span aria-hidden>→</span></button>
        </Reveal>
        <Reveal delay={0.12}>
          <div className="panel p-7">
            <div className="label">Delegated-token abuse as an unseen vector</div>
            <p className="mt-2 text-sm text-mist-400">Trained with this attack entirely removed, then scored on it.</p>
            <div className="mt-6 space-y-5">
              <div>
                <div className="mb-1 flex justify-between text-xs"><span className="text-mist-400">Supervised model alone</span><span className="stat text-threat">{sup}%</span></div>
                <div className="h-2 overflow-hidden rounded-full bg-white/[0.06]">
                  <motion.div className="h-2 rounded-full bg-threat" initial={{ width: 0 }} whileInView={{ width: `${sup}%` }} viewport={{ once: true }} transition={{ duration: 1 }} />
                </div>
              </div>
              <div>
                <div className="mb-1 flex justify-between text-xs"><span className="text-mist-400">+ novelty channel & agent-identity features</span><span className="stat text-defense">{nov}%</span></div>
                <div className="h-2 overflow-hidden rounded-full bg-white/[0.06]">
                  <motion.div className="h-2 rounded-full bg-defense" initial={{ width: 0 }} whileInView={{ width: `${nov}%` }} viewport={{ once: true }} transition={{ duration: 1, delay: 0.2 }} />
                </div>
              </div>
            </div>
            <p className="mt-6 text-[13px] leading-relaxed text-mist-500">
              The zero-day channel recovers a vector the supervised model has never seen - the direct answer
              to &ldquo;novel, emerging.&rdquo;
            </p>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

/* ----------------------------- feasibility ----------------------------- */
function Feasibility({ s, op, meta }: { s?: any; op?: any; meta?: any }) {
  const stats = [
    { v: s ? s.pr_auc.toFixed(4) : "0.9999", k: "PR-AUC", d: "under ~1.4% class imbalance" },
    { v: op ? `${op.value_detected_rate * 100}%` : "100%", k: "fraud value caught", d: "at the cost-optimal threshold" },
    { v: op ? `${op.alerts_per_10k}` : "–", k: "alerts / 10k txns", d: "the review workload a bank signs off" },
    { v: meta ? `${(meta.fraud_rate * 100).toFixed(2)}%` : "–", k: "fraud rate", d: `${meta ? Number(meta.n_total).toLocaleString() : ""} simulated events` },
  ];
  return (
    <section className="border-y border-white/[0.06] bg-white/[0.012]">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <Reveal className="max-w-2xl">
          <div className="label text-defense">Built for the real thing</div>
          <h2 className="display mt-3 text-display-sm">Reported the way a fraud desk reads a model - not just an AUC.</h2>
        </Reveal>
        <div className="mt-10 grid grid-cols-2 gap-5 md:grid-cols-4">
          {stats.map((st, i) => (
            <Reveal key={st.k} delay={i * 0.06}>
              <div className="panel h-full p-5">
                <div className="stat text-2xl font-semibold text-mist-100">{st.v}</div>
                <div className="mt-1 text-sm text-mist-300">{st.k}</div>
                <div className="mt-1 text-xs text-mist-500">{st.d}</div>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ----------------------------- tech stack ----------------------------- */
function TechStack() {
  const groups = [
    { c: "#8b8cf0", title: "Identify", items: ["ATT&CK-style taxonomy", "TF-IDF RAG corpus", "LangGraph multi-agent loop", "Groq gpt-oss-120b ideation"] },
    { c: "#ff5c49", title: "Generate", items: ["Multi-rail event simulator", "NetworkX entity graph", "Hard-negative injection", "Evolutionary (mu+lambda) evasion"] },
    { c: "#2ed6a6", title: "Defend", items: ["LightGBM gradient boosting", "IsolationForest + PCA novelty", "TreeSHAP reason codes", "Cost-aware operating point"] },
    { c: "#5ea0ff", title: "Delivery", items: ["FastAPI service", "Next.js + Tailwind + Framer Motion", "Monolithic Docker on Render", "Seeded + reproducible, 8 tests"] },
  ];
  return (
    <section className="border-y border-white/[0.06] bg-white/[0.012]">
      <div className="mx-auto max-w-6xl px-6 py-20">
        <Reveal className="mb-9 max-w-2xl">
          <div className="label">How it is built</div>
          <h2 className="display mt-3 text-display-sm">A modern, reproducible stack. Free-tier by default; paid infrastructure is a quality dial, not a rewrite.</h2>
        </Reveal>
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {groups.map((g, i) => (
            <Reveal key={g.title} delay={i * 0.06}>
              <div className="panel h-full p-5">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full" style={{ background: g.c }} />
                  <span className="text-sm font-semibold text-mist-100">{g.title}</span>
                </div>
                <ul className="mt-3 space-y-1.5">
                  {g.items.map((it) => (
                    <li key={it} className="flex gap-2 text-[13px] leading-relaxed text-mist-400">
                      <span style={{ color: g.c }}>·</span>{it}
                    </li>
                  ))}
                </ul>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ----------------------------- CTA + footer ----------------------------- */
function FinalCTA({ onLaunch }: { onLaunch: Launch }) {
  const tabs = [
    { id: "threats", label: "Threat Matrix" },
    { id: "lab", label: "Attack Lab" },
    { id: "loop", label: "Closed Loop" },
    { id: "graph", label: "Network Graph" },
    { id: "detect", label: "Detection" },
  ];
  return (
    <section className="mx-auto max-w-6xl px-6 py-28 text-center">
      <Reveal>
        <h2 className="display mx-auto max-w-2xl text-display">Run the loop yourself.</h2>
        <p className="lede mx-auto mt-5 max-w-xl">
          Every panel below is live: launch an attack, watch it evade the detector, retrain, and read the
          per-event reason codes.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-2">
          <ConsoleCTA onLaunch={onLaunch} label="Open the console" />
          {tabs.map((t) => (
            <button key={t.id} onClick={() => onLaunch(t.id)} className="btn">{t.label}</button>
          ))}
        </div>
      </Reveal>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-white/[0.06]">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-6 py-8 text-xs text-mist-500 sm:flex-row">
        <div className="flex items-center gap-3">
          <Wordmark />
          <span className="text-mist-600">·</span>
          <span>Identify · Generate · Defend — one closed loop.</span>
        </div>
        <div className="flex items-center gap-4">
          <a href="https://github.com/dhruv-decoder/Chimera" target="_blank" rel="noreferrer" className="transition-colors hover:text-mist-300">GitHub</a>
          <span className="text-mist-600">Mastercard Innovation Challenge · GFF 2026</span>
        </div>
      </div>
    </footer>
  );
}
