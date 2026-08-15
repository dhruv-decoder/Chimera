"""Baselines on a real public benchmark, and the closed loop applied to real data.

Two experiments on the ULB real credit-card fraud dataset:
  1. Standard baselines (Logistic Regression, Random Forest, [XGBoost if present],
     LightGBM) vs Chimera's two-channel ensemble - shows we are competitive with
     conventional fraud detection, so the contribution is the *loop*, not a better
     static classifier.
  2. The adversarial red-team/blue-team loop applied to real fraud: perturb real
     fraud toward the legitimate distribution (an evasion), watch recall drop, then
     retrain on the evasive samples and watch it recover - demonstrating the
     methodology does not depend on the synthetic simulator.

Writes data/artifacts/benchmark_report.json. Uses the ULB cache from validate_real.

    python scripts/benchmark_baselines.py
"""
from __future__ import annotations

import json

import lightgbm as lgb
import numpy as np
from rich.console import Console
from rich.table import Table
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from chimera.config import ARTIFACTS_DIR
from validate_real import load_real, two_channel

console = Console()


def _recall_at(p, y, legit_q=0.99):
    thr = float(np.quantile(p[y == 0], legit_q))
    return round(float((p[y == 1] >= thr).mean()), 4), thr


def main():
    console.rule("[bold]Baselines + closed loop on REAL fraud (ULB)")
    df = load_real()
    y = df["Class"].to_numpy().astype(int)
    feats = [c for c in df.columns if c != "Class"]
    X = df[feats].to_numpy(dtype=float)
    tr, te = train_test_split(np.arange(len(y)), test_size=0.3, random_state=42, stratify=y)

    baselines = {}
    sc = StandardScaler().fit(X[tr])
    lr = LogisticRegression(max_iter=1000, class_weight="balanced").fit(sc.transform(X[tr]), y[tr])
    baselines["Logistic Regression"] = lr.predict_proba(sc.transform(X[te]))[:, 1]
    rf = RandomForestClassifier(n_estimators=200, class_weight="balanced_subsample",
                                random_state=42, n_jobs=1).fit(X[tr], y[tr])
    baselines["Random Forest"] = rf.predict_proba(X[te])[:, 1]
    try:
        import xgboost as xgb
        spw = float((y[tr] == 0).sum() / max((y[tr] == 1).sum(), 1))
        xm = xgb.XGBClassifier(n_estimators=400, max_depth=6, learning_rate=0.1,
                               scale_pos_weight=min(spw, 50), n_jobs=1, eval_metric="aucpr",
                               tree_method="hist", random_state=42)
        xm.fit(X[tr], y[tr]); baselines["XGBoost"] = xm.predict_proba(X[te])[:, 1]
    except Exception:
        console.print("  (xgboost not installed locally; available on Kaggle)")
    _spw = min(float((y[tr] == 0).sum() / max((y[tr] == 1).sum(), 1)), 50)
    lgbm = lgb.LGBMClassifier(n_estimators=600, learning_rate=0.05, num_leaves=64,
                              subsample=0.85, subsample_freq=1, colsample_bytree=0.8,
                              reg_lambda=1.0, min_child_samples=40,
                              scale_pos_weight=_spw, random_state=42, n_jobs=1, verbose=-1).fit(X[tr], y[tr])
    baselines["LightGBM"] = lgbm.predict_proba(X[te])[:, 1]
    p_ch, _, risk_ch = two_channel(X[tr], y[tr], X[te])
    baselines["Chimera (two-channel)"] = risk_ch

    table = {k: {"roc_auc": round(float(roc_auc_score(y[te], p)), 4),
                 "pr_auc": round(float(average_precision_score(y[te], p)), 4)}
             for k, p in baselines.items()}

    # --- closed loop on real data ---
    base_p = lgbm.predict_proba(X[te])[:, 1]
    base_recall, thr = _recall_at(base_p, y[te])
    # evasion: move real fraud toward the legit median on the most important features
    imp = np.argsort(-lgbm.feature_importances_)[:15]
    legit_med = np.median(X[y == 0], axis=0)
    Xev = X.copy().astype(float)
    fraud_te = te[y[te] == 1]
    alpha = 0.8
    for j in imp:
        Xev[fraud_te, j] = (1 - alpha) * X[fraud_te, j] + alpha * legit_med[j]
    ev_p = lgbm.predict_proba(Xev[te])[:, 1]
    ev_recall = round(float((ev_p[y[te] == 1] >= thr).mean()), 4)
    # retrain including evasive fraud, then re-score a fresh evasive holdout
    fraud_tr = tr[y[tr] == 1]
    Xev_tr = X[tr].copy().astype(float)
    for j in imp:
        Xev_tr[np.isin(tr, fraud_tr), j] = (1 - alpha) * X[fraud_tr, j] + alpha * legit_med[j]
    X_aug = np.vstack([X[tr], Xev_tr[y[tr] == 1]]); y_aug = np.concatenate([y[tr], np.ones(int((y[tr] == 1).sum()), int)])
    lgbm2 = lgb.LGBMClassifier(n_estimators=600, learning_rate=0.05, num_leaves=64,
                               subsample=0.85, subsample_freq=1, colsample_bytree=0.8,
                               reg_lambda=1.0, min_child_samples=40,
                               scale_pos_weight=min(float((y_aug == 0).sum() / max((y_aug == 1).sum(), 1)), 50),
                               random_state=42, n_jobs=1, verbose=-1).fit(X_aug, y_aug)
    # recompute the operating threshold on the retrained model's own legit scores
    post_p = lgbm2.predict_proba(Xev[te])[:, 1]
    thr2 = float(np.quantile(lgbm2.predict_proba(X[te][y[te] == 0])[:, 1], 0.99))
    post_recall = round(float((post_p[y[te] == 1] >= thr2).mean()), 4)

    report = {"dataset": "ULB credit-card fraud (OpenML 1597)", "n": int(len(y)),
              "baselines": table,
              "closed_loop_on_real": {"baseline_recall": base_recall, "under_evasion": ev_recall,
                                      "after_retrain": post_recall, "threshold": round(thr, 4)}}
    (ARTIFACTS_DIR / "benchmark_report.json").write_text(json.dumps(report, indent=2))

    t = Table(title="Baselines on real ULB fraud (held-out)", header_style="bold cyan")
    for c in ("model", "ROC-AUC", "PR-AUC"):
        t.add_column(c)
    for k, v in table.items():
        t.add_row(k, f"{v['roc_auc']:.4f}", f"{v['pr_auc']:.4f}")
    console.print(t)
    console.print(f"Closed loop on REAL data: baseline {base_recall*100:.0f}% -> evasion "
                  f"{ev_recall*100:.0f}% -> retrained {post_recall*100:.0f}%")
    console.print("[green]Saved -> benchmark_report.json")


if __name__ == "__main__":
    main()
