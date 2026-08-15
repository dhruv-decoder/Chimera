"""End-to-end sanity checks for the three pillars.

Kept small and seeded so the suite runs in seconds while still exercising the
real code paths: generation, feature engineering, detection, evasion, taxonomy,
RAG and the offline ideation planner.
"""
from __future__ import annotations

import numpy as np
import pytest

from chimera.defend.detector import FraudDetector
from chimera.defend.evaluate import evaluate, leave_one_vector_out
from chimera.defend.features import build_features
from chimera.generate.adversarial import evade
from chimera.generate.simulator import SimConfig, simulate
from chimera.identify.ideation_agent import ideate
from chimera.identify.rag import get_retriever
from chimera.identify.taxonomy import TECHNIQUES, simulated_technique_ids


@pytest.fixture(scope="module")
def sim():
    return simulate(SimConfig(population=1400, days=20, seed=1, intensity=2.0))


def test_simulation_has_fraud_and_legit(sim):
    m = sim.meta
    assert m["n_fraud"] > 100
    assert m["n_legit"] > m["n_fraud"]
    assert 0.002 < m["fraud_rate"] < 0.1
    # Every simulated technique actually produced events.
    for aid in simulated_technique_ids():
        assert m["per_vector"].get(aid, 0) > 0, aid


def test_no_label_leakage_columns(sim):
    X, names = build_features(sim.frame)
    for banned in ("is_fraud", "vector", "campaign_id", "txn_id"):
        assert banned not in names
    assert len(X) == len(sim.frame)
    assert np.isfinite(X.to_numpy()).all()


def test_detector_learns(sim):
    report = evaluate(sim.frame, seed=1)
    # A real (not trivial) model: strong but grounded.
    assert report["supervised"]["roc_auc"] > 0.9
    assert report["supervised"]["pr_auc"] > 0.6
    # Reasonable precision/recall tradeoff exists.
    assert report["supervised"]["recall"] > 0.6


def test_novelty_channel_recovers_unseen(sim):
    # Remove account-takeover entirely from training. The supervised model
    # degrades on it, but the unsupervised novelty channel still flags a real
    # share of these never-before-seen events.
    r = leave_one_vector_out(sim.frame, "ATO-STUFF", seed=1)
    for k in ("supervised_recall", "novelty_recall", "blended_recall"):
        assert 0.0 <= r[k] <= 1.0
    assert r["novelty_recall"] > 0.2


def test_evasion_reduces_or_holds_risk(sim):
    det = FraudDetector(seed=1).fit(sim.frame)
    res = evade(det, "DF-APP", threshold=0.5, generations=2, popsize=4, seed=1)
    # Evasion search never increases the achieved risk over the baseline.
    assert res.evolved_risk <= res.baseline_risk + 1e-6


def test_taxonomy_and_rag():
    assert len(TECHNIQUES) >= 12
    hits = get_retriever().query("mule network layering fan-in fan-out", k=3)
    assert hits and hits[0]["score"] > 0


def test_offline_ideation():
    idea = ideate("MULE-NET", {"dwell_seconds": 40000})
    assert idea.mode in ("offline",) or idea.mode.startswith("groq")
    assert idea.variant_name
    assert idea.observable_footprint


def test_langgraph_router_terminates():
    """Regression guard: the LangGraph loop must terminate for rounds > 1.

    The router is pure (it must not mutate state, since LangGraph only persists
    updates returned from nodes); blue_team advances the round. If the round were
    incremented in the router, the graph would loop until the recursion limit.
    """
    from chimera.loop.graph import _route, build_graph
    assert _route({"round": 1, "max_rounds": 3}) == "loop"
    assert _route({"round": 3, "max_rounds": 3}) == "loop"   # round 3 still runs
    assert _route({"round": 4, "max_rounds": 3}) == "end"    # advanced past budget
    assert build_graph() is not None                          # compiles
