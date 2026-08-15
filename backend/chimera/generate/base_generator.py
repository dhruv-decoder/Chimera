"""Legitimate background traffic.

Each account emits card/merchant activity (Poisson in time, diurnally shaped)
and account-to-account transfers (mostly to its known-payee set). Counterparty
novelty, geography, amounts and timing all flow from the account's latent
profile, giving the detector a realistic 'normal' to separate fraud from.
"""
from __future__ import annotations

import numpy as np

from ..schema import Channel, Rail, Transaction
from .common import TxnFactory, local_amount
from .entities import DAY, Population


def _sample_hour(prof, rng: np.random.Generator) -> float:
    """Pick an hour-of-day from the account's diurnal curve, with sub-hour jitter."""
    h = int(rng.choice(24, p=prof.active_hours))
    return (h + rng.random()) * 3600.0


def generate_legit(pop: Population, days: int, seed: int) -> list[Transaction]:
    rng = np.random.default_rng(seed + 101)
    fac = TxnFactory(pop, rng, prefix="t")
    start = pop.sim_start_ts
    txns: list[Transaction] = []

    # Per-account memory of counterparties already transacted with.
    seen: dict[str, set[str]] = {aid: set() for aid in pop.account_ids}
    merch_ids = list(pop.merchants.keys())

    for aid in pop.account_ids:
        prof = pop.profiles[aid]

        # ---- card / merchant activity ----
        n_card = rng.poisson(prof.txns_per_day * days)
        for _ in range(int(n_card)):
            day = rng.integers(0, days)
            ts = start + day * DAY + _sample_hour(prof, rng)
            # Prefer favourite categories; sometimes explore.
            if rng.random() < 0.7 and prof.pref_mcc:
                mcc = int(rng.choice(prof.pref_mcc))
                pool = pop.merchant_ids_by_mcc(mcc) or merch_ids
            else:
                mid0 = str(rng.choice(merch_ids))
                mcc = pop.merchants[mid0].mcc
                pool = [mid0]
            mid = str(rng.choice(pool))
            merch = pop.merchants[mid]
            is_new = mid not in seen[aid]
            seen[aid].add(mid)

            rail = Rail.CARD_CP.value if (merch.mcc in (5411, 5541, 5812) and rng.random() < 0.5) \
                else Rail.CARD_CNP.value
            channel = Channel.POS.value if rail == Rail.CARD_CP.value else \
                str(rng.choice([Channel.WEB.value, Channel.MOBILE_APP.value], p=[0.45, 0.55]))
            amt = local_amount(prof, rng, merch.mcc)
            dev = str(rng.choice(prof.device_ids))
            txns.append(fac.make(
                account_id=aid, ts=ts, rail=rail, channel=channel, amount=amt,
                counterparty_id=mid, counterparty_type="merchant",
                counterparty_country=merch.country, mcc=merch.mcc, device_id=dev,
                is_new_counterparty=is_new,
            ))

        # ---- account-to-account transfers ----
        n_a2a = rng.poisson(prof.a2a_per_week * days / 7.0)
        for _ in range(int(n_a2a)):
            day = rng.integers(0, days)
            ts = start + day * DAY + _sample_hour(prof, rng)
            # Mostly pay known payees; occasionally a genuinely new one.
            if prof.known_payees and rng.random() < 0.82:
                payee = str(rng.choice(prof.known_payees))
                is_new = payee not in seen[aid]
            else:
                payee = str(rng.choice(pop.account_ids))
                is_new = payee not in seen[aid]
            seen[aid].add(payee)
            payee_home = pop.accounts[payee].home_country
            amt = local_amount(prof, rng) * rng.uniform(0.6, 1.6)
            dev = str(rng.choice(prof.device_ids))
            txns.append(fac.make(
                account_id=aid, ts=ts, rail=Rail.A2A_RT.value,
                channel=Channel.MOBILE_APP.value, amount=amt,
                counterparty_id=payee, counterparty_type="account",
                counterparty_country=payee_home, mcc=4829, device_id=dev,
                is_new_counterparty=is_new,
            ))

    return txns
