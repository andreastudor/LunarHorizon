# backend/

API-ul și motorul de calcul: FastAPI, SpiceyPy pentru astronomie, Rasterio și NumPy pentru relief.

De la E01 conține `pyproject.toml` (versiuni fixate, configurația uneltelor), `constraints.txt` (lockfile),
pachetul `lunarhorizon` gol și testele de fum; comenzile sunt în [README.md](../README.md). Modulele prevăzute (`core`, `catalog`, `astro`, `terrain`,
`visibility`, `simulation`, `api`) sunt descrise în [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) §4,
convențiile fizice în [docs/SPEC_FIZICA.md](../docs/SPEC_FIZICA.md), iar contractele în [docs/API.md](../docs/API.md).

De reținut: toate rezultatele numerice (direcții, orizont, evenimente, indicatori) se calculează aici,
din rasterul DEM la rezoluția declarată, în unități reale și în UTC.
