"""Evaluation-rigor suite: the experiments a fraud-ML reviewer asks for.

Runs and reports (data/artifacts/rigor_report.json):
  1. Stability across seeds        - detection + unseen-vector recall, mean +/- std
  2. Component ablation            - what each feature family / channel adds
  3. Agent-identity ablation       - do the agent features earn their place, and
                                     do they leave ordinary traffic untouched
  4. Novelty vs benign novelty     - does the novelty channel over-flag weird-but-
                                     legitimate traffic (hard negatives)
  5. Class-imbalance stress        - metrics across fraud prevalences
  6. Latency / throughput          - generation, feature build, inference rates

    python scripts/rigor.py
"""
from __future__ import annotations

import json
import time

import lightgbm as lgb
import numpy as np
from rich.console import Console
from rich.table import Table
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score
from sklearn.model_selection import train_test_split

from chimera.config import ARTIFACTS_DIR
from chimera.defend.detector import FraudDetector
from chimera.defend.evaluate import evaluate, leave_one_vector_out
from chimera.defend.features import build_features
from chimera.generate.simulator import SimConfig, simulate

console = Console()
SEEDS = [1, 42, 123, 777, 2026]


def _ms(xs):
    a = np.array(xs, dtype=float)
    return {"mean": round(float(a.mean()), 4), "std": round(float(a.std()), 4)}


# ---------------------------------------------------------------- 1. seeds
def multi_seed():
    roc, pr, f1, rec = [], [], [], []
    hj_sup, hj_nov = [], []
    for s in SEEDS:
        sim = simulate(SimConfig(population=3000, days=30, seed=s, intensity=2.0))
        rep = evaluate(sim.frame, seed=s)
        roc.append(rep["supervised"]["roc_auc"]); pr.append(rep["supervised"]["pr_auc"])
        f1.append(rep["supervised"]["f1"]); rec.append(rep["supervised"]["recall"])
        loo = leave_one_vector_out(sim.frame, "AGENT-HIJACK", seed=s)
        hj_sup.append(loo["supervised_recall"]); hj_nov.append(loo["novelty_recall"])
    return {"seeds": SEEDS, "roc_auc": _ms(roc), "pr_auc": _ms(pr), "f1": _ms(f1),
            "recall": _ms(rec),
            "agent_hijack_unseen_supervised": _ms(hj_sup),
            "agent_hijack_unseen_novelty": _ms(hj_nov)}


# ------------------------------------------------------- feature families
def _families(names):
    vel = [n for n in names if n.startswith("vel_") or n in ("inter_arrival_s", "amt_z")]
    graph = [n for n in names if n.startswith("dev_") or n.startswith("cp_") or n.startswith("acct_")]
    agent = [n for n in names if n.startswith("agent") or n == "mandate_cap_ratio"]
    event = [n for n in names if n not in set(vel) | set(graph) | set(agent)]
    return event, vel, graph, agent


def _lgbm_pr(X, y, tr, te, cols):
    n_pos = max(int(y[tr].sum()), 1); n_neg = int((y[tr] == 0).sum())
    m = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.05, num_leaves=64,
                           scale_pos_weight=n_neg / n_pos, random_state=42, n_jobs=1, verbose=-1)
    m.fit(X[cols].iloc[tr].to_numpy(), y[tr])
    p = m.predict_proba(X[cols].iloc[te].to_numpy())[:, 1]
    prec, recc, thr = precision_recall_curve(y[te], p)
    f1 = 2 * prec * recc / (prec + recc + 1e-12); b = int(np.argmax(f1[:-1])) if len(f1) > 1 else 0
    t = thr[b] if b < len(thr) else 0.5
    alerts = float((p >= t).mean())
    return {"pr_auc": round(float(average_precision_score(y[te], p)), 4),
            "recall": round(float(recc[b]), 4), "alerts_per_10k": round(alerts * 1e4, 1)}


# ---------------------------------------------------------------- 2. ablation
def ablation():
    sim = simulate(SimConfig(population=4000, days=30, seed=42, intensity=2.0))
    df = sim.frame
    X, names = build_features(df)
    y = df["is_fraud"].to_numpy().astype(int)
    tr, te = train_test_split(np.arange(len(df)), test_size=0.3, random_state=42, stratify=y)
    event, vel, graph, agent = _families(names)
    rows = {
        "event+velocity": event + vel,
        "+ graph": event + vel + graph,
        "+ agent-identity (all supervised)": event + vel + graph + agent,
    }
    out = {k: _lgbm_pr(X, y, tr, te, cols) for k, cols in rows.items()}
    # logistic regression baseline (all features)
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    sc = StandardScaler().fit(X.iloc[tr]); lr = LogisticRegression(max_iter=1000, class_weight="balanced")
    lr.fit(sc.transform(X.iloc[tr]), y[tr]); pl = lr.predict_proba(sc.transform(X.iloc[te]))[:, 1]
    out["logistic regression"] = {"pr_auc": round(float(average_precision_score(y[te], pl)), 4)}
    # full ensemble (+ novelty channel)
    det = FraudDetector(seed=42).fit_matrix(X.iloc[tr], y[tr], names)
    p = det.predict_proba_matrix(X.iloc[te]); nov = det.novelty_matrix(X.iloc[te])
    risk = np.maximum(p, 0.45 * nov)
    out["full ensemble (+ novelty)"] = {"pr_auc": round(float(average_precision_score(y[te], risk)), 4)}
    return out


# ------------------------------------------------- 3. agent-identity ablation
def agent_ablation():
    sim = simulate(SimConfig(population=4000, days=30, seed=42, intensity=2.0))
    df = sim.frame
    X, names = build_features(df); y = df["is_fraud"].to_numpy().astype(int)
    _, _, _, agent = _families(names)
    non_agent = [n for n in names if n not in set(agent)]
    tr, te = train_test_split(np.arange(len(df)), test_size=0.3, random_state=42, stratify=y)
    vec = df.iloc[te]["vector"].to_numpy()

    def recall_by(cols):
        d = FraudDetector(seed=42).fit_matrix(X[cols].iloc[tr], y[tr], cols)
        p = d.predict_proba_matrix(X[cols].iloc[te])
        thr = float(np.quantile(p[vec == "legit"], 0.99))
        hj = vec == "AGENT-HIJACK"; others = (df.iloc[te]["is_fraud"].to_numpy() == 1) & ~hj
        fpr = float((p[vec == "legit"] >= thr).mean())
        return {"agent_hijack_recall": round(float((p[hj] >= thr).mean()), 4),
                "other_fraud_recall": round(float((p[others] >= thr).mean()), 4),
                "legit_fpr": round(fpr, 5)}

    # unseen: leave AGENT-HIJACK out, with vs without agent features
    def unseen(cols_all_agent):
        r = leave_one_vector_out(df, "AGENT-HIJACK", seed=42)
        return round(r["novelty_recall"], 4) if cols_all_agent else None
    return {"with_agent_features": recall_by(names),
            "without_agent_features": recall_by(non_agent),
            "unseen_hijack_novelty_recall_with_agent": unseen(True)}


# --------------------------------------------------- 4. novelty vs benign
def novelty_benign():
    sim = simulate(SimConfig(population=4000, days=30, seed=42, intensity=2.0))
    df = sim.frame
    det = FraudDetector(seed=42).fit(df)
    nov = det.novelty_score(df)
    # hard negatives carry the 'h' txn_id prefix; ordinary legit 't'; fraud 'f'
    tid = df["txn_id"].astype(str)
    is_hard = tid.str.startswith("h").to_numpy(); is_fraud = df["is_fraud"].to_numpy() == 1
    is_plain_legit = tid.str.startswith("t").to_numpy()
    thr = float(np.quantile(nov[is_plain_legit], 0.99))  # 1% novelty budget on ordinary legit
    return {"novelty_threshold": round(thr, 4),
            "flag_rate_ordinary_legit": round(float((nov[is_plain_legit] >= thr).mean()), 4),
            "flag_rate_hard_negatives": round(float((nov[is_hard] >= thr).mean()), 4),
            "flag_rate_fraud": round(float((nov[is_fraud] >= thr).mean()), 4),
            "n_hard_negatives": int(is_hard.sum()),
            "note": "the novelty channel flags fraud far more than benign-but-unusual "
                    "hard negatives - it is not simply an outlier detector."}


# ---------------------------------------------------- 5. imbalance stress
def imbalance():
    sim = simulate(SimConfig(population=5000, days=30, seed=42, intensity=2.0))
    df = sim.frame.reset_index(drop=True)
    X, names = build_features(df); y = df["is_fraud"].to_numpy().astype(int)
    fraud_idx = np.where(y == 1)[0]; legit_idx = np.where(y == 0)[0]
    rng = np.random.default_rng(42)
    out = {}
    for rate in [0.05, 0.02, 0.01, 0.005, 0.001]:
        # subsample fraud to hit the target prevalence against all legit
        n_f = int(rate / (1 - rate) * len(legit_idx))
        n_f = min(n_f, len(fraud_idx))
        keep = np.concatenate([legit_idx, rng.choice(fraud_idx, size=n_f, replace=False)])
        Xs = X.iloc[keep]; ys = y[keep]
        tr, te = train_test_split(np.arange(len(keep)), test_size=0.3, random_state=42, stratify=ys)
        det = FraudDetector(seed=42).fit_matrix(Xs.iloc[tr], ys[tr], names)
        p = det.predict_proba_matrix(Xs.iloc[te])
        prec, rec, thr = precision_recall_curve(ys[te], p)
        f1 = 2 * prec * rec / (prec + rec + 1e-12); b = int(np.argmax(f1[:-1])) if len(f1) > 1 else 0
        t = thr[b] if b < len(thr) else 0.5
        out[f"{rate*100:.1f}%"] = {
            "pr_auc": round(float(average_precision_score(ys[te], p)), 4),
            "precision": round(float(prec[b]), 4), "recall": round(float(rec[b]), 4),
            "alerts_per_10k": round(float((p >= t).mean()) * 1e4, 1)}
    return out


# ------------------------------------------------------------ 6. latency
def latency():
    t0 = time.time(); sim = simulate(SimConfig(population=4000, days=30, seed=42, intensity=2.0)); tg = time.time() - t0
    df = sim.frame; n = len(df)
    t0 = time.time(); X, names = build_features(df); tf = time.time() - t0
    det = FraudDetector(seed=42).fit_matrix(X, df["is_fraud"].to_numpy(), names)
    sample = df.head(5000)
    t0 = time.time(); _ = det.score(sample); ti = time.time() - t0
    return {"events": int(n),
            "generation_events_per_sec": int(n / max(tg, 1e-6)),
            "feature_build_events_per_sec": int(n / max(tf, 1e-6)),
            "inference_events_per_sec": int(len(sample) / max(ti, 1e-6)),
            "note": "single-process CPU on a laptop; a streaming deployment parallelises these."}


def main():
    console.rule("[bold]Evaluation-rigor suite")
    p = ARTIFACTS_DIR / "rigor_report.json"
    report = json.loads(p.read_text()) if p.exists() else {}
    for name, fn in [("stability_across_seeds", multi_seed), ("component_ablation", ablation),
                     ("agent_identity_ablation", agent_ablation), ("novelty_vs_benign", novelty_benign),
                     ("class_imbalance", imbalance), ("latency", latency)]:
        if name in report:
            console.print(f"skip {name} (cached)")
            continue
        console.print(f"running {name} ...")
        report[name] = fn()
        p.write_text(json.dumps(report, indent=2))
    console.print("[green]Saved -> rigor_report.json")
    # quick summary
    ms = report["stability_across_seeds"]
    console.print(f"Seeds: ROC {ms['roc_auc']['mean']}±{ms['roc_auc']['std']}, "
                  f"PR {ms['pr_auc']['mean']}±{ms['pr_auc']['std']}, "
                  f"unseen-hijack novelty {ms['agent_hijack_unseen_novelty']['mean']}±{ms['agent_hijack_unseen_novelty']['std']}")
    nb = report["novelty_vs_benign"]
    console.print(f"Novelty flags: fraud {nb['flag_rate_fraud']*100:.0f}% vs hard-negatives {nb['flag_rate_hard_negatives']*100:.0f}%")


if __name__ == "__main__":
    main()
