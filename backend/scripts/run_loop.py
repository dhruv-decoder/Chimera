"""Run the closed adversarial loop and persist the hardening report.

    python scripts/run_loop.py [--rounds N] [--population N] [--engine orchestrator|langgraph]

Writes data/artifacts/loop_report.json (the hardening curve + per-round detail),
consumed by the web prototype's Closed-Loop console.
"""
from __future__ import annotations

import argparse
import json
import time

from rich.console import Console

from chimera.config import ARTIFACTS_DIR, settings

console = Console()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--population", type=int, default=3000)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--intensity", type=float, default=2.0)
    ap.add_argument("--generations", type=int, default=4)
    ap.add_argument("--popsize", type=int, default=6)
    ap.add_argument("--seed", type=int, default=settings.seed)
    ap.add_argument("--engine", choices=["orchestrator", "langgraph"], default="orchestrator")
    args = ap.parse_args()

    console.rule(f"[bold]Chimera closed loop - {args.engine}")
    console.print(f"LLM ideation: {'Groq ' + settings.groq_model if settings.llm_available else 'offline planner'}")
    t0 = time.time()

    if args.engine == "langgraph":
        from chimera.loop.graph import run_loop_graph
        report = run_loop_graph(rounds=args.rounds, population=args.population, days=args.days,
                                seed=args.seed, intensity=args.intensity,
                                generations=args.generations, popsize=args.popsize,
                                log=console.print)
    else:
        from chimera.loop.orchestrator import loop_result_to_dict, run_loop
        from chimera.identify.ideation_agent import ideate

        def ideation_fn(aid, params, meta):
            idea = ideate(aid, params)
            return [{"attack": aid, "variant": idea.variant_name, "twist": idea.novel_twist,
                     "footprint": idea.observable_footprint, "mode": idea.mode,
                     "sources": idea.sources}]

        res = run_loop(rounds=args.rounds, population=args.population, days=args.days,
                       seed=args.seed, intensity=args.intensity, generations=args.generations,
                       popsize=args.popsize, ideation_fn=ideation_fn, log=console.print)
        report = loop_result_to_dict(res)

    (ARTIFACTS_DIR / "loop_report.json").write_text(json.dumps(report, indent=2, default=str))
    console.rule("[bold green]Hardening curve")
    for pt in report["hardening_curve"]:
        console.print(f"  round {pt['round']}:  pre-retrain {pt['pre_recall']*100:5.1f}%   "
                      f"post-retrain {pt['post_recall']*100:5.1f}%")
    console.print(f"[green]Saved -> {ARTIFACTS_DIR/'loop_report.json'}  ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
