"""STRUCT: structuring / velocity-threshold evasion.

A large illicit sum is split into many sub-threshold transfers spread across
payees and time to stay under reporting and velocity limits. Signatures: amounts
clustered just below round thresholds, even spacing, fan across payees.
"""
from __future__ import annotations

from ...schema import AuthMethod, Channel, Rail
from . import AttackContext, AttackSpec, register, register_account

PARAMS = {
    "n_campaigns":  {"min": 1,     "max": 30,     "default": 8,     "desc": "structuring operations"},
    "total":        {"min": 2000,  "max": 200000, "default": 25000, "desc": "sum to move per operation"},
    "threshold":    {"min": 500,   "max": 10000,  "default": 5000,  "desc": "reporting threshold to stay under"},
    "n_payees":     {"min": 2,     "max": 20,     "default": 6,     "desc": "payees to fan across (evasion knob)"},
    "spacing_min":  {"min": 1,     "max": 1440,   "default": 90,    "desc": "minutes between transfers (evasion knob)"},
}


def synthesize(ctx: AttackContext, params: dict):
    rng, fac, pop = ctx.rng, ctx.fac, ctx.pop
    txns = []
    n_camp = int(params["n_campaigns"])
    total = float(params["total"])
    thr = float(params["threshold"])
    n_payees = int(params["n_payees"])
    spacing = float(params["spacing_min"]) * 60.0

    for c in range(n_camp):
        camp = f"STRUCT-{c}-{int(rng.integers(1e6))}"
        home = "IN" if rng.random() < 0.7 else "US"
        src = f"a_struct_{c}_{int(rng.integers(1e7))}"
        register_account(pop, src, ctx.start_ts - rng.uniform(20, 300) * 86400,
                         home, balance=total * 1.3, rng=rng, is_mule=True)
        payees = []
        for p in range(n_payees):
            pa = f"a_structp_{c}_{p}_{int(rng.integers(1e7))}"
            register_account(pop, pa, ctx.start_ts - rng.uniform(0, 30) * 86400,
                             home, balance=200.0, rng=rng, is_mule=True)
            payees.append(pa)

        # Per-transfer size sits just under the threshold, with jitter.
        per = thr * rng.uniform(0.82, 0.95)
        moved, t, i = 0.0, ctx.start_ts + rng.uniform(0, ctx.days * 0.5) * 86400, 0
        while moved < total and i < 200:
            amt = min(per * rng.uniform(0.9, 1.0), total - moved)
            if amt < 50:
                break
            payee = payees[i % len(payees)]
            txns.append(fac.make(
                account_id=src, ts=t, rail=Rail.A2A_RT.value, channel=Channel.MOBILE_APP.value,
                amount=amt, counterparty_id=payee, counterparty_type="account",
                counterparty_country=home, mcc=4829, device_id=f"d_{src}",
                auth_method=AuthMethod.UPI_PIN.value, is_new_counterparty=(i < len(payees)),
                is_fraud=1, vector="STRUCT", campaign_id=camp))
            moved += amt
            t += spacing * rng.uniform(0.7, 1.3)
            i += 1

    return txns


register(AttackSpec(id="STRUCT", name="Structuring / threshold evasion",
                    technique_id="STRUCT", fn=synthesize, param_spec=PARAMS))
