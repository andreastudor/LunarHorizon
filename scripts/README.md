# scripts/

Scripturi pentru descărcarea reproductibilă a datelor (kerneluri SPICE, DEM, texturi), prelucrarea
terenului pentru calcul și pentru afișare, interogarea cazurilor de referință Horizons și precalcularea
scenariilor offline.

Deocamdată conține numai `check_env.py` (E01), care verifică versiunile și driverele raster ale mediului.
Scripturile de date apar la E03 și E05; pașii prevăzuți sunt în [docs/DATA_PLAN.md](../docs/DATA_PLAN.md) §4.

De reținut: fiecare descărcare verifică suma de control și scrie în manifest; niciun script nu
completează golurile din date; precalcularea folosește motorul din `backend/`, nu o implementare separată.
