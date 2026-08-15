"""Chimera API - serves the three pillars to the web prototype.

Can run two ways:
  * API only (dev): Next.js runs separately on :3000 and proxies /api here.
  * Monolith (prod): if a built static frontend is present (frontend/out, or
    CHIMERA_STATIC_DIR), it is served from the same origin as the API, so a
    single Render service hosts the whole app - no separate frontend deploy.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .. import __version__
from ..config import REPO_ROOT
from .service import get_service

app = FastAPI(title="Chimera API", version=__version__,
              description="Closed-loop adversarial lab for GenAI-era payment fraud.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # demo prototype; tighten to the Vercel origin in prod
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    svc = get_service()
    return {
        "status": "ok",
        "version": __version__,
        "detector_loaded": svc.detector is not None,
        "has_eval": svc.eval_report is not None,
        "has_loop": svc.loop_report is not None,
    }


@app.get("/api/taxonomy")
def taxonomy() -> dict:
    return get_service().taxonomy()


@app.get("/api/attack-params")
def attack_params() -> dict:
    return get_service().attack_params()


@app.get("/api/metrics")
def metrics() -> dict:
    return get_service().metrics()


@app.get("/api/loop")
def loop() -> dict:
    return get_service().loop()


@app.get("/api/validation")
def validation() -> dict:
    return get_service().validation()


@app.get("/api/sim-meta")
def sim_meta() -> dict:
    return get_service().sim_meta or {"error": "run scripts/train.py first"}


class LabRequest(BaseModel):
    attack_id: str
    intensity: float = 1.0
    params: Optional[dict] = None


@app.post("/api/attack-lab")
def attack_lab(req: LabRequest) -> dict:
    svc = get_service()
    if req.attack_id not in svc.taxonomy()["attack_ids"]:
        raise HTTPException(404, f"unknown attack {req.attack_id}")
    return svc.attack_lab(req.attack_id, intensity=req.intensity, params=req.params)


class IdeationRequest(BaseModel):
    attack_id: str
    params: Optional[dict] = None


@app.post("/api/ideation")
def ideation(req: IdeationRequest) -> dict:
    try:
        return get_service().ideation(req.attack_id, req.params)
    except KeyError:
        raise HTTPException(404, f"unknown attack {req.attack_id}")


@app.get("/api/graph")
def graph() -> dict:
    return get_service().graph_snapshot()


@app.get("/api/case/{txn_id}")
def case(txn_id: str) -> dict:
    try:
        return get_service().case(txn_id)
    except KeyError:
        raise HTTPException(404, f"unknown transaction {txn_id}")


# --- optional monolith: serve the built static frontend from the same origin ---
_static = os.getenv("CHIMERA_STATIC_DIR") or str(REPO_ROOT / "frontend" / "out")
if Path(_static).is_dir():
    # Mounted last so every /api route above takes precedence; html=True serves
    # index.html at "/". The Next app is a static export (fully client-rendered).
    app.mount("/", StaticFiles(directory=_static, html=True), name="static")
