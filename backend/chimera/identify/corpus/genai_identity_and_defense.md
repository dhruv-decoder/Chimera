---
title: GenAI identity fraud and adversarial-robust defence (2026)
tags: [synthetic-identity, deepfake-kyc, faas, adversarial, gnn, gradient-boosting, robustness]
sources:
  - https://withpersona.com/blog/7-ways-synthetic-identity-fraud-is-changing-in-2026
  - https://www.pwc.com/cz/cs/blog/rizeni-rizik/the-fraud-trend-to-watch-in-2026-and-beyond.html
  - https://sumsub.com/blog/fraud-trends/
  - https://www.nature.com/articles/s41598-025-27010-z
---

Synthetic identity fraud is the fastest-growing driver of losses ($20-40B/yr
globally), now accelerated by GenAI stitching real and fabricated PII into
document-consistent identities; deepfakes reached ~11% of global fraudulent
activity and biometric-fraud deepfake attempts surged ~58%. Fraud-as-a-Service
kits let low-skill actors run enterprise-grade, templated campaigns (from ~$50/mo),
producing correlated device/UA fingerprints across many accounts.

Defence state of the art in 2026 pairs gradient-boosted trees and graph neural
networks with adversarial training. On the IEEE-CIS benchmark, temporal-graph +
anomaly-aware models report F1 ~0.87 and AUC-PR ~0.92, beating XGBoost/GraphSAGE
baselines by 12-18%; adversarial robustness is obtained by training jointly on
clean and gradient-perturbed samples. Two implications for a closed-loop system:

- Static supervised models degrade against novel/evasive variants; a novelty
  channel (reconstruction error / isolation forest on legitimate traffic) is
  needed to flag unseen attack types.
- Robustness must be earned adversarially: generate evasive attacks against the
  live model, then retrain on them. Detection efficacy should be reported with
  PR-AUC and FPR-at-fixed-recall, not accuracy, given heavy class imbalance.
