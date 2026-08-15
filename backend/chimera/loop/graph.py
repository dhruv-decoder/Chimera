"""LangGraph multi-agent orchestration of the closed loop.

This expresses the same feedback loop as a cyclic StateGraph so the pipeline is a
genuine multi-agent system, not a for-loop in disguise. Four agent roles pass a
shared state and the graph cycles until the round budget is exhausted:

    recon (RAG ideation)  ->  red_team (adversarial evasion)
        ->  attack (generate evasive stream + measure the breach)
        ->  blue_team (retrain + measure the recovery)  ->  [route back or END]

The heavy numeric primitives are shared with ``orchestrator`` so both entry
points stay consistent. Requires the ``agents`` extra (langgraph); callers that
only need metrics can use ``orchestrator.run_loop`` with no LLM dependency.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, TypedDict

import pandas as pd

from ..defend.detector import FraudDetector
from ..defend.features import build_features
from ..generate.adversarial import _AttackArena, evade
from ..generate.attacks import REGISTRY, load_all
from ..generate.simulator import SimConfig, simulate
from ..identify.ideation_agent import ideate
from .orchestrator import LoopResult, RoundResult, _recall_at, loop_result_to_dict


class LoopState(TypedDict, total=False):
    round: int
    max_rounds: int
    config: dict
    detector: Any
    arena: Any
    threshold: float
    accumulated: List[pd.DataFrame]
    evasive_params: Dict[str, dict]
    ideation: List[dict]
    pre_recall: float
    pre_per_vector: Dict[str, float]
    curve: List[dict]
    rounds: List[RoundResult]
    baseline_recall: float
    baseline_per_vector: Dict[str, float]
    trace: List[str]


def _log(state: LoopState, msg: str) -> None:
    """Record to the run trace and print live, so a long run shows progress."""
    state.setdefault("trace", []).append(msg)
    print("  " + msg, flush=True)


def _red_team(state: LoopState) -> LoopState:
    r = state["round"]
    cfg = state["config"]
    det, arena, thr = state["detector"], state["arena"], state["threshold"]
    evolved: Dict[str, dict] = {}
    for aid in REGISTRY:
        res = evade(det, aid, threshold=thr, generations=cfg["generations"],
                    popsize=cfg["popsize"], seed=cfg["seed"] + r, arena=arena)
        evolved[aid] = res.evolved_params
    state["evasive_params"] = evolved
    _log(state, f"[round {r}] red_team: evolved evasive parameters for {len(evolved)} vectors")
    return state


def _recon(state: LoopState) -> LoopState:
    notes = []
    for aid, params in state["evasive_params"].items():
        idea = ideate(aid, params)
        notes.append({"attack": aid, "variant": idea.variant_name, "twist": idea.novel_twist,
                      "footprint": idea.observable_footprint, "mode": idea.mode,
                      "sources": idea.sources})
    state["ideation"] = notes
    mode = notes[0]["mode"] if notes else "offline"
    _log(state, f"[round {state['round']}] recon: {len(notes)} RAG-grounded variants proposed ({mode})")
    return state


def _attack(state: LoopState) -> LoopState:
    r, cfg = state["round"], state["config"]
    evo = simulate(SimConfig(population=cfg["population"], days=cfg["days"],
                             seed=cfg["seed"] + 1000 + r, intensity=cfg["intensity"],
                             attack_params=state["evasive_params"]))
    pre, pre_pv = _recall_at(state["detector"], evo.frame, state["threshold"])
    state["accumulated"].append(evo.frame)
    state["pre_recall"], state["pre_per_vector"] = pre, pre_pv
    _log(state, f"[round {r}] attack: evasive stream breaches to {pre*100:.1f}% recall")
    return state


def _blue_team(state: LoopState) -> LoopState:
    r, cfg = state["round"], state["config"]
    train_df = pd.concat(state["accumulated"], ignore_index=True)
    X, names = build_features(train_df)
    det = FraudDetector(seed=cfg["seed"]).fit_matrix(X, train_df["is_fraud"].to_numpy(), names)
    holdout = simulate(SimConfig(population=cfg["population"] // 2, days=cfg["days"],
                                 seed=cfg["seed"] + 5000 + r, intensity=cfg["intensity"],
                                 attack_params=state["evasive_params"]))
    post, post_pv = _recall_at(det, holdout.frame, state["threshold"])
    state["detector"] = det
    state["rounds"].append(RoundResult(
        round=r, evasive_params=state["evasive_params"], pre_recall=state["pre_recall"],
        post_recall=post, pre_per_vector=state["pre_per_vector"], post_per_vector=post_pv,
        ideation=state.get("ideation", [])))
    state["curve"].append({"round": r, "pre_recall": state["pre_recall"],
                           "post_recall": post, "threshold": round(state["threshold"], 4)})
    _log(state, f"[round {r}] blue_team: retrained, recovers to {post*100:.1f}% recall")
    # Advance the round counter here (a node), not in the router: LangGraph only
    # persists state updates returned from nodes, so incrementing in the routing
    # function would never take effect and the graph would loop forever.
    state["round"] = r + 1
    return state


def _route(state: LoopState) -> str:
    # Pure routing decision - no state mutation. blue_team has already advanced
    # the round, so this just compares against the budget.
    return "end" if state["round"] > state["max_rounds"] else "loop"


def build_graph():
    from langgraph.graph import END, StateGraph
    g = StateGraph(LoopState)
    g.add_node("red_team", _red_team)
    g.add_node("recon", _recon)
    g.add_node("attack", _attack)
    g.add_node("blue_team", _blue_team)
    g.set_entry_point("red_team")
    g.add_edge("red_team", "recon")
    g.add_edge("recon", "attack")
    g.add_edge("attack", "blue_team")
    g.add_conditional_edges("blue_team", _route, {"loop": "red_team", "end": END})
    return g.compile()


def run_loop_graph(rounds: int = 2, population: int = 3000, days: int = 30, seed: int = 42,
                   intensity: float = 2.0, generations: int = 3, popsize: int = 5,
                   log: Optional[Callable[[str], None]] = None) -> dict:
    """Run the loop through the compiled LangGraph and return a serialisable report."""
    load_all()
    say = log or (lambda *_: None)
    base = simulate(SimConfig(population=population, days=days, seed=seed, intensity=intensity))
    X, names = build_features(base.frame)
    det = FraudDetector(seed=seed).fit_matrix(X, base.frame["is_fraud"].to_numpy(), names)
    import numpy as np
    legit = base.frame[base.frame["is_fraud"] == 0]
    thr = float(np.quantile(det.score(legit.sample(min(8000, len(legit)), random_state=seed))["risk"], 0.99))
    base_recall, base_pv = _recall_at(det, base.frame, thr)

    state: LoopState = {
        "round": 1, "max_rounds": rounds,
        "config": {"population": population, "days": days, "seed": seed,
                   "intensity": intensity, "generations": generations, "popsize": popsize},
        "detector": det, "arena": _AttackArena(seed=seed), "threshold": thr,
        "accumulated": [base.frame], "curve": [{"round": 0, "pre_recall": base_recall,
                                                "post_recall": base_recall, "threshold": round(thr, 4)}],
        "rounds": [], "baseline_recall": base_recall, "baseline_per_vector": base_pv,
        "trace": [f"baseline: detector recall {base_recall*100:.1f}% @ thr={thr:.3f}"],
    }
    app = build_graph()
    final = app.invoke(state, config={"recursion_limit": 100})
    for line in final.get("trace", []):
        say(line)
    result = LoopResult(
        baseline_recall=final["baseline_recall"], baseline_per_vector=final["baseline_per_vector"],
        rounds=final["rounds"], hardening_curve=final["curve"],
        meta={"population": population, "days": days, "seed": seed, "rounds": rounds,
              "intensity": intensity, "threshold": round(thr, 4),
              "attacks": list(REGISTRY.keys()), "orchestration": "langgraph"})
    out = loop_result_to_dict(result)
    out["trace"] = final.get("trace", [])
    return out
