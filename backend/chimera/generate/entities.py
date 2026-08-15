"""Synthetic population: accounts, devices, merchants, and behavioural profiles.

Fidelity comes from *structure*: each account has a latent profile (home
geography, spend cadence, typical ticket size, preferred merchant categories,
active hours, a stable set of known payees). Legitimate traffic is drawn from
these profiles, so a coordinated attack (e.g. a mule ring, or an aged account
suddenly paying a brand-new high-value payee) shows up as a genuine deviation
rather than something trivially separable by a single flag.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np

from ..schema import Account, Device, Merchant

# Country mix - weighted toward India for GFF/UPI relevance, with a realistic
# international tail for cross-border card traffic.
COUNTRIES = ["IN", "US", "GB", "AE", "SG", "DE", "AU", "NG", "PH", "BR"]
COUNTRY_W = np.array([0.46, 0.14, 0.08, 0.07, 0.05, 0.05, 0.05, 0.03, 0.03, 0.04])

# Merchant category codes with typical (log-mean, log-sigma) ticket in the
# account's local currency-normalised units, plus a base risk tier.
MCC_TABLE = {
    5411: ("grocery", 3.4, 0.6, 0),
    5812: ("restaurant", 3.0, 0.7, 0),
    5541: ("fuel", 3.6, 0.5, 0),
    5732: ("electronics", 4.6, 0.9, 1),
    4816: ("digital_services", 2.9, 0.8, 0),
    4899: ("telecom_utilities", 3.1, 0.5, 0),
    5999: ("misc_retail", 3.5, 0.9, 0),
    4111: ("transport", 2.6, 0.6, 0),
    5944: ("jewellery", 5.2, 0.8, 2),
    7995: ("gambling", 4.2, 1.1, 3),
    6051: ("crypto_quasicash", 4.8, 1.2, 3),
    5816: ("digital_goods_games", 3.0, 0.9, 1),
    4829: ("money_transfer", 4.4, 1.0, 2),
    5691: ("apparel", 3.8, 0.8, 0),
}
MCC_CODES = list(MCC_TABLE.keys())
# Everyday categories dominate; high-risk categories are a small tail.
MCC_W = np.array([0.16, 0.14, 0.10, 0.07, 0.08, 0.07, 0.09, 0.07,
                  0.03, 0.02, 0.02, 0.05, 0.05, 0.05])

DAY = 86400.0


@dataclass
class Profile:
    """Latent behavioural profile driving an account's legitimate activity."""
    account_id: str
    txns_per_day: float           # Poisson rate of card/merchant activity
    a2a_per_week: float           # rate of account-to-account transfers
    log_amount_mu: float          # per-account spend scale (log-normal)
    log_amount_sigma: float
    pref_mcc: List[int]           # favoured merchant categories
    active_hours: np.ndarray      # 24-length probability over hour-of-day
    home_country: str
    known_payees: List[str]       # stable beneficiaries for A2A
    device_ids: List[str]
    balance: float                # rough available balance (for amount/balance ratio)


@dataclass
class Population:
    accounts: Dict[str, Account]
    devices: Dict[str, Device]
    merchants: Dict[str, Merchant]
    profiles: Dict[str, Profile]
    sim_start_ts: float
    account_ids: List[str] = field(default_factory=list)

    def merchant_ids_by_mcc(self, mcc: int) -> List[str]:
        return [m.merchant_id for m in self.merchants.values() if m.mcc == mcc]


def _diurnal_curve(rng: np.random.Generator) -> np.ndarray:
    """A per-account active-hours distribution: bimodal (midday + evening) with jitter."""
    hours = np.arange(24)
    base = (
        np.exp(-((hours - 13) ** 2) / 8.0) * 0.9      # midday
        + np.exp(-((hours - 20) ** 2) / 6.0) * 1.0    # evening peak
        + 0.05                                         # background
    )
    base *= rng.uniform(0.7, 1.3, size=24)             # per-account taste
    base[0:6] *= 0.15                                  # very low overnight
    return base / base.sum()


def build_population(
    n_accounts: int,
    days: int,
    seed: int,
    sim_start_ts: float = 1_735_689_600.0,  # 2025-01-01 UTC, arbitrary stable epoch
) -> Population:
    rng = np.random.default_rng(seed)

    # Merchant catalogue: ~1 merchant per 12 accounts, min 40.
    n_merch = max(40, n_accounts // 12)
    merchants: Dict[str, Merchant] = {}
    for i in range(n_merch):
        mcc = int(rng.choice(MCC_CODES, p=MCC_W / MCC_W.sum()))
        _, _, _, risk = MCC_TABLE[mcc]
        country = str(rng.choice(COUNTRIES, p=COUNTRY_W / COUNTRY_W.sum()))
        merchants[f"m_{i:05d}"] = Merchant(
            merchant_id=f"m_{i:05d}", mcc=mcc, country=country, risk_tier=risk,
        )

    accounts: Dict[str, Account] = {}
    devices: Dict[str, Device] = {}
    profiles: Dict[str, Profile] = {}
    account_ids: List[str] = []

    for i in range(n_accounts):
        aid = f"a_{i:06d}"
        uid = f"u_{i:06d}"
        account_ids.append(aid)
        home = str(rng.choice(COUNTRIES, p=COUNTRY_W / COUNTRY_W.sum()))

        # Account age: mix of long-tenured and recently opened accounts.
        age_days = float(rng.gamma(shape=2.0, scale=260.0))  # mean ~520 days
        opened = sim_start_ts - age_days * DAY

        # Devices: 1-2 per account.
        n_dev = 1 + int(rng.random() < 0.35)
        dev_ids = []
        for d in range(n_dev):
            did = f"d_{i:06d}_{d}"
            kind = str(rng.choice(["ios", "android", "web"], p=[0.34, 0.5, 0.16]))
            devices[did] = Device(device_id=did, kind=kind,
                                   first_seen_ts=opened + rng.uniform(0, 10) * DAY)
            dev_ids.append(did)

        accounts[aid] = Account(
            account_id=aid, user_id=uid, opened_ts=opened, home_country=home,
            kyc_level=int(rng.choice([1, 2, 3], p=[0.2, 0.45, 0.35])),
            risk_seed=float(rng.beta(1.4, 6.0)),
        )

        # Behavioural rates - heavy-tailed activity across the population.
        txns_per_day = float(np.clip(rng.gamma(2.2, 0.55), 0.15, 12.0))
        a2a_per_week = float(np.clip(rng.gamma(1.6, 1.1), 0.0, 20.0))
        mu = float(rng.normal(3.4, 0.5))            # local spend scale
        sigma = float(np.clip(rng.normal(0.7, 0.15), 0.35, 1.3))
        pref = [int(x) for x in rng.choice(MCC_CODES, size=3, replace=False,
                                           p=MCC_W / MCC_W.sum())]
        balance = float(np.exp(rng.normal(mu + 2.2, 0.8)))  # balance scales with spend

        profiles[aid] = Profile(
            account_id=aid, txns_per_day=txns_per_day, a2a_per_week=a2a_per_week,
            log_amount_mu=mu, log_amount_sigma=sigma, pref_mcc=pref,
            active_hours=_diurnal_curve(rng), home_country=home,
            known_payees=[], device_ids=dev_ids, balance=balance,
        )

    # Wire up a stable set of known payees per account (their social graph).
    ids = np.array(account_ids)
    for aid in account_ids:
        k = int(rng.integers(2, 7))
        payees = [p for p in rng.choice(ids, size=k, replace=False).tolist() if p != aid]
        profiles[aid].known_payees = payees

    return Population(accounts=accounts, devices=devices, merchants=merchants,
                      profiles=profiles, sim_start_ts=sim_start_ts, account_ids=account_ids)
