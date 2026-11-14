# backend/

API-ul și motorul de calcul: FastAPI, SpiceyPy pentru astronomie, Rasterio și NumPy pentru relief.

De la E01 conține `pyproject.toml` (versiuni fixate, configurația uneltelor), `constraints.txt` (lockfile),
pachetul `lunarhorizon` gol și testele de fum; comenzile sunt în [README.md](../README.md). Modulele prevăzute (`core`, `catalog`, `astro`, `terrain`,
`visibility`, `simulation`, `api`) sunt descrise în [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) §4,
convențiile fizice în [docs/SPEC_FIZICA.md](../docs/SPEC_FIZICA.md), iar contractele în [docs/API.md](../docs/API.md).

De reținut: toate rezultatele numerice (direcții, orizont, evenimente, indicatori) se calculează aici,
din rasterul DEM la rezoluția declarată, în unități reale și în UTC.

## Serviciul HTTP (E06)

`lunarhorizon.api.app:app` expune `GET /api/health`, `/api/sites`, `/api/coverage`, `/api/terrain/manifest` și
`POST /api/simulations` + `GET /api/simulations/{id}`. Calculul E06 este numai `idealized_local_plane` (orizont
plan la 0°, fără efectele terenului local); `terrain_mode=dem` este refuzat cu `OUT_OF_DEM_COVERAGE`.
Pornire, verificări și limite: [docs/API.md](../docs/API.md) §8 și [docs/HANDOFF_CLAUDE.md](../docs/HANDOFF_CLAUDE.md).
