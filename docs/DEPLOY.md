# Deploy

Chimera ships as a **single monolithic app**: one Docker image builds the Next.js
frontend as a static site and serves it from FastAPI alongside the `/api`
endpoints. One Render service, one URL, no separate frontend deploy, no CORS
wiring. The trained detector, reports and the transfer-graph snapshot are
committed under `data/artifacts/`, so nothing trains or simulates at deploy time.

## Render (recommended, ~1 service)

1. Push to GitHub (done: `dhruv-decoder/chimera`). For a private repo, connect
   Render to your GitHub so it can read it; or make the repo public.
2. Render dashboard -> **New +** -> **Blueprint** -> select the repo. Render reads
   `render.yaml`, sees `runtime: docker`, and builds from the `Dockerfile`.
3. In the service **Environment**, add `GROQ_API_KEY` (from your local
   `backend/.env`) to enable live ideation in the Attack Lab. Optional - without
   it the service runs with the offline planner.
4. Deploy. First build takes a few minutes (it compiles the frontend and installs
   the backend). When live, open the service URL - the whole app is there.
5. Verify: `https://chimera-8vx7.onrender.com/api/health` returns
   `{"status":"ok","detector_loaded":true,...}`, and the root URL loads the app.

### Cold-start note (important for judging)

Render's free tier spins the service down after ~15 minutes idle; the first
request then takes ~30-60s to wake. Before a live demo, open the app (or
`/api/health`) once to warm it, or keep a tab open. The landing story renders
instantly; the graph is precomputed, so only the Attack Lab (which runs a small
live simulation per launch) does real work on the box.

## Local

```bash
make setup        # once
make dev          # API :8000 + web dev :3000  ->  http://localhost:3000
```

To run the exact production monolith locally:

```bash
cd frontend && NEXT_OUTPUT=export npm run build   # emits frontend/out
cd ../backend && .venv/bin/uvicorn chimera.api.server:app --port 8000
# open http://localhost:8000  (FastAPI serves the static app + /api)
```

Or build the image directly: `docker build -t chimera . && docker run -p 8000:8000 chimera`.

## Timings and what to do if something is slow or stuck

| Step | Expected time | If it takes longer |
|---|---|---|
| Render Docker build | ~5-8 min (frontend build + Python deps) | Watch the build log; it streams each step. If it stalls >15 min, Clear build cache and redeploy. |
| First page load after idle | ~30-60s (free-tier cold start) | Open `/api/health` once to wake it, then reload. Keep a tab open before a demo. |
| Attack Lab - default launch | instant (served from a precomputed result) | If it spins, the deploy predates the precompute fix; redeploy the latest commit. |
| Attack Lab - after tuning a knob | ~2-8s on free tier (a small live simulation) | Expected; this is the interactive path. Lower `intensity` for a faster run. |
| Network Graph | instant (precomputed snapshot) | If slow, redeploy the latest commit. |
| `make train` (local) | ~1-2 min | CPU-bound; it prints progress and a final metrics table. |
| `make loop` (local) | ~12-16 min (multi-agent LangGraph) | It now prints each agent step live (`red_team`, `recon`, `attack`, `blue_team`). If the log stops moving for >3 min, it is inside the evolutionary search; check `ps aux | grep run_loop` - rising CPU time means it is working, not stuck. |

The health check is the fastest way to know the backend is alive:
`curl https://<service>.onrender.com/api/health` should return
`{"status":"ok","detector_loaded":true,...}`.

## Alternative: split deploy (Render API + Vercel web)

If you prefer separate services, the split path still works:

1. Render: change `render.yaml` back to a Python runtime, or deploy just the API.
2. Vercel: import the repo, **Root Directory = `frontend`**, add env
   `NEXT_PUBLIC_API_BASE = https://chimera-8vx7.onrender.com` and deploy. `frontend/vercel.json`
   is kept for this path.

The monolith is simpler and is the recommended route.
