"""MULE-NET: money-mule network layering on real-time rails.

Illicit funds are placed into an entry mule, layered rapidly through a ring of
freshly-recruited mule accounts (fan-in then fan-out), and off-ramped through
high-risk cash-out merchants. Signatures: high in/out degree, short fund dwell,
young accounts with immediate high throughput, tight community structure.
"""
from __future__ import annotations

from ...schema import AuthMethod, Channel, Rail
from . import AttackContext, AttackSpec, register, register_account

PARAMS = {
    "n_rings":        {"min": 1,   "max": 12,     "default": 4,     "desc": "number of independent mule rings"},
    "ring_size":      {"min": 3,   "max": 15,     "default": 6,     "desc": "mule accounts per ring"},
    "layering_hops":  {"min": 1,   "max": 6,      "default": 3,     "desc": "hop count during layering"},
    "placement":      {"min": 500, "max": 40000,  "default": 6000,  "desc": "illicit sum placed per ring"},
    "dwell_seconds":  {"min": 30,  "max": 86400,  "default": 300,   "desc": "how long funds rest per hop (evasion knob)"},
    "fanout":         {"min": 1,   "max": 8,      "default": 3,     "desc": "off-ramp accounts funds disperse to"},
}


def synthesize(ctx: AttackContext, params: dict):
    rng, fac, pop = ctx.rng, ctx.fac, ctx.pop
    txns = []
    n_rings = int(params["n_rings"])
    ring_size = int(params["ring_size"])
    hops = int(params["layering_hops"])
    dwell = float(params["dwell_seconds"])
    fanout = int(params["fanout"])

    for r in range(n_rings):
        camp = f"MULE-{r}-{int(rng.integers(1e6))}"
        # Ring opens recently - a defining risk signal for mule networks.
        opened = ctx.start_ts + rng.uniform(0, ctx.days) * 86400 - rng.uniform(0, 5) * 86400
        home = "IN" if rng.random() < 0.7 else "PH"
        mules = []
        for m in range(ring_size):
            aid = f"a_mule_{r}_{m}_{int(rng.integers(1e6))}"
            register_account(pop, aid, opened, home, balance=200.0, rng=rng, is_mule=True)
            mules.append(aid)

        # Placement: illicit funds enter the entry mule.
        t0 = ctx.start_ts + rng.uniform(0, ctx.days) * 86400
        entry = mules[0]
        amount = float(params["placement"])
        src = f"a_src_{r}_{int(rng.integers(1e6))}"
        register_account(pop, src, opened, home, balance=amount * 1.2, rng=rng, is_mule=True)
        txns.append(fac.make(
            account_id=src, ts=t0, rail=Rail.A2A_RT.value, channel=Channel.MOBILE_APP.value,
            amount=amount, counterparty_id=entry, counterparty_type="account",
            counterparty_country=home, mcc=4829, device_id=f"d_{src}",
            auth_method=AuthMethod.UPI_PIN.value, is_new_counterparty=True,
            is_fraud=1, vector="MULE-NET", campaign_id=camp))

        # Layering: hop the funds through the ring, decaying slightly (fees skimmed).
        cur, bal, t = entry, amount, t0
        for h in range(hops):
            nxt = mules[(h + 1) % ring_size]
            t += dwell * rng.uniform(0.5, 1.5)
            bal *= rng.uniform(0.9, 0.98)
            txns.append(fac.make(
                account_id=cur, ts=t, rail=Rail.A2A_RT.value, channel=Channel.MOBILE_APP.value,
                amount=bal, counterparty_id=nxt, counterparty_type="account",
                counterparty_country=home, mcc=4829, device_id=f"d_{cur}",
                auth_method=AuthMethod.UPI_PIN.value, is_new_counterparty=True,
                is_fraud=1, vector="MULE-NET", campaign_id=camp))
            cur = nxt

        # Fan-out off-ramp to cash-out endpoints.
        share = bal / max(fanout, 1)
        for f in range(fanout):
            off = f"a_off_{r}_{f}_{int(rng.integers(1e6))}"
            register_account(pop, off, opened, home, balance=100.0, rng=rng, is_mule=True)
            t += dwell * rng.uniform(0.3, 1.0)
            txns.append(fac.make(
                account_id=cur, ts=t, rail=Rail.A2A_RT.value, channel=Channel.MOBILE_APP.value,
                amount=share * rng.uniform(0.85, 1.0), counterparty_id=off,
                counterparty_type="account", counterparty_country=home, mcc=6051,
                device_id=f"d_{cur}", auth_method=AuthMethod.UPI_PIN.value,
                is_new_counterparty=True, is_fraud=1, vector="MULE-NET", campaign_id=camp))

    return txns


register(AttackSpec(id="MULE-NET", name="Money-mule network layering",
                    technique_id="MULE-NET", fn=synthesize, param_spec=PARAMS))
