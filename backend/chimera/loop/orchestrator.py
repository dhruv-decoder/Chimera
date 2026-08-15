"""The closed loop: identify -> generate (evade) -> detect -> evaluate -> harden.

Each round:
  1. The red team evolves evasive parameters for every attack against the
     *current* detector (adversarial search).
  2. A fresh dataset is generated with those evasive parameters.
  3. PRE metrics: the current detector is scored on the new evasive attacks -
     recall drops (the attack wins).
  4. The detector is retrained on all accumulated data including the new evasive
     samples, then re-scored - recall recovers (the defence hardens).

The per-round PRE vs POST recall is the hardening curve: the single chart that
demonstrates the feedback loop actually closes.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from ..defend.detector import FraudDetector
from ..defend.features import build_features
from ..generate.adversarial import _AttackArena, evade
from ..generate.attacks import REGISTRY, load_all
from ..generate.simulator import SimConfig, simulate


@dataclass
class RoundResult:
    round: int
    evasive_params: Dict[str, dict]
    pre_recall: float
    post_recall: float
    pre_per_vector: Dict[str, float]
    post_per_vector: Dict[str, float]
    ideation: List[dict] = field(default_factory=list)


@dataclass
class LoopResult:
    baseline_recall: float
    baseline_per_vector: Dict[str, float]
    rounds: List[RoundResult]
    hardening_curve: List[dict]
    meta: dict


def _recall_at(det: FraudDetector, df: pd.DataFrame, threshold: float) -> tuple[float, Dict[str, float]]:
    fraud = df[df["is_fraud"] == 1]
    if fraud.empty:
        return 0.0, {}
    scores = det.score(fraud)["risk"].to_numpy()
    caught = scores >= threshold
    overall = float(caught.mean())
    per_vec = {}
    vecs = fraud["vector"].to_numpy()
    for v in sorted(set(vecs)):
        m = vecs == v
        per_vec[v] = round(float(caught[m].mean()), 4)
    return round(overall, 4), per_vec


def run_loop(
    rounds: int = 3,
    population: int = 4000,
    days: int = 30,
    seed: int = 42,
    intensity: float = 2.0,
    generations: int = 4,
    popsize: int = 6,
    threshold: Optional[float] = None,
    ideation_fn: Optional[Callable[[str, dict, dict], List[dict]]] = None,
    log: Optional[Callable[[str], None]] = None,
) -> LoopResult:
    load_all()
    say = log or (lambda *_: None)
    attacks = list(REGISTRY.keys())

    # --- baseline ---------------------------------------------------------
    say("Building baseline dataset and detector...")
    base = simulate(SimConfig(population=population, days=days, seed=seed, intensity=intensity))
    Xb, names = build_features(base.frame)
    det = FraudDetector(seed=seed).fit_matrix(Xb, base.frame["is_fraud"].to_numpy(), names)
    if threshold is None:
        # ~1% FPR operating point calibrated on legitimate traffic.
        legit_scores = det.score(base.frame[base.frame["is_fraud"] == 0].sample(
            min(8000, (base.frame["is_fraud"] == 0).sum()), random_state=seed))["risk"]
        threshold = float(np.quantile(legit_scores, 0.99))
    base_recall, base_pv = _recall_at(det, base.frame, threshold)
    say(f"Baseline recall @thr={threshold:.3f}: {base_recall*100:.1f}%")

    arena = _AttackArena(seed=seed)
    accumulated = [base.frame]
    round_results: List[RoundResult] = []
    curve = [{"round": 0, "pre_recall": base_recall, "post_recall": base_recall,
              "threshold": round(threshold, 4)}]

    for r in range(1, rounds + 1):
        say(f"--- Round {r}: red team evolving evasive campaigns ---")
        evasive_params: Dict[str, dict] = {}
        ideation_notes: List[dict] = []
        for aid in attacks:
            res = evade(det, aid, threshold=threshold, generations=generations,
                        popsize=popsize, seed=seed + r, arena=arena)
            evasive_params[aid] = res.evolved_params
            if ideation_fn is not None:
                ideation_notes.extend(ideation_fn(aid, res.evolved_params, base.meta))
            say(f"  {aid}: arena recall {res.baseline_recall*100:.0f}% -> {res.evolved_recall*100:.0f}%")

        # Generate this round's evasive dataset.
        evo = simulate(SimConfig(population=population, days=days, seed=seed + 1000 + r,
                                 intensity=intensity, attack_params=evasive_params))
        pre_recall, pre_pv = _recall_at(det, evo.frame, threshold)
        say(f"  PRE-retrain recall on evasive set: {pre_recall*100:.1f}%")

        # Harden: retrain on everything seen so far, including evasive samples.
        accumulated.append(evo.frame)
        train_df = pd.concat(accumulated, ignore_index=True)
        Xt, tn = build_features(train_df)
        det = FraudDetector(seed=seed).fit_matrix(Xt, train_df["is_fraud"].to_numpy(), tn)

        # Re-evaluate on a fresh evasive holdout generated with the same params.
        holdout = simulate(SimConfig(population=population // 2, days=days,
                                     seed=seed + 5000 + r, intensity=intensity,
                                     attack_params=evasive_params))
        post_recall, post_pv = _recall_at(det, holdout.frame, threshold)
        say(f"  POST-retrain recall on evasive holdout: {post_recall*100:.1f}%")

        round_results.append(RoundResult(
            round=r, evasive_params=evasive_params, pre_recall=pre_recall,
            post_recall=post_recall, pre_per_vector=pre_pv, post_per_vector=post_pv,
            ideation=ideation_notes))
        curve.append({"round": r, "pre_recall": pre_recall, "post_recall": post_recall,
                      "threshold": round(threshold, 4)})

    return LoopResult(
        baseline_recall=base_recall, baseline_per_vector=base_pv,
        rounds=round_results, hardening_curve=curve,
        meta={"population": population, "days": days, "seed": seed, "rounds": rounds,
              "intensity": intensity, "threshold": round(threshold, 4),
              "attacks": attacks},
    )


def loop_result_to_dict(res: LoopResult) -> dict:
    return {
        "baseline_recall": res.baseline_recall,
        "baseline_per_vector": res.baseline_per_vector,
        "rounds": [asdict(r) for r in res.rounds],
        "hardening_curve": res.hardening_curve,
        "meta": res.meta,
    }
