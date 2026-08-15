# Kaggle Writeup - copy/paste content

Everything below maps to a field in the Kaggle Writeup form. Copy each block into
the matching field. The "Project Description" body uses the exact section headers
Kaggle pre-fills, so it drops in cleanly.

---

## TITLE (max 80 chars)

Chimera: a closed-loop adversarial AI lab for GenAI-era payment fraud

## SUBTITLE (max 140 chars)

An AI red team evolves fraud against a live detector; the detector retrains on what gets through. Identify, generate, defend as one loop.

## SUBMISSION TRACK

AI Defense Lab for Payment Security (auto-selected)

---

## PROJECT DESCRIPTION (paste into the rich-text body)

### Overview

Generative AI has made payment fraud faster, cheaper, and adaptive, and a fraud model trained on a fixed dataset only measures how well it fits yesterday's fraud. Chimera treats attack and defence as a single feedback loop instead of three separate deliverables. An AI red team discovers emerging GenAI fraud vectors, simulates them at fidelity across card, real-time account-to-account, and agentic-commerce rails, evolves each attack to evade the live detector, and the detector retrains on exactly what breaks through. The headline is not a static AUC. It is a measured hardening curve: under live evasion, aggregate recall collapses from 72.9% to 19.2% in one round, retraining restores it to 82.9%, and by round three the red team can no longer find easy evasion and the loop converges. My headline new capability is delegated-token / agent-identity abuse, a 2026 attack surface created by Mastercard Agent Pay and Visa's Trusted Agent Protocol that did not exist a year ago.

### Identify - Attacks Researched

I built an ATT&CK-style matrix for payment fraud: six kill-chain tactics (recon, access, setup, execution, cash-out, evasion) crossed with 16 techniques, each grounded in 2026 fraud intelligence and annotated with the observable signatures a defender can act on. Nine are simulated end-to-end; the rest are mapped for breadth and feed the ideation agent. Highlights chosen for novelty and impact:

- **Delegated-token / agent-identity abuse (my headline vector).** A payment can now be initiated by an autonomous agent on a cardholder's behalf. Mastercard Agent Pay issues an Agentic Token that binds the cardholder, the registered agent, and the scope of the mandate; Visa's Trusted Agent Protocol signs the agent's identity for merchants to verify. Stolen or replayed via prompt injection, token theft, or a rogue agent SDK, that credential lets an attacker spend inside someone else's mandate while looking identical to a legitimate agent on velocity, device and cadence.
- **Agentic-commerce carding.** Autonomous agents run machine-speed carding on delegated tokens. Visa logged a 450%+ rise in dark-web "AI Agent" chatter in H1 2026 and a 25% rise in malicious bot-initiated transactions.
- **Deepfake-authorised push payments.** Cloned voice/video induces the victim to authorise a real-time transfer. Auth cannot stop a genuine authorisation, so this is the single hardest vector to detect, and my results reflect that honestly.
- **Money-mule networks** on real-time rails (524,121 mule accounts flagged in India in March 2026 alone), plus synthetic-identity bust-out, account takeover, real-time investment ("pig-butchering") scams, structuring, and automated card testing.

A RAG-grounded ideation agent proposes novel variants where the detector is currently weak, retrieving from a cited intel corpus and returning a structured attack spec. It runs live on Groq with the open-weight gpt-oss-120b model and degrades to a deterministic planner if no key is present or the rate limit is hit, so a live demo never stalls.

### Generate - Attack Simulation

A synthetic dataset is only useful if it is hard. Three design choices make it credible:

- **Realistic population and behaviour.** Each account carries a latent profile (home geography weighted toward India for UPI relevance, Poisson diurnal spend cadence, log-normal ticket size, preferred merchant categories, a stable known-payee set, devices, balance). Legitimate traffic is drawn from these profiles across card-not-present, card-present, and real-time A2A, with a shared agentic channel. The run reported here is ~5,000 accounts over 30 days, ~238,000 events at a 1.39% fraud rate.
- **An entity graph.** Accounts, devices, merchants and beneficiaries form a NetworkX graph, so coordinated attacks (mule rings, shared-device carding, one agent draining many mandates) surface as structural anomalies rather than single-flag outliers.
- **Hard negatives.** This separates a credible benchmark from a fake one. I inject legitimate look-alikes (benign agentic shopping through trusted agents, large first-time payees, travel, high-in-degree collector accounts, recurring investments, shared family devices) into the exact feature regions where fraud lives. The result: the single most discriminative feature reaches an AUC of only 0.84, so no one flag separates the classes. Without hard negatives, any model scores a meaningless AUC of 1.0.

Nine attack synthesizers each manipulate only observable fields, reuse a shared transaction factory (no label leakage), and expose a bounded parameter space split into volume knobs and shape knobs. A black-box evolutionary (mu + lambda) search treats the detector as an oracle and tunes each attack's shape parameters to minimise mean risk; volume is frozen so it cannot cheat by emitting fewer events. The output is an evasive configuration and the detection collapse it causes, which becomes the next round's training data.

### Defend - Detection Model

The detector combines two channels over ~45 engineered features:

- **Supervised:** LightGBM gradient boosting with class-imbalance weighting, over four feature families: event (amount, tenure, auth/channel/rail/entry, geo, MCC risk), behavioural velocity (per-account time-windowed counts/sums, inter-arrival, amount z-score vs the account's own history), structural/graph (device fan-out, counterparty in-degree, A2A degree and PageRank), and a new **agent-identity family** for delegated-token abuse (network attestation, directory trust, mandate-cap breach, off-scope merchant risk, and agent-id replay fan-out).
- **Novelty:** an isolation forest plus PCA reconstruction error fit on legitimate traffic only. It flags events that do not look normal even when the supervised model has never seen that attack type. The blended risk lets novelty escalate an unknown but never mask a known hit.

Every decision carries per-event reason codes from LightGBM's exact TreeSHAP contributions, and risk maps to graded actions (allow, step-up auth, hold, block), mirroring 3-DS step-up and RBI's proposed friction and kill-switch. I report a cost-aware operating point (share of fraudulent value recovered, alerts per 10k, and a cost-optimal threshold that minimises expected loss plus review), which is what a fraud desk actually signs off.

### Results & Evaluation

All numbers are seeded and reproducible (`make train && make loop`).

**Detection (held-out test set of 71,372 events):** ROC-AUC 1.0000, PR-AUC 0.9999, F1 0.995, precision 0.998, recall 0.992. The false-positive rate is low but not fabricated: the confusion matrix shows 2 false positives on 70,384 legitimate transactions (0.003%), and at a threshold set to catch 90% of fraud, essentially no legitimate traffic is flagged because the first-generation attacks are well-separated. Per-vector recall is honest: deepfake authorised push sits at 80.5% because the victim uses their own device and genuine auth, while structural vectors are caught in full. The cost-optimal operating point recovers 100% of fraudulent value at ~140 alerts per 10,000 transactions. The near-perfect in-distribution AUC is expected against first-generation campaigns and is *not* something I lean on; the credible numbers are the real-data validation (ROC 0.95) and the three tests below.

**Novelty channel (leave-one-vector-out):** each attack is removed entirely from training, then scored. The result to read is delegated-token abuse: unseen, the supervised model catches 14.9% of it, while the agent-identity features plus the novelty channel recover 100%. That is a genuinely emerging vector caught as an anomaly before the detector has ever been trained on it.

**Closed-loop hardening curve:** baseline recall 72.9%, round 1 breach 19.2% then hardened to 82.9%, round 2 breach 33.7% then 99.6%, round 3 breach 99.6% then 99.1%. Each round the breach shrinks as the detector generalises; by round three the red team cannot find easy evasion. A fixed detector cannot adapt to evasion it has never seen; the closed loop trains on exactly those failures.

**Ablation:** on held-out PR-AUC, an isolation-forest-only detector scores 0.24 and logistic regression 0.96, while the full ensemble reaches 0.998. The complexity is a measured lift, not an assertion.

**External validation on real fraud data.** To check the approach is not overfit to my own synthetic data, I applied the same two-channel ensemble, unchanged, to the ULB real-world credit-card fraud benchmark (284,807 genuine European card transactions, 492 fraud, via OpenML). Out of the box it reaches ROC-AUC 0.95 and PR-AUC 0.81, in line with published gradient-boosting baselines, confirming the detection method transfers to real fraud. The synthetic benchmark is also non-trivial: its single most discriminative feature reaches AUC 0.84 - lower, i.e. harder, than the real dataset's 0.93 - so results on the simulator are meaningful rather than a toy.

**A graph neural network for coordinated rings.** Mule and structuring fraud is relational: an account can look ordinary on its own features yet sit one hop from a collector. I built a two-layer GraphSAGE (message passing over the account-transfer graph, in PyTorch) and benchmarked it against gradient boosting on the *same* per-account features. On held-out accounts, message passing lifts ring-detection PR-AUC from 0.84 to 0.998 (+0.15) on the simulator's ring topology; the takeaway is the lift, not the absolute number. Because graph results leak easily, I guard against it twice: gradient boosting on the same features scores only 0.84 (so the features do not give the label away), and an *inductive* split that removes every test-account edge during training still lifts PR-AUC to 0.992 (+0.15), so the graph signal is not an artifact of leakage. It confirms graph structure is decisive for coordinated fraud - validating the temporal-GNN upgrade path I flag under real-world feasibility.

**Evaluation rigor.** I ran the audits a fraud-ML reviewer would ask for (all reproducible under `scripts/`, artifacts in `data/artifacts/`). Rebuilding the structural features strictly point-in-time (no look-ahead, cumulative up to each event) barely moves detection: PR-AUC 0.9999 to 0.9987, recall 0.992 to 0.978. Results are stable across five seeds (ROC-AUC 1.00 +/- 0.00, recall 0.994 +/- 0.003). A component ablation shows the graph features are the decisive lift (PR-AUC 0.94 to 0.9999); the agent-identity features are deliberately *not* a crutch in-distribution (identical with or without), earning their place only on the unseen vector, where the novelty channel recovers 100%. Against standard models on the real ULB benchmark, Chimera's static ensemble is competitive rather than superior (held-out PR-AUC: Random Forest 0.82, LightGBM 0.81, Chimera 0.78, Logistic Regression 0.70) - the point is that the contribution is the *loop*, and the loop transfers to real fraud: perturbing real fraud toward the legitimate distribution drops recall from 84% to 59%, and retraining on the evasive samples recovers it to 100% at the same operating threshold. The honest floor is deepfake-authorised push payment at ~80% recall: when a victim genuinely authorises a real-time transfer from their own device, the signal is weak by construction and needs pre-transaction intelligence, not a better classifier.

### How It Was Built

Identify, generate and defend are one codebase, run as a single loop. The loop is a live multi-agent system: a compiled LangGraph StateGraph cycles four agents (recon: RAG ideation on gpt-oss-120b, red_team: evolutionary evasion, attack: generate the evasive stream and measure the breach, blue_team: retrain and measure the recovery) with a full execution trace; the shipped loop report is generated by this engine. A plain engine shares the same numeric primitives for LLM-free runs.

Stack: Python, scikit-learn, LightGBM, NetworkX, PyTorch (the GraphSAGE GNN), FastAPI, LangGraph, Groq (gpt-oss, free tier); Next.js, TypeScript, Tailwind, Framer Motion. It ships as a single monolithic Docker image (FastAPI serves the static Next export alongside the API), so the whole thing is one Render service and one URL. Everything derives from a single seed and is reproducible; a fast test suite covers generation, leakage checks, detection, evasion, taxonomy, RAG, and the multi-agent loop.

- Code repository: https://github.com/dhruv-decoder/chimera
- Live prototype: https://chimera-8vx7.onrender.com

### Challenges Faced

- **Making the benchmark honest.** My first synthetic dataset was trivially separable (AUC 1.0) because a single flag split the classes. I engineered six families of hard negatives that sit exactly where fraud lives, dropping the best single-feature AUC to 0.84 and forcing the model to combine signals.
- **A vector that velocity cannot catch.** A hijacked agent is fast, automated, runs on reputable cloud, and serves many principals, so it looks identical to a legitimate agent. I had to model that faithfully and then build a new agent-identity feature family (attestation, directory trust, mandate breach, replay fan-out) that separates them on credential integrity, not behaviour. Leave-one-out (15% to 100%) is the proof it works.
- **A real multi-agent bug.** The LangGraph loop crashed on multi-round runs because the router mutated state that LangGraph does not persist, so the stop condition never fired. I moved the round counter into a node, made the router pure, and added a regression test.
- **Robustness.** A hard per-call LLM timeout and an offline fallback guarantee the loop never hangs or depends on the network, even when the free-tier rate limit is hit mid-run.
- **A threading deadlock.** The GraphSAGE benchmark hung at 0% CPU: PyTorch and LightGBM each grab every core through OpenMP, and the two thread pools deadlock. Pinning `OMP_NUM_THREADS=1` and single-threading torch fixed it, and the benchmark now runs in seconds.

### Real-World Feasibility

Chimera is designed to sit where a bank already decides. The detector scores the fields a switch sees at authorisation (ISO 8583 on card rails, the request/response API on UPI) and returns a graded action inline; velocity and graph features are read from a streaming feature store computed point-in-time-correct. Labels arrive late (chargebacks, confirmed fraud, mule confirmations) into a labelled buffer, and the closed loop becomes a scheduled offline retrain in the model-risk sandbox with champion/challenger promotion. The controls map onto systems that exist today: risk-graded mitigation is how 3-DS step-up and RBI's friction/kill-switch work; graph features mirror NPCI's MuleHunter.AI; and the agent-identity features model the public concepts Agent Pay and the Trusted Agent Protocol describe, so that vector is a directory lookup from production. Per-event SHAP reason codes satisfy model-risk and audit. Paid infrastructure is a quality dial, not a rewrite: a managed streaming feature store, a temporal GNN for large coordinated rings, managed embeddings plus a vector DB for richer ideation grounding, and a hosted low-latency endpoint for always-on variant generation.

Responsible use: the system runs entirely on synthetic data it generates itself, with no real cardholders, PII, credentials, or live payment connectivity. The attack modules are parameterised statistical patterns that stress a detector, not operational playbooks or working exploit code, and cannot be pointed at a real system. The red team exists only to harden the blue team.

### What I Learned

A static AUC measures yesterday's fraud; the deliverable that matters is a hardening curve that shows the loop closing. The unsupervised novelty channel is the honest answer to "novel, emerging," because it catches attacks the model has never been trained on. And agentic commerce is the real 2026 frontier: the same delegated-agent credential that makes checkout effortless is a brand-new attack surface, and it is defended not on behaviour but on the integrity of the credential itself.
