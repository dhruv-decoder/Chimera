"""Simulation orchestrator: population + legit traffic + attack injection.

Produces one labelled event stream in a single feature space. Attack parameters
can be overridden per-vector (this is the surface the adversarial agent drives)
and every run is fully seeded for reproducibility.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from ..schema import Transaction, transactions_to_frame
from .attacks import REGISTRY, AttackContext, load_all
from .base_generator import generate_legit
from .common import TxnFactory
from .entities import Population, build_population
from .hard_negatives import generate_hard_negatives


@dataclass
class SimConfig:
    population: int = 4000
    days: int = 30
    seed: int = 42
    enabled_attacks: Optional[List[str]] = None      # None = all registered
    attack_params: Dict[str, dict] = field(default_factory=dict)
    intensity: float = 1.0                            # global multiplier on attack volume
    hard_negatives: bool = True                       # inject benign look-alikes (prevents trivial separability)


@dataclass
class SimResult:
    frame: pd.DataFrame
    population: Population
    meta: dict


# Params that scale attack *volume* (as opposed to per-event shape). The global
# intensity multiplier only touches these, so evasion-relevant shape knobs stay put.
_VOLUME_PARAMS = {
    "n_rings", "n_campaigns", "n_agents", "n_victims", "n_identities",
    "cards_per_device", "purchases_per_agent", "principals_per_agent",
}


def _scaled_params(spec, override: dict, intensity: float) -> dict:
    params = spec.clip(override or {})
    if intensity != 1.0:
        for k in list(params):
            if k in _VOLUME_PARAMS:
                lo, hi = spec.param_spec[k]["min"], spec.param_spec[k]["max"]
                params[k] = float(np.clip(params[k] * intensity, lo, hi))
    return params


def simulate(config: SimConfig) -> SimResult:
    load_all()
    pop = build_population(config.population, config.days, config.seed)
    legit = generate_legit(pop, config.days, config.seed)
    n_hard = 0
    if config.hard_negatives:
        hard = generate_hard_negatives(pop, config.days, config.seed)
        legit.extend(hard)
        n_hard = len(hard)

    rng = np.random.default_rng(config.seed + 7)
    fac = TxnFactory(pop, rng, prefix="f")
    ctx = AttackContext(pop=pop, fac=fac, rng=rng, days=config.days)

    enabled = config.enabled_attacks or list(REGISTRY.keys())
    fraud: List[Transaction] = []
    per_vector: Dict[str, int] = {}
    used_params: Dict[str, dict] = {}
    for aid in enabled:
        spec = REGISTRY.get(aid)
        if spec is None:
            continue
        params = _scaled_params(spec, config.attack_params.get(aid, {}), config.intensity)
        used_params[aid] = params
        events = spec.fn(ctx, params)
        per_vector[aid] = len(events)
        fraud.extend(events)

    all_txns = legit + fraud
    df = transactions_to_frame(all_txns)
    meta = {
        "n_total": len(df),
        "n_legit": len(legit),
        "n_hard_negatives": n_hard,
        "n_fraud": len(fraud),
        "fraud_rate": round(len(fraud) / max(len(df), 1), 5),
        "per_vector": per_vector,
        "params": used_params,
        "config": {
            "population": config.population, "days": config.days, "seed": config.seed,
            "enabled_attacks": enabled, "intensity": config.intensity,
        },
    }
    return SimResult(frame=df, population=pop, meta=meta)
