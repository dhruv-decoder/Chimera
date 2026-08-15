"""Benchmark: does a graph neural network beat gradient boosting at finding
coordinated fraud (mule rings, structuring) on the account-to-account graph?

Both models see the *same per-account node features*. The GNN additionally
propagates those features along the transfer graph (two GraphSAGE message-passing
layers), so it can flag an account by the company it keeps, not just its own
behaviour. The gap between them is the value the graph structure adds.

Writes data/artifacts/gnn_benchmark.json + gnn_pr.png.

    python scripts/gnn_benchmark.py
"""
from __future__ import annotations

import os
os.environ.setdefault("OMP_NUM_THREADS", "1")  # torch + LightGBM OpenMP pools deadlock otherwise

import json

import lightgbm as lgb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from rich.console import Console
from rich.table import Table
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score
from sklearn.model_selection import train_test_split

from chimera.config import ARTIFACTS_DIR
from chimera.defend.gnn import build_node_dataset, train_gnn
from chimera.generate.simulator import SimConfig, simulate

console = Console()
DARK = {"figure.facecolor": "#06070a", "axes.facecolor": "#0e1016", "text.color": "#e7e9ee",
        "axes.edgecolor": "#252b38", "xtick.color": "#8a909f", "ytick.color": "#8a909f",
        "axes.labelcolor": "#aeb4c2", "font.size": 11}


def main():
    plt.rcParams.update(DARK)
    console.rule("[bold]GNN vs gradient boosting - coordinated-ring detection")
    sim = simulate(SimConfig(population=3000, days=30, seed=42, intensity=2.0))
    feats, A, y, nodes = build_node_dataset(sim.frame)
    console.print(f"Account graph: {len(nodes):,} nodes, {int(y.sum())} touch fraud "
                  f"({y.mean()*100:.2f}%), {feats.shape[1]} node features, "
                  f"avg degree {A.astype(bool).sum()/max(len(nodes),1):.1f}")

    idx = np.arange(len(y))
    tr, te = train_test_split(idx, test_size=0.3, random_state=42, stratify=y)
    train_mask = np.zeros(len(y), dtype=bool); train_mask[tr] = True

    # --- baseline: gradient boosting on node features only (no message passing) ---
    n_pos = max(int(y[tr].sum()), 1); n_neg = int((y[tr] == 0).sum())
    gbm = lgb.LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=48,
                             scale_pos_weight=n_neg / n_pos, random_state=42, n_jobs=1, verbose=-1)
    gbm.fit(feats[tr], y[tr])
    p_gbm = gbm.predict_proba(feats[te])[:, 1]

    # --- GNN (transductive): message passing on the full graph, standard protocol ---
    scores = train_gnn(feats, A, y, train_mask, epochs=200, seed=42)
    p_gnn = scores[te]

    # --- GNN (inductive): the leakage-proof version. Train on a graph with every
    # edge incident to a test node removed, so held-out accounts' connectivity never
    # touches the learned weights; they attach to their (train) neighbours only at
    # inference. This directly rules out cross-train/test graph contamination. ---
    A_ind = A.copy()
    A_ind[te, :] = 0.0
    A_ind[:, te] = 0.0
    A_ind = A_ind / (A_ind.sum(axis=1, keepdims=True) + 1e-9)
    scores_ind = train_gnn(feats, A_ind, y, train_mask, epochs=200, seed=42, infer_A=A)
    p_gnn_ind = scores_ind[te]

    yte = y[te]
    report = {
        "n_nodes": int(len(nodes)), "n_fraud_nodes": int(y.sum()),
        "fraud_node_rate": round(float(y.mean()), 4), "n_features": int(feats.shape[1]),
        "eval_note": "node-classification on the account graph; test-node labels are "
                     "never used in training. Gradient boosting sees the same node "
                     "features without message passing, isolating the graph's value.",
        "gradient_boosting": {"roc_auc": round(float(roc_auc_score(yte, p_gbm)), 4),
                              "pr_auc": round(float(average_precision_score(yte, p_gbm)), 4)},
        "graphsage_gnn": {"roc_auc": round(float(roc_auc_score(yte, p_gnn)), 4),
                          "pr_auc": round(float(average_precision_score(yte, p_gnn)), 4)},
        "graphsage_inductive": {"roc_auc": round(float(roc_auc_score(yte, p_gnn_ind)), 4),
                                "pr_auc": round(float(average_precision_score(yte, p_gnn_ind)), 4),
                                "note": "test-node edges removed during training (no graph leakage)"},
    }
    report["pr_auc_lift"] = round(report["graphsage_gnn"]["pr_auc"] - report["gradient_boosting"]["pr_auc"], 4)
    report["pr_auc_lift_inductive"] = round(report["graphsage_inductive"]["pr_auc"] - report["gradient_boosting"]["pr_auc"], 4)
    (ARTIFACTS_DIR / "gnn_benchmark.json").write_text(json.dumps(report, indent=2))

    fig, ax = plt.subplots(figsize=(6.4, 4.0), dpi=150)
    for name, pr, color in [("gradient boosting (node features)", p_gbm, "#5ea0ff"),
                            ("GraphSAGE (transductive)", p_gnn, "#2ed6a6"),
                            ("GraphSAGE (inductive, no leakage)", p_gnn_ind, "#8b8cf0")]:
        prec, rec, _ = precision_recall_curve(yte, pr)
        ax.plot(rec, prec, color=color, lw=2.2, label=f"{name}  PR-AUC {average_precision_score(yte, pr):.3f}")
    ax.set_xlabel("recall"); ax.set_ylabel("precision"); ax.set_xlim(0, 1); ax.set_ylim(0, 1.02)
    ax.legend(facecolor="#0e1016", edgecolor="#252b38", labelcolor="#e7e9ee", fontsize=9, loc="lower left")
    ax.set_title("Finding fraud-ring accounts on the transfer graph")
    for s in ax.spines.values():
        s.set_color("#252b38")
    fig.tight_layout(); fig.savefig(ARTIFACTS_DIR / "gnn_pr.png"); plt.close(fig)

    t = Table(title="Ring detection - held-out accounts", header_style="bold cyan")
    for c in ("model", "ROC-AUC", "PR-AUC"):
        t.add_column(c)
    t.add_row("gradient boosting (node features)", f"{report['gradient_boosting']['roc_auc']:.4f}", f"{report['gradient_boosting']['pr_auc']:.4f}")
    t.add_row("GraphSAGE (transductive)", f"{report['graphsage_gnn']['roc_auc']:.4f}", f"{report['graphsage_gnn']['pr_auc']:.4f}")
    t.add_row("GraphSAGE (inductive, no leakage)", f"{report['graphsage_inductive']['roc_auc']:.4f}", f"{report['graphsage_inductive']['pr_auc']:.4f}")
    console.print(t)
    console.print(f"PR-AUC lift (transductive): [bold]{report['pr_auc_lift']:+.4f}[/]  "
                  f"| inductive (leakage-proof): [bold]{report['pr_auc_lift_inductive']:+.4f}[/]")
    console.print(f"[green]Saved -> gnn_benchmark.json (+ gnn_pr.png)")


if __name__ == "__main__":
    main()
