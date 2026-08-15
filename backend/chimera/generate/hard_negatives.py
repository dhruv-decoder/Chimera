"""Hard negatives: legitimate traffic that superficially resembles fraud.

Without these, synthetic fraud is trivially separable (any single flag - the
agent channel, a shared device, a high-value new payee - perfectly splits the
classes) and the detector scores a meaningless AUC of 1.0. Injecting benign
look-alikes forces genuine class overlap, so reported metrics reflect a model
that actually has to discriminate:

  * benign agentic-commerce shopping (agent channel is mostly legitimate),
  * legitimate large first-time payees (a new landlord, a car purchase),
  * travel (foreign IP + cross-border spend),
  * high in-degree 'collector' accounts (landlords, clubs, popular sellers),
  * recurring escalating investments (SIPs) - a benign analogue of pig-butchering,
  * shared family devices (mild device fan-out).

All events are labelled legit; the label is never written into an observable.
"""
from __future__ import annotations

import numpy as np

from ..schema import AuthMethod, Channel, EntryMode, Rail
from .common import TRUSTED_AGENTS, TxnFactory, local_amount
from .entities import DAY, Population


def generate_hard_negatives(pop: Population, days: int, seed: int) -> list:
    rng = np.random.default_rng(seed + 202)
    fac = TxnFactory(pop, rng, prefix="h")
    start = pop.sim_start_ts
    end = start + days * DAY
    txns = []
    real_accounts = [a for a in pop.account_ids
                     if not pop.accounts[a].is_mule and not pop.accounts[a].is_synthetic]
    merch_pool = list(pop.merchants.values())

    # 1) Benign agentic commerce - a slice of users let a trusted, network-
    #    registered agent shop for them. Real agents run on shared cloud
    #    infrastructure and serve many principals, so a trusted agent id carries
    #    high device- and principal-fan-out that is entirely legitimate. This is
    #    the hard negative that stops the detector from flagging agent fan-out
    #    on its own - AGENT-HIJACK has to be caught on credential integrity.
    agent_users = rng.choice(real_accounts, size=max(1, len(real_accounts) // 5), replace=False)
    for aid in agent_users:
        prof = pop.profiles[aid]
        n = rng.poisson(2.5 * days / 7.0)
        agent_id = str(rng.choice(TRUSTED_AGENTS))
        for _ in range(int(n)):
            merch = merch_pool[int(rng.integers(len(merch_pool)))]
            ts = start + rng.uniform(0, days) * DAY
            amt = local_amount(prof, rng, merch.mcc)
            txns.append(fac.make(
                account_id=aid, ts=ts, rail=Rail.CARD_CNP.value, channel=Channel.AGENT.value,
                amount=amt, counterparty_id=merch.merchant_id, counterparty_type="merchant",
                counterparty_country=merch.country, mcc=merch.mcc,
                device_id=f"d_{agent_id}", auth_method=AuthMethod.NONE.value,
                entry_mode=EntryMode.AGENTIC_TOKEN.value, is_new_counterparty=rng.random() < 0.4,
                session_seconds=float(rng.uniform(1.0, 8.0)),  # agents are fast but legit
                agent_id=agent_id,  # attestation/trust/cap default to a legit delegated mandate
                is_fraud=0, vector="legit"))

    # 2) Legitimate large first-time payees (new landlord, vendor, big-ticket).
    for aid in rng.choice(real_accounts, size=max(1, len(real_accounts) // 7), replace=False):
        prof = pop.profiles[aid]
        payee = str(rng.choice(pop.account_ids))
        ts = start + rng.uniform(0, days) * DAY
        amt = float(np.exp(prof.log_amount_mu)) * rng.uniform(4, 12)
        auth = AuthMethod.VOICE.value if rng.random() < 0.15 else AuthMethod.UPI_PIN.value
        txns.append(fac.make(
            account_id=aid, ts=ts, rail=Rail.A2A_RT.value, channel=Channel.MOBILE_APP.value,
            amount=amt, counterparty_id=payee, counterparty_type="account",
            counterparty_country=prof.home_country, mcc=4829,
            device_id=str(rng.choice(prof.device_ids)), auth_method=auth,
            is_new_counterparty=True, session_seconds=float(rng.uniform(30, 240)),
            is_fraud=0, vector="legit"))

    # 3) Travel - foreign IP + cross-border card spend by real customers.
    for aid in rng.choice(real_accounts, size=max(1, len(real_accounts) // 15), replace=False):
        prof = pop.profiles[aid]
        foreign = str(rng.choice(["US", "GB", "AE", "SG", "DE", "AU"]))
        n = int(rng.integers(2, 8))
        t0 = start + rng.uniform(0, days) * DAY
        for _ in range(n):
            merch = merch_pool[int(rng.integers(len(merch_pool)))]
            ts = t0 + rng.uniform(0, 5) * DAY
            amt = local_amount(prof, rng, merch.mcc)
            txns.append(fac.make(
                account_id=aid, ts=ts, rail=Rail.CARD_CNP.value, channel=Channel.WEB.value,
                amount=amt, counterparty_id=merch.merchant_id, counterparty_type="merchant",
                counterparty_country=foreign, mcc=merch.mcc,
                device_id=str(rng.choice(prof.device_ids)), ip_country=foreign,
                ip_asn_risk=float(rng.uniform(0.05, 0.35)), is_new_counterparty=True,
                is_fraud=0, vector="legit"))

    # 4) Collector accounts - many legit payers -> one account (rent, clubs, sellers).
    collectors = rng.choice(real_accounts, size=max(2, len(real_accounts) // 300), replace=False)
    for coll in collectors:
        payers = rng.choice(real_accounts, size=int(rng.integers(25, 80)), replace=False)
        for p in payers:
            if p == coll:
                continue
            prof = pop.profiles[p]
            ts = start + rng.uniform(0, days) * DAY
            amt = float(np.exp(prof.log_amount_mu)) * rng.uniform(1.5, 4.0)
            txns.append(fac.make(
                account_id=p, ts=ts, rail=Rail.A2A_RT.value, channel=Channel.MOBILE_APP.value,
                amount=amt, counterparty_id=str(coll), counterparty_type="account",
                counterparty_country=pop.accounts[coll].home_country, mcc=4829,
                device_id=str(rng.choice(prof.device_ids)), is_new_counterparty=rng.random() < 0.3,
                is_fraud=0, vector="legit"))

    # 5) Recurring escalating investments (SIP) - benign analogue of pig-butchering.
    for aid in rng.choice(real_accounts, size=max(1, len(real_accounts) // 20), replace=False):
        prof = pop.profiles[aid]
        payee = str(rng.choice(pop.account_ids))
        t = start + rng.uniform(0, days * 0.3) * DAY
        amt = float(np.exp(prof.log_amount_mu)) * rng.uniform(1.0, 2.0)
        for d in range(int(rng.integers(3, 7))):
            t += rng.uniform(4, 9) * DAY
            if t > end:
                break
            txns.append(fac.make(
                account_id=aid, ts=t, rail=Rail.A2A_RT.value, channel=Channel.MOBILE_APP.value,
                amount=round(amt / 50) * 50, counterparty_id=payee, counterparty_type="account",
                counterparty_country=prof.home_country, mcc=6051,
                device_id=str(rng.choice(prof.device_ids)), is_new_counterparty=(d == 0),
                is_fraud=0, vector="legit"))
            amt *= rng.uniform(1.05, 1.25)

    # 6) Shared family devices - two accounts, one device (mild device fan-out).
    for _ in range(max(1, len(real_accounts) // 40)):
        pair = rng.choice(real_accounts, size=2, replace=False)
        shared = pop.profiles[pair[0]].device_ids[0]
        prof = pop.profiles[pair[1]]
        for _ in range(int(rng.integers(2, 6))):
            merch = merch_pool[int(rng.integers(len(merch_pool)))]
            ts = start + rng.uniform(0, days) * DAY
            txns.append(fac.make(
                account_id=str(pair[1]), ts=ts, rail=Rail.CARD_CNP.value,
                channel=Channel.MOBILE_APP.value, amount=local_amount(prof, rng, merch.mcc),
                counterparty_id=merch.merchant_id, counterparty_type="merchant",
                counterparty_country=merch.country, mcc=merch.mcc, device_id=shared,
                is_new_counterparty=False, is_fraud=0, vector="legit"))

    return txns
