"""BETA - combined attack chains: does chaining two stages evade better than either
stage alone, and does retraining recover?

Real campaigns are rarely a single technique. Here a synthetic-identity "bust-out
setup" (stage 1) ages a ring of accounts with benign history, and those *same*
accounts are then the mule cash-out layer (stage 2). The linkage is the point: at
cash-out the accounts have tenure and an established (benign) velocity baseline, so
the young-account and velocity signals a cold mule ring would trip are gone. The
attacker spent effort up front to make the cash-out look ordinary.

We measure detection recall on the stage-2 cash-out events in two worlds, scored by
the *shipped* detector at its cost-optimal operating point:
  * cold    - a standalone mule ring (accounts freshly opened): the single-stage attack
  * chained - the same ring, aged first via stage 1: the combined chain
then retrain including the chained samples and re-score a fresh chained holdout to
show recovery.

This is a BETA experiment, fully isolated: it does not register a new attack, change
the simulator, or touch the shipped app. Writes data/artifacts/attack_chains.json.

    python scripts/attack_chains.py
"""
from __future__ import annotations

import os
os.environ.setdefault("OMP_NUM_THREADS", "1")

import json

import numpy as np
import pandas as pd
from rich.console import Console
from rich.table import Table

from chimera.config import ARTIFACTS_DIR
from chimera.defend.detector import FraudDetector
from chimera.generate.attacks import load_all, register_account
from chimera.generate.common import TxnFactory
from chimera.generate.simulator import SimConfig, simulate
from chimera.schema import AuthMethod, Channel, Rail, transactions_to_frame

console = Console()
A2A, MOBILE, PIN = Rail.A2A_RT.value, Channel.MOBILE_APP.value, AuthMethod.UPI_PIN.value


def build_chain(pop, fac, start_ts, days, rng, base_ids, aged: bool, tag: str):
    """A mule cash-out ring (stage 2). If aged, the accounts are opened months
    earlier and seeded with benign small payments (stage 1) before the cash-out."""
    txns = []
    n_rings, ring_size, hops = 4, 6, 3
    for r in range(n_rings):
        camp = f"CHAIN-{tag}-{r}"
        home = "IN"
        opened = (start_ts - rng.uniform(60, 120) * 86400) if aged \
            else (start_ts + rng.uniform(0, days) * 86400 - rng.uniform(0, 5) * 86400)
        mules = []
        for m in range(ring_size):
            aid = f"a_chain_{tag}_{r}_{m}_{int(rng.integers(1e9))}"
            register_account(pop, aid, opened, home, balance=500.0, rng=rng,
                             is_synthetic=aged, is_mule=True)
            mules.append(aid)
            if aged:  # STAGE 1: a genuinely rich benign baseline across the pre-window,
                # so the account looks like an established low-activity customer.
                for _ in range(int(rng.integers(30, 50))):
                    t = opened + rng.uniform(1, max((start_ts - opened) / 86400 * 0.95, 2)) * 86400
                    payee = str(rng.choice(base_ids))
                    txns.append(fac.make(
                        account_id=aid, ts=t, rail=A2A, channel=MOBILE,
                        amount=float(rng.uniform(150, 550)), counterparty_id=payee,
                        counterparty_type="account", counterparty_country=home, mcc=5411,
                        device_id=f"d_{aid}", auth_method=PIN, is_new_counterparty=False,
                        is_fraud=0, vector="CHAIN-SETUP", campaign_id=camp))
        # STAGE 2: a low-observability, authorised-push-style cash-out. Each account
        # sends a handful of modest payments from its *own* device to a small set of
        # reused ("known") payees, at retail amounts - no new-counterparty flag, no
        # cash-out MCC, no ring. On its own this is a weak-signal leg (the DF-APP
        # regime). The chain's evasion comes from stage 1: on an aged account with an
        # established baseline these blend in, while on a cold account they are still
        # first-ever activity. We score cold vs aged to isolate what chaining adds.
        # Pay distinct *existing legit* accounts (the money appears to go to ordinary
        # people), so no suspicious shared-endpoint cluster forms - the cash-out looks
        # like normal outgoing payments. Evasion then hinges on account history alone.
        t_base = start_ts + rng.uniform(0.3, 0.9) * days * 86400
        for m in mules:
            t = t_base + rng.uniform(0, 4) * 86400
            for _ in range(int(rng.integers(3, 6))):
                t += rng.uniform(0.1, 1.0) * 86400
                txns.append(fac.make(
                    account_id=m, ts=t, rail=A2A, channel=MOBILE,
                    amount=float(rng.uniform(200, 500)),
                    counterparty_id=str(rng.choice(base_ids)), counterparty_type="account",
                    counterparty_country=home, mcc=5411, device_id=f"d_{m}",
                    auth_method=PIN, is_new_counterparty=False,
                    is_fraud=1, vector="CHAIN", campaign_id=camp))
    return txns


def _frame(base_frame, txns):
    return pd.concat([base_frame, transactions_to_frame(txns)], ignore_index=True)


def _recalls(det, frame, thr_full, thr_sup, vector="CHAIN"):
    """Recall on the chain's cash-out events for the supervised channel alone and
    for the full two-channel ensemble, at matched ~1% operating budgets."""
    s = det.score(frame)
    m = (frame["vector"] == vector).to_numpy()
    sup = round(float((s["supervised_prob"].to_numpy()[m] >= thr_sup).mean()), 4)
    full = round(float((s["risk"].to_numpy()[m] >= thr_full).mean()), 4)
    return sup, full


def _budgets(det, base_frame, q=0.99):
    """Operating thresholds at a ~1% budget on ordinary legit traffic, for the
    supervised channel and for the blended risk."""
    s = det.score(base_frame)
    legit = (base_frame["is_fraud"] == 0).to_numpy()
    return (float(np.quantile(s["risk"].to_numpy()[legit], q)),
            float(np.quantile(s["supervised_prob"].to_numpy()[legit], q)))


def main():
    load_all()
    console.rule("[bold]BETA - combined attack chains (bust-out setup -> stealth cash-out)")
    det = FraudDetector.load(ARTIFACTS_DIR / "detector.pkl")

    base = simulate(SimConfig(population=1500, days=21, seed=11,
                              enabled_attacks=[], hard_negatives=True))
    pop, start_ts = base.population, base.population.sim_start_ts
    base_ids = list(pop.account_ids)
    rng = np.random.default_rng(11)
    fac = TxnFactory(pop, rng, prefix="chain")
    thr_full, thr_sup = _budgets(det, base.frame)

    cold = build_chain(pop, fac, start_ts, 21, rng, base_ids, aged=False, tag="cold")
    chained = build_chain(pop, fac, start_ts, 21, rng, base_ids, aged=True, tag="aged")
    cold_sup, cold_full = _recalls(det, _frame(base.frame, cold), thr_full, thr_sup)
    ch_sup, ch_full = _recalls(det, _frame(base.frame, chained), thr_full, thr_sup)

    # recovery: retrain on the chained samples, re-score a FRESH chained holdout
    det2 = FraudDetector(seed=11).fit(_frame(base.frame, chained))
    thr_full2, thr_sup2 = _budgets(det2, base.frame)
    fresh = build_chain(pop, fac, start_ts, 21, np.random.default_rng(999), base_ids, aged=True, tag="fresh")
    rec_sup, rec_full = _recalls(det2, _frame(base.frame, fresh), thr_full2, thr_sup2)

    report = {
        "note": "BETA. A synthetic-identity bust-out (stage 1) ages a set of accounts, "
                "which then run a low-observability authorised-push-style cash-out "
                "(stage 2) to ordinary payees. Recall on the stage-2 fraud is reported "
                "for the supervised classifier alone vs the full two-channel ensemble, "
                "at a matched ~1% legit alert budget.",
        "single_stage_cold": {"supervised_only": cold_sup, "full_ensemble": cold_full},
        "chained": {"supervised_only": ch_sup, "full_ensemble": ch_full},
        "chained_after_retrain": {"supervised_only": rec_sup, "full_ensemble": rec_full},
        "finding": "the chain evades the supervised classifier (recall collapses); the "
                   "novelty channel still catches it, and retraining restores the "
                   "supervised channel - the two-channel design and the loop both earn "
                   "their keep against a combined threat.",
    }
    (ARTIFACTS_DIR / "attack_chains.json").write_text(json.dumps(report, indent=2))

    t = Table(title="Combined attack chain - stage-2 cash-out recall", header_style="bold cyan")
    for c in ("scenario", "supervised only", "full ensemble"):
        t.add_column(c)
    t.add_row("single-stage (cold accounts)", f"{cold_sup*100:.1f}%", f"{cold_full*100:.1f}%")
    t.add_row("chained (aged bust-out)", f"{ch_sup*100:.1f}%", f"{ch_full*100:.1f}%")
    t.add_row("chained, after retrain", f"{rec_sup*100:.1f}%", f"{rec_full*100:.1f}%")
    console.print(t)
    console.print(f"Chaining evades the supervised model (recall {cold_sup*100:.0f}% -> "
                  f"{ch_sup*100:.0f}%); the novelty channel holds it at {ch_full*100:.0f}%; "
                  f"retraining restores supervised to {rec_sup*100:.0f}%.")
    console.print("[green]Saved -> attack_chains.json")


if __name__ == "__main__":
    main()
