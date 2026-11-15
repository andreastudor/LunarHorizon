# E09 — orizontul din DEM

Stare 2026-11-15: **implementare tehnică finalizată pentru primul sit (Leibnitz Beta) și pentru celelalte puncte
DEM; D-08 și D-09 [GEO] rămân deschise**, deci parametrii sunt propuneri tehnice, nu valori validate. Criteriul
BACKLOG „D-08 și D-09 sunt închise” nu poate fi îndeplinit fără decizia geografilor. Vizibilitatea față de relief,
evenimentele și indicatorii sunt E10 și nu au fost începute.

## Ce s-a implementat

| Livrabil BACKLOG | Implementare |
|---|---|
| Algoritmul pe două niveluri | `backend/lunarhorizon/terrain/horizon.py` (`compute_horizon`), după SPEC_FIZICA §6.2 |
| Produsul îndepărtat pregătit | `LDEM_75S_120M` (LOLA GDR, PDS3), `scripts/acquire_lola_gdr.py`, `terrain/lola_gdr.py` |
| Cache pentru profil | `backend/lunarhorizon/api/horizon.py`: LRU în memorie + `data/_cache/horizon/<cheie>.json` |
| Modul `dem` în simulări | `api/jobs.py` + `simulation/idealized.py`: `horizon_elevation_deg = H(a(t))`, grupul `horizon` cu `mode = dem` |
| Studiul de convergență | `scripts/horizon_convergence.py` → `data/reference/horizon/e09_convergence.json`; rezumat mai jos și în VALIDARE |
| Graficul profilului | fila „Horizon profile” (`frontend/src/components/HorizonChart.tsx`) |
| API | `GET /api/horizon` → document `HorizonProfile` (schema **0.7.0**) |

## Algoritmul (SPEC_FIZICA §6.2)

Pentru fiecare azimut `a_k` (pas `Δa`) se parcurg distanțele `d_j` de la `d_min` la `d_max` pe cercul mare care
pleacă din observator: `u = cos δ·U + sin δ·(cos a·N + sin a·E)`, `δ = d / R`. Punctul se proiectează stereografic
polar (aceleași formule ca `core.projection`) și înălțimea se citește prin interpolare biliniară strictă din rasterul
**de calcul** (un vecin fără date invalidează eșantionul). Elevația aparentă se calculează în coordonate carteziene:
`el = atan2((R + h)·cos δ − r_obs, (R + h)·sin δ)`, cu `r_obs = R + h_teren + h_echipament`; curbura este inclusă
prin construcție. Nivelul apropiat are prioritate; nivelul îndepărtat se folosește numai unde cel apropiat nu are
date. Eșantioanele fără date nu intră în maxim și nu devin zero; starea per azimut este `complete`, `partial` sau
`no_data`. Între azimuturi, `H(a)` se interpolează liniar, continuu la 0°/360°, iar lângă `no_data` rezultatul este
necunoscut (`null`).

Altitudinea observatorului vine din rasterul de calcul al produsului apropiat (biliniar). Fără valoare validă,
profilul este `unavailable` (`observer_elevation_unknown`), nu calculat pe sferă.

Nivelurile se combină numai dacă declară același cadru și aceeași sferă de referință (verificat în cod); un produs
în alt cadru este refuzat, fără conversie.

## Produsul îndepărtat (D-08): verificare și compatibilitate

Candidații din DATA_PLAN §2.3 au fost verificați la sursă (PDS Geosciences Node, `LRO-L-LOLA-4-GDR-V1.0`,
`data/lola_gdr/polar/img/`). Eticheta `LDEM_75S_120M.LBL` declară: `COORDINATE_SYSTEM_NAME = "MEAN EARTH/POLAR AXIS OF
DE421"`, proiecție stereografică polară, centru −90°, meridian 0°, `A_AXIS_RADIUS = 1737.4 km`, `HEIGHT = DN · 0,5 m`
față de `OFFSET = 1737400 m`, 7624 × 7624 eșantioane int16 LSB, 120 m/pixel. Geometria pixelilor este cea din
`catalog/DSMAP_POLAR.CAT` (colțurile imaginii conțin date până dincolo de 75° S). Aceleași cadru declarat, sferă și
proiecție ca PGDA 104 (`MOON_ME_DE421`, care rămâne ipoteza D-10).

Verificare empirică (aceeași zonă, Leibnitz Beta): media pe blocuri de 120 m a rasterului PGDA 104 față de
`LDEM_75S_120M` pe 17 689 de puncte: diferența medie −0,29 m, σ 1,56 m, p5/p95 −2,86/+2,10 m, maxim |Δ| 18,5 m.
Control cu axa y inversată: |Δ| mediu 8,8 km (orientarea documentată este cea corectă).

Achiziție (2026-11-15): `LDEM_75S_120M.IMG` 116 250 752 octeți (85 s), `LDEM_75S_60M.IMG` 465 003 008 octeți (201 s,
numai pentru studiul de rezoluție). PDS nu publică sume de control: s-au verificat dimensiunea față de etichetă și
`Content-Length`; SHA-256 calculate local sunt fixate în `data/manifests/lola_gdr_acquisition.json`. Integritatea la
sursă nu este verificată. Produsul înregistrat ca nivel îndepărtat (`role = far`) în `terrain_products.json` este
`lola_gdr_ldem_75s_120m`. Alte produse (`LDEM_80S_20M`, 1,85 GB; PGDA 81, 3,3 GB) nu au fost descărcate.

## Studiul de convergență (T-07)

Punctul Leibnitz Beta (85,4266° S, 31,7442° E; teren 6 398,92 m; echipament 2 m). Configurația de bază: `Δa` 1°,
`d_min` 5 m, pas apropiat 5 m, pas îndepărtat 120 m, `d_max` 300 km. Un singur parametru variază; |ΔH| pe azimuturi.
Pragul propus: **0,05°** (o cincime din raza unghiulară a Soarelui, ≈ 0,267°) — propunere tehnică, nevalidată.

| Parametru | Comparație | max \|ΔH\| | p95 | RMS | Az. > 0,05° | Timp (s) |
|---|---|---|---|---|---|---|
| `d_max` | 50 → 100 km | 0,771° | 0 | 0,081° | 7 | 0,23 |
| `d_max` | 100 → 150 km | 0,516° | 0 | 0,050° | 9 | 0,27 |
| `d_max` | 150 → 200 km | 0,196° | 0 | 0,017° | 4 | 0,31 |
| `d_max` | 200 → 250 → 300 km | 0 | 0 | 0 | 0 | 0,35 / 0,41 |
| `d_max` | 300 → 350 → 400 km | 0 (pe datele existente) | — | — | 0 | 0,44 / 0,47; **32 / 101 az. `partial`** |
| Pas apropiat | 10 → 5 m | 0,028° | 0,012° | 0,005° | 0 | 0,39 |
| Pas apropiat | 5 → 2,5 m | 0,018° | 0,007° | 0,003° | 0 | 0,56 |
| Pas îndepărtat | 240 → 120 m | 0,0034° | 0 | 0,0003° | 0 | 0,41 |
| Pas îndepărtat | 120 → 60 m | 0,0007° | 0 | 0,0001° | 0 | 0,62 |
| Produs îndepărtat | 120 m → 60 m (`LDEM_75S_60M`) | 0,0047° | 0,0001° | 0,0003° | 0 | 0,69 |
| Rezoluție apropiată | 10 m (medie 2×2) → 5 m | **0,070°** | 0,033° | 0,016° | **5** | — |
| `Δa` (față de 0,1°, interpolat) | 2° | 0,163° | 0,022° | 0,016° | 56 / 3600 | 0,19 |
| `Δa` | 1° | 0,062° | 0,010° | 0,006° | 2 / 3600 | 0,38 |
| `Δa` | **0,5°** | 0,032° | 0,004° | 0,002° | 0 | 0,73 |
| `Δa` | 0,25° | 0,019° | 0,002° | 0,001° | 0 | 1,42 (referința 0,1°: 3,56) |

Verificare redusă pe alte puncte DEM: Haworth — `d_max` 100 → 200 → 300 km: 0; produs 120 → 60 m: 0,0057°.
Peak Near Shackleton — `d_max` 100 → 200 km: **1,85°** (68 az.), 200 → 300 km: 0; produs 120 → 60 m: 0,018°.

**Raza dincolo de date.** La `d_max` = 300 km profilul Leibnitz este complet pe toate azimuturile; la 350 și 400 km
32, respectiv 101 azimuturi ies din `LDEM_75S_120M` (`partial`), deci **nu se declară convergență fizică completă**.
Limită geometrică (din formula de mai sus, fără presupuneri despre teren): pentru a ridica azimutul cu orizontul cel
mai jos (−4,765°), un obstacol aflat la 300 km ar trebui să depășească 7 358,6 m față de sferă (Haworth: 28 338 m;
Peak Near Shackleton: 11 130 m); maximul întregii grile `LDEM_75S_120M` este 7 025 m. Terenul din afara grilei nu
este verificat.

**Rezoluția apropiată nu converge demonstrabil:** 10 m → 5 m schimbă până la 0,070° (5 azimuturi peste prag), iar
5 m este cel mai fin produs disponibil. Este o limită declarată, nu o toleranță.

## Parametrii propuși (D-08/D-09 deschise)

| Parametru | Valoare | Motiv |
|---|---|---|
| Produs îndepărtat | `LDEM_75S_120M` | 60 m schimbă ≤ 0,018°; 4 × mai mic |
| `d_max` | 300 km | nicio schimbare după 200 km pe trei puncte; ultima rază complet acoperită pentru Leibnitz |
| `Δa` | 0,5° | max 0,032° < 0,05° față de 0,1° |
| Pas apropiat / `d_min` | 5 m / 5 m | rezoluția produsului; 2,5 m schimbă ≤ 0,018° |
| Pas îndepărtat | 120 m | rezoluția produsului; 60 m schimbă ≤ 0,0007° |

Cu acești parametri, profilul Leibnitz: 720 de azimuturi, 4 668 de eșantioane pe azimut, acoperire 100 %,
`complete`, 38,4 % eșantioane din PGDA 104 și 61,6 % din LOLA GDR, obstacol cel mai depărtat la 176,6 km, timp de
calcul 0,72–0,87 s (servit apoi din cache).

## Integrare

- `GET /api/horizon?observer_height_m=…` cu `site_id` (cadrul sitului; alt `frame_id` → 422 `UNSUPPORTED_FRAME`)
  sau `latitude_deg`, `longitude_deg`, `frame_id`. Înălțimea echipamentului este obligatorie (D-14 deschisă, fără
  valoare implicită ascunsă). Răspunsul are trei stări: `complete`, `partial` (`reason_code = missing_samples`) și
  `unavailable` (`frame_mismatch`, `terrain_not_downloaded`, `coverage_unverified`, `no_dem_coverage`,
  `observer_elevation_unknown`), cu tablouri goale — niciodată orizont liber sau zero.
- Cheia cache-ului: SHA-256 peste poziție, cadru, înălțimea echipamentului, produse (id, rol, SHA-256), parametri și
  `algorithm_version`. Rasterele se verifică (SHA-256 față de manifest) o dată pe proces; fără sumă sau cu sumă
  diferită nu se folosesc. Profilurile `unavailable` nu se păstrează.
- `terrain_mode = dem`: profilul fiecărui sit se calculează la trimitere; un profil indisponibil oprește cererea
  (422/503 cu codul potrivit), fără trecere la modul idealizat. Rezultatul: observator pe teren
  (`on_reference_surface = false`), `horizon_elevation_deg = H(a(t))`, `visible = null` cu motiv
  (`visibility_pending_e10`), `events` și `summary` în `quality.not_computed` (E10).
- Interfață: fila „Horizon profile” (încărcare numai când este deschisă), cu lacune pentru `no_data`, marcaje pentru
  `partial`, Soarele și Pământul numai dacă simularea are același cadru, produse, acoperire și nota de parametri
  provizorii; insignele de mod arată „DEM horizon — visibility with terrain not computed yet”.

## Teste și verificări rulate

Backend 372/372 (noi în `test_horizon.py`: sferă plată → depresiunea geometrică ± 1·10⁻⁴°, obstacol cunoscut cu
curbură ± 0,02° și diferit de rezultatul „Pământ plat” cu > 0,1°, NoData → `partial` și diferit de zero, azimut fără
eșantioane → `no_data`, rasterul depășit → `partial` și completat de nivelul îndepărtat, prioritatea nivelului
apropiat, refuzul cadrelor și sferelor diferite, parametri invalizi, interpolare la 0°/360°, eticheta PDS citită,
profilul Leibnitz complet și cache-ul, profil parțial fără produsul îndepărtat, patru stări `unavailable`, validarea
cererii, simularea `dem`), Ruff, mypy, contracte la zi, `verify_terrain_products.py` 13/13, sumele LOLA verificate.
Frontend 221/221 (patru noi: încărcare numai la deschiderea filei, profil complet, lacune și azimuturi parțiale,
profil indisponibil afișat ca necunoscut, eroare și reîncercare), formatare, oxlint, `tsc`, build. Playwright 5/5
(nou `horizon.spec.ts`: profil Leibnitz complet cu 720 de azimuturi și produsul îndepărtat, simulare `dem` cu
orizontul pe corp, grupurile necalculate, insignele DEM și Soarele desenat pe grafic). Captură de ecran verificată
vizual (graficul, Soarele la 2,13°, Pământul la 0,22°).

## Rămâne deschis

- D-08/D-09 [GEO]: produsul îndepărtat, `d_max`, `Δa`, pașii radiali și pragul de 0,05°.
- D-10: cadrul `MOON_ME_DE421` al ambelor produse este ipoteză; D-14: înălțimea implicită a echipamentului.
- D-19: harta de măsurători reale (`ldec`) nu intră în indicatorul de calitate.
- Puncte ≥ 87° S fără produs PGDA 104: PGDA 81 neachiziționat (profil `unavailable`).
- E10: vizibilitate față de H(a), evenimente, indicatori.
