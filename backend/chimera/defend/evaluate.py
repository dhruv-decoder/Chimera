"""Evaluation harness.

Metrics reported the way a fraud team actually reads them:
  * ROC-AUC and PR-AUC (PR-AUC matters more under heavy class imbalance),
  * precision / recall / F1 at the max-F1 operating point,
  * FPR at a fixed 90% recall (the "how many good customers do we annoy to
    catch 9 in 10 fraud" question),
  * per-vector recall (which attack types slip through).

``leave_one_vector_out`` quantifies the novelty channel: train the supervised
model with one attack type entirely removed, then measure how much of that
unseen vector each channel still catches.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.metrics import (average_precision_score, confusion_matrix,
                             precision_recall_curve, roc_auc_score, roc_curve)
from sklearn.model_selection import train_test_split

from .detector import FraudDetector
from .features import build_features


def _operating_metrics(y: np.ndarray, score: np.ndarray) -> dict:
    prec, rec, thr = precision_recall_curve(y, score)
    f1 = 2 * prec * rec / (prec + rec + 1e-12)
    best = int(np.argmax(f1[:-1])) if len(f1) > 1 else 0
    t = float(thr[best]) if best < len(thr) else 0.5
    pred = (score >= t).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    fpr = fp / (fp + tn + 1e-12)

    # FPR needed to reach 90% recall.
    fpr_curve, tpr_curve, roc_thr = roc_curve(y, score)
    idx = np.searchsorted(tpr_curve, 0.90)
    idx = min(idx, len(fpr_curve) - 1)
    return {
        "threshold": round(t, 4),
        "precision": round(float(prec[best]), 4),
        "recall": round(float(rec[best]), 4),
        "f1": round(float(f1[best]), 4),
        "fpr": round(float(fpr), 5),
        "confusion": {"tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn)},
        "fpr_at_90_recall": round(float(fpr_curve[idx]), 5),
        "threshold_at_90_recall": round(float(roc_thr[idx]) if idx < len(roc_thr) else 0.0, 4),
    }


def _economics(y: np.ndarray, score: np.ndarray, amount: np.ndarray,
               review_cost: float = 3.0) -> dict:
    """Operating economics, the way a fraud desk reads a model.

    A missed fraud costs the money that moved; every alert costs a fixed review
    (an analyst's minute, or a step-up prompt's friction). Sweeping the threshold
    trades those off and picks the point that minimises expected loss. We also
    report the share of fraudulent *value* caught (not just event recall) and the
    review workload per 10k transactions - both are what a bank actually signs off.
    """
    n = len(y)
    fraud_value = float(amount[y == 1].sum()) + 1e-9
    order = np.unique(np.quantile(score, np.linspace(0.80, 0.9995, 60)))
    sweep = []
    best = None
    for t in order:
        flag = score >= t
        alerts = int(flag.sum())
        caught_value = float(amount[(y == 1) & flag].sum())
        missed_value = fraud_value - caught_value
        exp_cost = missed_value + review_cost * alerts
        point = {
            "threshold": round(float(t), 4),
            "alerts_per_10k": round(alerts / n * 1e4, 1),
            "value_detected_rate": round(caught_value / fraud_value, 4),
            "expected_cost": round(exp_cost, 1),
        }
        sweep.append(point)
        if best is None or exp_cost < best["expected_cost"]:
            best = point
    return {"cost_optimal": best, "review_cost_per_alert": review_cost,
            "total_fraud_value": round(fraud_value, 1), "sweep": sweep}


def _point_economics(y: np.ndarray, score: np.ndarray, amount: np.ndarray, t: float) -> dict:
    flag = score >= t
    fraud_value = float(amount[y == 1].sum()) + 1e-9
    return {
        "alerts_per_10k": round(int(flag.sum()) / len(y) * 1e4, 1),
        "value_detected_rate": round(float(amount[(y == 1) & flag].sum()) / fraud_value, 4),
    }


def _curves(y: np.ndarray, score: np.ndarray, n: int = 80) -> dict:
    fpr, tpr, _ = roc_curve(y, score)
    prec, rec, _ = precision_recall_curve(y, score)

    def _thin(a, b):
        if len(a) <= n:
            return list(zip(np.round(a, 4).tolist(), np.round(b, 4).tolist()))
        idx = np.linspace(0, len(a) - 1, n).astype(int)
        return list(zip(np.round(a[idx], 4).tolist(), np.round(b[idx], 4).tolist()))

    return {"roc": _thin(fpr, tpr), "pr": _thin(rec, prec)}


def evaluate(df: pd.DataFrame, test_size: float = 0.3, seed: int = 42,
             detector: Optional[FraudDetector] = None) -> dict:
    """Train/test split on a shared feature matrix; return full metric report."""
    X, names = build_features(df)
    y = df["is_fraud"].to_numpy().astype(int)
    idx = np.arange(len(df))
    tr, te = train_test_split(idx, test_size=test_size, random_state=seed, stratify=y)

    det = detector or FraudDetector(seed=seed)
    det.fit_matrix(X.iloc[tr], y[tr], names)

    Xte = X.iloc[te]
    p = det.predict_proba_matrix(Xte)
    nov = det.novelty_matrix(Xte)
    risk = np.maximum(p, 0.45 * nov)
    yte = y[te]
    amt_te = df.iloc[te]["amount"].to_numpy()

    sup = {
        "roc_auc": round(float(roc_auc_score(yte, p)), 4),
        "pr_auc": round(float(average_precision_score(yte, p)), 4),
        **_operating_metrics(yte, p),
    }
    sup.update(_point_economics(yte, p, amt_te, sup["threshold"]))
    report = {
        "n_train": int(len(tr)), "n_test": int(len(te)),
        "test_fraud": int(yte.sum()), "test_fraud_rate": round(float(yte.mean()), 5),
        "supervised": sup,
        "blended": {
            "roc_auc": round(float(roc_auc_score(yte, risk)), 4),
            "pr_auc": round(float(average_precision_score(yte, risk)), 4),
        },
        "operating_point": _economics(yte, p, amt_te),
        "curves": _curves(yte, p),
    }

    # Per-vector recall at the supervised operating threshold.
    t = report["supervised"]["threshold"]
    vec_te = df.iloc[te]["vector"].to_numpy()
    pv = {}
    for v in sorted(set(vec_te)):
        if v == "legit":
            continue
        mask = vec_te == v
        caught = (p[mask] >= t).mean() if mask.sum() else 0.0
        pv[v] = {"recall": round(float(caught), 4), "n": int(mask.sum())}
    report["per_vector_recall"] = pv
    report["global_importance"] = det.global_importance()[:15]
    return report


def leave_one_vector_out(df: pd.DataFrame, vector: str, seed: int = 42) -> dict:
    """Train with `vector` removed from the labelled fraud, then measure how much
    of that unseen vector the supervised vs novelty channels recover."""
    X, names = build_features(df)
    y = df["is_fraud"].to_numpy().astype(int)
    vec = df["vector"].to_numpy()

    is_target = vec == vector
    # Training set: everything except the target vector's fraud events.
    train_mask = ~is_target
    det = FraudDetector(seed=seed)
    det.fit_matrix(X.iloc[train_mask], y[train_mask], names)

    Xt = X.iloc[is_target]
    p = det.predict_proba_matrix(Xt)
    nov = det.novelty_matrix(Xt)

    # Calibrate a decision threshold on legit only (the operational reality: you
    # set thresholds on known-good traffic, not on the attack you haven't seen).
    legit_mask = vec == "legit"
    p_legit = det.predict_proba_matrix(X.iloc[legit_mask])
    nov_legit = det.novelty_matrix(X.iloc[legit_mask])
    t_sup = float(np.quantile(p_legit, 0.99))       # ~1% FPR operating point
    t_nov = float(np.quantile(nov_legit, 0.99))
    blended = np.maximum(p, 0.45 * nov)
    t_bl = float(np.quantile(np.maximum(p_legit, 0.45 * nov_legit), 0.99))

    return {
        "vector": vector, "n_unseen": int(is_target.sum()),
        "supervised_recall": round(float((p >= t_sup).mean()), 4),
        "novelty_recall": round(float((nov >= t_nov).mean()), 4),
        "blended_recall": round(float((blended >= t_bl).mean()), 4),
    }
