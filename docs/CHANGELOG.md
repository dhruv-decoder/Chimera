# Changelog - rigor & credibility additions

A running log of experiments and features added after the core system was
complete, to strengthen evaluation rigor and real-world credibility. Each item is
additive; the core writeup structure is unchanged.

## Real-world grounding
- **External validation on real fraud data** (`scripts/validate_real.py`,
  `data/artifacts/external_validation.json`): the unchanged two-channel ensemble on
  the ULB real credit-card fraud benchmark (284,807 real transactions) - ROC 0.95,
  PR-AUC 0.81. Confirms the method transfers off the synthetic simulator.
- **GraphSAGE GNN for coordinated rings** (`chimera/defend/gnn.py`,
  `scripts/gnn_benchmark.py`, `gnn_benchmark.json`): message passing lifts
  ring-detection PR-AUC from 0.84 (gradient boosting, same features) to 0.998.

## Evaluation rigor
- **Point-in-time (no look-ahead) features** (`features.py causal=True`,
  `scripts/point_in_time.py`, `point_in_time.json`): structural features recomputed
  strictly from events before t. Detection barely moves (PR-AUC 0.9999 -> 0.9987,
  recall 0.992 -> 0.978) because velocity/amount-history were already causal; only
  the batch aggregates and PageRank change. Confirms results are not a look-ahead
  artifact.
- **Stability across 5 seeds** (`scripts/rigor.py`, `rigor_report.json`): ROC-AUC
  1.00 +/- 0.00, PR-AUC 0.9999 +/- 0.00, recall 0.994 +/- 0.003; unseen AGENT-HIJACK
  novelty recovery 1.00 +/- 0.00. Results are not seed-dependent.
- **Component ablation**: event+velocity PR-AUC 0.943 -> +graph 0.9999 (graph is the
  big lift) -> +agent-identity 0.9999; logistic regression 0.96; full ensemble 0.996.
- **Agent-identity ablation**: in-distribution, with vs without the agent-identity
  features is identical (100% hijack recall, 1.0% FPR) - the family is not a crutch;
  its value is on the *unseen* vector (novelty recovery 100%).
- **Novelty vs benign novelty**: at a 1% budget on ordinary legit traffic, the
  novelty channel flags 83% of fraud but only 42% of deliberately-hard benign
  traffic - which is why it is a weighted escalation signal (0.45), never a
  standalone detector.
- **Class-imbalance stress**: PR-AUC holds ~1.00 at 5% / 2% / 1% / 0.5% fraud and
  degrades gracefully to 0.78 at 0.1%; alerts/10k fall as prevalence drops.
- **Latency / throughput** (single-process CPU): ~15.8k events/s generated, ~49k/s
  feature build, ~1.4k/s scored (incl. novelty + reason codes).

## Real-benchmark grounding
- **Baselines + loop on real data** (`scripts/benchmark_baselines.py`,
  `benchmark_report.json`, `notebooks/external_benchmark.ipynb`): LR / RandomForest /
  XGBoost / LightGBM vs Chimera's ensemble on the ULB benchmark (competitive, not a
  better static classifier), plus the evasion -> retrain loop applied to *real* fraud.
- **LLM vs offline ideation** (`scripts/llm_ablation.py`, `llm_ablation.json`): the
  live model produces a far larger, more varied attack-hypothesis vocabulary than the
  deterministic offline planner; the offline path exists only for robustness.

## Combined attack chains (beta)
- **Multi-stage chain probe** (`scripts/attack_chains.py`, `attack_chains.json`,
  `make chains`, isolated from the shipped pipeline): a synthetic-identity bust-out
  ages a ring of accounts that then run a low-observability, authorised-push-style
  cash-out. On the stage-2 fraud at a matched 1% budget, chaining collapses the
  *supervised* channel (38% -> 8% recall) while the novelty channel holds it at 62%,
  and retraining restores supervised recall to 94%. Demonstrates a real combined
  evasion + the two-channel safety net + loop recovery, all on-thesis (same lesson as
  AGENT-HIJACK). Surfaced in the live Validation view behind a "beta" chip.

## GNN leakage proof + presentation hardening (final review)
- **Inductive GNN evaluation** (`defend/gnn.py` `train_gnn(infer_A=...)`,
  `scripts/gnn_benchmark.py`): graph results leak easily and 0.998 invites scrutiny,
  so the benchmark now also runs a leakage-proof split - every edge incident to a
  test account is removed during training, and held-out accounts attach only at
  inference. The lift barely moves (PR-AUC 0.998 transductive -> 0.992 inductive;
  +0.154 -> +0.148 over gradient boosting), so the graph signal is not a leakage
  artifact. Second guard: gradient boosting on the same node features scores only
  0.84, so the features do not encode the label. Both are now stated in the docs.
- **"Evidence at a glance"** table added to the top of the walkthrough (adaptive
  simulated / adaptive real / novel vector / causal / relational / generalises /
  honest floor) so the five judging criteria land on the first screen.
- **Scorecard** now shows the real ULB numbers (ROC 0.95 / PR 0.81) next to the
  synthetic ones, so a skimming judge sees the credible number immediately.
- **Wording precision**: "a single static model cannot do this; a loop can" ->
  "a fixed detector does not adapt to evasion it has never seen; the closed loop
  trains on exactly those failures" (3 places). Added the model-agnostic note (the
  base learner is a swap, not a redesign).

## Showcased in the live app + claim hygiene
- **New "Validation" console view** (`frontend/components/views/Evidence.tsx`, served
  by a new `GET /api/validation` reading the artifacts): the real-data ROC/PR, the
  GNN lift, point-in-time, seed stability, the baselines bars, the loop-on-real
  (84% -> 59% -> 100%), and a datasets/benchmarks/models reference panel - so the
  external grounding is visible in the product, not only in the docs. Screenshot:
  `docs/gallery/07-validation.png`.
- **Submission guide** now has a "7b. External data, models and benchmarks" step for
  the Kaggle Datasets/Models/Benchmarks tabs (ULB dataset, gpt-oss, LightGBM,
  GraphSAGE), and lists `notebooks/external_benchmark.ipynb`.
- **Claim hygiene** (kept honest, nothing inflated): standardised the synthetic
  best-single-feature AUC to 0.84 everywhere; framed the GNN 0.998 as "on the
  simulator's ring topology - the takeaway is the lift"; the loop-on-real recovery
  is "to 100% at the same operating threshold"; the near-perfect synthetic AUC is
  explicitly flagged as *not* the point (the real-data 0.95 is the credible number);
  README FPR now cites the honest 2/70,384 (0.003%) instead of a bare 0.000%.
