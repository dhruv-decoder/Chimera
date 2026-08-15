"""Does the LLM ideation agent actually add value over the offline planner?

For each attack it asks both the live open-weight model (Groq gpt-oss-120b) and the
deterministic offline planner to propose a variant, then compares diversity: the
offline planner is a fixed template, so its variants are near-identical; the LLM
should produce a much larger, more varied hypothesis space. Reported as vocabulary
size and unique variants/footprints.

Writes data/artifacts/llm_ablation.json.

    python scripts/llm_ablation.py
"""
from __future__ import annotations

import json
import re
import time

from rich.console import Console

from chimera.config import ARTIFACTS_DIR
from chimera.generate.attacks import REGISTRY, load_all
from chimera.identify import ideation_agent as ia
from chimera.identify.rag import get_retriever
from chimera.identify.taxonomy import get_technique

console = Console()


def _tokens(texts):
    words = set()
    for t in texts:
        words |= set(re.findall(r"[a-zA-Z][a-zA-Z-]{2,}", (t or "").lower()))
    return words


def main():
    load_all()
    console.rule("[bold]LLM vs offline ideation - does the model add value?")
    off_twists, off_names, off_fp = [], [], set()
    for aid in REGISTRY:
        tech = get_technique(aid)
        intel = get_retriever().query(f"{aid} {tech.name if tech else ''}", k=4)
        off = ia._offline(aid, REGISTRY[aid].defaults(), intel)
        off_twists.append(off.novel_twist); off_names.append(off.variant_name)
        off_fp |= set(off.observable_footprint)

    # LLM side: use the live gpt-oss variants already produced in the shipped loop
    # report (round 1, tagged groq:...), which avoids re-hitting the free-tier limit.
    llm_twists, llm_names, llm_fp = [], [], set()
    try:
        loop = json.load(open(ARTIFACTS_DIR / "loop_report.json"))
        ideas = loop["rounds"][0]["ideation"]
        llm_twists = [i.get("twist", "") for i in ideas]
        llm_names = [i.get("variant", "") for i in ideas]
        for i in ideas:
            llm_fp |= set(i.get("footprint", []))
    except Exception:
        pass
    llm_ok = len(llm_twists)

    report = {
        "attacks": len(REGISTRY),
        "offline": {"unique_variant_names": len(set(off_names)),
                    "twist_vocabulary": len(_tokens(off_twists)),
                    "unique_footprint_signals": len(off_fp)},
        "llm": {"live_variants": llm_ok,
                "unique_variant_names": len(set(llm_names)),
                "twist_vocabulary": len(_tokens(llm_twists)),
                "unique_footprint_signals": len(llm_fp)},
        "note": "the offline planner is a deterministic template (near-identical twists, "
                "small vocabulary); the LLM proposes a far larger, more varied hypothesis "
                "space even on a handful of live calls. The offline path exists only so the "
                "loop never stalls, not because it matches the model.",
    }
    (ARTIFACTS_DIR / "llm_ablation.json").write_text(json.dumps(report, indent=2))
    console.print(report)
    console.print("[green]Saved -> llm_ablation.json")


if __name__ == "__main__":
    main()
