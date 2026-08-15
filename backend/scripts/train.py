"""Simulate a payment stream, train the detector, evaluate, and persist artifacts.

    python scripts/train.py [--population N] [--days N] [--intensity F] [--seed N]

Writes to data/artifacts: detector.pkl, dataset.parquet, eval_report.json.
"""
from __future__ import annotations

import argparse
import json
import time

from rich.console import Console
from rich.table import Table

from chimera.config import ARTIFACTS_DIR, settings
from chimera.defend.detector import FraudDetector
from chimera.defend.evaluate import evaluate, leave_one_vector_out
from chimera.generate.simulator import SimConfig, simulate

console = Console()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--population", type=int, default=5000)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--intensity", type=float, default=2.0)
    ap.add_argument("--seed", type=int, default=settings.seed)
    args = ap.parse_args()

    console.rule("[bold]Chimera - simulate + train + evaluate")
    t0 = time.time()
    sim = simulate(SimConfig(population=args.population, days=args.days,
                             seed=args.seed, intensity=args.intensity))
    console.print(f"Simulated [bold]{sim.meta['n_total']:,}[/] events "
                  f"({sim.meta['n_fraud']:,} fraud, {sim.meta['fraud_rate']*100:.2f}%) "
                  f"in {time.time()-t0:.1f}s")

    t1 = time.time()
    report = evaluate(sim.frame, seed=args.seed)
    console.print(f"Evaluated in {time.time()-t1:.1f}s")

    s = report["supervised"]
    tbl = Table(title="Detection - held-out test set", show_header=True, header_style="bold cyan")
    for col in ("Metric", "Value"):
        tbl.add_column(col)
    tbl.add_row("ROC-AUC", f"{s['roc_auc']:.4f}")
    tbl.add_row("PR-AUC", f"{s['pr_auc']:.4f}")
    tbl.add_row("Precision @ maxF1", f"{s['precision']:.4f}")
    tbl.add_row("Recall @ maxF1", f"{s['recall']:.4f}")
    tbl.add_row("F1", f"{s['f1']:.4f}")
    tbl.add_row("FPR @ maxF1", f"{s['fpr']*100:.3f}%")
    tbl.add_row("FPR @ 90% recall", f"{s['fpr_at_90_recall']*100:.3f}%")
    console.print(tbl)

    vt = Table(title="Per-vector recall", header_style="bold magenta")
    for col in ("Vector", "Recall", "n"):
        vt.add_column(col)
    for v, d in sorted(report["per_vector_recall"].items(), key=lambda x: -x[1]["recall"]):
        vt.add_row(v, f"{d['recall']*100:.1f}%", str(d["n"]))
    console.print(vt)

    # Leave-one-vector-out novelty study (always saved; drives the Detection view).
    console.print("Running leave-one-vector-out novelty study...")
    loo = [leave_one_vector_out(sim.frame, v, seed=args.seed) for v in report["per_vector_recall"]]
    report["leave_one_out"] = loo

    # Retrain on the full dataset for serving and persist. The full dataset is
    # not stored - it is regenerable bit-for-bit from (seed, config), which we
    # record instead. A small labelled sample is kept for the UI.
    det = FraudDetector(seed=args.seed).fit(sim.frame)
    det.save(ARTIFACTS_DIR / "detector.pkl")
    (ARTIFACTS_DIR / "eval_report.json").write_text(json.dumps(report, indent=2))
    (ARTIFACTS_DIR / "sim_meta.json").write_text(json.dumps(sim.meta, indent=2))

    # Precompute the transfer-graph snapshot so the deployed /api/graph endpoint
    # is instant (no on-demand simulation on a small free-tier box).
    from chimera.api.service import compute_graph_snapshot
    from chimera.generate.simulator import SimConfig as _SC, simulate as _sim
    gsim = _sim(_SC(population=1000, days=24, seed=123, intensity=2.0))
    thr = report["supervised"]["threshold"]
    graph = compute_graph_snapshot(det, gsim.frame, thr)
    (ARTIFACTS_DIR / "graph_snapshot.json").write_text(json.dumps(graph))
    console.print(f"Graph snapshot: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges")

    # Precompute each attack's default Attack Lab result so the deployed lab is
    # instant on a small box; tuned launches still simulate live.
    from chimera.api.service import Service
    from chimera.generate.attacks import REGISTRY as _REG
    svc = Service()
    lab = {aid: svc._attack_lab_live(aid, intensity=1.5, params=None,
                                     population=500, days=18, legit_sample=300)
           for aid in _REG}
    (ARTIFACTS_DIR / "lab_samples.json").write_text(json.dumps(lab))
    console.print(f"Lab samples precomputed for {len(lab)} attacks")
    sample = sim.frame.groupby("is_fraud", group_keys=False).apply(
        lambda g: g.sample(min(len(g), 1500), random_state=args.seed))
    sample.to_json(ARTIFACTS_DIR / "sample.json", orient="records")
    console.print(f"[green]Saved artifacts -> {ARTIFACTS_DIR}")

    console.rule("[bold]Leave-one-vector-out - novelty channel value")
    lt = Table(header_style="bold yellow")
    for col in ("Unseen vector", "Supervised recall", "Novelty recall", "Blended recall"):
        lt.add_column(col)
    for r in loo:
        lt.add_row(r["vector"], f"{r['supervised_recall']*100:.1f}%",
                   f"{r['novelty_recall']*100:.1f}%", f"{r['blended_recall']*100:.1f}%")
    console.print(lt)


if __name__ == "__main__":
    main()
