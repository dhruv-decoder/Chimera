"""CARD-TEST: automated card testing / BIN attack.

Many stolen or enumerated cards are validated with bursts of micro-value
authorisations from shared infrastructure. Signatures: micro amounts, many
distinct cards behind one device/IP, tight time window, velocity spike.
"""
from __future__ import annotations

from ...schema import AuthMethod, Channel, EntryMode, Rail
from . import AttackContext, AttackSpec, register, register_account

PARAMS = {
    "n_campaigns":     {"min": 1,    "max": 8,     "default": 3,    "desc": "distinct testing campaigns"},
    "cards_per_device":{"min": 5,    "max": 300,   "default": 60,   "desc": "cards behind one device/IP"},
    "amount_max":      {"min": 0.5,  "max": 30.0,  "default": 3.0,  "desc": "max micro-auth amount (evasion knob)"},
    "burst_minutes":   {"min": 2,    "max": 720,   "default": 20,   "desc": "window over which the burst runs (evasion knob)"},
    "probes_per_card": {"min": 1,    "max": 4,     "default": 1,    "desc": "auth attempts per card"},
}


def synthesize(ctx: AttackContext, params: dict):
    rng, fac, pop = ctx.rng, ctx.fac, ctx.pop
    txns = []
    n_camp = int(params["n_campaigns"])
    n_cards = int(params["cards_per_device"])
    amax = float(params["amount_max"])
    window = float(params["burst_minutes"]) * 60.0
    probes = int(params["probes_per_card"])

    # Testing usually hits low-friction digital-goods / donation-style merchants.
    test_merchants = [m for m in pop.merchants.values() if m.mcc in (5816, 4816, 5999)] \
        or list(pop.merchants.values())

    for c in range(n_camp):
        camp = f"CARDTEST-{c}-{int(rng.integers(1e6))}"
        dev = f"d_bot_{c}_{int(rng.integers(1e6))}"
        ip_country = str(rng.choice(["US", "NG", "DE", "IN"]))
        t0 = ctx.start_ts + rng.uniform(0, ctx.days) * 86400
        merch = test_merchants[int(rng.integers(len(test_merchants)))]

        for k in range(n_cards):
            # Each 'card' is a throwaway attacker-controlled payer account, all
            # sharing the one bot device/IP.
            card = f"a_card_{c}_{k}_{int(rng.integers(1e7))}"
            register_account(pop, card, ctx.start_ts - rng.uniform(30, 400) * 86400,
                             ip_country, balance=500.0, rng=rng, is_headless=True)
            for _ in range(probes):
                ts = t0 + rng.uniform(0, window)
                amt = float(rng.uniform(0.5, amax))
                txns.append(fac.make(
                    account_id=card, ts=ts, rail=Rail.CARD_CNP.value,
                    channel=Channel.WEB.value, amount=amt,
                    counterparty_id=merch.merchant_id, counterparty_type="merchant",
                    counterparty_country=merch.country, mcc=merch.mcc, device_id=dev,
                    ip_country=ip_country, ip_asn_risk=float(rng.uniform(0.6, 0.98)),
                    auth_method=AuthMethod.NONE.value, entry_mode=EntryMode.TOKEN.value,
                    is_new_counterparty=True, session_seconds=float(rng.uniform(0.5, 4.0)),
                    is_fraud=1, vector="CARD-TEST", campaign_id=camp))

    return txns


register(AttackSpec(id="CARD-TEST", name="Automated card testing / BIN attack",
                    technique_id="CARD-TEST", fn=synthesize, param_spec=PARAMS))
