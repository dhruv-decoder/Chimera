# Monolithic Chimera: one image, one Render service, one URL.
# Stage 1 builds the Next.js static export; stage 2 serves it from FastAPI
# alongside the /api endpoints, so there is no separate frontend deploy.

# ---- stage 1: build the static frontend ----
FROM node:20-alpine AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
ENV NEXT_OUTPUT=export
ENV NEXT_PUBLIC_API_BASE=""
# emits /web/out (static site, same-origin /api calls)
RUN npm run build

# ---- stage 2: python runtime serving API + static ----
FROM python:3.11-slim AS app
WORKDIR /app
# libgomp1 is required by LightGBM
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY backend/ ./backend/
RUN pip install --no-cache-dir -e "./backend[agents]"
# committed detector + reports, so nothing trains at deploy time
COPY data/ ./data/
# built static site from stage 1
COPY --from=web /web/out ./frontend/out
ENV CHIMERA_STATIC_DIR=/app/frontend/out
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn chimera.api.server:app --host 0.0.0.0 --port ${PORT:-8000}"]
