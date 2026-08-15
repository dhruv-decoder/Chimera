"""Service layer: loads artifacts and runs live simulation/scoring for the API.

Trained artifacts (detector, eval + loop reports) are produced offline by the
scripts and loaded once here. Live endpoints (attack lab, graph, case drilldown)
run small, fast simulations on demand so the UI is interactive without recomputing
the full training pipeline.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from functools import lru_cache
from typing import Optional

import numpy as np
import pandas as pd

from ..config import ARTIFACTS_DIR
from ..defend.detector import FraudDetector
from ..generate.attacks import REGISTRY, load_all
from ..generate.simulator import SimConfig, simulate
from ..identify.ideation_agent import ideate
from ..identify.taxonomy import TACTICS, TECHNIQUES, get_technique

# Columns surfaced to the UI (kept small for payload size).
_UI_COLS = ["txn_id", "ts", "rail", "channel", "amount", "mcc", "auth_method",
            "entry_mode", "counterparty_type", "account_age_days",
            "is_new_counterparty", "ip_asn_risk", "session_seconds",
            "amount_to_balance_ratio", "agent_id", "agent_attested", "agent_trust",
            "mandate_cap_ratio", "is_fraud", "vector"]


def _read(name: str):
    p = ARTIFACTS_DIR / name
    return json.loads(p.read_text()) if p.exists() else None


def compute_graph_snapshot(detector, df: pd.DataFrame, threshold: float, max_nodes: int = 220) -> dict:
    """Build the A2A transfer graph around mule/structuring rings, with legitimate
    high-degree accounts for contrast. Shared by the live service and train.py so
    the snapshot can be precomputed and committed as an artifact."""
    a2a = df[df["counterparty_type"] == "account"].copy()
    scores = detector.score(a2a)
    a2a = a2a.assign(risk=scores["risk"].to_numpy())

    ring = a2a[a2a["vector"].isin(["MULE-NET", "STRUCT"])]
    keep_accounts = set(ring["payer_account_id"]) | set(ring["counterparty_id"])
    legit_hub = a2a[a2a["is_fraud"] == 0]["counterparty_id"].value_counts().head(15).index
    keep_accounts |= set(legit_hub)
    sub = a2a[a2a["payer_account_id"].isin(keep_accounts) | a2a["counterparty_id"].isin(keep_accounts)]
    sub = sub.head(600)

    nodes: dict[str, dict] = {}
    edges = []
    for _, r in sub.iterrows():
        for nid in (r["payer_account_id"], r["counterparty_id"]):
            if nid not in nodes:
                nodes[nid] = {"id": nid, "fraud_edges": 0, "total_edges": 0}
        fr = int(r["is_fraud"])
        nodes[r["payer_account_id"]]["total_edges"] += 1
        nodes[r["counterparty_id"]]["total_edges"] += 1
        nodes[r["payer_account_id"]]["fraud_edges"] += fr
        edges.append({
            "source": r["payer_account_id"], "target": r["counterparty_id"],
            "amount": round(float(r["amount"]), 2), "risk": round(float(r["risk"]), 3),
            "is_fraud": fr, "vector": r["vector"],
        })
    node_list = list(nodes.values())[:max_nodes]
    keep = {n["id"] for n in node_list}
    edges = [e for e in edges if e["source"] in keep and e["target"] in keep]
    for n in node_list:
        n["suspicious"] = n["fraud_edges"] > 0
    return {"nodes": node_list, "edges": edges, "threshold": threshold}


class Service:
    def __init__(self) -> None:
        load_all()
        p = ARTIFACTS_DIR / "detector.pkl"
        self.detector: Optional[FraudDetector] = FraudDetector.load(p) if p.exists() else None
        self.eval_report = _read("eval_report.json")
        self.loop_report = _read("loop_report.json")
        self.sim_meta = _read("sim_meta.json")
        self._lab_cache: dict = {}
        self._lab_samples: Optional[dict] = None

    # --- identify --------------------------------------------------------
    def taxonomy(self) -> dict:
        return {
            "tactics": TACTICS,
            "techniques": [asdict(t) for t in TECHNIQUES],
            "attack_ids": list(REGISTRY.keys()),
        }

    def attack_params(self) -> dict:
        return {aid: spec.param_spec for aid, spec in REGISTRY.items()}

    def ideation(self, attack_id: str, params: Optional[dict] = None) -> dict:
        spec = REGISTRY.get(attack_id)
        if spec is None:
            raise KeyError(attack_id)
        idea = ideate(attack_id, params or spec.defaults())
        return asdict(idea)

    # --- defend / metrics ------------------------------------------------
    def metrics(self) -> dict:
        return self.eval_report or {"error": "run scripts/train.py first"}

    def loop(self) -> dict:
        return self.loop_report or {"error": "run scripts/run_loop.py first"}

    def validation(self) -> dict:
        """External-data, GNN and evaluation-rigor evidence, served from the
        precomputed artifacts (scripts/validate_real.py, gnn_benchmark.py,
        rigor.py, point_in_time.py, benchmark_baselines.py). Static by design:
        these are audits, not live computations."""
        return {
            "external": _read("external_validation.json"),
            "gnn": _read("gnn_benchmark.json"),
            "point_in_time": _read("point_in_time.json"),
            "rigor": _read("rigor_report.json"),
            "benchmark": _read("benchmark_report.json"),
            "attack_chains": _read("attack_chains.json"),
        }

    # --- generate + score (live) ----------------------------------------
    def _score_frame(self, df: pd.DataFrame, explain: bool = False) -> list[dict]:
        scores = self.detector.score(df)
        recs = df[_UI_COLS].copy()
        recs["risk"] = scores["risk"].to_numpy().round(4)
        recs["supervised_prob"] = scores["supervised_prob"].to_numpy().round(4)
        recs["novelty_score"] = scores["novelty_score"].to_numpy().round(4)
        out = recs.to_dict(orient="records")
        if explain:
            expl = self.detector.explain(df)
            for r, e in zip(out, expl):
                r["explanation"] = e
        return out

    def _is_default_lab(self, attack_id: str, intensity: float, params: Optional[dict]) -> bool:
        """True when the request is the untuned default view for an attack, which
        we serve from a precomputed sample so the first click is instant even on a
        small free-tier box. Any tuned knob or changed intensity runs live."""
        spec = REGISTRY.get(attack_id)
        if spec is None or abs(intensity - 1.5) > 0.05:
            return False
        if not params:
            return True
        d = spec.defaults()
        return all(abs(float(params.get(k, d[k])) - float(d[k])) < 1e-6 for k in d)

    def attack_lab(self, attack_id: str, intensity: float = 1.0,
                   params: Optional[dict] = None) -> dict:
        """Serve the precomputed default result instantly; simulate live only when
        the user has tuned the attack (the interactive case they opted into)."""
        if self._lab_samples is None:
            self._lab_samples = _read("lab_samples.json") or {}
        if self._is_default_lab(attack_id, intensity, params) and attack_id in self._lab_samples:
            return self._lab_samples[attack_id]
        return self._attack_lab_live(attack_id, intensity=intensity, params=params)

    def _attack_lab_live(self, attack_id: str, intensity: float = 1.0,
                         params: Optional[dict] = None, population: int = 340,
                         days: int = 14, seed: int = 7, legit_sample: int = 220) -> dict:
        """Run a small simulation of one attack, score it, return events + summary."""
        if self.detector is None:
            return {"error": "no trained detector"}
        cfg = SimConfig(population=population, days=days, seed=seed, intensity=intensity,
                        enabled_attacks=[attack_id],
                        attack_params={attack_id: params} if params else {})
        sim = simulate(cfg)
        df = sim.frame
        fraud = df[df["is_fraud"] == 1]
        legit = df[df["is_fraud"] == 0].sample(min(legit_sample, (df["is_fraud"] == 0).sum()),
                                               random_state=seed)
        subset = pd.concat([fraud, legit]).sort_values("ts").reset_index(drop=True)
        scored = self._score_frame(subset, explain=True)
        thr = (self.eval_report or {}).get("supervised", {}).get("threshold", 0.5)
        caught = [r for r in scored if r["is_fraud"] == 1 and r["risk"] >= thr]
        n_fraud = int((subset["is_fraud"] == 1).sum())
        fp = [r for r in scored if r["is_fraud"] == 0 and r["risk"] >= thr]
        return {
            "attack_id": attack_id,
            "technique": asdict(get_technique(attack_id)) if get_technique(attack_id) else None,
            "threshold": thr,
            "summary": {
                "n_fraud": n_fraud, "n_legit_shown": len(legit),
                "recall": round(len(caught) / max(n_fraud, 1), 4),
                "false_positives": len(fp),
                "fp_rate": round(len(fp) / max(len(legit), 1), 4),
            },
            "events": scored,
        }

    def _lab_snapshot(self) -> pd.DataFrame:
        if "df" not in self._lab_cache:
            sim = simulate(SimConfig(population=1000, days=24, seed=123, intensity=2.0))
            self._lab_cache["df"] = sim.frame
        return self._lab_cache["df"]

    def graph_snapshot(self, max_nodes: int = 220) -> dict:
        """A2A transfer graph around detected mule/structuring campaigns.

        Served from a precomputed artifact when present (train.py writes it), so
        the deployed endpoint is instant instead of simulating on demand. Falls
        back to an on-demand build cached in memory.
        """
        cached = _read("graph_snapshot.json")
        if cached:
            return cached
        if "graph" in self._lab_cache:
            return self._lab_cache["graph"]
        thr = (self.eval_report or {}).get("supervised", {}).get("threshold", 0.5)
        snap = compute_graph_snapshot(self.detector, self._lab_snapshot(), thr, max_nodes)
        self._lab_cache["graph"] = snap
        return snap

    def case(self, txn_id: str) -> dict:
        df = self._lab_snapshot()
        row = df[df["txn_id"] == txn_id]
        if row.empty:
            raise KeyError(txn_id)
        scored = self._score_frame(row, explain=True)[0]
        tech = get_technique(row.iloc[0]["vector"])
        scored["technique"] = asdict(tech) if tech else None
        return scored


@lru_cache(maxsize=1)
def get_service() -> Service:
    return Service()
