"""Unified payment event schema.

The design goal is fidelity: these are the fields a real card network or
real-time-payments switch actually observes at authorisation time. Attack
synthesizers may only write *observable* fields - never the label - so the
detector has to infer fraud from signal, not from leakage.

Two rails share one schema:
  - ``card_cnp`` / ``card_cp``: card-not-present and card-present (Mastercard-style)
  - ``a2a_rt``: real-time account-to-account push payments (UPI / FedNow / SEPA-Inst)

Channels include ``agent`` for agentic-commerce flows (Agent Pay / Intelligent
Commerce), where an autonomous AI shopper initiates payment on a user's behalf.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional

import pandas as pd


class Rail(str, Enum):
    CARD_CNP = "card_cnp"   # card, no card present (e-commerce)
    CARD_CP = "card_cp"     # card present (POS)
    A2A_RT = "a2a_rt"       # real-time account-to-account push (UPI-like)


class Channel(str, Enum):
    WEB = "web"
    MOBILE_APP = "mobile_app"
    POS = "pos"
    AGENT = "agent"         # autonomous AI shopping agent initiated the payment


class AuthMethod(str, Enum):
    NONE = "none"
    OTP = "otp"
    THREE_DS = "3ds"
    BIOMETRIC = "biometric"
    UPI_PIN = "upi_pin"
    VOICE = "voice"         # voice-authorised push (deepfake-exploitable)


class EntryMode(str, Enum):
    MANUAL = "manual"
    TOKEN = "token"                 # network token / saved credential
    AGENTIC_TOKEN = "agentic_token" # delegated agent credential (Agent Pay)
    CONTACTLESS = "contactless"


# --- entities ------------------------------------------------------------

@dataclass
class Account:
    account_id: str
    user_id: str
    opened_ts: float
    home_country: str
    kyc_level: int            # 0 minimal .. 3 full
    is_synthetic: bool = False  # opened under a GenAI-fabricated identity
    is_mule: bool = False       # recruited/controlled money mule
    risk_seed: float = 0.0      # latent per-account behavioural risk


@dataclass
class Device:
    device_id: str
    kind: str                 # ios, android, web, emulator, headless
    first_seen_ts: float
    is_emulator: bool = False
    is_headless: bool = False   # automation / agent runtime


@dataclass
class Merchant:
    merchant_id: str
    mcc: int                  # merchant category code
    country: str
    risk_tier: int = 0        # 0 low .. 3 high-risk (gambling, crypto, gift cards)


# --- the event -----------------------------------------------------------

@dataclass
class Transaction:
    txn_id: str
    ts: float                       # unix seconds
    rail: str
    channel: str
    amount: float
    currency: str

    payer_account_id: str
    payer_user_id: str
    counterparty_id: str            # merchant_id or payee account_id
    counterparty_type: str          # "merchant" | "account"
    counterparty_country: str
    mcc: int

    device_id: str
    ip_country: str
    ip_asn_risk: float              # 0..1 hosting/VPN/proxy likelihood

    auth_method: str
    entry_mode: str

    account_age_days: float
    is_new_counterparty: bool
    amount_to_balance_ratio: float  # requested amount / available balance
    session_seconds: float          # time from session start to submit
    hour: int
    day_of_week: int

    # ---- agentic-commerce identity fields (observable at agent checkout) --
    # These describe the delegated-agent credential a network sees under
    # Mastercard Agent Pay (Agentic Token) or Visa's Trusted Agent Protocol.
    # For non-agent events they carry neutral values (no mandate, fully trusted)
    # so they never separate agent from non-agent traffic on their own.
    agent_id: str = ""              # registered/claimed agent identity (directory id)
    agent_attested: int = 1         # 1 = network verified the agent's signature; 0 = missing/failed
    agent_trust: float = 1.0        # 0..1 directory reputation / attestation strength
    mandate_cap_ratio: float = 0.0  # amount / delegated per-txn cap (>1 = over mandate; 0 = N/A)

    # ---- labels (never read by the detector; used only for eval) --------
    is_fraud: int = 0
    vector: str = "legit"           # attack vector id or "legit"
    campaign_id: Optional[str] = None  # groups coordinated fraud events

    def as_row(self) -> dict:
        return asdict(self)


def transactions_to_frame(txns: list[Transaction]) -> pd.DataFrame:
    """Vectorise a list of events into a DataFrame with cheap derived columns."""
    df = pd.DataFrame([t.as_row() for t in txns])
    if df.empty:
        return df
    df = df.sort_values("ts").reset_index(drop=True)
    return df


# Columns the model is allowed to see. Labels and identifiers used only for
# grouping/eval are deliberately excluded here to prevent leakage.
LABEL_COLS = ["is_fraud", "vector", "campaign_id"]
ID_COLS = ["txn_id"]
