"""Adversarial evasion search - the red-team half of the closed loop.

Given a trained detector (treated as a black box) and an attack, an evolutionary
(mu + lambda) search tunes the attack's *shape* parameters - amount, cadence,
session time, payee reuse, dwell - to minimise the detector's mean risk on the
attack's own events. Volume parameters are frozen so the optimiser cannot cheat
by simply emitting fewer transactions; it must make each event stealthier.

The output is an evasive parameter set plus the detection collapse it causes
(baseline recall -> evolved recall). Feeding those evasive events back into
training is what hardens the detector over rounds.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..defend.detector import FraudDetector
from ..schema import transactions_to_frame
from .attacks import REGISTRY, AttackContext, load_all
from .base_generator import generate_legit
from .common import TxnFactory
from .entities import build_population
from .simulator import _VOLUME_PARAMS


@dataclass
class EvasionResult:
    attack_id: str
    evolved_params: dict
    baseline_risk: float
    evolved_risk: float
    baseline_recall: float
    evolved_recall: float
    trajectory: List[float] = field(default_factory=list)


class _AttackArena:
    """A small cached legit context that attacks are injected into for scoring."""

    def __init__(self, seed: int, population: int = 600, days: int = 24):
        load_all()
        self.seed = seed
        self.days = days
        self._template = build_population(population, days, seed)
        self._legit_frame = transactions_to_frame(generate_legit(self._template, days, seed))
        self._rng = np.random.default_rng(seed + 999)

    def run(self, attack_id: str, params: dict) -> pd.DataFrame:
        spec = REGISTRY[attack_id]
        pop = copy.deepcopy(self._template)
        rng = np.random.default_rng(int(self._rng.integers(1e9)))
        fac = TxnFactory(pop, rng, prefix="e")
        ctx = AttackContext(pop=pop, fac=fac, rng=rng, days=self.days)
        events = spec.fn(ctx, spec.clip(params))
        if not events:
            return self._legit_frame
        return pd.concat([self._legit_frame, transactions_to_frame(events)], ignore_index=True)

    def score(self, detector: FraudDetector, attack_id: str, params: dict,
              threshold: float) -> Tuple[float, float]:
        frame = self.run(attack_id, params)
        atk = frame[frame["vector"] == attack_id]
        if atk.empty:
            return 0.0, 0.0
        s = detector.score(frame).iloc[atk.index]
        risk = float(s["risk"].mean())
        recall = float((s["risk"].values >= threshold).mean())
        return risk, recall


def _shape_params(spec) -> List[str]:
    return [k for k in spec.param_spec if k not in _VOLUME_PARAMS]


def evade(detector: FraudDetector, attack_id: str, threshold: float = 0.5,
          generations: int = 5, popsize: int = 8, seed: int = 42,
          arena: Optional[_AttackArena] = None) -> EvasionResult:
    spec = REGISTRY[attack_id]
    arena = arena or _AttackArena(seed)
    rng = np.random.default_rng(seed + hash(attack_id) % 10000)
    shape = _shape_params(spec)

    base = spec.defaults()
    base_risk, base_recall = arena.score(detector, attack_id, base, threshold)

    best = dict(base)
    best_risk = base_risk
    traj = [base_risk]

    for _ in range(generations):
        children = []
        for _ in range(popsize):
            cand = dict(best)
            # Perturb a random subset of shape params within their bounds.
            for k in rng.choice(shape, size=max(1, len(shape) // 2), replace=False):
                lo, hi = spec.param_spec[k]["min"], spec.param_spec[k]["max"]
                span = hi - lo
                cand[k] = float(np.clip(cand[k] + rng.normal(0, 0.35) * span, lo, hi))
            children.append(cand)
        scored = [(arena.score(detector, attack_id, c, threshold)[0], c) for c in children]
        scored.sort(key=lambda x: x[0])
        if scored[0][0] < best_risk:
            best_risk, best = scored[0]
        traj.append(best_risk)

    evolved_risk, evolved_recall = arena.score(detector, attack_id, best, threshold)
    return EvasionResult(
        attack_id=attack_id, evolved_params={k: round(v, 3) for k, v in best.items()},
        baseline_risk=round(base_risk, 4), evolved_risk=round(evolved_risk, 4),
        baseline_recall=round(base_recall, 4), evolved_recall=round(evolved_recall, 4),
        trajectory=[round(t, 4) for t in traj],
    )
