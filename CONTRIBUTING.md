# Contribuții

Ghid de lucru pentru echipa LunarHorizon. Instalarea și comenzile de bază sunt în [README.md](README.md);
regulile de proiect pentru Claude Code sunt în [CLAUDE.md](CLAUDE.md) și se aplică tuturor.

## Fluxul de lucru

1. Alege o sarcină din etapa curentă ([docs/STATUS.md](docs/STATUS.md), [docs/BACKLOG.md](docs/BACKLOG.md)).
   Etapele se fac în ordine; bonusurile P1 încep numai după închiderea cerințelor P0.
2. Lucrează pe o ramură separată, de exemplu `e05-teren-primul-sit`. Ramura `main` rămâne verde.
3. Înainte de pull request, rulează toate verificările din README (sau sarcina VS Code „Toate verificările”).
4. Completează șablonul de pull request. Bifează numai verificările rulate efectiv.
5. Actualizează documentele atinse: `docs/STATUS.md` la fiecare etapă, `docs/ACCEPTANCE.md` și
   `docs/VALIDARE.md` numai cu dovezi reale, `docs/SOURCES.md` pentru orice sursă nouă.

Mesajele de commit sunt scurte, la imperativ, în română sau engleză, cu etapa la început când e cazul:
`E05: citește metadatele GeoTIFF în manifest`.

## Reguli care nu se negociază

- Harta 3D este cerință P0 și vederea implicită; nu se mută la bonusuri.
- Nu se inventează coordonate, surse, rezultate Horizons sau rezultate de test.
- Datele sintetice au prefixul `synthetic_` și nu înlocuiesc datele reale.
- `NoData` și valorile necunoscute nu devin zero.
- Timpul este UTC; unitatea apare în numele câmpului (`_deg`, `_m`, `_km`, `_s`, `_utc`).
- Deciziile marcate `[ASTRO]` / `[GEO]` se confirmă cu colegii respectivi.

## Ce nu intră în Git

Secrete și fișiere `.env` (numai `.env.example`, fără valori reale), medii virtuale, `node_modules`,
rezultate de build, cache-uri, kerneluri SPICE și fișiere DEM brute. Datele mari se obțin prin scripturile
din `scripts/` și se descriu în manifeste ([docs/DATA_PLAN.md](docs/DATA_PLAN.md)).

## Contracte și convenții comune

Modelele din `backend/lunarhorizon/contracts/` și convențiile din `backend/lunarhorizon/core/` sunt singura sursă
pentru `data/schemas/lunarhorizon.schema.json`, `tests/vectors/conventions.json` și
`frontend/src/contracts/generated.ts`. Aceste trei fișiere se regenerează (comenzile sunt în README), nu se
editează manual, și intră în același commit cu modificarea. O schimbare de structură crește `SCHEMA_VERSION`
și se consemnează în `docs/API.md`.

O formulă din `core` are o pereche în `frontend/src/geo/`. Cele două se modifică împreună; testele de
concordanță (T-05) eșuează dacă diferă.

## Date externe și referințe

- O poziție nouă în `data/catalog/sites.json` cere un document **deschis** (nu un rezultat de căutare sau un rezumat),
  cu instituție, titlu, URL, locator, coordonate originale, convenții declarate și un citat verificabil. Valorile
  necunoscute rămân `null`. Ținta planificată și poziția efectivă sunt intrări separate. Apoi se rulează
  `scripts/verify_catalog_sources.py --write-report` și `pytest`.
- Un kernel nou se adaugă în `data/manifests/kernels.json`, cu `expected_checksums` numai din surse reale (de
  exemplu `aa_checksums.txt` de la NAIF), apoi se rulează `scripts/download_kernels.py`. Scriptul refuză orice
  nepotrivire.
- Răspunsurile Horizons din `data/reference/horizons/` sunt originale și nu se editează. Un caz nou se adaugă în
  `cases.json`, apoi se rulează `scripts/query_horizons.py`. O eroare de rețea sau un răspuns fără tabel nu este
  o referință.
- Pragurile de comparație din `backend/lunarhorizon/astro/reference.py` rămân „propuse” până la confirmarea
  colegilor (D-12).

## Dependențe

Un singur manager de pachete pe ecosistem: **pip** pentru backend, **npm** pentru frontend.
Se adaugă numai dependențele necesare etapei curente.

**Backend.** Versiunile directe sunt fixate în `backend/pyproject.toml` (grupurile `runtime` și `dev`).
`backend/constraints.txt` fixează tot arborele. După orice schimbare în `pyproject.toml`, din `backend/`:

```powershell
.venv\Scripts\python -m pip install --only-binary=:all: --group dev
.venv\Scripts\python -m pip freeze
```

Liniile de pachete din `constraints.txt` (sub antetul comentat) se înlocuiesc cu ieșirea lui `pip freeze`,
apoi se rulează verificările. Pentru o actualizare curată, recreați întâi mediul virtual. Un pachet nou se
instalează numai din wheel (`--only-binary=:all:`); dacă pip încearcă o compilare, compatibilitatea se
verifică înainte de a continua.

**Frontend.** Din `frontend/`: `npm install --save-exact <pachet>@<versiune>` (cu `--save-dev` pentru unelte).
`package-lock.json` este generat de npm, intră în commit și nu se editează manual. Instalarea din lockfile
se face cu `npm ci`.

Orice versiune nouă se trece în [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) §2, iar licența în
[docs/SOURCES.md](docs/SOURCES.md) §5.

## Acțiuni externe

Crearea remote-ului GitHub, push-ul, publicarea și orice deployment se fac numai cu acordul explicit al
echipei (decizia D-15 din [docs/STATUS.md](docs/STATUS.md)). Nu se rescrie istoria ramurilor partajate.
