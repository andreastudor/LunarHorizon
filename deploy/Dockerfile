FROM node:26-bookworm-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 PORT=8000
WORKDIR /app
COPY backend/pyproject.toml backend/constraints.txt ./backend/
RUN python -m pip install --no-cache-dir pip==26.2.1 && \
    python -m pip install --no-cache-dir --only-binary=:all: \
      -c backend/constraints.txt --group backend/pyproject.toml:runtime jsonschema==4.26.0
COPY backend/lunarhorizon/ ./backend/lunarhorizon/
COPY scripts/ ./scripts/
COPY data/catalog/ ./data/catalog/
COPY data/manifests/ ./data/manifests/
COPY data/schemas/ ./data/schemas/
COPY --from=frontend /app/frontend/dist/ ./frontend/dist/
# Download real data once during build; failures stop the build rather than inventing substitutes.
RUN python scripts/download_kernels.py && \
    python scripts/download_terrain.py && python scripts/build_terrain.py && \
    python scripts/download_e05_auxiliary.py && python scripts/build_e05_auxiliary.py && \
    python scripts/acquire_pgda104.py --all && python scripts/build_pgda104_regions.py && \
    python scripts/acquire_lola_gdr.py LDEM_75S_120M && \
    python scripts/verify_terrain_products.py && python scripts/verify_e05.py
RUN useradd --create-home lunar && chown -R lunar:lunar /app
USER lunar
EXPOSE 8000
# A single process is required: simulation jobs and SPICE profile state are process-local.
CMD ["sh", "-c", "exec python -m uvicorn lunarhorizon.api.production:create_production_app --factory --app-dir backend --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --limit-concurrency 32"]
