# LunarHorizon

Aplicație web pentru **NASA Space Apps Challenge — Lunar Landing Site Navigator**. Pentru un punct de pe
Lună și un interval de timp, arată unde se află Soarele și Pământul pe cer, când sunt ascunse de relieful
local, cât durează lumina și întunericul și cum se compară mai multe situri între ele.

Vederea principală este o **hartă 3D**: un glob lunar navigabil și relief local construit din date
altimetrice reale (LOLA) pentru siturile polare. O hartă 2D sincronizată este disponibilă ca alternativă.

## Stare

Implementate: glob 3D, teren real pentru 13 regiuni PGDA 104, orizont DEM, vizibilitate și evenimente;
vederea Earth–Moon–Sun, hartă 2D și comparație 2–4 situri. Acceptarea științifică și unele verificări
rămân deschise: [docs/STATUS.md](docs/STATUS.md). Punctele DEM sunt reprezentative, nu locuri de aterizare.
Versiunea curentă pentru hackathon este pe ramura `e04-completare-dovezi`.

## Hackathon: datele și pornirea aplicației complete

După instalarea dependențelor de mai jos, o clonă nouă necesită datele reale. Acestea nu sunt incluse
în Git, la fel ca mediile virtuale și cache-urile; pe calculatorul de dezvoltare există deja.
Comenzile reproducibile (rădăcina proiectului, PowerShell):

```powershell
$env:PYTHONUTF8 = "1"
backend\.venv\Scripts\python scripts\download_kernels.py
backend\.venv\Scripts\python scripts\download_terrain.py
backend\.venv\Scripts\python scripts\build_terrain.py
backend\.venv\Scripts\python scripts\download_e05_auxiliary.py
backend\.venv\Scripts\python scripts\build_e05_auxiliary.py
backend\.venv\Scripts\python scripts\acquire_pgda104.py --all
backend\.venv\Scripts\python scripts\build_pgda104_regions.py
backend\.venv\Scripts\python scripts\acquire_lola_gdr.py LDEM_75S_120M
backend\.venv\Scripts\python scripts\verify_terrain_products.py
```

Descărcările cer acces la sursele oficiale și pot dura. La eroare nu se generează teren sintetic.
Pornește două terminale din rădăcina proiectului:

```powershell
# Terminal 1 — API
backend\.venv\Scripts\python -m uvicorn lunarhorizon.api.app:app --app-dir backend --host 127.0.0.1 --port 8000
# Terminal 2 — interfață
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173
```

Deschide http://127.0.0.1:5173. Pentru comparație: selectează **Leibnitz Beta**, adaugă-l în lista
de comparație; repetă pentru **Connecting Ridge** (nu Extension); alege **DEM terrain horizon**, **1 day**,
**Compare sites**. Prima rulare calculează orizontul fin și poate dura. Apasă titlul unei coloane și
**Local terrain** pentru situl activ. Sliderul este comun. **Earth–Moon–Sun** funcționează și fără
simulare locală; **2D map** păstrează selecția.

`npm --prefix frontend run build` produce frontendul, care necesită în continuare API și date.
**Push-ul Git nu este deployment. GitHub Pages singur nu rulează SPICE/DEM.** Modul complet offline E15
nu este implementat încă. Nu declarați MVP-ul complet cât timp criteriile deschise din ACCEPTANCE persistă.

## Structură

| Director | Conținut |
|---|---|
| [frontend/](frontend/) | Interfața: React, TypeScript, Vite, Three.js, OpenLayers |
| [backend/](backend/) | API și calcule: FastAPI, SpiceyPy, Rasterio, NumPy |
| [scripts/](scripts/) | Descărcarea și prelucrarea datelor, precalcularea scenariilor |
| [tests/](tests/) | Vectori de test comuni, teste de integrare și de interfață |
| [data/](data/) | Catalog, manifeste, teren, cazuri de referință, scenarii precalculate |
| [docs/](docs/) | Documentația de proiect |
| [deploy/](deploy/) | Configurații de build și publicare |

## Documentație

| Document | Conținut |
|---|---|
| [SPECIFICATIE.md](docs/SPECIFICATIE.md) | Cerințele și prioritățile P0/P1/P2 |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Module, moduri de funcționare, decizii tehnice |
| [SPEC_FIZICA.md](docs/SPEC_FIZICA.md) | Unități, timp, cadre de coordonate, formule |
| [API.md](docs/API.md) | Contracte de date, endpointuri, erori, export |
| [DATA_PLAN.md](docs/DATA_PLAN.md) | Produse de date, prelucrare, stocare |
| [BACKLOG.md](docs/BACKLOG.md) | Etapele de implementare |
| [ACCEPTANCE.md](docs/ACCEPTANCE.md) | Criterii de acceptanță și starea cerințelor P0 |
| [VALIDARE.md](docs/VALIDARE.md) | Toleranțe, cazuri de referință, rezultate |
| [SOURCES.md](docs/SOURCES.md) | Surse și credite |
| [LIMITATIONS.md](docs/LIMITATIONS.md) | Limitele modelului și ale datelor |
| [STATUS.md](docs/STATUS.md) | Starea curentă și deciziile deschise |

## Cerințe

| Unealtă | Versiune | Observații |
|---|---|---|
| Python | 3.13 | Pe Windows, lansatorul `py` poate avea altă versiune implicită; comenzile de mai jos cer explicit `py -3.13` |
| Node.js | 26 (LTS) | Fixat în [frontend/.nvmrc](frontend/.nvmrc) |
| npm | inclus în Node | Singurul manager de pachete pentru frontend |
| Git | orice versiune recentă | — |

Nu sunt necesare GDAL în linie de comandă, Conda sau Docker: pachetul Rasterio include biblioteca GDAL
și driverele folosite (GeoTIFF, COG, JPEG 2000).

## Instalare

Comenzile sunt pentru PowerShell pe Windows și se rulează din rădăcina repository-ului.

**Backend** — mediu virtual local în `backend\.venv`, cu versiunile exacte din
[backend/constraints.txt](backend/constraints.txt):

```powershell
py -3.13 -m venv backend\.venv
backend\.venv\Scripts\python -m pip install pip==26.2.1
backend\.venv\Scripts\python -m pip install --only-binary=:all: -c backend\constraints.txt --group backend\pyproject.toml:dev
backend\.venv\Scripts\python scripts\check_env.py
```

Ultima comandă afișează versiunile și driverele raster și se termină cu cod de eroare dacă lipsește ceva
obligatoriu. Pentru diacritice corecte în consolă, setați înainte `$env:PYTHONUTF8 = "1"`.

**Frontend** — dependențele exacte din [frontend/package-lock.json](frontend/package-lock.json):

```powershell
cd frontend
npm ci
cd ..
```

Dacă PowerShell refuză să ruleze `npm` din cauza politicii de execuție, folosiți `npm.cmd` în loc de `npm`.

## Pornire

```powershell
cd frontend
npm run dev
```

Pagina este la <http://localhost:5173>.

Interfața (E07, în engleză) folosește API-ul prin proxy-ul Vite (`/api` → `127.0.0.1:8000`), deci pornește și serverul API, în alt terminal, din `backend/`:

```powershell
$env:PYTHONUTF8 = '1'
.venv\Scripts\python -m uvicorn lunarhorizon.api.app:app --host 127.0.0.1 --port 8000
```

Documentația interactivă este la <http://127.0.0.1:8000/api/docs>, iar schema OpenAPI la `/api/openapi.json`.
Kernelurile SPICE trebuie descărcate (`scripts\download_kernels.py`); fără ele `health` raportează `degraded`.

## Verificări

Aceleași verificări rulează în CI ([.github/workflows/ci.yml](.github/workflows/ci.yml)).

```powershell
cd backend
.venv\Scripts\python -m ruff check . ..\scripts
.venv\Scripts\python -m ruff format --check . ..\scripts
.venv\Scripts\python -m mypy
.venv\Scripts\python -m pytest
.venv\Scripts\python ..\scripts\generate_contracts.py --check
cd ..\frontend
npm run format:check
npm run lint
npm run contracts:check
npm run typecheck
npm test
npm run build
cd ..
```

**Catalogul siturilor** (din E04, `data/catalog/sites.json`) se validează în `pytest` (offline). Reverificarea pozițiilor la
sursele originale cere rețea și rescrie raportul `data/catalog/source_verification.json`:

```powershell
backend\.venv\Scripts\python scripts\verify_catalog_sources.py --write-report
```

**Kernelurile SPICE** (din E03, ~62 MB, în `data/kernels/`, în afara Git) se descarcă de la NAIF și se verifică
față de sumele din [data/manifests/kernels.json](data/manifests/kernels.json):

```powershell
backend\.venv\Scripts\python scripts\download_kernels.py
backend\.venv\Scripts\python scripts\download_kernels.py --verify
```

Fără kerneluri, testele cu marcajul `kernels` sunt omise automat; restul verificărilor rulează normal. Cu
kerneluri, comparațiile cu referințele Horizons arhivate se pot regenera fără rețea:

```powershell
backend\.venv\Scripts\python scripts\validate_e03.py
```

Referințele însele (`data/reference/horizons/`) se reinterogează numai la nevoie, cu rețea:
`backend\.venv\Scripts\python scripts\query_horizons.py --refresh`.

**Contractele de date** (din E02) se definesc în `backend/lunarhorizon/contracts/`. După o modificare a lor sau
a convențiilor din `backend/lunarhorizon/core/`, se regenerează schema, vectorii comuni și tipurile TypeScript:

```powershell
backend\.venv\Scripts\python scripts\generate_contracts.py
cd frontend
npm run contracts:generate
cd ..
```

Pe Linux sau macOS, comenzile sunt aceleași, cu `python3.13 -m venv backend/.venv` și
`backend/.venv/bin/python` în loc de `backend\.venv\Scripts\python`. Aceste variante nu au fost
verificate local; CI le rulează pe Ubuntu.

În VS Code, sarcinile echivalente sunt în *Terminal → Run Task*, iar configurațiile de depanare în
*Run and Debug*. Nicio sarcină nu pornește automat. Regulile de lucru sunt în [CONTRIBUTING.md](CONTRIBUTING.md).

## Demo

Demonstrația (două situri polare cu relief real, comparație, mod offline) se adaugă la etapele E15–E16.
Vezi [docs/BACKLOG.md](docs/BACKLOG.md).

## Date și credite

Aplicația folosește date publice NASA (LOLA, PGDA, LROC, NAIF/SPICE, JPL Horizons). Sursele, citările și
starea verificării lor sunt în [docs/SOURCES.md](docs/SOURCES.md).

## Licență

MIT — vezi [LICENSE](LICENSE).

