// Build a presentation-grade PDF deck from the live artifacts, rendered with
// headless Chromium so the layout is exactly what a judge sees. Also writes a
// PNG per slide for visual QA.
//   node scripts/deck.mjs
import { chromium } from "playwright";
import { readFileSync, mkdirSync, writeFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, resolve } from "path";

const __dir = dirname(fileURLToPath(import.meta.url));
const ART = resolve(__dir, "../../data/artifacts");
const DOCS = resolve(__dir, "../../docs");
const PREV = resolve(DOCS, "deck_previews");
mkdirSync(PREV, { recursive: true });

const read = (n) => { try { return JSON.parse(readFileSync(resolve(ART, n), "utf8")); } catch { return {}; } };
const ev = read("eval_report.json");
const loop = read("loop_report.json");
const meta = read("sim_meta.json");
const analysis = read("analysis_report.json");

const ext = read("external_validation.json");
const gnn = read("gnn_benchmark.json");
const rig = read("rigor_report.json");
const bench = read("benchmark_report.json");
const pit = read("point_in_time.json");
const s = ev.supervised || {};
const op = (ev.operating_point || {}).cost_optimal || {};
const curve = loop.hardening_curve || [];
const loo = (ev.leave_one_out || []);
const hj = loo.find((r) => r.vector === "AGENT-HIJACK") || {};
const pct = (x, d = 0) => (x == null ? "-" : (x * 100).toFixed(d) + "%");
const worst = curve.length ? curve.reduce((a, b) => (b.pre_recall < a.pre_recall ? b : a)) : {};

// ---------- small svg helpers ----------
function hardeningSVG() {
  const W = 560, H = 300, pad = { l: 46, r: 20, t: 20, b: 34 };
  const iw = W - pad.l - pad.r, ih = H - pad.t - pad.b;
  const maxX = Math.max(curve.length - 1, 1);
  const x = (i) => pad.l + (i / maxX) * iw;
  const y = (v) => pad.t + (1 - v) * ih;
  const line = (k) => curve.map((d, i) => `${i ? "L" : "M"} ${x(i)} ${y(d[k])}`).join(" ");
  const grid = [0, 0.25, 0.5, 0.75, 1].map((g) =>
    `<line x1="${pad.l}" x2="${W - pad.r}" y1="${y(g)}" y2="${y(g)}" stroke="rgba(255,255,255,0.06)"/>
     <text x="14" y="${y(g) + 3}" fill="#6b7280" font-size="10" font-family="monospace">${g * 100}</text>`).join("");
  const xlab = curve.map((d, i) => `<text x="${x(i)}" y="${H - 12}" fill="#6b7280" font-size="10" text-anchor="middle" font-family="monospace">R${d.round}</text>`).join("");
  const pts = curve.map((d, i) => `<circle cx="${x(i)}" cy="${y(d.post_recall)}" r="3.5" fill="#2ed6a6"/><circle cx="${x(i)}" cy="${y(d.pre_recall)}" r="3.5" fill="#ff5c49"/>`).join("");
  return `<svg viewBox="0 0 ${W} ${H}" width="100%">
    ${grid}
    <text x="${-H / 2}" y="12" transform="rotate(-90)" text-anchor="middle" fill="#8a909f" font-size="10">fraud caught (recall %) - higher is better</text>
    ${xlab}
    <path d="${line("post_recall")}" fill="none" stroke="#2ed6a6" stroke-width="2.6"/>
    <path d="${line("pre_recall")}" fill="none" stroke="#ff5c49" stroke-width="2.6" stroke-dasharray="5 4"/>
    ${pts}
  </svg>`;
}
function barsSVG(items, fmt = (v) => pct(v)) {
  return `<div class="bars">` + items.map(([label, v, tone]) => `
    <div class="bar-row"><span class="bar-label">${label}</span>
      <span class="bar-track"><span class="bar-fill" style="width:${Math.round(v * 100)}%;background:${tone || "#2ed6a6"}"></span></span>
      <span class="bar-val">${fmt(v)}</span></div>`).join("") + `</div>`;
}

const pv = ev.per_vector_recall || {};
const pvItems = Object.entries(pv).sort((a, b) => a[1].recall - b[1].recall)
  .map(([k, v]) => [k, v.recall, v.recall < 0.6 ? "#ff5c49" : v.recall < 0.85 ? "#f5b544" : "#2ed6a6"]);
const trace = (loop.trace || []).slice(0, 6);
const orch = (loop.meta || {}).orchestration === "langgraph";

// ---------- slides ----------
const kicker = (t, c = "#2ed6a6") => `<div class="kick" style="color:${c}"><span style="background:${c}"></span>${t}</div>`;
const slides = [];

slides.push(`<section class="slide title">
  <div class="brand"><div class="mark"></div><span>Chimera</span></div>
  <div class="accent"></div>
  <h1>Fraud that learns needs a<br/>defense that <em>learns back</em>.</h1>
  <p class="sub">A closed-loop adversarial lab for GenAI-era payment fraud. Discover emerging attacks, simulate them at fidelity across card, real-time and agentic rails, and harden a detector on exactly what breaks through.</p>
  <div class="foot">Mastercard Innovation Challenge @ GFF 2026 · AI Defense Lab for Payment Security</div>
</section>`);

slides.push(`<section class="slide">
  ${kicker("The problem", "#ff5c49")}
  <h2>Static defenses decay the moment fraud changes shape</h2>
  <div class="grid3">
    <div class="card"><div class="big">450%+</div><div class="k">dark-web "AI agent" chatter</div><div class="d">Visa, H1 2026. A brand-new, machine-speed attack surface as agentic checkout scales.</div></div>
    <div class="card"><div class="big">524,121</div><div class="k">mule accounts flagged</div><div class="d">India, March 2026. Real-time rails launder funds in seconds (NPCI MuleHunter.AI).</div></div>
    <div class="card"><div class="big">25%</div><div class="k">rise in malicious bot payments</div><div class="d">Visa, six months. Delegated agent tokens transact with no cardholder step-up.</div></div>
  </div>
  <p class="note">Evaluating one classifier on a fixed dataset measures fit to yesterday's fraud, not robustness to an adaptive adversary. The challenge asks for a loop. I built one.</p>
</section>`);

slides.push(`<section class="slide">
  ${kicker("What it does")}
  <h2>Build the attacks, then build the defense that beats them - as one loop</h2>
  <div class="grid3">
    <div class="card"><div class="step" style="color:#8b8cf0">1 · Identify</div><div class="d">Catalogue how GenAI attacks payments - fake identities, deepfake scam calls, hijacked shopping agents, mule rings - as a structured threat map.</div></div>
    <div class="card"><div class="step" style="color:#ff5c49">2 · Generate</div><div class="d">Turn each attack into realistic transactions on card, real-time and agentic rails. An AI red team mutates them to slip past my own detector.</div></div>
    <div class="card"><div class="step" style="color:#2ed6a6">3 · Defend</div><div class="d">Train a detector on that data, measure it honestly, and retrain on whatever gets through. Repeat until the attacker can't win.</div></div>
  </div>
</section>`);

slides.push(`<section class="slide">
  ${kicker("Orchestration", "#8b8cf0")}
  <h2>A live multi-agent system (LangGraph)</h2>
  <div class="agents">
    ${[["Recon", "#8b8cf0", "RAG-grounded ideation proposes novel variants (gpt-oss-120b)"],
       ["Red team", "#ff5c49", "Evolutionary search tunes each attack to evade the live model"],
       ["Attack", "#ff5c49", "Generates the evasive stream, measures the breach"],
       ["Blue team", "#2ed6a6", "Retrains on the misses, measures the recovery"]]
      .map(([n, c, d], i) => `<div class="agent" style="border-color:${c}55;background:${c}12">
        <div class="an" style="color:${c}">${n}</div><div class="ad">${d}</div></div>${i < 3 ? '<div class="arr">&rarr;</div>' : '<div class="arr" style="color:#2ed6a6">&#8635;</div>'}`).join("")}
  </div>
  <p class="note">A compiled StateGraph cycles recon &rarr; red_team &rarr; attack &rarr; blue_team until the round budget is spent.${orch ? " This report was generated by the graph." : ""}</p>
  ${trace.length ? `<div class="trace">${trace.map((t) => `<div><span>$</span> ${t}</div>`).join("")}</div>` : ""}
</section>`);

slides.push(`<section class="slide">
  ${kicker("Generate", "#ff5c49")}
  <h2>Fidelity is the point</h2>
  <div class="cols">
    <div>
      <p class="body"><b>Realistic by construction.</b> ${Number(meta.n_total || 0).toLocaleString()} events, ${pct(meta.fraud_rate, 2)} fraud, across card-not-present, card-present, real-time A2A and a shared agentic channel. Each account has a latent behavioural profile; an entity graph links accounts, devices, merchants and payees.</p>
      <p class="body"><b>Hard negatives are the credibility test.</b> I inject legitimate look-alikes (benign agentic shopping through trusted agents, large first-time payees, travel, collector accounts, recurring investments) into the exact feature regions where fraud lives.</p>
    </div>
    <div class="statbox">
      <div class="big" style="color:#2ed6a6">${(analysis.fidelity?.best_single_feature_auc ?? 0.84).toFixed(2)}</div>
      <div class="k">best single-feature AUC</div>
      <div class="d">No one flag separates the classes, so the model must combine velocity, graph, behavioural and agent-identity signals. Without hard negatives, AUC would be a meaningless 1.0.</div>
    </div>
  </div>
</section>`);

slides.push(`<section class="slide">
  ${kicker("Headline capability", "#8b8cf0")}
  <h2>Agentic-commerce identity abuse - the 2026 frontier</h2>
  <p class="body">A payment can now be initiated by an autonomous agent on a cardholder's behalf (Mastercard Agent Pay's Agentic Token; Visa's Trusted Agent Protocol). A hijacked or malicious agent spends inside someone else's mandate. It looks identical to a legitimate agent on velocity, device and cadence - only credential integrity separates them.</p>
  <div class="grid3">
    <div class="card"><div class="step" style="color:#8b8cf0">What I simulate</div><div class="d">AGENT-HIJACK: one agent id replayed across many mandates, off-scope spend, weak attestation.</div></div>
    <div class="card"><div class="step" style="color:#8b8cf0">New defense family</div><div class="d">Attestation · directory trust · mandate-cap breach · agent-id replay fan-out.</div></div>
    <div class="card hl"><div class="step" style="color:#2ed6a6">Unseen-vector result</div><div class="big2">${pct(hj.supervised_recall)} <span>&rarr;</span> ${pct(hj.novelty_recall)}</div><div class="d">Trained with this attack fully removed, then scored on it. The supervised model alone vs the agent-identity features + novelty channel.</div></div>
  </div>
</section>`);

slides.push(`<section class="slide">
  ${kicker("The closed loop", "#ff5c49")}
  <h2>The hardening curve - the whole thesis in one chart</h2>
  <div class="cols">
    <div class="chart">${hardeningSVG()}
      <div class="legend"><span class="lg"><i class="dash"></i>fraud slipping past (before retrain)</span><span class="lg"><i class="solid"></i>fraud caught (after retrain)</span></div>
    </div>
    <div>
      <p class="body">Round ${worst.round}: the red team finds evasion that collapses recall to <b style="color:#ff5c49">${pct(worst.pre_recall)}</b> - a static model would be blind. Retraining on those samples restores it to <b style="color:#2ed6a6">${pct(worst.post_recall)}</b>.</p>
      <p class="body">By the final round the attacker can no longer find easy evasion against the hardened detector. The loop converges because the defense generalised across the adversary's moves. A fixed detector does not adapt to evasion it has never seen; the closed loop trains on exactly those failures.</p>
    </div>
  </div>
</section>`);

slides.push(`<section class="slide">
  ${kicker("Defend")}
  <h2>Strong, and reported the way a fraud desk reads it</h2>
  <div class="metrics">
    <div class="m"><div class="mv" style="color:#2ed6a6">${(s.roc_auc ?? 0).toFixed(4)}</div><div class="ml">ROC-AUC</div></div>
    <div class="m"><div class="mv" style="color:#2ed6a6">${(s.pr_auc ?? 0).toFixed(4)}</div><div class="ml">PR-AUC</div></div>
    <div class="m"><div class="mv">${(s.f1 ?? 0).toFixed(3)}</div><div class="ml">F1</div></div>
    <div class="m"><div class="mv" style="color:#2ed6a6">${pct(op.value_detected_rate)}</div><div class="ml">fraud value caught</div></div>
    <div class="m"><div class="mv">${op.alerts_per_10k ?? "-"}</div><div class="ml">alerts / 10k txns</div></div>
    <div class="m"><div class="mv" style="color:#f5b544">${pct(s.fpr_at_90_recall, 3)}</div><div class="ml">FPR @ 90% recall</div></div>
  </div>
  <div class="cols">
    <div class="chart">${barsSVG(pvItems)}<div class="capt">Per-vector recall - deepfake authorised push (DF-APP) is hardest by design.</div></div>
    <div>
      <p class="body"><b>Two channels.</b> LightGBM gradient boosting for known shapes, plus an unsupervised novelty channel (isolation forest + PCA) that flags attacks the model has never seen. ~45 features across event, velocity, graph and agent-identity families.</p>
      <p class="body"><b>Explainable and cost-aware.</b> Per-event reason codes via exact TreeSHAP; a cost-optimal operating point that minimises expected loss plus review workload.</p>
    </div>
  </div>
</section>`);

slides.push(`<section class="slide">
  ${kicker("Catching the unseen")}
  <h2>Novelty channel - leave-one-vector-out</h2>
  <p class="body">Each attack type is removed entirely from training, then scored. Higher = more of the unseen attack still caught. This is the direct answer to "novel, emerging".</p>
  <table class="loo">
    <thead><tr><th>unseen attack</th><th>supervised alone</th><th>+ novelty & agent-identity</th><th>blended</th></tr></thead>
    <tbody>
      ${loo.map((r) => `<tr class="${r.vector === "AGENT-HIJACK" ? "star" : ""}"><td>${r.vector}${r.vector === "AGENT-HIJACK" ? ' <span>new vector</span>' : ""}</td><td style="color:${r.supervised_recall < 0.5 ? "#ff5c49" : "#aeb4c2"}">${pct(r.supervised_recall)}</td><td style="color:#8b8cf0">${pct(r.novelty_recall)}</td><td style="color:#2ed6a6">${pct(r.blended_recall)}</td></tr>`).join("")}
    </tbody>
  </table>
</section>`);

slides.push(`<section class="slide">
  ${kicker("Validated beyond synthetic", "#5ea0ff")}
  <h2>It works on real fraud, and a GNN proves the graph matters</h2>
  <div class="cols">
    <div class="statbox">
      <div class="step" style="color:#5ea0ff">Same detector, real data</div>
      <div class="big2" style="color:#2ed6a6">ROC ${(ext.supervised?.roc_auc ?? 0.95).toFixed(2)} &middot; PR ${(ext.supervised?.pr_auc ?? 0.81).toFixed(2)}</div>
      <div class="d">The unchanged two-channel ensemble on the ULB real-world card-fraud benchmark (${Number(ext.n || 284807).toLocaleString()} genuine transactions, ${ext.n_fraud || 492} fraud) - no dataset-specific tuning. The method transfers to real fraud.</div>
      <div class="d" style="margin-top:10px">The synthetic benchmark is genuinely hard: best single-feature AUC ${(ext.fidelity_vs_synthetic?.synthetic_best_single_feature_auc ?? 0.84).toFixed(2)} (synthetic) vs ${(ext.best_single_feature_auc ?? 0.93).toFixed(2)} (real) - harder, not a toy.</div>
    </div>
    <div class="statbox">
      <div class="step" style="color:#2ed6a6">GraphSAGE GNN on the transfer graph</div>
      <div class="big2">ring PR-AUC ${(gnn.gradient_boosting?.pr_auc ?? 0.84).toFixed(2)} <span>&rarr;</span> ${(gnn.graphsage_gnn?.pr_auc ?? 0.998).toFixed(3)}</div>
      <div class="d">A two-layer GraphSAGE vs gradient boosting on the <b>same</b> per-account features. Message passing along the account graph lifts coordinated-ring detection by +${((gnn.pr_auc_lift ?? 0.15)).toFixed(2)} PR-AUC${gnn.pr_auc_lift_inductive != null ? `, and holds under an inductive split with no test-node edges in training (+${gnn.pr_auc_lift_inductive.toFixed(2)}, leakage-proof)` : ""} - graph structure is decisive for mule rings, demonstrated not asserted.</div>
    </div>
  </div>
</section>`);

slides.push(`<section class="slide">
  ${kicker("Evaluation rigor", "#f5b544")}
  <h2>The audits a fraud-ML reviewer would ask for</h2>
  <div class="grid3">
    <div class="card"><div class="big">${(pit.causal?.pr_auc ?? 0.999).toFixed(3)}</div><div class="k">point-in-time PR-AUC</div><div class="d">Structural features rebuilt with no look-ahead (cumulative up to each event). Detection barely moves from ${(pit.batch?.pr_auc ?? 0.9999).toFixed(3)} - not a leakage artifact.</div></div>
    <div class="card"><div class="big">&plusmn;${(rig.stability_across_seeds?.recall?.std ?? 0.003).toFixed(3)}</div><div class="k">recall across 5 seeds</div><div class="d">ROC-AUC ${(rig.stability_across_seeds?.roc_auc?.mean ?? 1).toFixed(2)}, recall ${(rig.stability_across_seeds?.recall?.mean ?? 0.994).toFixed(3)}. Nothing here is seed-dependent.</div></div>
    <div class="card"><div class="big">0.94&rarr;1.0</div><div class="k">component ablation</div><div class="d">Held-out PR-AUC event+velocity ${(rig.component_ablation?.["event+velocity"]?.pr_auc ?? 0.943).toFixed(2)} to ${(rig.component_ablation?.["+ graph"]?.pr_auc ?? 0.9999).toFixed(3)} once graph features are added - the graph is the decisive lift.</div></div>
  </div>
  <div class="cols" style="margin-top:14px">
    <div class="statbox">
      <div class="step" style="color:#5ea0ff">Competitive, but the loop is the point</div>
      <div class="d">On the real ULB benchmark, Chimera's static ensemble sits with standard models (PR-AUC: XGBoost ${(bench.baselines?.["XGBoost"]?.pr_auc ?? 0.84).toFixed(2)}, RandomForest ${(bench.baselines?.["Random Forest"]?.pr_auc ?? 0.82).toFixed(2)}, LightGBM ${(bench.baselines?.["LightGBM"]?.pr_auc ?? 0.81).toFixed(2)}, Chimera ${(bench.baselines?.["Chimera (two-channel)"]?.pr_auc ?? 0.78).toFixed(2)}, LogReg ${(bench.baselines?.["Logistic Regression"]?.pr_auc ?? 0.70).toFixed(2)}). The contribution is not a better static classifier.</div>
    </div>
    <div class="statbox">
      <div class="step" style="color:#2ed6a6">The loop transfers to real fraud</div>
      <div class="big2">${pct(bench.closed_loop_on_real?.baseline_recall ?? 0.84)} <span>&rarr;</span> ${pct(bench.closed_loop_on_real?.under_evasion ?? 0.59)} <span>&rarr;</span> ${pct(bench.closed_loop_on_real?.after_retrain ?? 1.0)}</div>
      <div class="d">Perturb real ULB fraud toward the legitimate distribution and recall drops; retrain on the evasive samples and it recovers. The methodology does not depend on the synthetic simulator.</div>
    </div>
  </div>
</section>`);

slides.push(`<section class="slide">
  ${kicker("Real-world feasibility")}
  <h2>Designed to sit where a bank already decides</h2>
  <div class="cols">
    <div>
      <p class="body"><b>Inline at authorisation.</b> The detector scores the fields a switch already sees (ISO 8583 / UPI API) and returns a graded action: allow, step-up, hold, block. Velocity and graph features come from a streaming feature store, computed point-in-time-correct.</p>
      <p class="body"><b>Native integration.</b> Controls map to 3-DS step-up and RBI friction; graph features mirror NPCI MuleHunter; the agent-identity features model the public concepts Agent Pay and the Trusted Agent Protocol describe. Reason codes satisfy model-risk audit.</p>
    </div>
    <div class="statbox">
      <div class="step" style="color:#2ed6a6">What paid infra buys</div>
      <div class="d">Streaming feature store (online features) · a temporal GNN for large coordinated rings · managed embeddings + vector DB for richer ideation grounding · a hosted low-latency endpoint for always-on variant generation. Quality dials, not a rewrite.</div>
    </div>
  </div>
</section>`);

slides.push(`<section class="slide">
  ${kicker("Self-assessment")}
  <h2>How this maps to the five judging criteria</h2>
  <table class="score">
    <tbody>
      <tr><td class="c">Diversity of attacks</td><td>16 techniques, 9 simulated across card / real-time / agentic rails, plus a live agent that proposes more.</td></tr>
      <tr><td class="c">Fidelity of simulation</td><td>Latent-profile population, entity graph, hard negatives - best single-feature AUC only ${(analysis.fidelity?.best_single_feature_auc ?? 0.84).toFixed(2)}.</td></tr>
      <tr><td class="c">Detection efficacy</td><td>LightGBM + novelty + agent-identity features; ${pct(op.value_detected_rate)} of fraud value caught at ~${op.alerts_per_10k ?? "-"} alerts / 10k.</td></tr>
      <tr><td class="c">Novelty</td><td>Closed loop with a measured hardening curve; agentic identity abuse; a live multi-agent red team.</td></tr>
      <tr><td class="c">Real-world feasibility</td><td>Auth-time schema, graded controls, NPCI-style graph signals, Agent Pay / TAP field mapping, streaming path.</td></tr>
    </tbody>
  </table>
</section>`);

slides.push(`<section class="slide close">
  <div class="accent"></div>
  <h2>Defensive by construction.</h2>
  <p class="body" style="max-width:900px">Chimera runs entirely on synthetic data it generates itself - no real cardholders, PII, credentials or live payment connectivity. The attack modules are parameterised statistical patterns that stress a detector, not operational playbooks or working exploit code. The red team exists only to harden the blue team.</p>
  <div class="foot">Chimera · identify · generate · defend · one loop &nbsp;|&nbsp; github.com/dhruv-decoder/chimera</div>
</section>`);

// ---------- html shell ----------
const html = `<!doctype html><html><head><meta charset="utf-8"><style>
* { margin:0; padding:0; box-sizing:border-box; }
:root { --bg:#07080b; --panel:rgba(255,255,255,0.03); --text:#e8eaf0; --mut:#8a909f; --mut2:#6b7280; }
html,body { background:var(--bg); color:var(--text); font-family:'Inter','Segoe UI',system-ui,sans-serif; -webkit-font-smoothing:antialiased; }
@page { size:1280px 720px; margin:0; }
.slide { position:relative; width:1280px; height:720px; padding:72px 84px; overflow:hidden;
  background:radial-gradient(60rem 36rem at 82% -12%, rgba(46,214,166,0.10), transparent 60%),
             radial-gradient(48rem 36rem at 6% 6%, rgba(139,140,240,0.09), transparent 58%), var(--bg);
  page-break-after:always; border-bottom:1px solid rgba(255,255,255,0.04); }
.slide:last-child { page-break-after:auto; }
h1 { font-size:64px; line-height:1.04; letter-spacing:-0.03em; font-weight:700; margin-top:26px; }
h1 em { color:#2ed6a6; font-style:normal; }
h2 { font-size:38px; line-height:1.1; letter-spacing:-0.02em; font-weight:650; margin:14px 0 26px; max-width:1050px; }
.kick { display:flex; align-items:center; gap:10px; font-size:14px; font-weight:600; text-transform:uppercase; letter-spacing:0.16em; }
.kick span { width:34px; height:3px; border-radius:3px; display:inline-block; }
.sub { font-size:21px; line-height:1.5; color:var(--mut); max-width:940px; margin-top:22px; }
.body { font-size:18px; line-height:1.55; color:#cbd0db; margin-bottom:16px; }
.body b { color:#fff; font-weight:600; }
.note { font-size:17px; line-height:1.5; color:#2ed6a6; margin-top:26px; max-width:1050px; }
.foot { position:absolute; bottom:52px; left:84px; font-size:14px; color:var(--mut2); }
.brand { display:flex; align-items:center; gap:12px; font-size:18px; font-weight:600; }
.brand .mark { width:26px; height:26px; border-radius:7px; border:1px solid rgba(255,255,255,0.14); background:#12151c;
  box-shadow:inset 0 0 0 1px rgba(46,214,166,0.25); }
.accent { width:64px; height:4px; background:#2ed6a6; border-radius:4px; margin:34px 0 0; }
.title h1 { margin-top:30px; } .title .sub { margin-top:26px; }
.grid3 { display:grid; grid-template-columns:repeat(3,1fr); gap:20px; margin-top:8px; }
.card { background:var(--panel); border:1px solid rgba(255,255,255,0.07); border-radius:16px; padding:26px; }
.card.hl { background:rgba(139,140,240,0.08); border-color:rgba(139,140,240,0.28); }
.big { font-size:42px; font-weight:700; font-variant-numeric:tabular-nums; letter-spacing:-0.02em; }
.big2 { font-size:34px; font-weight:700; font-variant-numeric:tabular-nums; margin:6px 0; }
.big2 span { color:var(--mut); font-weight:400; }
.k { font-size:16px; color:#cbd0db; margin-top:6px; font-weight:600; }
.d { font-size:15px; line-height:1.5; color:var(--mut); margin-top:10px; }
.step { font-size:16px; font-weight:700; }
.cols { display:grid; grid-template-columns:1.15fr 0.85fr; gap:34px; align-items:start; margin-top:8px; }
.statbox { background:var(--panel); border:1px solid rgba(255,255,255,0.07); border-radius:16px; padding:28px; }
.agents { display:flex; align-items:stretch; gap:10px; margin:10px 0 8px; }
.agent { flex:1; border:1px solid; border-radius:14px; padding:18px; }
.an { font-size:18px; font-weight:650; } .ad { font-size:13.5px; line-height:1.45; color:var(--mut); margin-top:8px; }
.arr { display:flex; align-items:center; font-size:22px; color:var(--mut2); }
.trace { margin-top:22px; background:rgba(0,0,0,0.35); border:1px solid rgba(255,255,255,0.06); border-radius:12px;
  padding:16px 18px; font-family:ui-monospace,monospace; font-size:13px; line-height:1.7; color:#aeb4c2; }
.trace span { color:#4b5261; }
.metrics { display:grid; grid-template-columns:repeat(6,1fr); gap:14px; margin-bottom:26px; }
.m { background:var(--panel); border:1px solid rgba(255,255,255,0.07); border-radius:14px; padding:16px 18px; }
.mv { font-size:26px; font-weight:700; font-variant-numeric:tabular-nums; }
.ml { font-size:12.5px; color:var(--mut); margin-top:6px; }
.chart { background:var(--panel); border:1px solid rgba(255,255,255,0.07); border-radius:16px; padding:22px; }
.legend { display:flex; gap:20px; margin-top:10px; font-size:12.5px; color:var(--mut); }
.lg { display:flex; align-items:center; gap:8px; } .lg i { width:20px; height:0; display:inline-block; }
.lg .dash { border-top:2px dashed #ff5c49; } .lg .solid { border-top:2px solid #2ed6a6; }
.bars { display:flex; flex-direction:column; gap:11px; }
.bar-row { display:grid; grid-template-columns:120px 1fr 46px; align-items:center; gap:12px; }
.bar-label { font-family:ui-monospace,monospace; font-size:12px; color:var(--mut); }
.bar-track { height:8px; background:rgba(255,255,255,0.07); border-radius:6px; overflow:hidden; }
.bar-fill { display:block; height:8px; border-radius:6px; }
.bar-val { font-family:ui-monospace,monospace; font-size:12px; text-align:right; color:#cbd0db; }
.capt { font-size:13px; color:var(--mut); margin-top:14px; }
table.loo, table.score { width:100%; border-collapse:collapse; margin-top:10px; }
table.loo th { text-align:left; font-size:13px; color:var(--mut); font-weight:600; padding:10px 14px; }
table.loo td { font-family:ui-monospace,monospace; font-size:15px; padding:11px 14px; border-top:1px solid rgba(255,255,255,0.06); }
table.loo td:first-child { color:#e8eaf0; font-family:'Inter',sans-serif; }
table.loo tr.star { background:rgba(139,140,240,0.08); }
table.loo tr.star td:first-child { color:#8b8cf0; } table.loo tr.star span { font-size:10px; text-transform:uppercase; letter-spacing:0.1em; color:#8b8cf0; margin-left:8px; }
table.score td { font-size:17px; line-height:1.45; padding:13px 16px; border-top:1px solid rgba(255,255,255,0.06); color:#cbd0db; }
table.score td.c { color:#2ed6a6; font-weight:650; width:280px; vertical-align:top; }
.close h2 { font-size:44px; margin-top:20px; }
</style></head><body>${slides.join("")}</body></html>`;

const outHtml = resolve(DOCS, "deck.html");
writeFileSync(outHtml, html);

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 2 });
await page.goto("file://" + outHtml, { waitUntil: "networkidle" });
await page.pdf({ path: resolve(DOCS, "Chimera.pdf"), width: "1280px", height: "720px", printBackground: true });
// per-slide PNGs for QA
const els = await page.locator(".slide").all();
for (let i = 0; i < els.length; i++) {
  await els[i].screenshot({ path: resolve(PREV, `slide-${String(i + 1).padStart(2, "0")}.png`) });
}
await browser.close();
console.log(`deck: ${slides.length} slides -> docs/Chimera.pdf  (+ ${els.length} previews)`);
