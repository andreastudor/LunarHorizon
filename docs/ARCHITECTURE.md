# Arhitectură — LunarHorizon

Proiectare pentru cerințele din [SPECIFICATIE.md](SPECIFICATIE.md). Convențiile fizice sunt în
[SPEC_FIZICA.md](SPEC_FIZICA.md), contractele în [API.md](API.md), datele în [DATA_PLAN.md](DATA_PLAN.md).
Nimic din acest document nu este încă implementat.

## 1. Vedere de ansamblu

```
                         ┌──────────────────────── Browser ────────────────────────┐
                         │  React + TypeScript (Vite)                              │
                         │                                                         │
                         │  Stare comună: situri selectate, sit activ, moment UTC, │
                         │  interval, parametri, mod simplu/expert, vedere 3D/2D   │
                         │        │                                                │
                         │  ┌─────┴──────┬────────────┬────────────┬───────────┐   │
                         │  │ Hartă 3D   │ Hartă 2D   │ Cer local  │ Grafice,  │   │
                         │  │ Three.js   │ OpenLayers │ SVG        │ comparație│   │
                         │  │ (implicit) │ (alternativă)           │           │   │
                         │  └─────┬──────┴─────┬──────┴─────┬──────┴─────┬─────┘   │
                         │        └────────────┴─── DataSource ──────────┘         │
                         │                    ┌───────┴────────┐                   │
                         │             ApiDataSource    StaticDataSource           │
                         └────────────────────┼────────────────┼───────────────────┘
                                              │ HTTP /api      │ fișiere locale
                         ┌────────────────────┴───────┐   ┌────┴──────────────────┐
                         │ Backend FastAPI            │   │ data/precomputed/     │
                         │  catalog · acoperire       │   │ scenarii + teren      │
                         │  teren · simulări          │   │ (incluse în build)    │
                         │  ┌───────────┬───────────┐ │   └───────────────────────┘
                         │  │ Astronomie│ Teren     │ │              ▲
                         │  │ SpiceyPy  │ Rasterio  │ │              │ scripts/precompute
                         │  └─────┬─────┴─────┬─────┘ │──────────────┘
                         │   kerneluri    raster DEM  │
                         │   SPICE        de calcul   │
                         └────────────────────────────┘
```

Două principii structurează totul:

1. **Un singur rezultat numeric.** Harta 3D, harta 2D, vederea cerului, graficele și comparația citesc același
   rezultat de simulare. Nicio componentă vizuală nu recalculează pozițiile sau vizibilitatea.
2. **Calculul și randarea folosesc geometrii separate** (vezi [SPEC_FIZICA.md](SPEC_FIZICA.md) §10). Backendul
   calculează orizontul din rasterul DEM la rezoluția declarată; browserul primește un mesh simplificat, numai pentru afișare.

## 2. Tehnologii și versiuni

Fiecare dependență se fixează în etapa care o folosește prima dată. Sursele adevărului sunt
`backend/pyproject.toml` și `backend/constraints.txt` (backend), `frontend/package.json` și
`frontend/package-lock.json` (frontend).

**Fixate și instalate la E01 (2026-11-14)**

| Componentă | Pachet | Versiune | Observații |
|---|---|---|---|
| Limbaj backend | Python | 3.13 (local 3.13.16) | Ales explicit cu `py -3.13`; lansatorul `py` are 3.15 ca implicit |
| Manager backend | pip | 26.2.1 | Grupuri PEP 735 (`--group`) și fișier de constrângeri generat cu `pip freeze` |
| Calcul numeric | NumPy | 2.5.4 | — |
| Astronomie | SpiceyPy | 8.4.0 | Legat de CSPICE N0067 (confirmat cu `tkvrsn`) |
| Teren | Rasterio | 1.5.2 | Wheel cu GDAL 3.12.2 și PROJ 9.7.1; vezi §7 |
| Teste backend | pytest | 9.2.0 | — |
| Lint și format backend | Ruff | 0.17.5 | — |
| Tipuri backend | mypy | 2.4.1 | Mod strict; Rasterio și jsonschema nu publică adnotări de tip |
| Contracte | Pydantic | 2.14.3 | Din E02; mod strict, câmpuri necunoscute respinse |
| Validarea schemelor (teste) | jsonschema | 4.26.0 | Din E02; Draft 2020-12 |
| Tipuri TS generate | json-schema-to-typescript | 16.0.0 | Din E02; folosește Prettier-ul existent |
| Runtime frontend | Node.js | 26 LTS (local 26.13.1) | Fixat în `frontend/.nvmrc`; LTS din 2026-10-28 |
| Manager frontend | npm | 11.20.0 (local) | Lockfile v3 |
| Interfață | React, React DOM | 19.3.1 | — |
| Limbaj | TypeScript | 7.0.2 | Versiunea din șablonul oficial Vite |
| Build | Vite | 8.3.8 | Cu `@vitejs/plugin-react` 6.3.0 |
| Lint frontend | oxlint | 1.93.0 | Linterul șablonului oficial; avertismentele opresc rularea |
| Format frontend | Prettier | 3.10.1 | — |
| Teste frontend | Vitest 5.1.0, jsdom 31.0.1, Testing Library (React 16.3.3, DOM 10.4.2) | — | — |

Toate pachetele backend s-au instalat din wheels (`--only-binary=:all:`) pe Windows, Python 3.13.

**Observate, încă neinstalate** (se fixează în etapa indicată, după o nouă verificare)

| Componentă | Alegere | Versiune observată | Cerințe observate | Etapă |
|---|---|---|---|---|
| API | FastAPI | 0.162.7 | Python ≥ 3.11, Pydantic ≥ 2.9 (fixat deja la 2.14.3) | E06 |
| Hartă 3D | Three.js | 0.187.0 | — | E07 |
| Hartă 2D | OpenLayers (`ol`) | 10.11.0 | Proiecții proprii prin `proj4` ≥ 2.8 și `ol/proj/proj4.register` | E11 |
| Grafice | Plotly (`plotly.js-dist-min`) | 4.3.0 | Pachet de aproximativ 6,2 MB nearhivat | E10 |

Neverificate încă: Pydantic, Uvicorn, Playwright, proj4.

Mediul local observat: Git 2.56 cu Git LFS 3.8.1. Lipsesc utilitarele GDAL în linie de comandă, Conda,
Docker și GitHub CLI; niciunul nu este necesar până la E16.

### Decizii tehnice

| Decizie | Alegere | Motiv |
|---|---|---|
| Integrarea Three.js | Three.js direct, într-un controler de scenă imperativ, învelit de o componentă React subțire | Control explicit asupra încărcării și eliberării resurselor GPU; testabil fără React. `@react-three/fiber` 9.8.2 este compatibil (React ≥ 19 < 19.4, three ≥ 0.156), dar nu este necesar |
| Procesarea rasterelor | Rasterio ca interfață unică către GDAL | Pachetele Rasterio includ biblioteca GDAL; utilitarele GDAL în linie de comandă nu sunt instalate local. Vezi §7 |
| Vedere locală a cerului | SVG | Puține elemente, accesibil, ușor de testat |
| Cache | Fișiere pe disc, cheie SHA-256 | Fără serviciu suplimentar; SQLite rămâne opțiune pentru evidența simulărilor |
| Export | Generat în frontend din obiectul rezultat | Aceeași cale de cod online și offline |
| Gestionarea pachetelor | `venv` + `pip` cu versiuni fixate; `npm` cu `package-lock.json` | Unelte deja prezente; fără instalări suplimentare |
| Lockfile backend | `constraints.txt` generat cu `pip freeze`, folosit cu `-c` | `pip lock` (pylock.toml) este experimental și valid numai pentru platforma pe care a fost generat; constrângerile sunt portabile între Windows și Linux. Nu conțin hash-uri |
| Lint frontend | oxlint în loc de ESLint (abatere de la planul E00) | Este linterul șablonului oficial Vite actual; un al doilea linter ar dubla rolul |

**[ECHIPĂ] D-16.** Specificația propune Plotly. Dimensiunea pachetului contează pentru încărcare și pentru
scenariul offline. Propunere: Plotly, încărcat la cerere; dacă bugetul de performanță nu se respectă, se alege o bibliotecă mai mică.

## 3. Moduri de funcționare

Sunt două axe independente. Proveniența fiecărui rezultat le declară pe amândouă.

**Axa sursei rezultatului**

| Mod | Ce face | Limite |
|---|---|---|
| `live` | Backendul calculează la cerere, cu SPICE și DEM-ul de calcul | Cere backendul pornit, kernelurile și rasterele locale. Durata depinde de calculul orizontului. Acoperire limitată la DEM-urile și efemeridele încărcate. Limitele de interval și de pas sunt în D-20 |
| `precomputed` | Frontendul citește rezultate statice produse în avans de același motor | Funcționează fără backend și fără rețea. Disponibile sunt numai combinațiile declarate de situri, intervale și parametri. Orice altă combinație afișează starea „neprecalculat” și nu aproximează |

**Axa terenului**

| Mod | Ce face | Limite |
|---|---|---|
| `dem` | Orizont calculat din relieful LOLA | Numai în zonele acoperite; calitatea depinde de produs, de `d_max` și de datele lipsă |
| `idealized_local_plane` | Orizont la 0° pentru orice azimut | Nu conține relief. Mesaj permanent în interfață. Nu contează drept integrare LOLA și nu satisface cerința de teren 3D real |

Combinații: `live + dem` este modul complet; `live + idealized` servește punctelor din afara acoperirii DEM;
`precomputed + dem` este demonstrația offline; `precomputed + idealized` este permis și etichetat.

Trecerea în modul precalculat este explicită: dacă `GET /api/health` eșuează, aplicația afișează un banner
și restrânge selecția la scenariile din index. Nu comută pe ascuns.

## 4. Backend

Un singur pachet Python, `backend/lunarhorizon/`. Dependențele merg într-un singur sens: `api → simulation → (astro, terrain, visibility) → contracts → core`.

| Modul | Responsabilitate |
|---|---|
| `core` | Unități, convenții, timp UTC, validarea și normalizarea coordonatelor, cadrul local, proiecția stereografică, identificatorii de cadru, codurile de eroare, vectorii de test comuni (implementat la E02) |
| `contracts` | Modelele Pydantic ale tuturor documentelor, exportul schemei JSON comune (implementat la E02) |
| `catalog` | Cititorul catalogului de situri (`load_catalog`, `get_site`, `planned_target_of`); validarea structurală este în `contracts/catalog.py` (implementat la E04). Verificarea la surse: `scripts/verify_catalog_sources.py` |
| `astro` | Încărcarea și verificarea profilului de kerneluri, acoperire temporală, UTC ↔ ET, vectori și az/el pentru Soare și Pământ, distanțe, raze unghiulare, comparația cu referințele Horizons (implementat la E03; apelurile SPICE trec prin `SPICE_LOCK`) |
| `terrain` | Registrul produselor DEM (din manifeste), eșantionare, acoperire, profilul orizontului, manifestul de teren vizual |
| `visibility` | Criterii, detectarea și rafinarea evenimentelor, indicatori |
| `simulation` | Orchestrare, evidența simulărilor, cache, construirea răspunsului și a provenienței |
| `api` | Rutere FastAPI, scheme Pydantic, maparea erorilor |

Reguli:

- **SPICE nu este sigur pentru fire de execuție.** Toate apelurile SpiceyPy trec printr-un singur executor
  dedicat. Kernelurile se încarcă o dată, la pornire; lipsa unui fișier oprește pornirea cu un mesaj clar.
- **Simulările sunt asincrone.** `POST /api/simulations` întoarce un identificator; rezultatul se citește cu
  `GET /api/simulations/{id}`. O cerere identică întoarce simularea existentă.
- **Două niveluri de cache.** Profilul orizontului depinde numai de poziție, de înălțimea observatorului, de
  produsele DEM și de parametrii algoritmului, deci se păstrează separat și se refolosește la schimbarea intervalului.
  Rezultatul complet al simulării are cheie proprie.
- **Cheia de cache** este SHA-256 peste JSON-ul canonic al: coordonatelor efectiv calculate, înălțimii
  observatorului, intervalului, criteriilor, modului de teren, profilului de kerneluri, identificatorilor și
  sumelor de control ale produselor DEM și versiunilor algoritmilor. Dacă se aplică o rotunjire spațială,
  răspunsul conține coordonatele rotunjite, efectiv folosite.
- Backendul rulează ca un singur proces. Aceasta este o limită acceptată pentru demonstrație, nu o soluție de scalare.

## 5. Frontend

| Zonă | Conținut |
|---|---|
| `app/` | Ecranul principal (patru zone), ecranul de comparație, comutarea 3D/2D și simplu/expert |
| `state/` | Starea comună: selecție, sit activ, moment curent, interval, parametri, starea cererilor |
| `data/` | Interfața `DataSource` cu implementările `ApiDataSource` și `StaticDataSource` |
| `contracts/` | Tipurile contractului, generate din schema comună (`generated.ts`, din E02) |
| `geo/` | UTC, coordonate, cadrul local, proiecția și transformările către scenele 3D, verificate pe aceiași vectori de test ca backendul (din E02) |
| `map3d/` | Controlerul de scenă: glob, teren local, marcaje, camere, raycasting, direcții Soare/Pământ, resurse GPU |
| `map2d/` | Harta OpenLayers polară și globală, proiecții lunare înregistrate prin proj4 |
| `sky/`, `charts/` | Vederea locală a cerului; graficele de elevație, benzile, profilul orizontului |
| `compare/` | Coloanele de comparație |
| `export/` | CSV și JSON |
| `i18n/` | Texte în română (implicit) și engleză, prin chei |

Reguli:

- **Sliderul temporal nu declanșează cereri.** Momentul curent se interpolează în seria deja încărcată; evenimentele vin separat și nu se interpolează.
- **Cererile depășite se anulează** (`AbortController`) sau se ignoră după un număr de secvență. Un rezultat vechi nu înlocuiește selecția nouă.
- **Calculul pornește după confirmarea selecției** sau după o scurtă pauză, nu la fiecare mișcare.
- **Camera nu face parte din starea fizică.** Rotirea, zoomul și exagerarea verticală nu ating timpul, selecția sau rezultatele.
- **Aceleași identificatoare și culori** pentru situri în 3D, 2D și comparație, atribuite în starea comună.
- **Mesajele din specificație date în engleză** („Currently hidden”, „Local terrain not included” etc.) devin chei de text cu traducere în română. **[ECHIPĂ] D-17** confirmă formulările.

## 6. Harta 3D

O singură instanță de renderer WebGL și două scene, fiecare cu sistemul ei de coordonate ([SPEC_FIZICA.md](SPEC_FIZICA.md) §10.1).

| | Scena globală | Scena locală |
|---|---|---|
| Conținut | Glob lunar texturat, grilă de coordonate, marcaje, conturul acoperirii DEM | Mesh de teren din DEM real, observator, direcții Soare/Pământ, zone `NoData` |
| Unități | kilometri, centrul Lunii în origine | metri, origine locală pe teren |
| Camere | Orbitare în jurul globului; orientare inițială spre polul sud | Perspectivă oblică, vedere de sus, vedere de la observator |
| Selecție | Raycasting pe sferă → punct pe suprafața de referință | Raycasting pe mesh → latitudine și longitudine |

- **Globul** are geometrie sferică și textură. Nivelul lui de detaliu este etichetat în interfață. Globul singur nu îndeplinește cerința 3D; relieful local este obligatoriu.
- **„Mergi la sit”** animă camera globală spre sit și trece în scena locală când există teren pentru acel sit. Fără teren, rămâne pe glob și afișează starea „fără date de relief”.
- **Terenul local** vine ca hartă de înălțimi pe niveluri de detaliu, descrisă de manifest. Vârfurile se calculează în browser cu transformarea documentată. Pixelii `NoData` rămân goluri vizibile, marcate; nu se completează.
- **Clic sau rotire:** selecția se face numai dacă indicatorul s-a deplasat sub un prag mic între apăsare și eliberare.
- **Iluminarea** este o lumină direcțională orientată după vectorul solar din rezultat. Umbrele sunt aproximative și etichetate. Indicatorul vizibil/ascuns citește rezultatul numeric.
- **Exagerarea verticală** este 1× implicit, se aplică numai grupului de teren și se afișează permanent când diferă de 1×.
- **Resurse GPU:** la schimbarea sitului se eliberează explicit geometriile, materialele și texturile scenei locale. Un test verifică numărul de resurse raportat de renderer.
- **Fără WebGL suficient:** aplicația pornește în 2D și explică indisponibilitatea 3D.
- **Comparație:** o singură scenă 3D urmărește situl activ, lângă cele 2–4 coloane.

Bugetul de vârfuri, numărul de niveluri de detaliu și întinderea decupajului vizual sunt parametri de reglat la etapa E08, pe dispozitivele echipei.

## 7. Datele de teren și uneltele GDAL

Fluxul complet este în [DATA_PLAN.md](DATA_PLAN.md). Operațiile necesare și unealta propusă:

| Operație | Cu Rasterio | Echivalent GDAL în linie de comandă |
|---|---|---|
| Inspecția metadatelor (CRS, rezoluție, `NoData`, blocuri) | `rio info` | `gdalinfo` |
| Decupaj pe o fereastră | citire pe fereastră, `rio clip` | `gdal_translate -projwin` |
| Conversie din JPEG 2000 și scriere optimizată pentru citire pe ferestre | driverul COG, dacă este prezent în pachet | `gdal_translate -of COG` |
| Reeșantionare pentru niveluri de detaliu | `rasterio.warp`, medii pe blocuri | `gdalwarp`, `gdaladdo` |
| Transformări de coordonate | `rasterio.warp.transform` (PROJ) | `gdaltransform` |

**Verificat la E01:** wheel-ul Rasterio 1.5.2 pentru Windows include GDAL 3.12.2 și PROJ 9.7.1, cu driverele
`GTiff`, `COG`, `JP2OpenJPEG`, `PDS`, `PDS4` și `ISIS3`. Utilitarele GDAL în linie de comandă nu sunt deci
necesare pentru operațiile din tabel. Testul `test_required_raster_drivers_available` și `scripts/check_env.py`
semnalează dacă un driver obligatoriu dispare la o actualizare.

De verificat la E05: dacă GeoTIFF-ul de 3,3 GB este organizat pe blocuri, ceea ce ar permite citirea de
ferestre la distanță fără descărcarea întregului fișier.

## 8. Gestionarea erorilor

- Erorile API folosesc `application/problem+json`, cu un câmp `code` stabil ([API.md](API.md) §6).
- Trei stări diferite nu se confundă niciodată: valoare zero, valoare necunoscută (`null` cu motiv în `quality`) și funcție necalculată (stare explicită).
- Fiecare vedere are stări vizibile pentru încărcare, eroare și lipsa datelor. O eroare într-o vedere nu blochează celelalte vederi.
- O resursă externă inaccesibilă (descărcare de date, Horizons) produce o eroare explicită în script și un blocaj consemnat în [STATUS.md](STATUS.md). Aplicația nu apelează servicii externe în timpul rulării.

## 9. Proveniență

Fiecare rezultat conține: profilul de kerneluri cu numele și sumele de control ale fișierelor, cadrul explicit,
corecțiile aplicate, produsele DEM cu identificator, URL, rezoluție și sumă de control, parametrii
algoritmului de orizont, criteriile de vizibilitate, versiunea aplicației și data calculului. Modul simplu arată
sursa principală și rezumatul limitelor; modul expert arată tot.

## 10. Offline

- Un scenariu precalculat este un director în `data/precomputed/`, cu un index, rezultatul simulării în exact
  schema API și resursele de teren pentru siturile lui.
- Scriptul de precalculare rulează același motor ca backendul. Nu există o a doua implementare a calculelor.
- La build, scenariile, texturile și hărțile de înălțimi sunt copiate în aplicația statică. Bibliotecile și fonturile sunt incluse local; nu se folosește niciun CDN.
- Indexul scenariilor spune explicit ce situri, intervale și parametri sunt disponibile. Interfața arată această listă în modul offline.

## 11. Deployment

| Țintă | Conținut | Observații |
|---|---|---|
| Demonstrație statică | Frontendul construit și scenariile precalculate | Orice găzduire de fișiere statice sau un server local; fără backend |
| Aplicație completă | Imagine de container cu backendul, care servește și frontendul; volum pentru kerneluri și rastere | Docker nu este instalat local |

**[ECHIPĂ] D-15.** Furnizorul de găzduire, vizibilitatea repository-ului și crearea remote-ului GitHub sunt
decizii ale echipei. Nimic nu se publică fără confirmare explicită.

## 12. Testare și CI

| Nivel | Unealtă propusă | Ce acoperă |
|---|---|---|
| Unitar backend | Pytest | Coordonate, timp, astronomie, orizont pe teren sintetic, evenimente |
| Referință | Pytest cu marcaj separat | Comparația cu cazurile Horizons salvate; cere kernelurile |
| Unitar frontend | Vitest (jsdom, Testing Library) | Transformări, starea comună, export, sursele de date |
| Interfață | Playwright | Fluxurile principale, sincronizarea 3D/2D, offline |
| Contract | Schemă JSON comună generată din Pydantic; fixture-uri sintetice; tipuri TS generate | Catalog, manifeste, cererea și rezultatul simulării, scenarii precalculate, stare, acoperire, erori |

Fluxul contractelor (din E02): modelele Pydantic → `scripts/generate_contracts.py` →
`data/schemas/lunarhorizon.schema.json` și `tests/vectors/conventions.json` → `npm run contracts:generate` →
`frontend/src/contracts/generated.ts`. Cele trei fișiere generate intră în Git. CI verifică, cu `--check` și
`contracts:check`, că sunt la zi.

CI pe GitHub Actions (`.github/workflows/ci.yml`, din E01) rulează pe Ubuntu și Windows verificările rapide
care nu cer fișiere mari: Ruff, mypy, pytest, verificarea mediului, Prettier, oxlint, TypeScript, Vitest și build.
Din E02, CI verifică și schemele: fixture-urile se validează prin Pydantic și prin JSON Schema în pytest, iar fișierele generate trebuie să fie la zi. Din E03, testele cu kerneluri (marcajul pytest
`kernels`) rulează în jobul separat `astro`: kernelurile oficiale se descarcă la prima rulare, se verifică față
de manifest și se păstrează în cache după hash-ul manifestului. Comparațiile cu Horizons folosesc răspunsurile
arhivate; CI nu interoghează Horizons. În joburile `backend` obișnuite, aceste teste sunt omise automat.
Testele cu rastere DEM se decid la E05. Randarea WebGL în browser fără
interfață grafică este un risc cunoscut pentru testele de interfață și se verifică la E07.
