# Chimera - Solution Walkthrough

**Mastercard Innovation Challenge @ GFF 2026 · AI Defense Lab for Payment Security**

One system that discovers emerging GenAI payment fraud, simulates it at fidelity
across modern rails, and hardens a detector on exactly what breaks through.
Identify, generate and defend are a single feedback loop, not three deliverables.

---

## 1. Thesis

Most fraud systems tackle detection in isolation and are graded against a fixed
dataset. That measures how well a model fits yesterday's fraud, not how it holds
up when an adaptive, GenAI-powered adversary changes shape against it. Chimera
treats attack and defence as one loop: an AI red team evolves evasive campaigns
against the *live* detector, and the detector retrains on what evades it. The
headline is not a static AUC. It is a **hardening curve** that shows the loop
closing:

| Round | Recall under live evasion (breach) | Recall after retrain (hardened) |
|---|---|---|
| 0 (baseline) | 72.9% | 72.9% |
| 1 | **19.2%** | 82.9% |
| 2 | 33.7% | 99.6% |
| 3 | 99.6% | 99.1% |

In round 1 the red team drives aggregate recall from 72.9% to 19.2% at a fixed
conservative operating point. Retraining on those evasive samples restores it to
82.9%. Each round the breach shrinks (19.2% then 33.7%) as the detector learns to
generalise, and by round 3 the red team can no longer find easy evasion against
the hardened model (pre-retrain recall stays at 99.6%). The loop converges. A
fixed detector does not adapt to evasion it has never seen; the closed loop trains
on exactly those failures. This report is produced by the multi-agent LangGraph
engine (Section 6).

### Evidence at a glance

The whole case, before the details. Each line is a separate experiment, reproducible
from `scripts/`, and the credible generalisation number is the real-data one - the
near-perfect synthetic AUC is expected against first-generation attacks, not the point.

| | Claim | Evidence |
|---|---|---|
| **Adaptive (simulated)** | the loop breaks and recovers | recall 72.9% -> 19.2% -> 82.9% -> 99.6% over 3 rounds |
| **Adaptive (real data)** | the loop transfers off the simulator | on ULB real fraud, recall 84% -> 59% under evasion -> 100% after retrain |
| **Novel vector** | catches an attack never seen in training | AGENT-HIJACK leave-one-out: supervised 14.9% -> novelty + agent-identity 100% |
| **Causally correct** | no look-ahead inflating the score | point-in-time PR-AUC 0.9999 -> 0.9987, recall 0.992 -> 0.978 |
| **Relational** | graph structure is decisive, not leaked | GNN ring PR-AUC 0.84 -> 0.99, and it holds inductively (no test edges in training) |
| **Generalises** | works beyond synthetic data | ULB real benchmark ROC-AUC 0.95, PR-AUC 0.81, in line with published baselines |
| **Honest floor** | states where it fails | deepfake-authorised push payment ~80% recall, by construction |

## 2. System at a glance

```
        +--------------- IDENTIFY ----------------+
        |  ATT&CK-style taxonomy (16 techniques)  |
        |  RAG intel corpus + ideation agent      |
        +---------------------+-------------------+
                              | novel / evasive attack specs
        +---------------------v------- GENERATE --+
        |  Multi-rail simulator (card, A2A,        |
        |  agentic) + entity graph + hard          |
        |  negatives + 9 attack synthesizers       |
        |  Evolutionary search evolves evasion     |
        +---------------------+-------------------+
                              | labelled event stream
        +---------------------v------- DEFEND -----+
        |  LightGBM + novelty channel (iForest     |
        |  + PCA recon) + agent-identity features  |
        |  + SHAP reason codes + cost operating pt |
        +---------------------+--------------------+
                              | misses / gaps
                              +------> feeds the next round (retrain + re-ideate)
```

One codebase, three pillars, one loop. The web console exposes each stage live,
including live red-team ideation from an open-weight model.

## Scorecard - how this maps to the five judging criteria

| Criterion | What I deliver | Evidence |
|---|---|---|
| **Diversity of attacks** | 16 techniques across a 6-tactic kill chain; 9 simulated end-to-end across card, real-time A2A and agentic rails; a live agent proposes more. | Threat Matrix; `identify/taxonomy.py`; ideation output tagged `groq:gpt-oss-120b`. |
| **Fidelity of simulation** | Latent-profile population, entity graph, and hard negatives placed exactly where fraud lives, so no single flag separates the classes. Validated against a real dataset. | Best single-feature AUC 0.84 (harder than real ULB's 0.93); the same ensemble scores ROC 0.95 on real ULB fraud; `generate/hard_negatives.py`, `scripts/validate_real.py`. |
| **Detection efficacy** | Two channels (LightGBM + novelty) + an agent-identity family + a GraphSAGE GNN for rings, cost-aware operating point. | Synthetic ROC-AUC 1.00 / PR-AUC 0.9999 (expected vs first-gen attacks); **real ULB ROC 0.95 / PR 0.81** is the credible number. 100% of fraud value at ~140 alerts/10k; holds point-in-time (PR 0.999) and across 5 seeds; GNN lifts ring PR-AUC 0.84 -> 0.99. |
| **Novelty** | A closed loop with a measured hardening curve; agentic-commerce identity abuse with a matching defence family; a live multi-agent (LangGraph) red team. | Hardening curve 73% to 19% to 83%; leave-one-out AGENT-HIJACK 15% to 100%; loop transfers to real fraud (84% -> 59% -> 100%); `loop/graph.py`. |
| **Real-world feasibility** | Auth-time schema, graded controls (3-DS / RBI friction), NPCI-style graph signals, agent-identity fields that map to Agent Pay / TAP; a concrete streaming-store integration path. | Section 10; risk-to-action mitigation; per-event SHAP reason codes for model-risk audit. |

## 3. Identify - mapping the threat

I built an **ATT&CK-style matrix for payment fraud**: six tactics across the
kill chain (recon, access, setup, execution, cash-out, evasion) crossed with 16
techniques, each grounded in 2026 fraud intelligence and annotated with the
observable signatures a defender can exploit. Nine are simulated end-to-end;
the rest are mapped for breadth and form the queue the ideation agent draws from.
Highlights, chosen for breadth and novelty:

- **Delegated-token / agent-identity abuse (AGENT-HIJACK)** - a hijacked or
  malicious AI shopping agent spends inside a cardholder's delegated mandate
  under Mastercard Agent Pay (Agentic Token) or Visa's Trusted Agent Protocol.
  This is a 2026 frontier tied to newly-deployed agentic payment protocols, and it
  is my headline new capability (Section 8).
- **Agentic-commerce carding (AGENT-CARD)** - autonomous agents running
  machine-speed carding on delegated credentials. Visa logged a 450%+ rise in
  dark-web "AI Agent" chatter in H1 2026 and a 25% rise in malicious
  bot-initiated transactions.
- **Deepfake-authorised push payments (DF-APP)** - cloned voice/video induces the
  victim to authorise a real-time transfer. Auth controls cannot stop a genuine
  authorisation; this is the single hardest vector to detect and my results
  reflect that honestly.
- **Money-mule networks (MULE-NET)** on real-time rails - 524,121 mule accounts
  flagged in India in March 2026 alone; fan-in/fan-out layering within minutes.
- Synthetic-identity bust-out, account takeover, pig-butchering, structuring,
  automated card testing.

**Ideation agent.** A RAG-grounded agent proposes *novel variants*. Given where
the detector is currently weak (an attack that just evaded it, plus the evasive
parameters found), it retrieves relevant intel from a TF-IDF corpus (taxonomy +
cited 2026 notes) and returns a structured attack spec: technique mapping, a
concrete twist, parameter directions, and the residual observable footprint. It
runs live on **Groq** with the open-weight `openai/gpt-oss-120b` model (free
tier). It degrades gracefully: if no key is present, or the free-tier rate limit
is hit mid-run, it falls back to a deterministic planner, so the loop never stalls
and a live demo never depends on the network. In the shipped loop report the
early-round ideation is tagged `groq:openai/gpt-oss-120b` (real model outputs, not
canned text); later rounds show the offline tag where the rate limit kicked in -
the fallback working as designed. A hard per-call timeout guarantees a single slow
request can never hang the loop.

> Note on models: Groq retired the Llama 3.x endpoints on 17 June 2026. Chimera
> uses the current open-weight replacements (`gpt-oss-120b` / `gpt-oss-20b`).

## 4. Generate - fidelity is the point

A synthetic dataset is only useful if it is *hard*. Three design choices make it
so.

**Realistic population and behaviour.** Each account carries a latent profile:
home geography (weighted toward India for GFF/UPI relevance), spend cadence
(Poisson, diurnally shaped), log-normal ticket size, preferred merchant
categories, a stable known-payee set, device(s) and a rough balance. Legit
traffic is drawn from these profiles across three rails: card-not-present,
card-present, and real-time account-to-account. The agentic channel carries both
legitimate and malicious agent traffic.

**An entity graph.** Accounts, devices, merchants and beneficiaries form a graph,
so coordinated attacks (mule rings, shared-device card testing, one agent
draining many mandates) are expressible and show up as *structural* anomalies
rather than being separable by a single flag.

**Hard negatives.** This is what separates a credible benchmark from a fake one.
I deliberately inject legitimate traffic into the feature regions where fraud
lives: benign agentic shopping through trusted, network-registered agents (which
legitimately serve many principals from shared cloud infrastructure), legitimate
large first-time payees, travel (foreign IP + cross-border), high in-degree
"collector" accounts (landlords, clubs), recurring escalating investments (a
benign analogue of pig-butchering), and shared family devices. Without these, any
single flag perfectly separates the classes and the model scores a meaningless
AUC of 1.0.

**Nine attack synthesizers.** Each manipulates only observable fields, reuses the
shared transaction factory (no label leakage), and exposes an explicit, bounded
parameter space split into *volume* knobs and *shape* knobs. The shape knobs are
exactly the levers that trade detectability for yield.

**Adversarial evasion.** An evolutionary (mu + lambda) search treats the detector
as a black box and tunes each attack's shape parameters to minimise mean risk.
Volume is frozen so it cannot cheat by emitting fewer events; it must make each
event stealthier. The output is an evasive configuration and the detection
collapse it causes, which becomes the next round's training data.

## 5. Defend - accuracy with an honest novelty story

**Three signal families, two channels.** Around 45 engineered features across:

- *Event* - amount, tenure, auth/channel/rail/entry encodings, geo, MCC risk.
- *Behavioural velocity* - per-account time-windowed counts/sums, inter-arrival,
  amount z-score vs the account's own expanding history.
- *Structural / graph* - device fan-out, counterparty in-degree, A2A
  account-graph degree and PageRank.
- *Agent-identity* (new) - attestation, directory trust, mandate-cap breach,
  off-scope high-risk merchant, and agent-id principal fan-out. This is the
  family that separates a hijacked delegated agent from a legitimate one when
  velocity, device and cadence cannot (Section 8).

These feed two channels:

1. *Supervised* - LightGBM gradient boosting, class-imbalance weighted.
2. *Novelty* - an isolation forest plus PCA reconstruction error fit on
   legitimate traffic only. It flags events that don't look normal even when the
   supervised model has never seen that attack type. This is the channel for
   previously unseen vectors and the direct answer to "novel, emerging."

The blended risk lets novelty *escalate* an unknown but never mask a known hit.

**Explainability.** Per-event reason codes come from LightGBM's exact TreeSHAP
contributions (`pred_contrib`), with no extra serving dependency. The console
shows the top signed contributions for any flagged transaction.

**Cost-aware operating point.** I report the metrics a fraud desk signs off, not
just an AUC: the share of fraudulent *value* recovered (amount-weighted recall),
the review workload (alerts per 10k transactions), and a cost-optimal threshold
that minimises expected loss (missed fraud value + review cost per alert). On the
held-out test set the cost-optimal point recovers **100% of fraud value at ~140
alerts per 10k transactions**.

**Mitigation policy.** Risk maps to graded actions - allow / step-up auth / hold
/ block - which is how RBI's proposed friction (delays on large first-time
transfers, a transaction kill switch) and 3-DS step-up work in production.

## 6. The closed loop

Each round: the red team evolves evasion against the current detector; a fresh
evasive dataset is generated; the current detector is scored on it (**pre-retrain
recall - the breach**); the detector retrains on all accumulated data including
the evasive samples; it is re-scored on a fresh evasive holdout (**post-retrain
recall - the recovery**). The per-round pre/post recall is the hardening curve in
Section 1.

### Multi-agent orchestration (LangGraph)

The loop is a genuine multi-agent system, not a for-loop in disguise. It ships as
a compiled **LangGraph `StateGraph`** (`loop/graph.py`) with four agent nodes that
pass a shared typed state and cycle via a conditional edge until the round budget
is spent:

```
recon (RAG ideation, gpt-oss-120b)
   -> red_team (evolutionary evasion search vs the live model)
   -> attack (generate the evasive stream, measure the breach)
   -> blue_team (retrain on the misses, measure the recovery)
   -> [route: loop back to recon, or END]
```

Each node appends to an execution `trace`, so the run is observable end-to-end;
the shipped `loop_report.json` is generated by this engine (`meta.orchestration =
langgraph`) and the console renders both the agent pipeline and the trace. A plain
engine (`orchestrator.py`) shares the same numeric primitives for callers that
want the metrics without the LLM dependency, so the two stay consistent.

## 7. Results

Seeded and reproducible via `make train && make loop`. Simulation: ~5,000
accounts over 30 days, ~238k events, 1.39% fraud.

### Detection (held-out test set)

| Metric | Value |
|---|---|
| ROC-AUC | 1.0000 |
| PR-AUC | 0.9999 |
| Precision @ max-F1 | 0.998 |
| Recall @ max-F1 | 0.992 |
| F1 | 0.995 |
| FPR @ max-F1 | 0.003% |
| FPR @ 90% recall | 0.000% |
| Fraud value recovered (cost-optimal) | 100% |
| Alerts / 10k txns (cost-optimal) | 140 |

The near-perfect in-distribution numbers are *expected*, not the point: first-
generation campaigns carry loud structural signatures. Per-vector recall is
honest - the deepfake authorised-push vector sits at **80.5%** because the victim
uses their own device and genuine auth. The interesting results are the two that
follow.

### Novelty channel - leave-one-vector-out

Each attack type is entirely removed from training, then scored. The supervised
model degrades on the unseen vector; the novelty channel recovers much of it.

| Unseen vector | Supervised | Novelty | Blended |
|---|---|---|---|
| **AGENT-HIJACK** | **14.9%** | **100%** | **100%** |
| ATO-STUFF | 57.6% | 78.1% | 79.5% |
| CARD-TEST | 100% | 95.8% | 100% |
| MULE-NET | 100% | 100% | 100% |
| STRUCT | 100% | 100% | 100% |
| DF-APP | 80.0% | 19.1% | 32.2% |
| PIG-BUTCH | 100% | 36.7% | 47.1% |
| SYN-ID | 1.7% | 19.9% | 19.9% |

The result to read is the first row. With delegated-token abuse **entirely
removed from training**, the supervised model catches 14.9% of it - but the
agent-identity features plus the novelty channel recover **100%**. That is a
genuinely emerging vector caught as an anomaly before the detector has ever been
trained on it. The heterogeneity is honest: novelty helps enormously on some
vectors and little on others (a socially-engineered push transfer looks like a
legitimate one), which is exactly why the closed loop matters.

### Closed-loop hardening curve

The table in Section 1. Under evasion at a fixed conservative threshold, the
behavioural and social-engineering vectors (deepfake push, pig-butchering,
structuring, account takeover, and a well-tuned agent hijack) can be driven
toward invisibility, while structural vectors (shared-device carding, agentic
velocity) stay robust. Closed-loop retraining is what recovers the evadable
classes: a fixed detector does not adapt to those evasive samples, the loop trains
on them.

### External validation on real fraud data

A fair objection to any synthetic benchmark is "does it only work on data you
made up?". To answer it, the *same two-channel ensemble* (gradient boosting plus
the isolation-forest + PCA novelty channel) is applied, unchanged, to the ULB
real-world credit-card fraud dataset - 284,807 genuine European card transactions,
492 fraud (0.17%), pulled via OpenML (`scripts/validate_real.py`; the raw file is
cached locally and never committed).

| Model on real ULB fraud (held-out) | ROC-AUC | PR-AUC |
|---|---|---|
| Gradient boosting (supervised) | 0.95 | 0.81 |
| Novelty channel only | 0.94 | 0.20 |
| Full ensemble | 0.95 | 0.78 |

Out of the box, with no dataset-specific tuning, the method reaches ROC-AUC 0.95
and PR-AUC 0.81 on real fraud, in line with published gradient-boosting baselines
for this benchmark. Two honest notes: the novelty channel does not add
in-distribution lift here (it slightly lowers ensemble PR-AUC) because its value
is specifically on *unseen* attacks, as the leave-one-out study shows, not on a
fully-labelled set; and the synthetic simulator is genuinely hard by the same
measure - its single most discriminative feature reaches AUC 0.84, *lower* (harder)
than the real dataset's 0.93 - so results on the simulator are meaningful rather
than trivially separable. Transaction amounts in both are heavy-tailed and
right-skewed (`external_amount.png`), the hallmark of real spend, though the scale
differs because ULB is European card spend and the simulator spans card plus
real-time transfers.

### A graph neural network for coordinated rings

Per-transaction and per-account models judge an entity on its own features. Mule
and structuring fraud is relational: an account can look ordinary alone yet sit
one hop from a collector. A graph neural network propagates signal along the
transfer graph, so an account is judged partly by the company it keeps.

I built a compact two-layer **GraphSAGE** (mean-aggregation message passing over
the account-to-account graph, in PyTorch; `defend/gnn.py`) and benchmarked it
against gradient boosting on the *same* per-account node features - so the only
difference is whether graph structure is used. On held-out accounts:

| Ring detection (held-out accounts) | ROC-AUC | PR-AUC |
|---|---|---|
| Gradient boosting (node features only) | 0.89 | 0.84 |
| GraphSAGE GNN (transductive) | 1.00 | 0.998 |
| **GraphSAGE GNN (inductive, no leakage)** | **1.00** | **0.992** |

Message passing lifts ring-detection PR-AUC from 0.84 to 0.998 (+0.15;
`gnn_pr.png`, `scripts/gnn_benchmark.py`) on the simulator's ring topology - the
takeaway is the lift, not the absolute number. Graph structure is decisive for
coordinated fraud, which is exactly why a temporal GNN is the flagged paid-infra
upgrade in Section 10.

**Two guards against the leakage that inflates graph results.** Graph benchmarks
are notoriously easy to leak, and a PR-AUC of 0.998 invites scrutiny, so the result
is checked twice. First, if the node features already encoded the label, gradient
boosting on those same features would score near 1.0; it scores 0.84, so the +0.15
the GNN adds is graph structure, not a feature that gives the answer away. Second,
the *inductive* row removes every edge incident to a test account during training,
so held-out accounts' connectivity never touches the learned weights and attaches
only at inference - the strictest no-contamination split. The lift barely moves
(+0.15 to +0.148, PR-AUC 0.992), so the graph signal is real and not an artifact of
the test nodes being visible while training. Here it is demonstrated, not asserted. (An
engineering aside: PyTorch and LightGBM both claim every core via OpenMP and their
thread pools deadlock; pinning `OMP_NUM_THREADS=1` resolves it.)

## 7b. Evaluation rigor

The audits a fraud-ML reviewer would run, so the strong headline numbers are not
taken on faith. All are reproducible (`scripts/`, artifacts in `data/artifacts/`).

**Point-in-time (no look-ahead).** A live decision at time t may only use
information from before t. The structural features are rebuilt causally (cumulative
device/counterparty/graph degree + agent-id fan-out; PageRank dropped as it needs an
incremental engine) and detection re-evaluated:

| Features | ROC-AUC | PR-AUC | recall | F1 |
|---|---|---|---|---|
| batch (look-ahead) | 1.0000 | 0.9999 | 0.992 | 0.995 |
| point-in-time (causal) | 1.0000 | 0.9987 | 0.978 | 0.987 |

The drop is small because the velocity and amount-history features were already
causal by construction; only the batch aggregates change. The results are not a
look-ahead artifact.

**Stability across 5 seeds** (1, 42, 123, 777, 2026): ROC-AUC 1.00 +/- 0.00,
PR-AUC 0.9999 +/- 0.00, recall 0.994 +/- 0.003, and unseen AGENT-HIJACK novelty
recovery 1.00 +/- 0.00. Nothing here is seed-dependent.

**Component ablation.** Held-out PR-AUC: event+velocity 0.943 -> +graph 0.9999
(the graph features are the decisive lift) -> +agent-identity 0.9999; logistic
regression 0.96; full ensemble with the novelty channel 0.996. Every family earns
its place. The **agent-identity ablation** is deliberately honest: in-distribution,
with vs without those features is identical (100% hijack recall, 1.0% FPR) - they
are not a crutch. Their value is on the *unseen* vector, where the novelty channel
reads the credential-integrity anomalies to recover 100%.

**Novelty vs benign novelty.** At a threshold set to a 1% budget on ordinary
legitimate traffic, the novelty channel flags 83% of fraud but 42% of the
deliberately-hard benign traffic (family devices, travel, collector accounts, ...).
That 42% is exactly why novelty is a *weighted escalation* signal (0.45) that never
decides alone - it is not a standalone outlier detector.

**Class-imbalance stress.** PR-AUC holds ~1.00 at 5% / 2% / 1% / 0.5% fraud and
degrades gracefully to 0.78 at 0.1%; alerts per 10k fall from ~140 to ~12 as
prevalence drops. Real monitoring runs at low prevalence, and the detector holds.

**Baselines and the loop on real data.** On the ULB real benchmark, standard models
and Chimera's ensemble are close (held-out PR-AUC: XGBoost 0.84, Random Forest 0.82,
LightGBM 0.81, Chimera 0.78, Logistic Regression 0.70), which is the point - the
contribution is not a marginally-better static classifier, it is the loop. The loop is
also model-agnostic: the base learner is a swap, not a redesign, so adopting the
stronger XGBoost or Random Forest baseline as the supervised channel is a config change. And the loop transfers
to real fraud: perturbing real fraud toward the legitimate distribution drops recall
from 84% to 59%, and retraining on those evasive samples recovers it to 100% at the same
operating threshold (`scripts/benchmark_baselines.py`, `notebooks/external_benchmark.ipynb`).

**LLM vs offline ideation.** The live gpt-oss-120b agent proposes a far larger,
more varied attack-hypothesis space than the deterministic offline planner - twist
vocabulary 163 vs 67 across nine variants - so the LLM genuinely adds diversity; the
offline path exists only so the loop never stalls.

**Throughput** (single-process CPU): ~15.8k events/s generated, ~49k/s feature build,
~1.4k/s scored including the novelty channel and reason codes. A streaming deployment
parallelises these; the point is the prototype is not a toy on runtime either.

**Combined attack chains (beta).** Real campaigns are rarely one technique. A beta
probe (`scripts/attack_chains.py`, isolated from the shipped pipeline) links two
stages: a synthetic-identity bust-out ages a set of accounts, which then run a
low-observability, authorised-push-style cash-out to ordinary payees. Measured on
the stage-2 fraud at a matched 1% alert budget:

| Scenario | Supervised only | Full ensemble |
|---|---|---|
| single-stage (cold accounts), shipped detector | 38% | 100% |
| chained (aged bust-out), shipped detector | **8%** | 62% |
| chained, after retrain (fresh holdout, retrained detector) | 94% | 76% |

Read the rows carefully, because they are not all the same measurement. The first
two use the *shipped* detector at its 1% budget; the third uses a detector
*retrained* on the chain, scored on a *fresh* chained holdout at its own 1% budget.
So the honest before/after for retraining is the second row versus the third
(supervised 8% to 94%, full ensemble 62% to 76% - both improve); the 100% in row one
is the easy single-stage attack, not a baseline the retrained number should be
compared against.

Two things it demonstrates, both on-thesis. First, chaining is a genuine evasion of
the *supervised* classifier - recall collapses from 38% to 8% as the aged, low-signal
cash-out removes the tenure and velocity cues a cold ring would trip. Second, the
novelty channel is the safety net that stops it going to zero (62%), and retraining
lifts both channels on the held-out chain - the same lesson as AGENT-HIJACK, now
against a multi-stage threat. The novelty dip to 62% is honest: a sufficiently
patient chain degrades even the ensemble, which is exactly why the loop, not any
single model, is the contribution. Marked beta because it is a scripted two-stage
chain, not yet wired into the evolutionary search.

## Coverage - identified vs simulated vs evaluated

To keep the breadth honest and legible:

| Stage | Count |
|---|---|
| Techniques identified (ATT&CK matrix) | 16 |
| Simulated end-to-end | 9 |
| Adversarially optimised (evasion search) | 9 |
| Evaluated as unseen (leave-one-vector-out) | 9 |
| Validated on real data | detector + loop (ULB) |
| Live in the web console | all 9 |

## What the system cannot detect (by design)

Deepfake-authorised push payment sits at ~80% recall and is the honest floor. When
the victim authorises a real-time transfer themselves, from their own device, after
genuine authentication, the transaction is legitimate from the network's point of
view - the observable signal is weak by construction. No amount of modelling makes a
genuinely-authorised payment look fraudulent; this class needs pre-transaction
signals (scam-intent detection, payee-risk intelligence, confirmation-of-payee), not
a better classifier. Stating this plainly is more useful than claiming to solve it.

## 8. The headline capability - agentic-commerce identity abuse

The 2026 frontier is that a payment can now be initiated by an autonomous agent
on a cardholder's behalf. Mastercard Agent Pay issues an Agentic Token that binds
three identities into one credential (the cardholder, the registered agent, and
the scope of the mandate); Visa's Trusted Agent Protocol signs the agent's
identity into request headers for merchants to verify against a directory.

That binding is what an attacker attacks. Credential theft, prompt injection of a
shopping agent, or a rogue agent SDK lets an attacker spend inside someone else's
mandate. The hard part, in Visa's own words, is telling a legitimately delegated
agent from a scripted attacker reusing a stolen token. Velocity, device and
cadence cannot answer it: a real trusted agent is also fast, automated, runs on
reputable cloud, and serves many principals. I modelled this faithfully - the
hijack shares infrastructure and cadence with legitimate agents - so the only
thing left to separate them is credential integrity:

- **Attestation** - was the agent's network signature verified, or missing/replayed?
- **Directory trust** - reputation of the agent identity.
- **Mandate scope** - amount over the delegated cap, off-scope high-risk merchant.
- **Replay structure** - one agent id draining many mandates at once.

I added an agent-identity feature family that reads exactly these, and the
attack exposes them as evasion knobs (raise attestation, raise trust, stay under
the cap, buy in-scope) so the red team can tune toward mimicry - and the loop
recovers it. The leave-one-out result (15% to 100%) is the proof that this family
turns an unseen, emerging vector into a detectable anomaly.

## 9. What's novel here

- A **working closed loop** with a measured hardening curve (73% to 19% to 83% to
  convergence), not three disconnected deliverables.
- **Agentic-commerce identity abuse** as a first-class simulated vector with a
  matching defence family - the 2026 frontier grounded in Agent Pay and the
  Trusted Agent Protocol.
- **Live red-team ideation** from an open-weight model (`gpt-oss-120b`), running
  in the real loop, not mocked.
- **Adversarial evasion as a live red team** (black-box evolutionary search
  against the deployed model), turning the generator into a stress-tester.
- A **novelty channel** evaluated with leave-one-vector-out, directly answering
  "novel, emerging."
- **Cost-aware reporting** (fraud value recovered, alerts per 10k, cost-optimal
  threshold) and hard-negative-driven benchmarking - the metrics a fraud team
  actually uses.

## 10. Real-world feasibility

### How it plugs into a live payment stack

Chimera is designed to sit where a bank or network already makes decisions, not to
replace that stack.

- **Inline scoring at authorisation.** The detector runs as a scoring service
  behind the existing authorisation path (an ISO 8583 message on card rails, or
  the request/response API on UPI / FedNow / an acquirer gateway). It reads the
  fields already present at auth time - the exact fields in my event schema - and
  returns a risk score plus a graded action: allow, step-up (3-DS / UPI-PIN /
  biometric), hold, or block. Inference is a single LightGBM call plus the novelty
  channel, which is single-digit milliseconds; the graph and velocity aggregates
  are read from a feature store, not recomputed inline.
- **Streaming features.** The velocity and graph features move to a streaming
  feature store (Kafka + Flink, or a managed store) computed point-in-time-correct
  (no look-ahead). Account and agent-id aggregates are updated on each event and
  read at scoring time. This is the one real engineering change from the batch
  prototype, and it is standard fraud-platform work.
- **Label feedback.** Ground truth arrives late and noisily - chargebacks,
  confirmed-fraud tags, customer reports, mule-account confirmations. These flow
  into a labelled buffer. The closed loop then runs as a scheduled offline job in
  the model-risk sandbox: retrain on the buffer plus the red team's newest evasive
  samples, evaluate, and promote via champion/challenger with shadow scoring before
  any traffic shift.
- **Native integration points.** The controls map onto systems that already exist
  in 2026: risk-graded mitigation is how 3-DS step-up and RBI's friction /
  kill-switch proposals work; the graph features are the signal NPCI's
  MuleHunter.AI and the RBI Digital Payments Intelligence Platform already act on
  (Chimera can consume their shared mule signals as features); and the
  agent-identity features model the public concepts Mastercard Agent Pay's Agentic
  Token and Visa's Trusted Agent Protocol describe - attestation status, directory
  trust, mandate scope - so that vector is a directory lookup away from production.
- **Governance.** Every decision carries per-event reason codes (SHAP), which is
  what model-risk (SR 11-7-style) and audit require. The system stays inside the
  bank's controlled environment with human-in-the-loop review on held and
  stepped-up cases.

### What paid infrastructure and keys buy you

Kept deliberately small - only what is appropriate, and none of it changes the
architecture:

- **Streaming feature store** (managed Feast + Redis, or Tecton). Turns the batch
  aggregates into point-in-time-correct online features. This is the one upgrade
  that is a genuine requirement for live deployment, not a nicety.
- **Temporal graph neural network** over the entity graph, replacing the
  NetworkX-derived features fed to LightGBM. This is the current SOTA for large,
  coordinated mule rings and where 2026 fraud-GNN research points; it lifts recall
  on exactly the coordinated cases a per-transaction model misses.
- **Managed embeddings + a vector DB** (pgvector or Pinecone) in place of the
  TF-IDF RAG - better grounding for the ideation agent as the intel corpus grows
  to full threat-feed scale.
- **A paid Groq (or equivalent) tier / hosted endpoint** for the ideation and
  red-team agents - higher rate limits and a larger model for always-on live
  variant generation, removing the offline fallback in production.

These are quality dials on latency, grounding, and recall on coordinated rings.
The core loop, schema, controls and reason codes are unchanged.

## 11. Reproducibility & running it

```bash
make setup        # venv + backend (agents) + frontend deps
make train        # simulate + train + evaluate + LOO study  -> data/artifacts
make loop         # closed adversarial loop -> loop_report.json
make dev          # API :8000 + web :3000
make test         # fast end-to-end suite (7 checks)
```

Every stochastic step is seeded from `CHIMERA_SEED`. The full dataset regenerates
bit-for-bit from `(seed, config)` recorded in `sim_meta.json`; only the trained
detector and JSON reports are persisted.

## 12. Limitations (stated plainly)

- Synthetic data, however carefully constructed, is not live payment traffic;
  absolute metrics will differ on real streams and should be read as relative and
  methodological, not as production SLAs.
- Batch aggregation is temporally optimistic vs a streaming deployment (noted in
  Section 10); I flag it rather than hide it.
- The adversarial search is a practical black-box optimiser, not a formal
  robustness guarantee; it demonstrates the loop, it does not certify it.

## 13. Responsible use

Chimera is defensive tooling. It runs entirely on synthetic data it generates
itself, with no real cardholders, PII, credentials or live payment connectivity.
The attack modules are parameterised statistical patterns (amounts, timing, graph
shape, credential-integrity fields) tuned to stress a detector, not operational
playbooks, social-engineering scripts, or working exploit code, and they cannot
be pointed at a real payment system. The value is one-directional by
construction: the red team exists only to harden the blue team, and the loop's
output is a stronger detector plus a prioritised view of which vectors most need
human review and step-up controls. In a real deployment this belongs inside a
bank's controlled environment with human oversight, aligned to responsible-AI and
model-risk governance.
