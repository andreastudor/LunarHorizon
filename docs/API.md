# Contracte de date și API

Contractul pentru cerințele din [SPECIFICATIE.md](SPECIFICATIE.md) §13. Convențiile de unități, timp
și cadre sunt în [SPEC_FIZICA.md](SPEC_FIZICA.md).

> **Versiunea de schemă curentă: 0.3.0 (E04, 2026-11-14).** Versiunea inițială, 0.1.0, a fost înghețată la E02.
> Istoric:
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
> Endpointurile nu există încă; serverul se implementează la E06.

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
