.DEFAULT_GOAL := help
SHELL := /bin/bash
VENV := backend/.venv
PY := $(VENV)/bin/python

.PHONY: help setup train loop validate gnn chains api web dev test clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

setup: ## Create venv, install backend (with agents) + frontend deps
	cd backend && uv venv --python 3.11 && uv pip install -e ".[agents,dev]"
	cd frontend && npm install

train: ## Simulate + train detector + evaluate (writes data/artifacts)
	cd backend && .venv/bin/python scripts/train.py --population 5000 --days 30 --intensity 2.0

loop: ## Run the closed adversarial loop via the LangGraph multi-agent engine
	cd backend && .venv/bin/python scripts/run_loop.py --rounds 3 --population 3000 --engine langgraph

validate: ## External validation: run the detector on real ULB fraud (via OpenML)
	cd backend && .venv/bin/python scripts/validate_real.py

gnn: ## Benchmark the GraphSAGE GNN vs gradient boosting on ring detection (needs the gnn extra)
	cd backend && .venv/bin/python scripts/gnn_benchmark.py

chains: ## BETA: combined attack chains - does chaining evade, and does the loop recover?
	cd backend && .venv/bin/python scripts/attack_chains.py

api: ## Serve the FastAPI backend on :8000
	cd backend && .venv/bin/uvicorn chimera.api.server:app --host 0.0.0.0 --port 8000 --reload

web: ## Serve the Next.js frontend on :3000
	cd frontend && npm run dev

dev: ## Run backend + frontend together
	@$(MAKE) -j2 api web

test: ## Run the backend test suite
	cd backend && .venv/bin/pytest

clean: ## Remove build/cache artifacts
	find . -name __pycache__ -type d -prune -exec rm -rf {} + ; rm -rf frontend/.next
