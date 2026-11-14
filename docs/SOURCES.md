# Surse și credite

Registrul surselor folosite sau avute în vedere. Pentru fiecare sursă utilizată efectiv se păstrează: URL,
data accesării, instituția, identificatorul produsului și condițiile de creditare.

**Starea verificării**

- **Citită** — pagina a fost accesată în sesiunea de planificare din 2026-11-14 și informația de mai jos provine din ea. Nu înseamnă că datele au fost descărcate sau validate.
- **Găsită** — a apărut într-o căutare; pagina nu a fost citită.
- **Necitită** — punct de pornire din specificație, neaccesat.

Condițiile de creditare marcate „de stabilit” trebuie citite de la sursă înainte de folosire.

## 1. Relief

**E05 — surse efectiv pregătite (2026-11-14):**

- [PGDA 104](https://pgda.gsfc.nasa.gov/products/104), Bertone et al., DOI 10.3847/PSJ/ae5b70; arhiva
  [Zenodo 17954508](https://zenodo.org/records/17954508), Leibnitz Beta. Au fost extrase prin HTTP Range
  rasterul de elevație și membrii GLDMASK, GLDSBCT și GLDSIGM; CRC ZIP și SHA-256 fixat local verificate.
  README-ul numește GLDMASK numărul de imagini NAC iluminate și GLDSBCT numărul de categorii de azimut solar;
  acestea nu sunt numărul de măsurători LOLA. README-ul numește produsul de incertitudine `GLDISGM`, dar ZIP-ul
  conține `GLDSIGM`; identitatea/semnificația exactă nu este confirmată. SHA-urile și metadatele citite sunt în
  `data/manifests/e05_auxiliary.json`; SHA-256 este calculat de proiect, nu publicat pentru membru de autor.
- [NASA SVS CGI Moon Kit](https://svs.gsfc.nasa.gov/4720/), `lroc_color_2k.jpg`, 2048 × 1024; credit cerut:
  **NASA's Scientific Visualization Studio**, vizualizare Ernie Wright, date LROC WAC și LOLA. Hartă adaptată
  pentru randare, fără garanție de calitate științifică: sursa descrie completare polară cu albedo LOLA mai
  grosier și corecții de imagine. [Condițiile NASA](https://www.nasa.gov/nasa-brand-center/images-and-media/)
  permit în general utilizarea informativă a materialelor NASA cu credit, fără a sugera susținerea produsului;
  materialele terților marcate separat pot avea alte drepturi. D-11 nu este confirmată.

| Sursă | Instituție | Identificator | Ce s-a constatat | Stare |
|---|---|---|---|---|
| <https://pgda.gsfc.nasa.gov/products/81> | NASA GSFC, PGDA (autor: M. K. Barker) | South Pole LOLA DEM Mosaic | 87–90°S, 5 m/pixel, stereografică polară sudică, „MOON_ME, DE421”, pixeli goi interpolați; reziduu RMS tipic 30–55 cm față de câmpurile individuale; fișiere și dimensiuni listate | Citită |
| <https://pgda.gsfc.nasa.gov/products/78> | NASA GSFC, PGDA | High-Resolution LOLA Topography for Lunar South Pole Sites | Lista siturilor, tipurile de fișiere, același cadru și aceeași proiecție. Pagina a fost citită parțial (primele 100 000 de caractere) | Citită parțial |
| <https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/README> | NASA GSFC, PGDA | README al setului `LOLA_5mpp` | Descrierea fișierelor; nu conține parametrii proiecției, raza de referință sau valoarea `NoData` | Citită |
| <https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/catalog/gdr_ds.cat> | PDS Geosciences Node | `LRO-L-LOLA-4-GDR-V1.0` | Produse polare stereografice de la 240 la 5 m/pixel; citarea setului | Citită |
| <https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/jp2/> | PDS Geosciences Node | Produse `LDEM_*S_*M` | 19 produse pentru polul sud, cu dimensiuni | Citită |

Citare cerută de PGDA: Barker, M. K., et al. (2021), „Improved LOLA Elevation Maps for South Pole Landing
Sites: Error Estimates and Their Impact on Illumination Conditions”, *Planetary & Space Science*, 203, 105119,
doi:10.1016/j.pss.2020.105119. Numerotarea siturilor urmează Mazarico et al. (2011), *Icarus*, 211,
doi:10.1016/j.icarus.2010.10.030.

Citarea setului GDR, așa cum apare în catalog: Neumann, G. A., „2009 Lunar Orbiter Laser Altimeter Raw Data
Set, LRO-L-LOLA-4-GDR-V1.0”, NASA Planetary Data System, 2010.

### Căi alternative investigate pentru E05 (2026-11-14)

- [NASA PGDA 104](https://pgda.gsfc.nasa.gov/products/104) descrie SDEM-uri obținute din LOLA și imagini LROC,
  pe grilă de 5 m/pixel, pentru cele 13 regiuni Artemis din 2022. [Arhiva indicată de NASA](https://zenodo.org/records/17954508)
  listează 13 ZIP-uri, 26,6 GB în total, cu sume MD5 publicate. Este un produs diferit de PGDA 78/81; nu au fost
  descărcate fișierele și nu sunt cunoscute acoperirea pentru IM-1/IM-2, NoData sau compatibilitatea pentru orizont.
  Actualizare: antetele rasterelor de elevație din toate cele 13 ZIP-uri au fost citite parțial; niciun raster
  nu conține IM-1 sau IM-2 în extindere, sub ipoteza de cadru. NoData este declarat în antete; pixelii și
  compatibilitatea pentru orizont rămân neverificate. Rezultatele detaliate sunt în VALIDARE §7.9.
- [NASA PGDA 90](https://pgda.gsfc.nasa.gov/products/90) oferă COG-uri polare DE421, inclusiv un DEM 80–90°S la
  20 m/pixel; este un candidat pentru date mai grosiere, nu dovedește îndeplinirea criteriului propus de 5 m/pixel.
  Limitele exacte și datele valide la situri nu au fost verificate.
- [Nodul LOLA PDS](https://imbrium.mit.edu/) trimite pentru DEM-urile regionale de 5 m/pixel înapoi la PGDA;
  nu a fost identificată acolo o oglindă verificată a fișierelor PGDA 78.
- [USGS](https://www.usgs.gov/data/down-selected-artemis-iii-candidate-landing-site-navigational-grids) spune că
  regiunile pentru grilele de navigație provin din [LROC QuickMap](https://quickmap.lroc.im-ldi.com/). Acesta este
  o cale oficială de vizualizare, nu o dovadă că geometria USGS a fost descărcată sau că grilele sunt poligoanele
  originale. Pagina QuickMap cere JavaScript; browserul interactiv nu este disponibil. ScienceBase rămâne blocat
  de verificarea de acces observată anterior; nu s-a încercat ocolirea acesteia.

## 2. Astronomie

| Sursă | Instituție | Ce s-a constatat | Stare |
|---|---|---|---|
| <https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/aareadme.txt> | NASA JPL, NAIF | Kernelurile de orientare lunară și perechile lor de cadre; `pck00011.tpc` | Citită |
| <https://naif.jpl.nasa.gov/pub/naif/generic_kernels/fk/satellites/> | NASA JPL, NAIF | Fișierele prezente, inclusiv `moon_de440_250416.tf`, `moon_080317.tf` | Citită |
| `moon_de440_250416.tf` (în directorul de mai sus) | NASA JPL, NAIF | Cadrele definite, aliasurile, diferența față de cadrul ME al DE421 | Citită |
| `moon_080317.tf` (în directorul de mai sus) | NASA JPL, NAIF | Cadrele definite, aliasurile, diferența față de `IAU_MOON` | Citită |
| <https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/aa_summaries.txt> | NASA JPL, NAIF | Acoperirea `de440.bsp`, `de440s.bsp` și corpurile incluse. `de421.bsp` nu a apărut în porțiunea citită | Citită parțial |
| <https://ssd-api.jpl.nasa.gov/doc/horizons.html> | NASA JPL, SSD | API Horizons, versiunea documentului 1.3 (iunie 2025): parametri, valori implicite, coduri de eroare | Citită |
| <https://ssd.jpl.nasa.gov/horizons/manual.html> | NASA JPL, SSD | Observator pe suprafața altui corp; ordinea și unitățile coordonatelor; cadrul mean-Earth pentru Lună; longitudine estică pozitivă pentru Lună; definiția coordonatelor aparente. Citit parțial | Citită parțial |
| <https://spiceypy.readthedocs.io> | SpiceyPy | Existența funcției `azlcpo` și trimiterea la CSPICE N0067. La E03, semnăturile folosite (`spkcpo`, `spkcov`, `pckcov`, `str2et`, `et2utc`, `timout`, `bodvrd`, `subpnt`, `namfrm`, `frinfo`, `spkpos`) au fost confirmate prin inspecția versiunii instalate 8.4.0 | Citită parțial; semnături verificate local |

### 2.1. Folosite efectiv la E03 (2026-11-14)

| Sursă | Instituție | Ce s-a folosit | Stare |
|---|---|---|---|
| Kerneluri NAIF: `naif0012.tls`, `pck00011.tpc`, `de440s.bsp`, `moon_pa_de440_200625.bpc`, `moon_de440_250416.tf`, `de421.bsp` (din `spk/planets/a_old_versions/`), `moon_pa_de421_1900-2050.bpc`, `moon_080317.tf` | NASA JPL, NAIF | Descărcate de pe <https://naif.jpl.nasa.gov/pub/naif/generic_kernels/>; URL-urile exacte, momentele, mărimile și sumele de control sunt în `data/manifests/kernels.json` | Descărcate și verificate |
| <https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/aa_checksums.txt> și echivalentul din `a_old_versions/` | NASA JPL, NAIF | MD5 publicate pentru `de440s.bsp` și `de421.bsp` | Citite; sumele se potrivesc |
| <https://naif.jpl.nasa.gov/pub/naif/generic_kernels/lsk/> | NASA JPL, NAIF | `naif0012.tls` este cel mai recent LSK publicat (ultima secundă intercalare: 2017-01-01) | Citită |
| API JPL Horizons, <https://ssd.jpl.nasa.gov/api/horizons.api> | NASA JPL, Solar System Dynamics | 26 de cereri (24 de observator, 2 de vectori); parametrii și răspunsurile originale sunt în `data/reference/horizons/`. Antetele indică DE441, `MEAN_ME (high precision)`, raze 1737,4 km, fără refracție, cu devierea gravitațională a luminii | Interogat; arhivat |
| Material de referință al unui prototip LunarHorizon separat (anexele promptului E03) | Echipa proiectului | Sumele SHA-256 ale unei descărcări anterioare (verificare independentă a fișierelor), coordonatele Apollo 11 și altitudinile de test, valorile anterioare pentru comparație. Fișierele originale (`C:\Users\Erikutzu\…`) nu există pe acest calculator; s-au folosit numai anexele. Coordonatele Apollo 11 au fost verificate la E04 la sursa LROC (§2.2) | Material de lucru, nu sursă verificată |

### 2.2. Folosite efectiv la E04, catalogul siturilor (2026-11-14)

Toate documentele de mai jos au fost **deschise** în această sesiune (pagini HTML descărcate și citite ca text; PDF-uri
citite prin extragere de text). Pozițiile, citatele, locatorii și convențiile declarate sunt în `position_sources`
din `data/catalog/sites.json`. Reverificarea automată: `scripts/verify_catalog_sources.py`; rezultatul arhivat:
`data/catalog/source_verification.json`.

| Sursă | Instituție | Rol în catalog | Ce declară despre convenții | Stare |
|---|---|---|---|---|
| Produs PDS „Anthropogenic (man-made) Features on the Moon”, `LRO-L-LROC-5-RDR-V1.0`, volumul `LROLRC_2001`, `EXTRAS/SHAPEFILE/ANTHROPOGENIC_OBJECTS` (pagina <https://data.lroc.im-ldi.com/lroc/view_rdr/SHAPEFILE_ANTHROPOGENIC_OBJECTS>; fișiere `…_180.ZIP`, `…_360.ZIP`, `…_README.TXT`) | LROC (NASA/GSFC/Arizona State University) | **Sursa primară a tuturor pozițiilor efective** (11 intrări). Câmpuri: `LATITUDE`, `LONGITUDE`, `LON_360`, `RADIUS`, `COORD_SRC`, `UNCERTAIN`, `DATE`, `REFERENCES`. Actualizat 2026-08-14. ZIP-ul de 180° are SHA-256 `f0145e0b…e4408b` | `.PRJ`: `GCS_Moon_2000`, sferă `Moon_2000_IAU_IAG` de 1 737 400 m, meridian de referință 0°. **Nu numește ME și nu numește o realizare (DE)**. `UNCERTAIN`: „Uncertainty of the coordinates in meters” (metoda nedefinită) | Deschis și parsat |
| „Spacecraft Related Coordinates - 2016 Update” (<https://lroc.im-ldi.com/images/938>), Mark Robinson, 25 noiembrie 2016 | LROC | Coroborare pentru Apollo 11–17 (tabelul „Crewed Missions”) | „mean Earth/polar axis (ME) system”, fără realizare; longitudini 0–360°; incertitudine orbitală LRO ≈ ±15 m. Coloana „Uncertainty (m)” nu este definită | Deschis |
| Wagner et al. (2017), *Coordinates of anthropogenic features on the Moon*, Icarus 283, 92–103, doi:10.1016/j.icarus.2016.05.011 | Wagner, Nelson, Plescia, Robinson, Speyerer, Mazarico | Lucrarea citată de produs și de pagina din 2016 | — | **Inaccesibilă**: ScienceDirect HTTP 403; Crossref dă doar metadate. Definiția coloanei de incertitudine nu a putut fi citită |
| PDF-ul „2016_LROC_Coordinates_of_Human_Features.pdf”, legat de pagina din 2016 | LROC | — | — | **Inaccesibil**: HTTP 500 |
| LROC, pagini de imagine: 1360 (IM-1, 26.02.2024), 1314 (Chandrayaan-3, 05.09.2023), 1407 (Blue Ghost 1, 07.03.2025), 1168 (Chang'e 4, 01.12.2020), 1409 (IM-2, 11.03.2025); pagina „IM2: Flip Book” (<https://lroc.im-ldi.com/featured_sites/im2/flip-book>) | LROC | Coroborări, cu valori rotunjite | Nu declară cadrul. Pagina 1168: „13 meters (95% confidence interval)” | Deschise |
| NASA, „NASA’s LRO Images Intuitive Machine’s Odysseus Lander”, 26 februarie 2024 (<https://www.nasa.gov/missions/lro/nasas-lro-images-intuitive-machines-odysseus-lander/>) | NASA (Goddard Digital Team) | Coroborare IM-1: „80.13 degrees south latitude, 1.44 degrees east longitude … 2,579 meters” | Nu declară cadrul | Deschis |
| NASA CLPS, kituri de presă: IM-1 (`np-2023-12-016-…`, creat 2024-01-31), IM-2 (`np-2025-02-005-…`, creat 2025-02-25), Blue Ghost Mission One (`np-2025-01-001-…`, creat 2025-01-10) | NASA (JSC) | Context de misiune și ținte planificate numite (Malapert A; Mons Mouton; Mons Latreille). Kitul IM-1 din ianuarie 2024 listează și „IM-2 LANDING SITE: Shackleton Connecting Ridge”, stare ulterior depășită | Fără coordonate numerice | Deschise (PDF; verificare manuală, nu automată) |
| ISRO, „Chandrayaan-3 Details” (<https://www.isro.gov.in/Chandrayaan3_Details.html>) | ISRO | **Ținta planificată** Chandrayaan-3: „Landing Site (Prime) 4 km x 2.4 km, 69.367621 S, 32.348126 E” | Nu declară cadrul; rolul perechii de coordonate (centru/colț) nu este precizat | Deschis |
| NASA NTRS 20240009936, „Thermoplastic Space Point Design (TSPD) Tall Tower Lunar Thermal Analysis” (Will Grier, NASA Langley), pagina 8 | NASA | **Respinsă ca sursă de sit**: punctul „Shackleton Connecting Ridge” (-89.46752°, -138.012788°) este locația unui turn într-un studiu termic, „chosen to match available average seasonal surface temperature flight data from LRO” | Nu declară cadrul | Deschis; nu folosit în catalog |
| Crossref, metadate pentru doi:10.1016/j.icarus.2016.05.011 | Crossref | Identificarea lucrării (Icarus 283, 92–103, 2017-02) | — | Deschis |

**Neconfirmate:** paginile NSSDCA (au răspuns cu XML gol, fără conținut); QuickMap și Moon Trek (verificarea vizuală
este a colegilor de geografie); fișierele geometrice ale regiunilor candidate Artemis III din 2024.

**Actualizare 2026-11-14:** [broșura ISRO](https://www.isro.gov.in/media_isro/pdf/Missions/LVM3/LVM3M4_Chandrayaan3_brochure.pdf), pagina 6, a fost citită și coroborează coordonatele țintei planificate (69,367621°S, 32,348126°E); nu reprezintă poziția efectivă. [USGS, grile Artemis III](https://www.usgs.gov/data/down-selected-artemis-iii-candidate-landing-site-navigational-grids), publicat 2024-12-05, descrie grile și regiuni din selecția 2024; fișierele geometrice nu au fost inspectate deoarece ScienceBase a afișat o verificare de acces.

Citarea cerută de produs: Wagner, R. V., Nelson, D. M., Plescia, J. B., Robinson, M. S., Speyerer, E. J., & Mazarico,
E. (2017). Coordinates of anthropogenic features on the Moon. *Icarus, 283*, 92–103. doi:10.1016/j.icarus.2016.05.011.
Condițiile de reutilizare ale produsului nu au fost găsite pe pagină; textele de creditare finale rămân de stabilit (D-11).

## 3. Cartografie și sisteme de referință

| Sursă | Ce s-a constatat | Stare |
|---|---|---|
| <https://spatialreference.org/ref/iau_2015/30135/> | „Moon (2015) - Sphere / Ocentric / South Polar”, metoda Polar Stereographic (variant A), bază `IAU_2015:30100`. Parametrii nu sunt afișați pe pagină | Citită |
| <https://openlayers.org/en/latest/apidoc/module-ol_proj_proj4.html> | `register(proj4)` face disponibile în OpenLayers proiecțiile definite cu `proj4.defs()`; cere proj4 ≥ 2.8 | Citită |
| <https://astrogeology.usgs.gov/search/map/moon_lro_lroc_wac_global_morphology_mosaic_100m> | Mozaicul global LROC WAC, 100 m/pixel (originator: Arizona State University; publicat de USGS Astrogeology) | Găsită |

## 4. Resurse din specificație, încă necitite

| Resursă | Rol prevăzut | Stare |
|---|---|---|
| LROC QuickMap | Inspecția siturilor și a straturilor | Necitită |
| NASA Moon Trek | Explorare cartografică și verificare vizuală | Necitită |
| <https://www.asc-csa.gc.ca/eng/astronomy/moon-exploration/> (Canadian Space Agency) | Context educațional | Necitită |
| Documentația misiunilor | Coordonate, statut, ținte și puncte de aterizare | Necitită |

QuickMap și Moon Trek sunt aplicații interactive. Accesul la interfață nu confirmă existența unui serviciu
reutilizabil; serviciile, descărcările și condițiile fiecărui produs se verifică separat.

## 5. Software

Versiunile sunt listate în [ARCHITECTURE.md](ARCHITECTURE.md) §2. Licențele de mai jos sunt citite din
metadatele pachetelor instalate (PyPI: `License-Expression`; npm: câmpul `license`) la 2026-11-14.
Proiectul însuși este sub licență MIT ([LICENSE](../LICENSE)).

| Pachet | Versiune | Licență declarată | Rol |
|---|---|---|---|
| NumPy | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | Backend |
| SpiceyPy | 8.4.0 | MIT | Backend |
| Rasterio | 1.5.2 | BSD-3-Clause | Backend |
| Pydantic | 2.14.3 | MIT | Backend (contracte, din E02) |
| jsonschema | 4.26.0 | MIT | Dezvoltare (validarea fixture-urilor, din E02) |
| json-schema-to-typescript | 16.0.0 | MIT | Dezvoltare (tipurile TS generate, din E02) |
| pytest | 9.2.0 | MIT | Dezvoltare |
| Ruff | 0.17.5 | MIT | Dezvoltare |
| mypy | 2.4.1 | MIT | Dezvoltare |
| React, React DOM | 19.3.1 | MIT | Frontend |
| Vite | 8.3.8 | MIT | Build |
| @vitejs/plugin-react | 6.3.0 | MIT | Build |
| TypeScript | 7.0.2 | Apache-2.0 | Dezvoltare |
| oxlint | 1.93.0 | MIT | Dezvoltare |
| Prettier | 3.10.1 | MIT | Dezvoltare |
| Vitest | 5.1.0 | MIT | Dezvoltare |
| jsdom | 31.0.1 | MIT | Dezvoltare |
| @testing-library/react | 16.3.3 | MIT | Dezvoltare |
| @testing-library/dom | 10.4.2 | MIT | Dezvoltare |
| @types/node, @types/react, @types/react-dom | 26.6.6, 19.3.0, 19.3.0 | MIT | Dezvoltare |

Wheel-urile SpiceyPy și Rasterio includ biblioteci native (CSPICE, respectiv GDAL, PROJ și dependențele lor),
cu licențe proprii. Acestea nu au fost inventariate la E01; se verifică înainte de distribuirea unei imagini
de container (E16).

## 6. De completat pe parcurs

- Sumele de control ale fiecărui fișier descărcat (în manifeste).
- Textele exacte de creditare pentru LROC WAC, LOLA, PGDA și NAIF.
- Sursele fiecărei poziții din catalog.
- Configurația și data fiecărei interogări Horizons.

## Sursă secundară autorizată: Ahammad204/Nasa-moon

Consultat la 2026-11-14: https://github.com/Ahammad204/Nasa-moon,
README.md și src/data/sites.json (ramura main; conținutul acestei ramuri se poate schimba).
Proiect educațional independent, nu produs NASA. README declară cod MIT și calcule geometrice fără relief.
Nu este dovadă de acoperire DEM și nu înlocuiește datele de elevație cerute de E05.
Fișierul sites.json are 14 intrări; 11 nu au coordonate. Cele trei piste numerice sunt:

| Pistă | Latitudine / longitudine est (grade), conform repository-ului | Sursa primară indicată; verificare în acest proiect |
|---|---|---|
| Malapert Massif | -85.99 / -2.93 | https://science.nasa.gov/image-detail/20100618/ ; neefectuată |
| Mons Mouton | -84.6 / 31.0 | https://planetarynames.wr.usgs.gov/Feature/16070 ; neefectuată |
| Shackleton | -89.67 / 129.78 | https://planetarynames.wr.usgs.gov/Feature/5450 ; neefectuată |

Acestea sunt poziții aproximative de regiune/centre de formațiuni, nu poziții de aterizare validate.
Centrul craterului Shackleton nu reprezintă automat un punct pe marginea craterului.
Lista Artemis din repository este etichetată 2022; nu se tratează drept geometria regiunilor din 2024.
Datele sunt consemnate ca piste; nu au fost importate în catalogul activ și nu s-a copiat cod.
Înainte de adoptare: verificare la sursa primară, cadru, extindere DEM, pixeli valizi/NoData,
suprafață necesară pentru orizont și criteriile de comparație D-07.
