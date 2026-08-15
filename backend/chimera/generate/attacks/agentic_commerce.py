"""AGENT-CARD: agentic-commerce carding / autonomous checkout abuse.

Autonomous shopping agents (Agent Pay / Intelligent Commerce style) run
machine-speed purchase and card-validation campaigns using delegated tokens.
Signatures: agent channel + agentic token, headless runtime, sub-second-to-
few-second sessions, atypical purchase cadence, many SKUs in a short window.
"""
from __future__ import annotations

from ...schema import AuthMethod, Channel, EntryMode, Rail
from . import AttackContext, AttackSpec, register, register_account

PARAMS = {
    "n_agents":         {"min": 1,   "max": 40,    "default": 8,    "desc": "autonomous agent instances"},
    "purchases_per_agent":{"min": 3, "max": 80,    "default": 20,   "desc": "purchases per agent run"},
    "session_seconds":  {"min": 0.3, "max": 90.0,  "default": 2.0,  "desc": "per-checkout time (evasion knob - raise to humanise)"},
    "amount_mu":        {"min": 2.5, "max": 6.0,   "default": 4.3,  "desc": "log-mean ticket size"},
    "window_minutes":   {"min": 3,   "max": 480,   "default": 30,   "desc": "campaign window (evasion knob)"},
}


def synthesize(ctx: AttackContext, params: dict):
    import numpy as np
    rng, fac, pop = ctx.rng, ctx.fac, ctx.pop
    txns = []
    n_agents = int(params["n_agents"])
    per = int(params["purchases_per_agent"])
    sess = float(params["session_seconds"])
    amu = float(params["amount_mu"])
    window = float(params["window_minutes"]) * 60.0

    merch_pool = list(pop.merchants.values())
    for a in range(n_agents):
        camp = f"AGENT-{a}-{int(rng.integers(1e6))}"
        # Delegated agent account - the human principal exists, but the agent
        # runs headless with a delegated token and no step-up.
        acct = f"a_agent_{a}_{int(rng.integers(1e7))}"
        register_account(pop, acct, ctx.start_ts - rng.uniform(20, 300) * 86400,
                         "US", balance=8000.0, rng=rng, is_headless=True)
        dev = f"d_{acct}"
        t0 = ctx.start_ts + rng.uniform(0, ctx.days) * 86400
        for k in range(per):
            merch = merch_pool[int(rng.integers(len(merch_pool)))]
            ts = t0 + (k / max(per, 1)) * window + rng.uniform(0, window / max(per, 1))
            amt = float(np.exp(rng.normal(amu, 0.5)))
            txns.append(fac.make(
                account_id=acct, ts=ts, rail=Rail.CARD_CNP.value,
                channel=Channel.AGENT.value, amount=amt,
                counterparty_id=merch.merchant_id, counterparty_type="merchant",
                counterparty_country=merch.country, mcc=merch.mcc, device_id=dev,
                ip_asn_risk=float(rng.uniform(0.3, 0.85)),
                auth_method=AuthMethod.NONE.value, entry_mode=EntryMode.AGENTIC_TOKEN.value,
                is_new_counterparty=True, session_seconds=max(0.3, sess * rng.uniform(0.6, 1.4)),
                is_fraud=1, vector="AGENT-CARD", campaign_id=camp))

    return txns


register(AttackSpec(id="AGENT-CARD", name="Agentic-commerce carding",
                    technique_id="AGENT-CARD", fn=synthesize, param_spec=PARAMS))
