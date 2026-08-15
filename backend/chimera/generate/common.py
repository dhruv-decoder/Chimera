"""Shared transaction construction used by the base generator and all attacks.

Centralising field derivation (tenure, hour/day, amount-to-balance, auth-method
selection) guarantees legitimate and fraudulent events are built the same way,
so nothing leaks the label through an inconsistently-populated field.
"""
from __future__ import annotations

import itertools
from datetime import datetime, timezone

import numpy as np

from ..schema import (Account, AuthMethod, Channel, EntryMode, Merchant, Rail,
                      Transaction)
from .entities import DAY, MCC_TABLE, Population

# A small directory of well-known, network-registered shopping agents. Legitimate
# agent traffic is delegated to these; each serves many principals, so a high
# principal fan-out per agent is normal and cannot flag fraud on its own. What
# separates abuse is weak attestation, low directory trust, and mandate breach.
TRUSTED_AGENTS = ["agt_operator", "agt_rufus", "agt_concierge", "agt_paypilot", "agt_shopmate"]


class TxnFactory:
    """Builds Transaction objects with consistent derived fields."""

    def __init__(self, pop: Population, rng: np.random.Generator, prefix: str = "t"):
        self.pop = pop
        self.rng = rng
        self.prefix = prefix
        self._counter = itertools.count(1)

    def next_id(self) -> str:
        return f"{self.prefix}_{next(self._counter):09d}"

    @staticmethod
    def hour_dow(ts: float) -> tuple[int, int]:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        return dt.hour, dt.weekday()

    def account_age_days(self, account_id: str, ts: float) -> float:
        acc = self.pop.accounts.get(account_id)
        if acc is None:
            return 0.0
        return max(0.0, (ts - acc.opened_ts) / DAY)

    def _auth_for(self, rail: str, channel: str, amount: float, balance: float) -> str:
        if channel == Channel.AGENT.value:
            return AuthMethod.NONE.value  # delegated agent token carries no step-up
        if rail == Rail.A2A_RT.value:
            # Real-time push: PIN by default, occasional voice-authorised transfer.
            return AuthMethod.VOICE.value if self.rng.random() < 0.05 else AuthMethod.UPI_PIN.value
        if rail == Rail.CARD_CP.value:
            return AuthMethod.NONE.value
        # card_cnp: 3DS step-up more likely for larger tickets; otherwise the
        # saved-credential/token path carries no explicit cardholder auth.
        p_3ds = min(0.85, 0.15 + amount / (balance + 1.0))
        return AuthMethod.THREE_DS.value if self.rng.random() < p_3ds else AuthMethod.NONE.value

    def make(
        self,
        *,
        account_id: str,
        ts: float,
        rail: str,
        channel: str,
        amount: float,
        counterparty_id: str,
        counterparty_type: str,
        counterparty_country: str,
        mcc: int,
        device_id: str,
        ip_country: str | None = None,
        ip_asn_risk: float | None = None,
        auth_method: str | None = None,
        entry_mode: str | None = None,
        is_new_counterparty: bool = False,
        session_seconds: float | None = None,
        agent_id: str | None = None,
        agent_attested: int | None = None,
        agent_trust: float | None = None,
        mandate_cap_ratio: float | None = None,
        is_fraud: int = 0,
        vector: str = "legit",
        campaign_id: str | None = None,
    ) -> Transaction:
        acc = self.pop.accounts[account_id]
        prof = self.pop.profiles[account_id]
        hour, dow = self.hour_dow(ts)
        amount = round(float(max(0.5, amount)), 2)
        balance = max(prof.balance, 1.0)

        if ip_country is None:
            # Usually transact from home; small chance of travel/foreign IP.
            ip_country = acc.home_country if self.rng.random() < 0.94 else counterparty_country
        if ip_asn_risk is None:
            ip_asn_risk = float(np.clip(self.rng.beta(1.2, 20.0), 0, 1))  # mostly clean
        if auth_method is None:
            auth_method = self._auth_for(rail, channel, amount, balance)
        if entry_mode is None:
            if channel == Channel.AGENT.value:
                entry_mode = EntryMode.AGENTIC_TOKEN.value
            elif rail == Rail.CARD_CP.value:
                entry_mode = EntryMode.CONTACTLESS.value
            else:
                entry_mode = EntryMode.TOKEN.value
        if session_seconds is None:
            # Humans deliberate: tens of seconds, log-normal.
            session_seconds = float(np.clip(self.rng.lognormal(3.4, 0.7), 3, 1200))

        # Agentic-commerce identity. Only meaningful when an agent initiated the
        # payment; for every other channel these stay neutral so they cannot, on
        # their own, separate agent traffic from the rest.
        is_agent = channel == Channel.AGENT.value
        if is_agent:
            if agent_id is None:
                agent_id = str(self.rng.choice(TRUSTED_AGENTS))
            if agent_attested is None:
                # Registered agents are attested against the network directory;
                # a small share are brand-new and not yet verified (benign).
                agent_attested = int(self.rng.random() < 0.97)
            if agent_trust is None:
                agent_trust = float(np.clip(self.rng.beta(6.0, 2.0), 0, 1))  # skewed high
            if mandate_cap_ratio is None:
                # Legit delegated spend stays within the granted cap, with the
                # occasional benign near-cap purchase.
                mandate_cap_ratio = float(np.clip(self.rng.uniform(0.05, 0.85)
                                                  + (0.2 if self.rng.random() < 0.05 else 0.0), 0, 3))
        else:
            agent_id = agent_id or ""
            agent_attested = 1 if agent_attested is None else int(agent_attested)
            agent_trust = 1.0 if agent_trust is None else float(agent_trust)
            mandate_cap_ratio = 0.0 if mandate_cap_ratio is None else float(mandate_cap_ratio)

        return Transaction(
            txn_id=self.next_id(), ts=float(ts), rail=rail, channel=channel,
            amount=amount, currency="USD",
            payer_account_id=account_id, payer_user_id=acc.user_id,
            counterparty_id=counterparty_id, counterparty_type=counterparty_type,
            counterparty_country=counterparty_country, mcc=int(mcc),
            device_id=device_id, ip_country=ip_country, ip_asn_risk=round(ip_asn_risk, 4),
            auth_method=auth_method, entry_mode=entry_mode,
            account_age_days=round(self.account_age_days(account_id, ts), 3),
            is_new_counterparty=bool(is_new_counterparty),
            amount_to_balance_ratio=round(amount / balance, 5),
            session_seconds=round(session_seconds, 2),
            hour=hour, day_of_week=dow,
            agent_id=agent_id, agent_attested=int(agent_attested),
            agent_trust=round(float(agent_trust), 4),
            mandate_cap_ratio=round(float(mandate_cap_ratio), 4),
            is_fraud=int(is_fraud), vector=vector, campaign_id=campaign_id,
        )


def local_amount(prof, rng: np.random.Generator, mcc: int | None = None) -> float:
    """Draw a realistic ticket size from the account's log-normal, tilted by MCC."""
    mu, sigma = prof.log_amount_mu, prof.log_amount_sigma
    if mcc is not None and mcc in MCC_TABLE:
        _, mcc_mu, mcc_sigma, _ = MCC_TABLE[mcc]
        mu = 0.5 * mu + 0.5 * mcc_mu
        sigma = 0.5 * sigma + 0.5 * mcc_sigma
    return float(np.exp(rng.normal(mu, sigma)))
