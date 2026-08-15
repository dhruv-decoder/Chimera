"""Red-team ideation agent (RAG-grounded).

Given a signal about where the defence is weak (an attack that just evaded the
detector, plus the evasive parameters found), the agent retrieves relevant fraud
intelligence and proposes a *novel attack variant* as a structured spec:
technique mapping, a concrete new twist, parameter directions, and the observable
footprint a defender should watch.

Two execution modes, auto-selected:
  * LLM mode - Groq (open-source models, free tier) via LangChain, when a key is
    present. Fast enough for an interactive loop.
  * Offline mode - a deterministic planner that composes retrieved intel with the
    evasive parameters. Always available, so the loop and the demo never depend
    on network or credits.

The output schema is identical in both modes, so downstream code is agnostic.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import List, Optional

from ..config import settings
from .rag import get_retriever
from .taxonomy import get_technique

SYSTEM_PROMPT = (
    "You are a payments fraud red-team strategist. Given intelligence and a current "
    "attack that evaded detection, propose ONE novel, realistic variant that would "
    "further stress a fraud detector. Ground it in how real payment systems work. "
    "Respond as strict JSON with keys: variant_name, technique_id, novel_twist, "
    "param_directions (object of param->'increase'|'decrease' with a short reason), "
    "observable_footprint (list of signals a defender could still use), rationale. "
    "Be concrete and non-generic. No preamble."
)


@dataclass
class Ideation:
    variant_name: str
    technique_id: str
    novel_twist: str
    param_directions: dict
    observable_footprint: List[str]
    rationale: str
    sources: List[str]
    mode: str  # "groq:<model>" or "offline"


def _prompt(attack_id: str, evasive_params: dict, intel: List[dict]) -> str:
    tech = get_technique(attack_id)
    intel_block = "\n".join(f"- {d['title']}: {d['snippet'][:220]}" for d in intel)
    return (
        f"CURRENT ATTACK: {attack_id} ({tech.name if tech else ''}).\n"
        f"EVASIVE PARAMETERS THAT BEAT THE MODEL: {json.dumps(evasive_params)}\n"
        f"RELEVANT INTELLIGENCE:\n{intel_block}\n\n"
        f"Propose the next variant."
    )


def _offline(attack_id: str, evasive_params: dict, intel: List[dict]) -> Ideation:
    """Deterministic planner: turn the evasive direction + top intel into a spec."""
    tech = get_technique(attack_id)
    # Prefer a narrative intel note over the attack's own taxonomy entry.
    others = [d for d in intel if d["id"] != attack_id]
    top = (others or intel or [{"title": "", "sources": []}])[0]
    # Infer parameter directions from the evasive params vs the technique defaults.
    directions = {}
    for k, v in list(evasive_params.items())[:4]:
        directions[k] = {"direction": "tune", "reason": f"evasive search favoured {k}={v}"}
    twist = (f"Blend {tech.name.lower() if tech else attack_id} with the tradecraft in "
             f"'{top['title']}': stagger events to mimic legitimate cadence and reuse "
             f"aged, low-risk infrastructure so per-event anomaly stays below threshold.")
    footprint = (tech.signatures[:4] if tech else []) + ["cross-entity correlation over time"]
    return Ideation(
        variant_name=f"{attack_id}-adaptive",
        technique_id=attack_id,
        novel_twist=twist,
        param_directions=directions,
        observable_footprint=footprint,
        rationale=("Static single-event scoring misses this; it is only visible by "
                   "correlating entities (device, payee, timing) across the campaign."),
        sources=top.get("sources", []),
        mode="offline",
    )


def _content_text(resp) -> str:
    """LangChain content may be a string or a list of parts; normalise to text."""
    c = getattr(resp, "content", "")
    if isinstance(c, list):
        c = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in c)
    return str(c).strip()


def _groq(attack_id: str, evasive_params: dict, intel: List[dict]) -> Optional[Ideation]:
    try:
        from langchain_groq import ChatGroq
        from langchain_core.messages import HumanMessage, SystemMessage
    except Exception:
        return None
    debug = os.getenv("CHIMERA_LLM_DEBUG")
    # One retry: hosted endpoints occasionally cold-start or rate-limit, and a
    # silent fall back to the offline planner would understate the live agent.
    for attempt in range(2):
        try:
            # Hard per-call timeout so the loop can never hang on a slow/rate-limited
            # endpoint; we handle retries ourselves and fall back to the offline planner.
            llm = ChatGroq(model=settings.groq_model, api_key=settings.groq_api_key,
                           temperature=settings.llm_temperature,
                           max_tokens=max(settings.llm_max_tokens, 1500),
                           timeout=settings.llm_timeout_s, max_retries=0)
            resp = llm.invoke([SystemMessage(content=SYSTEM_PROMPT),
                               HumanMessage(content=_prompt(attack_id, evasive_params, intel))])
            text = _content_text(resp)
            if text.startswith("```"):
                text = text.strip("`").split("\n", 1)[-1]
            data = json.loads(text[text.find("{"): text.rfind("}") + 1])
            return Ideation(
                variant_name=data.get("variant_name", f"{attack_id}-variant"),
                technique_id=data.get("technique_id", attack_id),
                novel_twist=data.get("novel_twist", ""),
                param_directions=data.get("param_directions", {}),
                observable_footprint=data.get("observable_footprint", []),
                rationale=data.get("rationale", ""),
                sources=[s for d in intel for s in d.get("sources", [])][:4],
                mode=f"groq:{settings.groq_model}",
            )
        except Exception as e:  # noqa: BLE001 - degrade to offline, optionally log
            if debug:
                print(f"[ideation] groq attempt {attempt+1} failed: {type(e).__name__}: {e}")
    return None


def ideate(attack_id: str, evasive_params: dict, k: int = 4) -> Ideation:
    tech = get_technique(attack_id)
    query = f"{attack_id} {tech.name if tech else ''} {' '.join((tech.signatures if tech else []))}"
    intel = get_retriever().query(query, k=k)
    if settings.llm_available:
        out = _groq(attack_id, evasive_params, intel)
        if out is not None:
            return out
    return _offline(attack_id, evasive_params, intel)
