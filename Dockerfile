# syntax=docker/dockerfile:1
# ---------- 1. build the React frontend ----------
FROM node:20-alpine AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---------- 2. backend image (serves API + built frontend; also used by the worker) ----------
FROM python:3.12-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

# Docker CLI so the worker can start sandbox containers through the mounted socket.
COPY --from=docker:cli /usr/local/bin/docker /usr/local/bin/docker

# Install dependencies first (cached unless pyproject.toml changes).
COPY backend/pyproject.toml ./
RUN python -c "import tomllib;d=tomllib.load(open('pyproject.toml','rb'));print('\n'.join(d['project']['dependencies']+d['project']['optional-dependencies']['dev']))" > /tmp/req.txt \
 && pip install -r /tmp/req.txt

COPY backend/ /app/
COPY --from=frontend /fe/dist /app/static
COPY examples/ /app/static/examples/
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh && mkdir -p /data

ENV DATA_DIR=/data STATIC_DIR=/app/static
EXPOSE 8000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["web"]
