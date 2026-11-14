# LunarHorizon — reguli pentru Claude Code

Aplicație web pentru NASA Space Apps Challenge (Lunar Landing Site Navigator): poziția Soarelui și a
Pământului pe cerul unui punct lunar, orizontul din relief, intervalele de lumină și de vizibilitate,
comparația între situri.

## Înainte de a lucra

1. Citește `docs/STATUS.md`: etapa curentă, deciziile deschise, blocajele.
2. Citește etapa respectivă din `docs/BACKLOG.md`.
3. Deschide celelalte documente numai când ai nevoie de ele:

| Subiect | Document |
|---|---|
| Cerințe și priorități P0/P1/P2 | `docs/SPECIFICATIE.md` |
| Module, moduri de funcționare, decizii tehnice | `docs/ARCHITECTURE.md` |
| Unități, timp, cadre, formule | `docs/SPEC_FIZICA.md` |
| Endpointuri, scheme, erori | `docs/API.md` |
| Produse de date și prelucrare | `docs/DATA_PLAN.md` |
| Criterii de acceptanță și starea P0 | `docs/ACCEPTANCE.md` |
| Toleranțe și rezultate de test | `docs/VALIDARE.md` |
| Surse, limite | `docs/SOURCES.md`, `docs/LIMITATIONS.md` |

## Reguli care nu se negociază

- **Harta 3D este P0 și vederea principală:** glob navigabil și teren local din DEM real, pentru cel puțin două situri polare. Harta 2D este alternativa sincronizată. 3D-ul nu se mută la bonusuri; un glob doar texturat nu este suficient.
- **Nu inventa** coordonate, surse, rezultate Horizons, acoperire DEM, toleranțe validate sau rezultate de test. Datele sintetice au prefixul `synthetic_` și apar numai în teste.
- **Timp:** UTC peste tot, ISO 8601 cu `Z`. Conversia spre timpul SPICE se face numai prin SPICE.
- **Unități în numele câmpurilor:** `_deg`, `_m`, `_km`, `_s`, `_utc`. Longitudine pozitivă spre est.
- **Cadru:** Mean Earth / Polar Axis, cu numele explicit al cadrului (nu aliasul `MOON_ME`, nu `IAU_MOON`).
- **Calculul nu folosește geometria de randare.** Orizontul și vizibilitatea vin din backend, din rasterul DEM. Mesh-ul, umbrele și exagerarea verticală sunt numai vizuale.
- **`NoData` nu este altitudine zero.** Zero, necunoscut (`null` cu motiv) și necalculat sunt stări diferite.
- Un test se raportează ca trecut numai dacă a fost rulat.
- Deciziile marcate `[ASTRO]` sau `[GEO]` se confirmă cu colegii înainte de a fi tratate ca validate.

## Mod de lucru

- O etapă pe rând, în ordinea din backlog. Bonusurile P1 încep numai după închiderea cerințelor P0.
- La sfârșitul fiecărei etape: rulează verificările, actualizează `docs/STATUS.md`, `docs/VALIDARE.md` și `docs/ACCEPTANCE.md`.
- Fixează versiunile dependențelor și verifică documentația oficială înainte de integrare.
- Nu crea remote-uri, nu publica și nu face push fără acordul explicit al utilizatorului. Nu rescrie istoria Git.
- **Interfața web este în engleză** (decizia utilizatorului, 2026-11-14), cu texte prin chei în `frontend/src/i18n/en.ts`, fără selector de limbă. Documentația internă rămâne în română. Nu se traduc identificatorii, câmpurile API, titlurile originale ale surselor și denumirile oficiale ale siturilor.

## Comenzi

Repository-ul este `Desktop\LunarHorizon\LunarHorizon`. Instalarea completă este în `README.md`; pe Windows
folosește explicit `py -3.13` (lansatorul `py` are implicit 3.15), nu Python-ul global.

| Ce | Unde | Comandă |
|---|---|---|
| Teste, lint, tipuri backend | `backend/` | `.venv\Scripts\python -m pytest`, `-m ruff check . ..\scripts`, `-m ruff format --check . ..\scripts`, `-m mypy` |
| Verificarea mediului | rădăcină | `backend\.venv\Scripts\python scripts\check_env.py` (cu `PYTHONUTF8=1` pentru diacritice) |
| Verificări frontend | `frontend/` | `npm run format:check`, `npm run lint`, `npm run contracts:check`, `npm run typecheck`, `npm test`, `npm run build` |
| Catalog de situri | rădăcină | `backend\.venv\Scripts\python scripts\verify_catalog_sources.py [--write-report]` (rețea); testele offline sunt în `pytest` |
| Kerneluri SPICE | rădăcină | `backend\.venv\Scripts\python scripts\download_kernels.py [--verify]`; testele `-m kernels` le cer |
| Horizons | rădăcină | `scripts\query_horizons.py` (rețea, arhivează răspunsurile originale); `scripts\validate_e03.py` (fără rețea) |
| Contracte și vectori comuni | rădăcină, apoi `frontend/` | `backend\.venv\Scripts\python scripts\generate_contracts.py [--check]`, apoi `npm run contracts:generate`; nu edita manual fișierele generate |
| Server API (E06) | `backend/` | `.venv\Scripts\python -m uvicorn lunarhorizon.api.app:app --port 8000` → http://127.0.0.1:8000/api/docs |
| Server de dezvoltare | `frontend/` | `npm run dev` → http://localhost:5173 |
| Dependențe | — | pip (`--group`, `-c constraints.txt`) și npm (`--save-exact`); procedura în `CONTRIBUTING.md` |
