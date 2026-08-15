"""Attack synthesizer framework and registry.

Every attack is a registered callable with an explicit, bounded parameter space.
Two properties matter:

  * Fidelity - attacks manipulate only observable fields and reuse the shared
    TxnFactory, so fraud is embedded in the same feature space as legit traffic.
  * Tunability - the ``param_spec`` exposes exactly the knobs that trade
    detectability for yield (amount, cadence, payee reuse, ...). The adversarial
    agent perturbs these to search for evasive configurations - this is what
    turns the generator into a live red team rather than a fixed dataset.
"""
from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass, field
from typing import Callable, Dict, List

import numpy as np

from ...schema import Account, Device, Transaction
from ..common import TxnFactory
from ..entities import DAY, Population, Profile


@dataclass
class AttackContext:
    pop: Population
    fac: TxnFactory
    rng: np.random.Generator
    days: int

    @property
    def start_ts(self) -> float:
        return self.pop.sim_start_ts


@dataclass
class AttackSpec:
    id: str
    name: str
    technique_id: str
    fn: Callable[["AttackContext", dict], List[Transaction]]
    # param -> {min, max, default, desc}. Bounds keep the adversarial search sane.
    param_spec: Dict[str, dict] = field(default_factory=dict)

    def defaults(self) -> dict:
        return {k: v["default"] for k, v in self.param_spec.items()}

    def clip(self, params: dict) -> dict:
        out = dict(self.defaults())
        for k, v in params.items():
            if k in self.param_spec:
                lo, hi = self.param_spec[k]["min"], self.param_spec[k]["max"]
                out[k] = float(np.clip(v, lo, hi))
        return out


REGISTRY: Dict[str, AttackSpec] = {}


def register(spec: AttackSpec) -> AttackSpec:
    REGISTRY[spec.id] = spec
    return spec


def load_all() -> Dict[str, AttackSpec]:
    """Import every sibling module so its @register call runs."""
    pkg = __name__
    for mod in pkgutil.iter_modules(__path__):
        if mod.name.startswith("_"):
            continue
        importlib.import_module(f"{pkg}.{mod.name}")
    return REGISTRY


# --- helpers for standing up attacker-controlled entities ----------------

def register_account(
    pop: Population, account_id: str, opened_ts: float, home: str,
    balance: float, rng: np.random.Generator, *,
    is_mule: bool = False, is_synthetic: bool = False, kind: str = "android",
    is_emulator: bool = False, is_headless: bool = False,
) -> str:
    """Add a fresh attacker-controlled account + device + profile to the population."""
    uid = account_id.replace("a_", "u_")
    pop.accounts[account_id] = Account(
        account_id=account_id, user_id=uid, opened_ts=opened_ts, home_country=home,
        kyc_level=int(rng.choice([0, 1])) if (is_mule or is_synthetic) else 2,
        is_synthetic=is_synthetic, is_mule=is_mule, risk_seed=float(rng.beta(3, 3)),
    )
    did = f"d_{account_id}"
    pop.devices[did] = Device(device_id=did, kind="emulator" if is_emulator else kind,
                              first_seen_ts=opened_ts, is_emulator=is_emulator,
                              is_headless=is_headless)
    pop.profiles[account_id] = Profile(
        account_id=account_id, txns_per_day=0.2, a2a_per_week=0.2,
        log_amount_mu=3.4, log_amount_sigma=0.7, pref_mcc=[4829],
        active_hours=np.ones(24) / 24, home_country=home,
        known_payees=[], device_ids=[did], balance=balance,
    )
    pop.account_ids.append(account_id)
    return did
