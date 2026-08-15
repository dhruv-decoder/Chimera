"""PIG-BUTCH: real-time investment ('pig-butchering') scam.

The victim is groomed, then makes a ladder of escalating authorised transfers to
the same attacker-controlled payee, believing they are funding an investment.
Signatures: escalating round-number transfers to one new payee, high-risk / crypto
off-ramp, no prior relationship with the beneficiary.
"""
from __future__ import annotations

import numpy as np

from ...schema import AuthMethod, Channel, Rail
from . import AttackContext, AttackSpec, register, register_account

PARAMS = {
    "n_victims":    {"min": 1,   "max": 120,  "default": 20,   "desc": "victims groomed"},
    "n_deposits":   {"min": 2,   "max": 15,   "default": 6,    "desc": "transfers in the escalation ladder"},
    "escalation":   {"min": 1.0, "max": 2.2,  "default": 1.35, "desc": "growth factor per deposit (evasion knob)"},
    "seed_amount":  {"min": 50,  "max": 5000, "default": 250,  "desc": "first deposit size"},
    "round_bias":   {"min": 0.0, "max": 1.0,  "default": 0.6,  "desc": "tendency to round numbers (evasion knob)"},
    "crypto_prob":  {"min": 0.0, "max": 1.0,  "default": 0.5,  "desc": "share routed via crypto off-ramp vs plain transfer (evasion knob)"},
}


def synthesize(ctx: AttackContext, params: dict):
    rng, fac, pop = ctx.rng, ctx.fac, ctx.pop
    txns = []
    n = int(params["n_victims"])
    n_dep = int(params["n_deposits"])
    esc = float(params["escalation"])
    seed = float(params["seed_amount"])
    round_bias = float(params["round_bias"])
    crypto_p = float(params["crypto_prob"])

    pool = [a for a in pop.account_ids if not pop.accounts[a].is_mule
            and not pop.accounts[a].is_synthetic]
    if not pool:
        return txns
    victims = rng.choice(pool, size=min(n, len(pool)), replace=False)

    for v in victims:
        prof = pop.profiles[v]
        camp = f"PIG-{int(rng.integers(1e7))}"
        payee = f"a_pig_{int(rng.integers(1e8))}"
        register_account(pop, payee, ctx.start_ts - rng.uniform(5, 40) * 86400,
                         prof.home_country, balance=100.0, rng=rng, is_mule=True)
        t = ctx.start_ts + rng.uniform(0, ctx.days * 0.3) * 86400
        amt = seed
        for d in range(n_dep):
            # Deposits are spaced days apart (a long con), escalating over time.
            t += rng.uniform(0.5, 4) * 86400
            if t > ctx.start_ts + ctx.days * 86400:
                break
            val = amt
            if rng.random() < round_bias:
                val = round(val / 50.0) * 50.0  # round-number ladder
            mcc = 6051 if rng.random() < crypto_p else 4829
            txns.append(fac.make(
                account_id=v, ts=t, rail=Rail.A2A_RT.value, channel=Channel.MOBILE_APP.value,
                amount=max(val, 50.0), counterparty_id=payee, counterparty_type="account",
                counterparty_country=prof.home_country, mcc=mcc,
                device_id=str(rng.choice(prof.device_ids)), auth_method=AuthMethod.UPI_PIN.value,
                is_new_counterparty=(d == 0), session_seconds=float(rng.uniform(20, 120)),
                is_fraud=1, vector="PIG-BUTCH", campaign_id=camp))
            amt *= esc

    return txns


register(AttackSpec(id="PIG-BUTCH", name="Pig-butchering investment scam",
                    technique_id="PIG-BUTCH", fn=synthesize, param_spec=PARAMS))
