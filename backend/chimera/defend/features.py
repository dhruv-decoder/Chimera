"""Feature engineering for the detector.

Three families, all derived from observable fields only:

  1. Event features     - amount, tenure, auth/channel/rail/entry encodings, geo.
  2. Behavioural velocity - per-account time-windowed counts/sums, inter-arrival,
                            amount z-score vs the account's own expanding history.
  3. Structural / graph  - device fan-out (distinct accounts per device),
                            counterparty in-degree, and A2A account-graph degree
                            + PageRank. This is what exposes coordinated rings.

The transform is stateless w.r.t. labels and deterministic given the input
frame, so training and live scoring share one code path.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd

try:  # networkx is a hard dep, but keep the import defensive
    import networkx as nx
except Exception:  # pragma: no cover
    nx = None

from ..generate.entities import MCC_TABLE

HOUR = 3600.0
DAY = 86400.0

_MCC_RISK = {code: risk for code, (_n, _a, _b, risk) in MCC_TABLE.items()}

RAILS = ["card_cnp", "card_cp", "a2a_rt"]
CHANNELS = ["web", "mobile_app", "pos", "agent"]
AUTHS = ["none", "otp", "3ds", "biometric", "upi_pin", "voice"]
ENTRIES = ["manual", "token", "agentic_token", "contactless"]


def _windowed(ts: np.ndarray, values: np.ndarray, window: float):
    """For a per-group, time-sorted array, return (count, sum) of events within
    ``window`` seconds up to and including each event. O(n) via a moving left edge."""
    n = len(ts)
    counts = np.empty(n, dtype=np.float64)
    sums = np.empty(n, dtype=np.float64)
    csum = np.concatenate([[0.0], np.cumsum(values)])
    left = 0
    for i in range(n):
        edge = ts[i] - window
        while ts[left] < edge:
            left += 1
        counts[i] = i - left + 1
        sums[i] = csum[i + 1] - csum[left]
    return counts, sums


def _per_group_velocity(df: pd.DataFrame) -> pd.DataFrame:
    """Account-level velocity, inter-arrival and expanding amount z-score."""
    out = pd.DataFrame(index=df.index)
    cols = ["vel_cnt_1h", "vel_cnt_24h", "vel_amt_1h", "vel_amt_24h",
            "inter_arrival_s", "amt_z"]
    for c in cols:
        out[c] = 0.0
    for _, idx in df.groupby("payer_account_id", sort=False).groups.items():
        g = df.loc[idx].sort_values("ts")
        ts = g["ts"].to_numpy()
        amt = g["amount"].to_numpy()
        c1, s1 = _windowed(ts, amt, HOUR)
        c24, s24 = _windowed(ts, amt, DAY)
        inter = np.diff(ts, prepend=ts[0] - DAY)  # first event: large gap
        # Expanding mean/std of amount up to (not including) current event.
        cum = np.cumsum(amt)
        cnt = np.arange(1, len(amt) + 1)
        prev_mean = np.concatenate([[amt[0]], cum[:-1] / np.maximum(cnt[:-1], 1)])
        cum2 = np.cumsum(amt ** 2)
        prev_var = np.concatenate([[0.0], cum2[:-1] / np.maximum(cnt[:-1], 1) - prev_mean[1:] ** 2])
        prev_std = np.sqrt(np.maximum(prev_var, 0.0))
        z = (amt - prev_mean) / (prev_std + 1.0)
        gi = g.index
        out.loc[gi, "vel_cnt_1h"] = c1
        out.loc[gi, "vel_cnt_24h"] = c24
        out.loc[gi, "vel_amt_1h"] = s1
        out.loc[gi, "vel_amt_24h"] = s24
        out.loc[gi, "inter_arrival_s"] = inter
        out.loc[gi, "amt_z"] = z
    return out


def _device_features(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    # Distinct payer accounts sharing a device over the window - the single
    # strongest card-testing / bot-farm / synthetic-ring signal.
    dev_accts = df.groupby("device_id")["payer_account_id"].transform("nunique")
    dev_cnt = df.groupby("device_id")["txn_id"].transform("count")
    out["dev_distinct_accounts"] = dev_accts.to_numpy()
    out["dev_txn_count"] = dev_cnt.to_numpy()
    return out


def _counterparty_features(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    cp_indeg = df.groupby("counterparty_id")["payer_account_id"].transform("nunique")
    cp_cnt = df.groupby("counterparty_id")["txn_id"].transform("count")
    out["cp_in_degree"] = cp_indeg.to_numpy()
    out["cp_txn_count"] = cp_cnt.to_numpy()
    return out


def _agent_features(df: pd.DataFrame, with_fanout: bool = True) -> pd.DataFrame:
    """Agent-identity integrity signals for delegated-token (Agent Pay / TAP) flows.

    A legitimate delegated agent and a hijacked one look the same on velocity and
    device features - both are fast, both are automated, both serve many
    principals. What separates them is the integrity of the credential itself:
    whether the network attested the agent's signature, its directory trust, and
    whether the purchase stayed inside the granted mandate. These features fire
    only on the agent channel, so they add signal without perturbing other rails.
    """
    out = pd.DataFrame(index=df.index)
    is_agent = (df["channel"] == "agent").astype(float).to_numpy()
    attested = df.get("agent_attested", pd.Series(1, index=df.index)).astype(float).to_numpy()
    trust = df.get("agent_trust", pd.Series(1.0, index=df.index)).astype(float).to_numpy()
    cap = df.get("mandate_cap_ratio", pd.Series(0.0, index=df.index)).astype(float).clip(0, 5).to_numpy()
    mcc_risk = df["mcc"].map(_MCC_RISK).fillna(0).astype(float).to_numpy()

    out["agent_txn"] = is_agent
    out["agent_unattested"] = is_agent * (1.0 - attested)
    out["agent_low_trust"] = is_agent * (1.0 - trust)
    out["mandate_cap_ratio"] = cap
    out["agent_over_cap"] = is_agent * (cap > 1.0).astype(float)
    out["agent_highrisk_mcc"] = is_agent * mcc_risk

    # Token-replay structure: how many distinct principals (and how many events)
    # one agent identity drives. High fan-out is normal for a trusted agent, so
    # this only bites in combination with the integrity signals above.
    out["agent_principal_fanout"] = 0.0
    out["agent_id_txn_count"] = 0.0
    if with_fanout and "agent_id" in df.columns:
        amask = (df["channel"] == "agent") & (df["agent_id"].astype(str) != "")
        ag = df[amask]
        if not ag.empty:
            fanout = ag.groupby("agent_id")["payer_account_id"].transform("nunique")
            cnt = ag.groupby("agent_id")["txn_id"].transform("count")
            out.loc[ag.index, "agent_principal_fanout"] = fanout.to_numpy()
            out.loc[ag.index, "agent_id_txn_count"] = cnt.to_numpy()
    return out


def _graph_features(df: pd.DataFrame) -> pd.DataFrame:
    """A2A account-to-account graph: out/in degree and PageRank per account.

    Mule and structuring rings show extreme degree and PageRank mass relative to
    ordinary customers. Computed once over the batch (a streaming approximation
    is noted as a production upgrade in the write-up)."""
    out = pd.DataFrame(index=df.index)
    out["acct_out_deg"] = 0.0
    out["acct_in_deg"] = 0.0
    out["acct_pagerank"] = 0.0
    a2a = df[(df["counterparty_type"] == "account")]
    if nx is None or a2a.empty:
        return out
    G = nx.DiGraph()
    for payer, cp in zip(a2a["payer_account_id"], a2a["counterparty_id"]):
        if G.has_edge(payer, cp):
            G[payer][cp]["w"] += 1
        else:
            G.add_edge(payer, cp, w=1)
    outdeg = dict(G.out_degree())
    indeg = dict(G.in_degree())
    try:
        pr = nx.pagerank(G, alpha=0.85, max_iter=60, weight="w")
    except Exception:
        pr = {n: 0.0 for n in G.nodes}
    payers = df["payer_account_id"]
    out["acct_out_deg"] = payers.map(lambda a: outdeg.get(a, 0)).to_numpy()
    out["acct_in_deg"] = payers.map(lambda a: indeg.get(a, 0)).to_numpy()
    # Scale PageRank up so it isn't numerically swamped by other features.
    out["acct_pagerank"] = payers.map(lambda a: pr.get(a, 0.0)).to_numpy() * 1e4
    return out


# --------------------------- point-in-time (causal) ---------------------------
# The structural families above are computed over the whole batch, which is fine
# for offline analysis but uses information from t+1..T at time t. The causal
# variants below recompute the same quantities using only events strictly up to
# each event (in global time order), so a feature at time t depends only on the
# past - the correctness a live scoring service must satisfy.

def _cumulative_group(df: pd.DataFrame, group_col: str, distinct_col: str,
                      mask: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """For each event in time order, the running (distinct-count, count) within its
    group up to and including that event. O(n)."""
    n = len(df)
    cum_d = np.zeros(n); cum_c = np.zeros(n)
    order = np.argsort(df["ts"].to_numpy(), kind="stable")
    g = df[group_col].to_numpy(); d = df[distinct_col].to_numpy()
    if mask is None:
        mask = np.ones(n, dtype=bool)
    seen: dict = {}; cnt: dict = {}
    for oi in order:
        if not mask[oi]:
            continue
        key = g[oi]
        s = seen.get(key)
        if s is None:
            s = set(); seen[key] = s
        s.add(d[oi]); cnt[key] = cnt.get(key, 0) + 1
        cum_d[oi] = len(s); cum_c[oi] = cnt[key]
    return cum_d, cum_c


def _causal_structural(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    dd, dc = _cumulative_group(df, "device_id", "payer_account_id")
    out["dev_distinct_accounts"] = dd; out["dev_txn_count"] = dc
    ci, cc = _cumulative_group(df, "counterparty_id", "payer_account_id")
    out["cp_in_degree"] = ci; out["cp_txn_count"] = cc
    a2a = (df["counterparty_type"] == "account").to_numpy()
    od, _ = _cumulative_group(df, "payer_account_id", "counterparty_id", mask=a2a)
    idg, _ = _cumulative_group(df, "counterparty_id", "payer_account_id", mask=a2a)
    out["acct_out_deg"] = od; out["acct_in_deg"] = idg
    out["acct_pagerank"] = 0.0  # PageRank is not available point-in-time without an incremental engine
    ag = (df["channel"] == "agent").to_numpy() & (df.get("agent_id", pd.Series("", index=df.index)).astype(str).to_numpy() != "")
    fo, tc = _cumulative_group(df, "agent_id", "payer_account_id", mask=ag)
    out["agent_principal_fanout"] = fo; out["agent_id_txn_count"] = tc
    return out


def build_features(df: pd.DataFrame, causal: bool = False) -> tuple[pd.DataFrame, List[str]]:
    """Return (feature_matrix, feature_names) aligned to df's index.

    causal=True swaps the batch structural features (device/counterparty/graph and
    agent-id fan-out) for point-in-time versions that use only past events.
    """
    df = df.reset_index(drop=True)
    f = pd.DataFrame(index=df.index)

    # --- event features ---
    f["log_amount"] = np.log1p(df["amount"])
    f["amount_to_balance_ratio"] = df["amount_to_balance_ratio"].clip(0, 50)
    f["log_age"] = np.log1p(df["account_age_days"].clip(lower=0))
    f["is_new_counterparty"] = df["is_new_counterparty"].astype(float)
    f["ip_asn_risk"] = df["ip_asn_risk"]
    f["log_session"] = np.log1p(df["session_seconds"].clip(lower=0))
    f["hour"] = df["hour"]
    f["is_night"] = (df["hour"] < 6).astype(float)
    f["is_business_hours"] = df["hour"].between(9, 18).astype(float)
    f["day_of_week"] = df["day_of_week"]
    f["mcc_risk"] = df["mcc"].map(_MCC_RISK).fillna(0).astype(float)
    f["cp_is_account"] = (df["counterparty_type"] == "account").astype(float)
    f["cross_border"] = (df["ip_country"] != df["counterparty_country"]).astype(float)

    for r in RAILS:
        f[f"rail_{r}"] = (df["rail"] == r).astype(float)
    for c in CHANNELS:
        f[f"chan_{c}"] = (df["channel"] == c).astype(float)
    for a in AUTHS:
        f[f"auth_{a}"] = (df["auth_method"] == a).astype(float)
    for e in ENTRIES:
        f[f"entry_{e}"] = (df["entry_mode"] == e).astype(float)

    # --- behavioural + structural + agent-identity ---
    if causal:
        # velocity/amount-z are already causal; swap the batch structural + agent
        # fan-out for point-in-time cumulative versions.
        f = pd.concat([f, _per_group_velocity(df), _agent_features(df, with_fanout=False),
                       _causal_structural(df)], axis=1)
    else:
        f = pd.concat([f, _per_group_velocity(df), _device_features(df),
                       _counterparty_features(df), _graph_features(df),
                       _agent_features(df)], axis=1)

    # A couple of interaction features that encode domain intuition cheaply.
    f["young_acct_highflow"] = (f["log_age"] < np.log1p(30)).astype(float) * np.log1p(f["vel_amt_24h"])
    f["new_cp_high_amount"] = f["is_new_counterparty"] * f["log_amount"]

    f = f.replace([np.inf, -np.inf], 0.0).fillna(0.0)
    return f, list(f.columns)
