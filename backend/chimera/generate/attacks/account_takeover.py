"""ATO-STUFF: AI-orchestrated account takeover and drain.

A compromised, established account is accessed from a new device and risky
network, its trusted-payee/limit state is changed, then value is drained via a
push to a mule plus card-not-present spend. Signatures: new device on an aged
account, geo/ASN anomaly, new high-value payee shortly after login.
"""
from __future__ import annotations

import numpy as np

from ...schema import AuthMethod, Channel, Device, EntryMode, Rail
from . import AttackContext, AttackSpec, register, register_account

PARAMS = {
    "n_victims":    {"min": 1,    "max": 200,  "default": 35,   "desc": "accounts taken over"},
    "drain_ratio":  {"min": 0.2,  "max": 1.0,  "default": 0.7,  "desc": "fraction of balance drained (evasion knob)"},
    "asn_risk":     {"min": 0.1,  "max": 0.98, "default": 0.8,  "desc": "attacker network risk (evasion knob - lower to blend)"},
    "foreign_prob": {"min": 0.0,  "max": 1.0,  "default": 0.7,  "desc": "share of logins from foreign geo (evasion knob)"},
    "card_legs":    {"min": 0,    "max": 6,    "default": 2,    "desc": "extra CNP purchases during the drain"},
}


def synthesize(ctx: AttackContext, params: dict):
    rng, fac, pop = ctx.rng, ctx.fac, ctx.pop
    txns = []
    n = int(params["n_victims"])
    drain = float(params["drain_ratio"])
    asn = float(params["asn_risk"])
    foreign_p = float(params["foreign_prob"])
    card_legs = int(params["card_legs"])

    # Target aged, well-funded, real accounts.
    pool = [a for a in pop.account_ids
            if not pop.accounts[a].is_mule and not pop.accounts[a].is_synthetic
            and (ctx.start_ts - pop.accounts[a].opened_ts) / 86400 > 200]
    if not pool:
        return txns
    victims = rng.choice(pool, size=min(n, len(pool)), replace=False)
    merch_pool = list(pop.merchants.values())

    for v in victims:
        prof = pop.profiles[v]
        acc = pop.accounts[v]
        camp = f"ATO-{int(rng.integers(1e7))}"
        # Attacker device + network, distinct from the account's own devices.
        atk_dev = f"d_ato_{int(rng.integers(1e8))}"
        pop.devices[atk_dev] = Device(
            device_id=atk_dev, kind="web", first_seen_ts=ctx.start_ts, is_headless=True)
        prof.device_ids.append(atk_dev)
        ip_country = str(rng.choice(["US", "NG", "DE", "RU", "PH"])) if rng.random() < foreign_p \
            else acc.home_country
        t0 = ctx.start_ts + rng.uniform(0, ctx.days) * 86400

        # Drain via push to a fresh mule.
        mule = f"a_atomule_{int(rng.integers(1e8))}"
        register_account(pop, mule, ctx.start_ts - rng.uniform(0, 4) * 86400,
                         acc.home_country, balance=100.0, rng=rng, is_mule=True)
        txns.append(fac.make(
            account_id=v, ts=t0, rail=Rail.A2A_RT.value, channel=Channel.WEB.value,
            amount=prof.balance * drain, counterparty_id=mule, counterparty_type="account",
            counterparty_country=acc.home_country, mcc=4829, device_id=atk_dev,
            ip_country=ip_country, ip_asn_risk=asn, auth_method=AuthMethod.OTP.value,
            is_new_counterparty=True, session_seconds=float(rng.uniform(8, 40)),
            is_fraud=1, vector="ATO-STUFF", campaign_id=camp))

        # A few CNP purchases from the same hijacked session.
        for _ in range(card_legs):
            merch = merch_pool[int(rng.integers(len(merch_pool)))]
            ts = t0 + rng.uniform(60, 3600)
            amt = float(np.exp(rng.normal(prof.log_amount_mu + 0.8, 0.6)))
            txns.append(fac.make(
                account_id=v, ts=ts, rail=Rail.CARD_CNP.value, channel=Channel.WEB.value,
                amount=amt, counterparty_id=merch.merchant_id, counterparty_type="merchant",
                counterparty_country=merch.country, mcc=merch.mcc, device_id=atk_dev,
                ip_country=ip_country, ip_asn_risk=asn, entry_mode=EntryMode.MANUAL.value,
                is_new_counterparty=True, session_seconds=float(rng.uniform(5, 30)),
                is_fraud=1, vector="ATO-STUFF", campaign_id=camp))

    return txns


register(AttackSpec(id="ATO-STUFF", name="Account takeover and drain",
                    technique_id="ATO-STUFF", fn=synthesize, param_spec=PARAMS))
