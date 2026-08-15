"""Point-in-time (no look-ahead) evaluation.

A production fraud decision at time t may only use information available strictly
before t. Some structural features (device fan-out, counterparty in-degree,
account-graph degree, agent-id replay fan-out) are naturally batch-computed and
would leak the future. This script rebuilds them causally (cumulative, in time
order) and re-evaluates the detector, reporting the honest batch-vs-causal gap.

Writes data/artifacts/point_in_time.json.

    python scripts/point_in_time.py
"""
from __future__ import annotations

import json

import numpy as np
from rich.console import Console
from rich.table import Table
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split

from chimera.config import ARTIFACTS_DIR
from chimera.defend.detector import FraudDetector
from chimera.defend.evaluate import _operating_metrics
from chimera.defend.features import build_features
from chimera.generate.simulator import SimConfig, simulate

console = Console()


def _eval(df, causal, seed=42):
    X, names = build_features(df, causal=causal)
    y = df["is_fraud"].to_numpy().astype(int)
    tr, te = train_test_split(np.arange(len(df)), test_size=0.3, random_state=seed, stratify=y)
    det = FraudDetector(seed=seed).fit_matrix(X.iloc[tr], y[tr], names)
    p = det.predict_proba_matrix(X.iloc[te])
    yte = y[te]
    m = _operating_metrics(yte, p)
    pv = {}
    vec = df.iloc[te]["vector"].to_numpy()
    for v in sorted(set(vec)):
        if v == "legit":
            continue
        mask = vec == v
        pv[v] = round(float((p[mask] >= m["threshold"]).mean()), 4) if mask.sum() else 0.0
    return {"roc_auc": round(float(roc_auc_score(yte, p)), 4),
            "pr_auc": round(float(average_precision_score(yte, p)), 4),
            "recall": m["recall"], "precision": m["precision"], "f1": m["f1"],
            "fpr": m["fpr"], "per_vector": pv}


def main():
    console.rule("[bold]Point-in-time (no look-ahead) evaluation")
    sim = simulate(SimConfig(population=5000, days=30, seed=42, intensity=2.0))
    batch = _eval(sim.frame, causal=False)
    causal = _eval(sim.frame, causal=True)
    report = {"batch": batch, "causal": causal,
              "delta_roc_auc": round(causal["roc_auc"] - batch["roc_auc"], 4),
              "delta_pr_auc": round(causal["pr_auc"] - batch["pr_auc"], 4),
              "note": "Causal features use only events strictly before t (cumulative "
                      "device/counterparty/graph degree + agent-id fan-out; PageRank "
                      "dropped as it needs an incremental engine). A modest drop is "
                      "expected and honest; it is what a live streaming store would see."}
    (ARTIFACTS_DIR / "point_in_time.json").write_text(json.dumps(report, indent=2))

    t = Table(title="Batch vs point-in-time features (held-out test)", header_style="bold cyan")
    for c in ("mode", "ROC-AUC", "PR-AUC", "recall", "F1"):
        t.add_column(c)
    t.add_row("batch (look-ahead)", f"{batch['roc_auc']:.4f}", f"{batch['pr_auc']:.4f}", f"{batch['recall']:.3f}", f"{batch['f1']:.3f}")
    t.add_row("point-in-time (causal)", f"{causal['roc_auc']:.4f}", f"{causal['pr_auc']:.4f}", f"{causal['recall']:.3f}", f"{causal['f1']:.3f}")
    console.print(t)
    console.print(f"Delta: ROC {report['delta_roc_auc']:+.4f}, PR-AUC {report['delta_pr_auc']:+.4f}")
    console.print("[green]Saved -> point_in_time.json")


if __name__ == "__main__":
    main()
