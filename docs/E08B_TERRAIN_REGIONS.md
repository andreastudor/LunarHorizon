# E08b — teren local pentru siturile și regiunile polare sudice

Extindere **obligatorie** a cerinței de acoperire a terenului (decizia utilizatorului, 2026-11-15), nu bonus. E08
(terenul pentru punctul Leibnitz Beta) rămâne o etapă încheiată; E08b o extinde la o listă explicită. Nu închide E12
(comparația) și nu calculează orizonturi (E09).

## Lista vizată (explicită, verificabilă)

**Regula „polar sud”**: intrările de catalog cu latitudinea ≤ −60°. **Inventarul DEM**: PGDA 104 (13 regiuni,
achiziție selectivă), PGDA 81 (mozaic 87–90° S, inventariat, neachiziționat), PGDA 78 (DEM-uri de sit cu coduri, fără
regiuni documentate; neînregistrate). Lista vizată are **15 intrări**: 13 regiuni PGDA 104 și 2 poziții Chandrayaan-3.

| Sit / regiune | Poziție (sursă) | Produs DEM | Rezoluție calcul / mesh | Cadru | Extindere X × Y (km) | Verificare | Acces |
|---|---|---|---|---|---|---|---|
| Amundsen Rim | 84.2287° S, 69.4450° E — pixel central, `A300_GLDELEV_005.tif` | `pgda104_amundsen_rim` | 5 m / 40 m / 80 m | MOON_ME_DE421 (ipoteză) | 154–174 × 51.5–71.5 | `verify_terrain_products.py` OK; NoData 0 % | descărcat, 34.8 MB |
| Connecting Ridge | 89.4632° S, 137.5020° W — pixel central, `A306_GLDELEV_005.tif` | `pgda104_connecting_ridge` | 5 m / 40 m / 80 m | MOON_ME_DE421 (ipoteză) | -19–-3 × -20–-4 | `verify_terrain_products.py` OK; NoData 0 % | descărcat, 21.0 MB |
| Connecting Ridge Extension | 89.0325° S, 102.0051° W — pixel central, `A305_GLDELEV_005.tif` | `pgda104_connecting_ridge_extension` | 5 m / 40 m / 80 m | MOON_ME_DE421 (ipoteză) | -38.7–-18.7 × -16.1–3.9 | `verify_terrain_products.py` OK; NoData 0 % | descărcat, 35.1 MB |
| deGerlache Kocher Massif | 85.8296° S, 116.3235° W — pixel central, `A312_GLDELEV_005.tif` | `pgda104_degerlache_kocher_massif` | 5 m / 40 m / 80 m | MOON_ME_DE421 (ipoteză) | -123.4–-103.4 × -66.1–-46.1 | `verify_terrain_products.py` OK; NoData 0 % | descărcat, 32.3 MB |
| deGerlache Rim | 88.6835° S, 67.9341° W — pixel central, `A309_GLDELEV_005.tif` | `pgda104_degerlache_rim` | 5 m / 40 m / 80 m | MOON_ME_DE421 (ipoteză) | -45–-29 × 7–23 | `verify_terrain_products.py` OK; NoData 0 % | descărcat, 22.1 MB |
| deGerlache Rim 2 | 88.2301° S, 64.6297° W — pixel central, `A304_GLDELEV_005.tif` | `pgda104_degerlache_rim_2` | 5 m / 40 m / 80 m | MOON_ME_DE421 (ipoteză) | -58.5–-38.5 × 13–33 | `verify_terrain_products.py` OK; NoData 0 % | descărcat, 34.0 MB |
| Faustini Rim A | 87.8896° S, 90.0022° E — pixel central, `A303_GLDELEV_005.tif` | `pgda104_faustini_rim_a` | 5 m / 40 m / 80 m | MOON_ME_DE421 (ipoteză) | 54–74 × -10–10 | `verify_terrain_products.py` OK; NoData 0 % | descărcat, 34.2 MB |
| Haworth | 86.7640° S, 22.7762° W — pixel central, `A302_GLDELEV_005.tif` | `pgda104_haworth` | 5 m / 40 m / 100 m | MOON_ME_DE421 (ipoteză) | -52.9–-23.1 × 75.6–105.4 | `verify_terrain_products.py` OK; NoData 0 % | descărcat, 73.0 MB |
| Leibnitz Beta Plateau | 85.4266° S, 31.7442° E — pixel central, `A310_GLDELEV_005.tif` | `pgda104_leibnitz_beta` | 5 m / 40 m / 80 m | MOON_ME_DE421 (ipoteză) | 65–81 × 110–126 | `verify_terrain_products.py` OK; NoData 0 % | descărcat, 16.6 MB |
| Malapert Massif | 85.9949° S, 0.2346° W — pixel central, `A311_GLDELEV_005.tif` | `pgda104_malapert_massif` | 5 m / 40 m / 100 m | MOON_ME_DE421 (ipoteză) | -11–10 × 111–132 | `verify_terrain_products.py` OK; NoData 0 % | descărcat, 31.2 MB |
| Nobile Rim 1 | 85.4381° S, 37.3681° E — pixel central, `A307_GLDELEV_005.tif` | `pgda104_nobile_rim_1` | 5 m / 40 m / 80 m | MOON_ME_DE421 (ipoteză) | 74–94 × 100–120 | `verify_terrain_products.py` OK; NoData 0 % | descărcat, 27.4 MB |
| Nobile Rim 2 | 83.9540° S, 58.8231° E — pixel central, `A301_GLDELEV_005.tif` | `pgda104_nobile_rim_2` | 5 m / 40 m / 80 m | MOON_ME_DE421 (ipoteză) | 147–167 × 85–105 | `verify_terrain_products.py` OK; NoData 0 % | descărcat, 32.8 MB |
| Peak Near Shackleton | 88.8109° S, 123.6912° E — pixel central, `A308_GLDELEV_005.tif` | `pgda104_peak_near_shackleton` | 5 m / 40 m / 80 m | MOON_ME_DE421 (ipoteză) | 22–38 × -28–-12 | `verify_terrain_products.py` OK; NoData 0 % | descărcat, 21.7 MB |
| Chandrayaan-3 — Vikram lander | 69,3740° S, 32,3187° E — catalog E04 (LROC) | — | — | MOON_ME_DE440_ME421 (ipoteză) | — | niciun produs inventariat nu acoperă 69° S | **Coverage unverified** |
| Chandrayaan-3 — țintă planificată | 69,3676° S, 32,3481° E — catalog E04 (ISRO) | — | — | MOON_ME_DE440_ME421 (ipoteză) | — | idem | **Coverage unverified** |

Punctul fiecărei regiuni este **pixelul central** al rasterului oficial (rândul = înălțimea // 2, coloana = lățimea // 2;
metoda LunarHorizon, aceeași ca la E05). Este etichetat „representative point”, cu `status = dem_region`, fără
misiune; **nu este loc de aterizare, țintă sau selecție curentă**. Numele regiunilor sunt cele din numele arhivelor
Zenodo (prefix `A3CLR22`); nu s-au importat coordonate din surse secundare. Mesh-ul folosește cel mai fin nivel vizual
cu cel mult 300.000 de vârfuri (40 m; 100 m pentru Haworth și Malapert la nivelul 1).

## Produse inventariate, neînregistrate sau blocate

| Produs | Stare | Motiv |
|---|---|---|
| PGDA 81, mozaic LOLA 87–90° S (5 m) | Neachiziționat | 3,3 GB; un punct ≥ 87° S în afara rasterelor PGDA 104 apare „Terrain not downloaded” |
| PGDA 78 — DM1, DM2, Haworth, LM1, LM2, LM3 | Citite în E04 (metadate), neînregistrate | Coduri fără poziții de sit documentate; DM1, DM2 și Haworth au aceleași limite ca Amundsen Rim, Nobile Rim 2 și Haworth din PGDA 104 |
| PGDA 78 — 21 de DEM-uri (LM4–LM8, NPA–NPD, SL2, SL3, Shoemaker, Site01/04/06/07/11/20/20v2/23/42) | **Blocate** | HTTP 403 la verificarea E04 (`data/catalog/pgda_coverage.json`); nereîncercate |

## Regula de selecție (deterministă) și stări

Printre produsele înregistrate al căror dreptunghi conține punctul și al căror cadru este cel cerut: (1) eșantion valid
în rasterul de calcul (nu NoData, nu margine), (2) rezoluția de calcul mai fină, (3) distanța mai mare până la marginea
rasterului, (4) `terrain_id` mai mic. Rasterele nu se combină. Suprapunerile reale: Leibnitz Beta ∩ Nobile Rim 1 și
deGerlache Rim ∩ deGerlache Rim 2. Stări: **Terrain available**, **Terrain not downloaded** (produs cunoscut, date
absente), **Coverage unverified** (polar, fără produs inventariat), **No DEM coverage** (în afara domeniului polar al
inventarului), **Frame mismatch** (DEM declarat în alt cadru; nicio conversie). Disponibilitatea reliefului vizual nu este
acoperirea necesară orizontului (E09).

## Date, reproducere și verificare

- Achiziție: `scripts/acquire_pgda104.py --all` (HTTP Range, numai membrul `*_GLDELEV_005.tif`; CRC al membrului ZIP
  verificat; SHA-256 fixat în `data/manifests/pgda104_acquisition.json`; MD5-ul arhivelor complete **neverificat**).
  12 membri noi ≈ 399 MB în ≈ 3,5 min (≈ 2 MB/s); Leibnitz Beta reutilizat (16,6 MB). Arhivele complete (1–4,4 GB) nu
  au fost descărcate.
- Pregătire: `scripts/build_pgda104_regions.py` (rasterul de calcul identic, niveluri vizuale prin medii pe blocuri,
  manifeste, `terrain_index.json`, produse și intrările de catalog). Leibnitz Beta păstrează produsele E05.
- Validare: `scripts/verify_terrain_products.py` — 13/13 produse OK (manifest Pydantic + JSON Schema, sumă de control,
  CRS, limite, rezoluție, niveluri vizuale recalculate, punct central).
