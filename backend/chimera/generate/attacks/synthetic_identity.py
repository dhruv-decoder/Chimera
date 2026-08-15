"""SYN-ID: GenAI synthetic-identity nurture-and-bust-out.

A fabricated identity opens a low-KYC account, nurtures it with thin, plausible
activity to build standing, then busts out - rapidly consuming available balance
across card rails. Signatures: young synthetic account, clustered device reuse,
sudden jump in amount-to-balance ratio after a quiet nurture phase.
"""
from __future__ import annotations

import numpy as np

from ...schema import Channel, Rail
from . import AttackContext, AttackSpec, register, register_account

PARAMS = {
    "n_identities":    {"min": 1,    "max": 150,   "default": 30,   "desc": "synthetic identities"},
    "nurture_txns":    {"min": 0,    "max": 25,    "default": 6,    "desc": "small legit-looking priming txns (evasion knob)"},
    "bustout_ratio":   {"min": 0.3,  "max": 3.0,   "default": 1.4,  "desc": "bust-out spend as x balance (evasion knob)"},
    "shared_device_rings":{"min": 1, "max": 20,    "default": 4,    "desc": "identities collapse onto few devices"},
}


def synthesize(ctx: AttackContext, params: dict):
    rng, fac, pop = ctx.rng, ctx.fac, ctx.pop
    txns = []
    n = int(params["n_identities"])
    nurture = int(params["nurture_txns"])
    ratio = float(params["bustout_ratio"])
    rings = max(1, int(params["shared_device_rings"]))

    merch_pool = list(pop.merchants.values())
    for i in range(n):
        camp = f"SYNID-{i}-{int(rng.integers(1e6))}"
        opened = ctx.start_ts - rng.uniform(20, 120) * 86400  # young-ish
        balance = float(np.exp(rng.normal(4.0, 0.5)))
        acct = f"a_syn_{i}_{int(rng.integers(1e7))}"
        register_account(pop, acct, opened, "IN" if rng.random() < 0.6 else "US",
                         balance=balance, rng=rng, is_synthetic=True)
        # Device fingerprint reuse across a small number of rings (bot farm).
        shared_dev = f"d_synring_{i % rings}"
        prof = pop.profiles[acct]

        # Nurture phase: small, ordinary purchases to age the account.
        for _ in range(nurture):
            merch = merch_pool[int(rng.integers(len(merch_pool)))]
            ts = opened + rng.uniform(5, 90) * 86400
            amt = float(np.exp(rng.normal(2.6, 0.5)))
            txns.append(fac.make(
                account_id=acct, ts=min(ts, ctx.start_ts + ctx.days * 86400),
                rail=Rail.CARD_CNP.value, channel=Channel.MOBILE_APP.value, amount=amt,
                counterparty_id=merch.merchant_id, counterparty_type="merchant",
                counterparty_country=merch.country, mcc=merch.mcc, device_id=shared_dev,
                is_new_counterparty=True, is_fraud=1, vector="SYN-ID", campaign_id=camp))

        # Bust-out: rapid consumption of the line across a short window.
        n_bust = int(rng.integers(3, 8))
        t0 = ctx.start_ts + rng.uniform(0, ctx.days) * 86400
        per = (balance * ratio) / n_bust
        for _ in range(n_bust):
            merch = merch_pool[int(rng.integers(len(merch_pool)))]
            ts = t0 + rng.uniform(0, 2 * 3600)
            txns.append(fac.make(
                account_id=acct, ts=ts, rail=Rail.CARD_CNP.value,
                channel=Channel.WEB.value, amount=per * rng.uniform(0.7, 1.3),
                counterparty_id=merch.merchant_id, counterparty_type="merchant",
                counterparty_country=merch.country, mcc=merch.mcc, device_id=shared_dev,
                is_new_counterparty=True, is_fraud=1, vector="SYN-ID", campaign_id=camp))

    return txns


register(AttackSpec(id="SYN-ID", name="Synthetic-identity bust-out",
                    technique_id="SYN-ID", fn=synthesize, param_spec=PARAMS))
