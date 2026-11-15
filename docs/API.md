# Contracte de date și API

Contractul pentru cerințele din [SPECIFICATIE.md](SPECIFICATIE.md) §13. Convențiile de unități, timp
și cadre sunt în [SPEC_FIZICA.md](SPEC_FIZICA.md).

> **Versiunea de schemă curentă: 0.8.0 (E10, 2026-11-15).** Versiunea inițială, 0.1.0, a fost înghețată la E02.
> Istoric:
> - **0.8.0 (E10)** — `SimulationRequest.solar_criterion = "disc_positive_area"` (D-04; `disc_center` nu mai este
>   acceptat); `BodySeries`: `state`, `state_reason`, `visible_fraction`, `visible_uncertainty_fraction`; `Event`:
>   tipul `tangent_contact`, cauza `elevation_threshold`, `criterion`, `window_start_utc`, `window_end_utc`,
>   `quality`; `SiteSummary`: duratele necunoscute și `sun_timeline` / `earth_timeline` (`StateInterval`), care
>   partiționează intervalul cerut. Modul `dem` calculează vizibilitatea, evenimentele și indicatorii.
> - **0.7.0 (E09)** — document nou `HorizonProfile` (`GET /api/horizon`): `status` (`complete`, `partial`,
>   `unavailable`), `reason_code`, `reason`, `elevation_deg`, `obstacle_distance_m`, `quality` pe azimut,
>   `max_search_distance_m`, `coverage_fraction`, `dem_products` (cu rol, cadru, rezoluție, SHA-256), `parameters`,
>   `parameters_status = provisional`, `cache_key`. Celelalte documente au aceeași structură ca în 0.6.0; în modul
>   `dem`, `SimulationResult` folosește câmpurile existente (`horizon`, `horizon_elevation_deg`, `not_computed`).
> - **0.6.0 (E08b)** — document nou `TerrainStatusReport` (`GET /api/terrain/status`: produse și stări pe situri);
>   `Site.status` acceptă `dem_region` și `Site.mission_status` acceptă `not_applicable` (punct reprezentativ al unei
>   regiuni DEM, fără misiune; validator dedicat). Celelalte documente au aceeași structură ca în 0.5.0.
> - **0.5.0 (E08)** — document nou `TerrainSample` (răspunsul `GET /api/terrain/elevation`): `terrain_id`, `product_id`,
>   `frame_id`, `latitude_deg`, `longitude_deg`, `x_m`, `y_m`, `elevation_m` (`null` dacă și numai dacă `reason =
>   "edge_or_nodata"`), `calc_resolution_m`, `method = "bilinear"`. Celelalte documente au aceeași structură ca în 0.4.0.
> - **0.4.0 (E07)** — `BodySeries.azimuth_deg[]` și `Event.azimuth_deg` acceptă `null` numai la zenit/nadir (azimut
>   nedefinit). Fiecare `null` cere o intrare în `quality.issues` cu același `site_ref` și câmpul
>   `series.<corp>.azimuth_deg`, respectiv `events.<corp>.azimuth_deg` (cod `azimuth_undefined`). Simularea nu mai eșuează
>   în acest caz și azimutul nu este înlocuit cu zero. Celelalte documente au aceeași structură ca în 0.3.0.
> - **0.3.0 (E04)** — `Catalog`/`Site`: câmpuri noi `mission_status`, `related_site_id`, `planned_target_note`,
>   `position_sources[]` (`SourceRecord`: instituție, titlu, URL, identificator, versiune, dată publicată și accesată,
>   locator, starea accesului, coordonate originale, cadru declarat, citat, SHA-256 al fișierului citit),
>   `position_verification` și `adoption_note`; `Catalog.demo_site_selection` (starea D-07). `status=planned` este
>   starea poziției (o țintă planificată), iar `mission_status` este starea misiunii. Validatori noi: coordonatele
>   adoptate = originalul normalizat; incertitudinea = cea publicată; legătura țintă–poziție reciprocă.
>   Celelalte documente au aceeași structură ca în 0.2.0 (numai `schema_version` s-a schimbat).
> - **0.2.0 (E03)** — `KernelManifest`: `KernelFile` primește `md5`, `retrieved_at_utc` (moment UTC complet, în
>   locul datei `accessed_at`) și `expected_checksums` (sume așteptate, cu algoritmul, originea —
>   `published_by_source` sau `prior_independent_download` — și sursa), distincte de sumele calculate după
>   descărcare. `KernelProfile` primește `pa_frame_id` și acoperirea profilului; ordinea fișierelor este ordinea
>   încărcării. Celelalte documente au aceeași structură ca în 0.1.0.
> - **0.1.0 (E02)** — versiunea inițială.
>
> **Versiunea 0.1.0, înghețată la E02 (2026-11-14):**
> Sursa structurii este setul de modele Pydantic din `backend/lunarhorizon/contracts/`. Din ele se
> generează [data/schemas/lunarhorizon.schema.json](../data/schemas/lunarhorizon.schema.json) (JSON Schema
> 2020-12) și `frontend/src/contracts/generated.ts`. Când acest document și schema diferă, schema are
> prioritate, iar documentul se corectează. Orice schimbare de structură crește `schema_version`, regenerează
> ambele fișiere și se consemnează aici.
>
> Regulile dintre câmpuri (de exemplu „`null` cere un motiv”, „grup prezent sau declarat necalculat”) nu pot
> fi exprimate în JSON Schema. Le impun validatorii Pydantic, adică backendul care produce rezultatele.
> Endpointurile sunt implementate la E06 (2026-11-14), inițial cu schema 0.3.0; vezi §8.

Valorile din exemple sunt substituenți (`<...>`), nu rezultate. Exemple complete, sintetice și valide, pentru
fiecare tip de document: [tests/fixtures/contracts/synthetic_valid_documents.json](../tests/fixtures/contracts/synthetic_valid_documents.json).

## 1. Convenții generale

- Prefix `/api`, JSON în UTF-8. La E06, schema OpenAPI a FastAPI (`/api/openapi.json`) se generează din aceleași modele.
- Fiecare câmp numeric poartă unitatea în nume: `_deg`, `_m`, `_km`, `_s`, `_utc`, `_fraction`, `_factor`,
  `_px`, `_bytes`, `_count`. Excepțiile sunt listate și motivate în `backend/tests/test_contracts.py`
  (de exemplu `status` din RFC 9457 și pozițiile GeoJSON). Un test verifică regula pe schema generată.
- Coordonatele se numesc `latitude_deg` și `longitude_deg` în toate documentele.
- Timpul este UTC, ISO 8601, cu `Z`, cu cel mult 3 zecimale (milisecunde). La intrare se acceptă și un offset
  explicit (`+02:00`), convertit în UTC; în documentele validate valoarea apare în forma canonică, cu `Z`.
  Timestampurile fără zonă și secunda intercalară `:60` sunt respinse.
- Longitudinea este pozitivă spre est; răspunsurile o normalizează în [−180, 180).
- Cadrul apare explicit, în `frame_id`, cu numele complet (de exemplu `MOON_ME_DE440_ME421`), niciodată cu aliasul `MOON_ME`.
- Fiecare răspuns de date conține `schema_version`.

### Zero, necunoscut, necalculat

| Situație | Reprezentare |
|---|---|
| Valoare zero reală | `0` |
| Valoare necunoscută sau indisponibilă | `null`, cu o intrare în `quality.issues` care are același `site_ref` și `field` (de exemplu `summary.sun_visible_fraction`) |
| Funcție necalculată sau dezactivată | grupul lipsește pentru acel sit și apare în `quality.not_computed` (`group`, `site_ref`, `reason`); nu poate fi și prezent, și declarat necalculat |
| Fără eveniment în interval | listă goală și `status: "none_in_interval"` |

## 2. Endpointuri

| Endpoint | Rol |
|---|---|
| `GET /api/health` | Disponibilitatea serviciului și starea datelor încărcate |
| `GET /api/sites` | Catalogul siturilor |
| `GET /api/coverage` | Acoperirea temporală (efemeride) și geografică (DEM) |
| `GET /api/terrain/manifest` | Resursele de teren vizual și metadatele pentru o zonă |
| `POST /api/simulations` | Pornește sau regăsește o simulare |
| `GET /api/simulations/{id}` | Starea și rezultatul unei simulări |

Fișierele de teren vizual și texturile se servesc static, de la căile indicate în manifest. Exportul se
generează în frontend (§7), deci nu are endpoint.

### 2.1. `GET /api/health`

```json
{
  "status": "ok",
  "app_version": "<versiune>",
  "kernel_profile": "<id profil>",
  "kernels_loaded": true,
  "dem_products": ["<id produs>"],
  "time_utc": "<moment>"
}
```

`status` poate fi `ok` sau `degraded` (serviciul răspunde, dar lipsesc date; motivul apare în `issues`).

### 2.2. `GET /api/sites`

Întoarce `{ "schema_version", "catalog_version", "sites": [Site] }`. Câmpurile unui `Site` sunt cele din
[SPECIFICATIE.md](SPECIFICATIE.md) §6.1, plus:

| Câmp | Tip | Observații |
|---|---|---|
| `elevation_m` | număr sau `null` | Cu `elevation_reference` obligatoriu când este prezent |
| `position_kind` | `actual`, `planned_target`, `representative_point` | Ținta planificată și poziția efectivă sunt intrări distincte |
| `region` | GeoJSON sau `null` | Poligonul regiunii candidate, în aceleași convenții de coordonate |
| `landing_date_utc` | text sau `null` | Data istorică; nu este începutul simulării |
| `terrain_available` | boolean | Există teren local pentru acest sit |
| `mission_status` | `landed`, `impacted`, `not_landed`, `planned`, `unknown` | Starea misiunii, separată de `status` |
| `related_site_id` | identificator sau `null` | Țintă planificată ↔ poziție efectivă (reciproc) |
| `planned_target_note` | text sau `null` | Ținta ca regiune numită, fără coordonate numerice |
| `position_sources[]` | listă de `SourceRecord` | Documentele consultate; cel puțin una de poziție |
| `position_verification` | `verified_at_original`, `incomplete`, `conflict_open` | Starea verificării la sursă |
| `adoption_note` | text | Valoarea adoptată, normalizările și ipotezele de cadru |

Un câmp necunoscut este `null`; interfața explică lipsa.

### 2.3. `GET /api/coverage`

```json
{
  "schema_version": "<v>",
  "temporal": { "start_utc": "<moment>", "end_utc": "<moment>", "kernel_profile": "<id>" },
  "terrain": [
    {
      "product_id": "<id>",
      "role": "near | far",
      "resolution_m": "<număr>",
      "footprint": { "type": "Polygon", "coordinates": "<lon, lat>" },
      "min_latitude_deg": "<număr>", "max_latitude_deg": "<număr>"
    }
  ]
}
```

Acoperirea temporală este intersecția acoperirilor efemeridelor și ale kernelului de orientare. Conturul
acoperirii DEM este desenat de ambele hărți din acest răspuns.

### 2.4. `GET /api/terrain/manifest`

Parametri: `site_id`, sau perechea `latitude_deg` și `longitude_deg`. Parametrii sunt validați; un punct fără teren
întoarce `404` cu `code: "OUT_OF_DEM_COVERAGE"`.

```json
{
  "schema_version": "<v>",
  "terrain_id": "<id>",
  "source": { "product_id": "<id>", "url": "<url>", "sha256": "<sumă>", "citation": "<text>" },
  "frame_id": "<cadru explicit>",
  "crs": { "proj4": "<definiție>", "wkt": "<definiție>" },
  "reference_radius_m": "<număr>",
  "vertical": { "units": "m", "reference": "<descriere>", "exaggeration_default_factor": 1 },
  "calc_resolution_m": "<număr>",
  "local_origin": { "latitude_deg": "<număr>", "longitude_deg": "<număr>", "elevation_m": "<număr>" },
  "bounds": { "x_min_m": "<număr>", "x_max_m": "<număr>", "y_min_m": "<număr>", "y_max_m": "<număr>" },
  "nodata": { "present": "<boolean>", "encoding": "<descriere>", "area_fraction": "<număr sau null>" },
  "interpolated_pixels": { "flagged": "<boolean>", "note": "<text>" },
  "lods": [
    {
      "level": 0,
      "visual_resolution_m": "<număr>",
      "width_px": "<întreg>", "height_px": "<întreg>",
      "heights_path": "<cale relativă, fără ..>",
      "encoding": "<format și tip numeric>",
      "sha256": "<sumă>"
    }
  ]
}
```

`calc_resolution_m` și `visual_resolution_m` sunt întotdeauna câmpuri distincte. Formatul fișierelor de
înălțimi se fixează la E05.

### 2.5. `POST /api/simulations`

```json
{
  "sites": [
    { "site_id": "<id din catalog>" },
    { "custom": { "label": "<text>", "latitude_deg": "<număr>", "longitude_deg": "<număr în [-180, 360)>" } }
  ],
  "frame_id": "<cadru explicit>",
  "start_utc": "<moment>",
  "end_utc": "<moment>",
  "observer_height_m": "<număr>",
  "solar_criterion": "disc_center",
  "earth_criterion": { "kind": "center_above_horizon", "min_elevation_deg": "<număr>" },
  "terrain_mode": "dem | idealized_local_plane",
  "series_step_s": "<întreg, opțional>",
  "panel": null
}
```

Validare: 1–4 situri; `end_utc` după `start_utc`; durata sub limita configurată (D-20); latitudine în [−90, 90];
`observer_height_m` nenegativ; `frame_id` printre cadrele acceptate. `panel` este rezervat bonusului de putere relativă.

Răspuns `202` (simulare nouă) sau `200` (simulare existentă, aceeași cheie):

```json
{ "id": "<id>", "status": "queued | running | done | failed", "cache_hit": "<boolean>" }
```

`terrain_mode: "dem"` pentru un sit fără acoperire produce eroarea `OUT_OF_DEM_COVERAGE`. Backendul nu
trece singur în modul idealizat; alegerea rămâne a utilizatorului.

### 2.6. `GET /api/simulations/{id}`

Cât timp simularea rulează: `{ "id", "status", "progress": { "stage", "completed_fraction" }, "error": null, "result": null }`.
`result` există dacă și numai dacă `status` este `done`; `error` dacă și numai dacă `status` este `failed`.
La eșec: `status: "failed"` și un obiect de eroare (§6). La final: `status: "done"` și `result` (§3).

## 3. Rezultatul simulării

Aceeași schemă este folosită de API și de fișierele precalculate.

```json
{
  "schema_version": "<v>",
  "request": { "...": "cererea, cu valorile efectiv folosite" },
  "sites": [],
  "series": [],
  "events": [],
  "summary": [],
  "horizon": [],
  "terrain": [],
  "provenance": {},
  "quality": {}
}
```

Grupurile `series`, `events`, `summary`, `horizon` și `terrain` au câte o intrare pentru fiecare sit, identificată prin `site_ref`.

### 3.1. `sites`

`site_ref`, `label`, `kind` (`catalog` sau `custom`), `catalog_id` (obligatoriu numai pentru `catalog`),
`latitude_deg`, `longitude_deg`, `frame_id`, `terrain_elevation_m`
(sau `null`), `observer_height_m`, `on_reference_surface`, `azimuth_convention` (`standard` sau `pole_meridian`),
`coordinates_rounded` (boolean; dacă este adevărat, coordonatele sunt cele rotunjite, efectiv calculate).

### 3.2. `series`

Tablouri paralele, pentru transfer compact:

| Câmp | Conținut |
|---|---|
| `step_s`, `time_utc[]` | Pasul și momentele seriei |
| `sun.azimuth_deg[]`, `sun.elevation_deg[]`, `sun.distance_km[]`, `sun.angular_radius_deg[]` | Soare |
| `earth.*` | Aceleași câmpuri pentru Pământ |
| `sun.horizon_elevation_deg[]`, `earth.horizon_elevation_deg[]` | `H(a)` la azimutul corpului |
| `sun.visible[]`, `earth.visible[]` | `true`, `false` sau `null` |

Seria este destinată afișării. Evenimentele și duratele nu se deduc din ea.

### 3.3. `events`

Pentru fiecare corp: `status` (`found`, `none_in_interval`, `unavailable`), motivul când este `unavailable`, și lista:

```json
{
  "body": "sun | earth",
  "type": "appearance | disappearance",
  "cause": "terrain | idealized_horizon",
  "time_utc": "<moment>",
  "azimuth_deg": "<număr>",
  "elevation_deg": "<număr>",
  "obstacle_distance_m": "<număr sau null>",
  "refinement_tolerance_s": "<număr>"
}
```

Tipul `eclipse` (P1) are câmpuri proprii și se adaugă odată cu bonusul.

### 3.4. `summary`

`sun_visible_duration_s`, `sun_visible_fraction`, `earth_visible_duration_s`, `both_visible_duration_s`,
`sun_intervals[]` și `earth_windows[]` (fiecare cu `start_utc`, `end_utc`, `truncated_start`, `truncated_end`).

„Timpul până la următoarea tranziție” se calculează în frontend din `events` și din momentul curent, deci urmează sliderul fără cereri noi.

### 3.5. `horizon`

`mode` (`dem` sau `idealized_local_plane`), `azimuth_step_deg`, `elevation_deg[]`, `obstacle_distance_m[]`,
`quality[]` (`complete`, `partial`, `no_data`), `max_search_distance_m`, `coverage_fraction` și produsele DEM folosite pe fiecare nivel.

### 3.6. `terrain`

Referința la manifestul de teren (`terrain_id`), produsul DEM, `calc_resolution_m`, rezoluțiile vizuale
disponibile, acoperirea, cadrul, unitățile, originea locală și limitele. Pentru modul idealizat sau pentru
situri fără teren: `available: false`, cu motiv.

### 3.7. `provenance`

`app_version`, `computed_at_utc`, `source_mode` (`live` sau `precomputed`), profilul de kerneluri cu fișiere
și sume de control, `frame_id`, corecția de aberație, razele corpurilor folosite, produsele DEM, parametrii
algoritmului de orizont și de detectare a evenimentelor, criteriile.

### 3.8. `quality`

`issues[]` (fiecare cu `code`, `severity`, `site_ref`, `field`, `message_key`), `not_computed[]` (fiecare cu
`group`, `site_ref`, `reason`), `approximations[]`
(de exemplu criteriul centrului discului, umbre vizuale aproximative) și `limits[]`.

## 4. Catalogul și manifestele ca fișiere

Catalogul (`data/catalog/`), manifestele (`data/manifests/`) și scenariile (`data/precomputed/`) au scheme JSON
în repository, validate în CI. Structura lor este descrisă în [DATA_PLAN.md](DATA_PLAN.md).

## 5. Sursa de date offline

Indexul scenariilor precalculate:

```json
{
  "schema_version": "<v>",
  "scenarios": [
    {
      "scenario_id": "<id>",
      "title_ro": "<text>", "title_en": "<text>",
      "site_ids": ["<site_id>"],
      "start_utc": "<moment>", "end_utc": "<moment>",
      "request": { "...": "cererea de simulare exactă (SimulationRequest)" },
      "result_path": "<cale relativă>",
      "terrain_manifest_paths": ["<cale relativă>"],
      "result_sha256": "<sumă>"
    }
  ]
}
```

`StaticDataSource` potrivește exact cererea cu un scenariu. Fără potrivire, întoarce eroarea
`PRECOMPUTED_NOT_AVAILABLE`, iar interfața arată combinațiile disponibile.

## 6. Erori

Format `application/problem+json`: `type`, `title`, `status`, `detail`, `code`, plus câmpuri specifice.

| `code` | HTTP | Când |
|---|---|---|
| `VALIDATION_ERROR` | 422 | Câmp lipsă, tip greșit, coordonate sau timp invalid |
| `TOO_MANY_SITES` | 422 | Mai mult de patru situri |
| `INTERVAL_TOO_LONG` | 422 | Durata depășește limita configurată |
| `UNSUPPORTED_FRAME` | 422 | Cadru neacceptat |
| `OUT_OF_EPHEMERIS_COVERAGE` | 422 | Interval în afara acoperirii; răspunsul conține limitele reale |
| `OUT_OF_DEM_COVERAGE` | 404 sau 422 | Punct fără teren, cu modul `dem` cerut |
| `SIMULATION_NOT_FOUND` | 404 | Identificator necunoscut |
| `KERNEL_MISSING` | 503 | Kerneluri neîncărcate |
| `TERRAIN_DATA_MISSING` | 503 | Rasterul de calcul lipsește de pe disc |
| `PRECOMPUTED_NOT_AVAILABLE` | — | Numai în sursa statică: combinație neprecalculată |
| `INTERNAL_ERROR` | 500 | Orice altceva; fără detalii interne în răspuns |

Datele parțiale nu sunt erori: un profil de orizont incomplet întoarce rezultatul, cu `quality.issues`.

## 7. Export

Exportul se generează în frontend din rezultatul încărcat și funcționează identic online și offline.

- **CSV** — seriile numerice, câte un fișier per sit. Antetul coloanelor include unitățile
  (`time_utc`, `sun_azimuth_deg`, …). Primele linii, comentate, conțin identificatorul simulării, cadrul și versiunea schemei.
- **JSON** — configurația completă și metadatele: `request`, `sites`, `events`, `summary`, `horizon`, `provenance`, `quality`.

Identificatorii tehnici din export nu se traduc.

## 8. Implementarea E06 (2026-11-14)

Aplicația este `lunarhorizon.api.app:app` (FastAPI 0.162.7, Uvicorn 0.54.0); schema OpenAPI este la
`/api/openapi.json`, documentația la `/api/docs`. Toate endpointurile din §2 există. Precizări față de specificația
inițială:

- **Numai modul idealizat este calculat.** Rezultatul declară `horizon[].mode = "idealized_local_plane"`,
  `terrain[].available = false` cu motiv și `quality.approximations` care spune explicit că relieful local nu este
  inclus. Observatorul este pe sfera de referință (`on_reference_surface = true`); `sites.terrain_elevation_m` este
  `null` cu o intrare în `quality.issues` (`terrain_elevation_not_used`); elevația din catalog nu se folosește.
- **`terrain_mode = "dem"` este refuzat** cu `OUT_OF_DEM_COVERAGE` (422) pentru orice sit, deoarece calculul
  orizontului din DEM (E09) nu există și acoperirea nu este validată. Serviciul nu trece niciodată singur în modul
  idealizat.
- **Cadre.** `frame_id` selectează profilul de kerneluri (`MOON_ME_DE440_ME421` → `de440_me421`, `MOON_ME_DE421` →
  `de421`). Un sit din catalog cu alt cadru decât cel cerut este refuzat cu `UNSUPPORTED_FRAME` (nu se convertește).
  Punctele `custom` sunt interpretate în cadrul cererii. Aliasurile `MOON_ME`, `MOON_PA`, `IAU_MOON` sunt respinse
  la validare (`UNSUPPORTED_FRAME`).
- **Identificator și cache.** `id = "sim-" + primele 32 de caractere SHA-256` ale cererii canonice, după completarea
  `series_step_s` (implicit: primul pas dintre 60, 300, 600, 900, 1800, 3600, 7200, 21600, 43200, 86400 s care dă cel
  mult 1500 de puncte). Aceeași cerere → același `id`; `200` cu `cache_hit: true` pentru o simulare existentă și
  neeșuată, `202` pentru una nouă. Cache-ul este în memorie, limitat la `cache_size = 64` simulări terminate.
- **Validări sincrone** (înainte de a crea simularea): structură Pydantic (`VALIDATION_ERROR`, `TOO_MANY_SITES`,
  `UNSUPPORTED_FRAME` numai pentru valoare de cadru invalidă), durata maximă 366 de zile (`INTERVAL_TOO_LONG`, D-20
  provizoriu), cel mult 20.000 de puncte de serie, `site_id` necunoscut sau repetat (`VALIDATION_ERROR`), încărcarea
  kernelurilor (`KERNEL_MISSING`, 503) și acoperirea efemeridelor (`OUT_OF_EPHEMERIS_COVERAGE`, 422, cu limitele
  profilului; motorul aplică și marja de 600 s a corecției de timp de lumină).
- **Evenimente și rezumat (idealizat).** Soarele este vizibil la elevația centrului ≥ 0°; Pământul la elevația centrului
  ≥ `earth_criterion.min_elevation_deg`. Grila de scanare are pasul ≥ 900 s (mărit pentru intervale lungi, cel mult
  20.000 de puncte); fiecare trecere se rafinează prin bisecție la 1 ms (`refinement_tolerance_s = 0.001`).
  Intervalele deschise la capete au `truncated_start`/`truncated_end`. Seria folosește aceleași funcții de vizibilitate.
- **Azimut nedefinit** (zenit/nadir): din schema 0.4.0 azimutul este `null` cu motiv în `quality.issues`
  (`azimuth_undefined`); simularea continuă.
- **`GET /api/coverage`** primește opțional `frame_id` (implicit cadrul profilului implicit). Lista `terrain` conține
  numai produsele al căror raster de calcul există pe disc; conturul este dreptunghiul rasterului, nu acoperirea
  orizontului. **`GET /api/terrain/manifest`** întoarce manifestul de teren al rasterului care conține punctul
  (`site_id` sau `latitude_deg` + `longitude_deg`); în afara lui `404` cu `OUT_OF_DEM_COVERAGE`, iar fără raster pe disc
  `503` cu `TERRAIN_DATA_MISSING`. Fișierele de teren vizual nu se servesc static la E06.
- **Erori** au tipul de conținut `application/problem+json`; `type` este `urn:lunarhorizon:problem:<cod>`. Erorile
  neașteptate nu expun detalii interne. Rutele inexistente folosesc răspunsul implicit Starlette.
- CORS permite numai originile serverului Vite local (`localhost:5173`, `127.0.0.1:5173`).

## 9. Completări E07 (2026-11-14)

- **`GET /api/assets/{name}`** servește fundalurile E05 (în prezent `globe.jpg`, textura NASA SVS 2K) din
  `data/_cache/e05_auxiliary/`, numai dacă numele figurează în `data/manifests/e05_auxiliary.json` și SHA-256 corespunde;
  altfel `TERRAIN_DATA_MISSING` (503) sau `VALIDATION_ERROR` (422) pentru un nume nelistat. Textura este produs estetic,
  nu date științifice și nu DEM.
- În dezvoltare, frontendul accesează API-ul prin proxy-ul Vite (`/api` → `http://127.0.0.1:8000`), deci CORS nu este
  necesar pentru serverul de dezvoltare.
- Interfața afișează mesaje în engleză după `code`; câmpul `detail` (scris pentru dezvoltatori) nu este afișat.
- Catalogul (`catalog_version` `e07-2026-11-14-english-names`): câmpul `name` și adnotările proiectului din
  `position_sources[].institution`/titlul paginii Chang'e 4 au formulare în engleză; pozițiile, sursele și titlurile
  originale nu s-au schimbat.

## 10. Completări E08 — teren local (2026-11-15)

- **`GET /api/terrain/elevation?terrain_id=&latitude_deg=&longitude_deg=`** → `TerrainSample`. Înălțimea terenului
  față de sfera produsului, interpolată biliniar din **rasterul de calcul** (5 m/pixel), pentru observatorul scenei locale.
  La margine sau în `NoData`: `elevation_m = null`, `reason = "edge_or_nodata"` (niciodată 0). Punct în afara rasterului:
  `404 OUT_OF_DEM_COVERAGE`; `terrain_id` necunoscut sau invalid: `422 VALIDATION_ERROR`.
- **`GET /api/terrain/{terrain_id}/lods/{level}`** → `application/octet-stream`: înălțimile nivelului vizual ca float32
  little-endian, rânduri nord → sud, coloane vest → est, `NaN` = NoData; antete `X-Width`, `X-Height`, `X-Lod-Level`.
  Se servesc numai nivelurile listate în manifest; calea `heights_path` (fără `..`, după contract) se rezolvă în dosarul
  produsului și trebuie să rămână în el; SHA-256 trebuie să fie cel din manifest, iar dimensiunile și georeferențierea
  GeoTIFF-ului trebuie să corespundă manifestului (altfel `503 TERRAIN_DATA_MISSING`). Nivel necunoscut: `422`.
- Interfața folosește nivelul 0 (40 m/pixel) pentru mesh; rasterul de calcul (5 m) numai pentru altitudinea
  observatorului. Rezoluțiile sunt declarate separat (`calc_resolution_m`, `visual_resolution_m`).
- **Cadre.** Manifestul de teren declară `MOON_ME_DE421` (ipoteză de lucru). Punctul reprezentativ DEM folosește în cerere
  cadrul declarat de produs (coordonatele vin din DEM); un punct al utilizatorului se reinterpretează în acest cadru numai
  la cererea explicită, cu mențiunea că nu se face conversie; pozițiile din catalog nu se reinterpretează (revizia E08b); direcțiile Soare/Pământ
  se desenează pe teren numai dacă rezultatul are același `frame_id` ca terenul. Nicio conversie între cadre.

## 11. Completări E08b — mai multe regiuni (2026-11-15)

- **`GET /api/terrain/status`** → `TerrainStatusReport`: fiecare produs al indexului (`available` / `not_downloaded`)
  și starea terenului pentru fiecare sit din catalog (`terrain_available`, `terrain_not_downloaded`,
  `coverage_unverified`, `no_dem_coverage`, `frame_mismatch`), cu regula polară și regula de selecție.
- **`GET /api/terrain/manifest`** acceptă exact unul dintre `site_id`, `terrain_id` sau `latitude_deg` + `longitude_deg`,
  plus `frame_id` opțional (implicit cadrul sitului). Selecția urmează regula din [E08B_TERRAIN_REGIONS.md](E08B_TERRAIN_REGIONS.md).
  Răspunsuri: 200 manifest; 503 `TERRAIN_DATA_MISSING` (terrain not downloaded); 422 `UNSUPPORTED_FRAME` (frame
  mismatch); 404 `OUT_OF_DEM_COVERAGE`, cu `detail` care începe cu `coverage_unverified` sau `no_dem_coverage`.

## 12. Completări E09 — orizontul din DEM (2026-11-15)

- `GET /api/horizon?observer_height_m=…&site_id=…` sau `…&latitude_deg=…&longitude_deg=…&frame_id=…` → `HorizonProfile`.
  `observer_height_m` este obligatoriu (fără valoare implicită). Un sit din catalog folosește cadrul în care este
  declarat; alt `frame_id` → 422 `UNSUPPORTED_FRAME`. Un punct cere `frame_id` (422 altfel).
- Datele lipsă dau `200` cu `status = unavailable` și `reason_code` (`frame_mismatch`, `terrain_not_downloaded`,
  `coverage_unverified`, `no_dem_coverage`, `observer_elevation_unknown`), cu tablouri goale. `partial` are
  `reason_code = missing_samples`. Niciun azimut fără date nu devine zero sau orizont liber.
- `POST /api/simulations` cu `terrain_mode = dem`: profilul fiecărui sit se calculează la trimitere; dacă este
  indisponibil, cererea este refuzată (`UNSUPPORTED_FRAME` 422, `TERRAIN_DATA_MISSING` 503, `OUT_OF_DEM_COVERAGE`
  422), fără trecere la modul idealizat. Rezultatul are `horizon[].mode = dem`, `series.*.horizon_elevation_deg =
  H(a(t))` (interpolare liniară; `null` lângă `no_data`), `visible = null` cu `quality.issues`
  (`visibility_pending_e10`), iar `events` și `summary` în `quality.not_computed` până la E10.
- Parametrii și cheia cache-ului fiecărui profil apar în `provenance.horizon_parameters`.

