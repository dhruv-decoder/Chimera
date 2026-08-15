"""DF-APP: deepfake-authorised push payment scam.

A real victim is socially engineered by a cloned voice/video into authorising a
real-time push to an attacker-controlled payee. The authorisation is genuine,
so auth alone cannot stop it. Signatures: first-time high-value payee, voice-
auth channel, amount far above the victim's history, short deliberation.
"""
from __future__ import annotations

import numpy as np

from ...schema import AuthMethod, Channel, Rail
from . import AttackContext, AttackSpec, register, register_account

PARAMS = {
    "n_victims":       {"min": 1,    "max": 200,   "default": 40,   "desc": "victims targeted"},
    "amount_mult":     {"min": 1.5,  "max": 25.0,  "default": 4.5,  "desc": "x the victim's typical ticket (evasion knob)"},
    "urgency_seconds": {"min": 3,    "max": 600,   "default": 45,   "desc": "deliberation time under pressure (evasion knob)"},
    "voice_prob":      {"min": 0.0,  "max": 1.0,   "default": 0.5,  "desc": "share authorised via voice channel (evasion knob)"},
    "groom_prob":      {"min": 0.0,  "max": 1.0,   "default": 0.4,  "desc": "victims first sent a small 'test' transfer (blends in - evasion knob)"},
}


def synthesize(ctx: AttackContext, params: dict):
    rng, fac, pop = ctx.rng, ctx.fac, ctx.pop
    txns = []
    n_victims = int(params["n_victims"])
    mult = float(params["amount_mult"])
    urgency = float(params["urgency_seconds"])
    voice_p = float(params["voice_prob"])
    groom_p = float(params["groom_prob"])

    # Victims: established, non-mule accounts (the scam preys on real customers).
    pool = [a for a in pop.account_ids if not pop.accounts[a].is_mule
            and not pop.accounts[a].is_synthetic and pop.accounts[a].opened_ts < ctx.start_ts]
    if not pool:
        return txns
    victims = rng.choice(pool, size=min(n_victims, len(pool)), replace=False)

    for v in victims:
        prof = pop.profiles[v]
        camp = f"DFAPP-{int(rng.integers(1e7))}"
        # Fresh mule beneficiary the victim has never paid.
        mule = f"a_dfmule_{int(rng.integers(1e8))}"
        register_account(pop, mule, ctx.start_ts - rng.uniform(0, 6) * 86400,
                         prof.home_country, balance=200.0, rng=rng, is_mule=True)
        typical = float(np.exp(prof.log_amount_mu))
        ts = ctx.start_ts + rng.uniform(0, ctx.days) * 86400
        dev = str(rng.choice(prof.device_ids))
        # Grooming: a fraction of victims are induced to send a small 'test'
        # transfer first, so the beneficiary is no longer brand-new when the big
        # transfer lands. This blends the scam into legitimate new-payee behaviour.
        groomed = rng.random() < groom_p
        if groomed:
            txns.append(fac.make(
                account_id=v, ts=ts - rng.uniform(1, 48) * 3600, rail=Rail.A2A_RT.value,
                channel=Channel.MOBILE_APP.value, amount=typical * rng.uniform(0.3, 0.9),
                counterparty_id=mule, counterparty_type="account",
                counterparty_country=prof.home_country, mcc=4829, device_id=dev,
                auth_method=AuthMethod.UPI_PIN.value, is_new_counterparty=True,
                session_seconds=float(rng.uniform(20, 90)),
                is_fraud=1, vector="DF-APP", campaign_id=camp))
        amt = typical * mult * rng.uniform(0.7, 1.3)
        auth = AuthMethod.VOICE.value if rng.random() < voice_p else AuthMethod.UPI_PIN.value
        txns.append(fac.make(
            account_id=v, ts=ts, rail=Rail.A2A_RT.value, channel=Channel.MOBILE_APP.value,
            amount=amt, counterparty_id=mule, counterparty_type="account",
            counterparty_country=prof.home_country, mcc=4829,
            device_id=dev, auth_method=auth,
            is_new_counterparty=(not groomed), session_seconds=urgency * rng.uniform(0.6, 1.5),
            is_fraud=1, vector="DF-APP", campaign_id=camp))

    return txns


register(AttackSpec(id="DF-APP", name="Deepfake-authorised push payment scam",
                    technique_id="DF-APP", fn=synthesize, param_spec=PARAMS))
