"""AGENT-HIJACK: delegated-token / agent-identity abuse in agentic commerce.

The 2026 frontier. Under Mastercard Agent Pay (Agentic Token) and Visa's Trusted
Agent Protocol, a purchase can be initiated by an autonomous agent acting on a
cardholder's behalf via a delegated credential. An attacker who obtains that
credential - through prompt injection of a shopping agent, token theft, or a
malicious agent SDK - can spend inside someone else's mandate.

Why this is hard, and why it needs a new defence family: a hijacked agent looks
identical to a legitimate one on the signals that catch ordinary carding. It is
fast (so session-time and velocity look agentic-normal), it is automated (so
device features look agentic-normal), and a real trusted agent already serves
many principals (so principal fan-out looks agentic-normal). The only thing that
separates abuse is the integrity of the credential itself: a missing or replayed
network attestation, low directory trust, spend outside the granted mandate
(amount over the delegated cap, off-scope high-risk merchant). The evasion knobs
below are exactly those integrity signals - raise attestation, raise trust, keep
spend under the cap - which is what the adversarial search will exploit and what
retraining then has to recover.
"""
from __future__ import annotations

from ...schema import AuthMethod, Channel, EntryMode, Rail
from ..common import local_amount
from . import AttackContext, AttackSpec, register

PARAMS = {
    "n_agents":            {"min": 1,   "max": 20,   "default": 4,    "desc": "compromised/rogue agent identities"},
    "principals_per_agent":{"min": 3,   "max": 60,   "default": 18,   "desc": "victim mandates replayed per agent (fan-out)"},
    "purchases_per_principal":{"min": 1,"max": 6,    "default": 2,    "desc": "purchases per hijacked mandate"},
    "attestation_prob":    {"min": 0.0, "max": 1.0,  "default": 0.1,  "desc": "share carrying a valid-looking attestation (evasion knob - raise to mimic a trusted agent)"},
    "cap_breach":          {"min": 0.4, "max": 2.5,  "default": 1.4,  "desc": "amount / delegated cap (evasion knob - lower to stay inside the mandate)"},
    "trust_mu":            {"min": 0.1, "max": 0.95, "default": 0.35, "desc": "mean directory trust of the agent id (evasion knob - raise to look reputable)"},
    "offscope_prob":       {"min": 0.0, "max": 1.0,  "default": 0.6,  "desc": "share hitting off-mandate high-risk merchants (evasion knob - lower to blend into normal agent shopping)"},
}


def synthesize(ctx: AttackContext, params: dict):
    import numpy as np
    rng, fac, pop = ctx.rng, ctx.fac, ctx.pop
    txns = []
    n_agents = int(params["n_agents"])
    principals = int(params["principals_per_agent"])
    per = int(params["purchases_per_principal"])
    att_prob = float(params["attestation_prob"])
    cap_breach = float(params["cap_breach"])
    trust_mu = float(params["trust_mu"])
    offscope = float(params["offscope_prob"])

    # Off-mandate targets: resellable / high-risk merchants (gift cards, crypto,
    # jewellery). In-mandate mimicry draws from the same merchant + amount
    # distribution as legitimate agent shopping, so the only thing left to catch
    # a well-tuned hijack is the credential integrity - which is the point.
    high_risk = [m for m in pop.merchants.values() if m.risk_tier >= 2] or \
                [m for m in pop.merchants.values() if m.risk_tier >= 1]
    all_merch = list(pop.merchants.values())
    victims_all = [a for a in pop.account_ids
                   if not pop.accounts[a].is_mule and not pop.accounts[a].is_synthetic]

    for a in range(n_agents):
        agent_id = f"agt_hj_{a}_{int(rng.integers(1e6))}"
        dev = f"d_{agent_id}"                       # shared agent runtime (cloud infra)
        k = min(principals, len(victims_all))
        victims = rng.choice(victims_all, size=k, replace=False)
        for v in victims:
            prof = pop.profiles[str(v)]
            t0 = ctx.start_ts + rng.uniform(0, ctx.days) * 86400
            for j in range(per):
                if rng.random() < offscope and high_risk:
                    merch = high_risk[int(rng.integers(len(high_risk)))]
                    amt = float(np.exp(rng.normal(4.6, 0.7)))       # elevated, resellable
                else:
                    merch = all_merch[int(rng.integers(len(all_merch)))]
                    amt = local_amount(prof, rng, merch.mcc)        # blends with normal
                ts = t0 + j * rng.uniform(20, 900)   # a short automated burst per mandate
                txns.append(fac.make(
                    account_id=str(v), ts=ts, rail=Rail.CARD_CNP.value,
                    channel=Channel.AGENT.value, amount=amt,
                    counterparty_id=merch.merchant_id, counterparty_type="merchant",
                    counterparty_country=merch.country, mcc=merch.mcc, device_id=dev,
                    # runs on the same reputable agent cloud as legitimate agents,
                    # so the network origin (ASN risk) is deliberately not a tell
                    auth_method=AuthMethod.NONE.value, entry_mode=EntryMode.AGENTIC_TOKEN.value,
                    is_new_counterparty=bool(rng.random() < 0.6),
                    session_seconds=float(rng.uniform(1.0, 8.0)),   # mimics a legit agent
                    agent_id=agent_id,
                    agent_attested=int(rng.random() < att_prob),
                    agent_trust=float(np.clip(rng.normal(trust_mu, 0.1), 0, 1)),
                    mandate_cap_ratio=float(np.clip(cap_breach * rng.uniform(0.8, 1.2), 0, 3)),
                    is_fraud=1, vector="AGENT-HIJACK", campaign_id=agent_id))

    return txns


register(AttackSpec(id="AGENT-HIJACK", name="Delegated-token / agent-identity abuse",
                    technique_id="AGENT-HIJACK", fn=synthesize, param_spec=PARAMS))
