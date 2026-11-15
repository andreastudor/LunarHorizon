# Criterii de acceptanță
## E07 — stare 2026-11-14: **încheiată tehnic** (toate criteriile BACKLOG îndeplinite); acceptare științifică restantă

| Criteriu BACKLOG E07 | Stare | Dovadă |
|---|---|---|
| Cele patru zone; starea comună; sursa de date API | Îndeplinit | `frontend/src/App.tsx`, `api/dataSource.ts`; test „four zones” |
| Glob: rotire, zoom, deplasare, resetare, orientare spre polul sud, grilă, marcaje, contur DEM, eticheta LOD | Îndeplinit | `globe/threeGlobe.ts`; verificat în Chrome (capturi descrise în VALIDARE) |
| Selecție prin raycasting cu distincția clic/rotire; coordonate manuale validate | Îndeplinit | `geo/globe.ts` + teste; în Chrome: clic central = situl focalizat, est la dreapta, drag ignorat |
| Control temporal: dată, oră UTC, interval, slider, redare/pauză | Îndeplinit | `ParamsForm`, `TimeBar`; Chrome: slider și Play |
| Direcțiile Soare/Pământ la situl activ, din rezultat | Îndeplinit | `bodyDirectionScene` + teste; săgeți și lumină în Chrome |
| Teste: transformări scenă ↔ coordonate | Îndeplinit | `geo/globe.test.ts` (axe, sensul longitudinii, UV, fețe, direcții) |
| Teste UI: catalog, clic pe glob, slider fără cereri noi, rezultate depășite | Îndeplinit | `App.test.tsx` (10 teste) |
| Verificarea timpurie a randării WebGL în mediul de test | Îndeplinit (2026-11-14) | Test automat Playwright 1.65.1 în Chromium headless (`frontend/e2e/webgl.spec.ts`, `npm run test:e2e`): context WebGL2 (SwiftShader), textura 200, cadru randat cu pixeli citiți înapoi (suprafață ≠ fundal, valori variate), fără erori JS; control negativ fără textură → eșec |
| Criteriu de finalizare: punct în 3D → simulare → derularea timpului actualizează direcțiile | Îndeplinit | Verificat în Chrome cu backend real (Chandrayaan-3, punct Leibnitz, Chang'e 4) |

Restant științific: valorile afișate provin din modul idealizat E06 (fără relief) și depind de deciziile ASTRO/GEO
deschise; globul texturat nu este DEM local (E08). Criteriile de acceptanță nu au fost modificate.

## E06 — stare 2026-11-14: implementare tehnică finalizată; acceptare științifică restantă

| Criteriu BACKLOG E06 | Stare | Dovadă |
|---|---|---|
| FastAPI cu `health`, `sites`, `coverage`, `simulations` (+ `terrain/manifest`) | Îndeplinit | `backend/lunarhorizon/api/app.py`; cereri HTTP reale în VALIDARE |
| Simulări asincrone, cache, serii temporale, `provenance`, `quality` | Îndeplinit | `api/jobs.py`, `simulation/idealized.py`; cache în memorie (limitat) |
| Erori în formatul stabilit | Îndeplinit | `application/problem+json`, validate față de schema `Problem` în `tests/test_api.py` |
| Teste de contract pentru fiecare endpoint | Îndeplinit | `tests/test_api.py` (25) cu răspunsuri validate față de JSON Schema |
| Erori de validare și de acoperire temporală | Îndeplinit | matrice de cereri invalide; `OUT_OF_EPHEMERIS_COVERAGE` cu limite pentru ambele profiluri |
| Aceeași cerere → aceeași simulare | Îndeplinit | același `id`, `cache_hit`, rezultat identic (și recalculat, fără `computed_at_utc`) |
| Apeluri concurente către SPICE | Îndeplinit | 6 fire cu 2 profiluri = rezultate secvențiale; 4 cereri HTTP simultane |
| O simulare idealizată întoarce rezultat complet conform schemei | Îndeplinit | `SimulationResult` validat prin Pydantic și JSON Schema; coerență cu `body_direction` |

Restant științific: rezultatele depind de D-02 (corecția), D-04/D-16 (criterii de vizibilitate), D-01–D-03 și de E04
(D-07, D-10, verificarea pozițiilor) rămase deschise; modul idealizat nu include relief și nu validează acoperirea
orizontului. Nu s-au schimbat criteriile de acceptanță.

## E05 — închidere 2026-11-14: implementare tehnică finalizată; acceptare științifică restantă

Stare declarată exact: **implementare tehnică finalizată; acceptare științifică restantă.** E05 nu este declarată
complet acceptată. Aprobările de produs ale utilizatorului (D-05, D-06, D-07, D-10, D-11, D-19) permit implementarea,
dar nu sunt validări [GEO]/[ASTRO]; vezi [E05_DECIZII.md](E05_DECIZII.md).

| Criteriu BACKLOG E05 | Stare | Dovadă |
|---|---|---|
| Scripturi de descărcare/inspecție, manifest cu metadate citite din fișier | Îndeplinit | `download_terrain.py`, `download_e05_auxiliary.py`, `verify_e05.py`; rezoluția fiecărui raster citită din transformare |
| Raster de calcul, eșantionare cu `NoData`/margini | Îndeplinit | `terrain/sampling.py`, `test_terrain_sampling.py`; `calculation.tif` identic cu sursa (SHA-256) |
| Teren vizual pe LOD și manifest valid; dimensiune consemnată | Îndeplinit | 520.950 și 131.661 octeți; manifest validat Pydantic și JSON Schema |
| Conturul acoperirii DEM, textura globului, fundaluri 2D | Îndeplinit tehnic | `raster_extent.geojson`, `globe.jpg`, `global_2d.tif`, `south_polar_2d.tif`; credit NASA SVS în SOURCES |
| Sume de control | Îndeplinit cu distincție | CRC membru ZIP verificat; SHA-256 local fixat și verificat; **MD5 publicat al arhivei complete neverificat** |
| D-05, D-06, D-19 „închise pe baza metadatelor reale” | **Restant științific** | Metadatele reale sunt consemnate și deciziile de produs aprobate; validarea [GEO] a sferei, a proiecției și a interpretării calității lipsește. `GLDSIGM` neinterpretat, exclus din indicatorii validați |
| D-07 / D-10 | **Deschise** | Punct reprezentativ provizoriu, nu loc de aterizare; `MOON_ME_DE421` ipoteză |

Acoperirea orizontului, `d_max` și convergența sunt E09; al doilea sit și comparația sunt E12. Rapoartele de mai jos
descriu istoricul și sunt înlocuite de acest tabel acolo unde diferă.


## Actualizare E05 — produse tehnice și criterii rămase

| Criteriu | Stare și dovadă |
|---|---|
| Achiziție și metadate | Realizate pentru rasterul provizoriu, cele trei auxiliare și textura NASA; SHA-256 fixat după prima achiziție, CRC al membrilor ZIP verificat; MD5 al întregului ZIP neverificat |
| Calcul, eșantionare, NoData/margini | Realizate și verificate pe pixel real și test sintetic; calculul rămâne separat de afișare |
| LOD și manifest | Realizate; manifest validat, SHA-256 și toate mediile/măștile verificate; vizualele au 520.950 și 131.661 octeți |
| Contur și fundaluri | Extinderea rasterului, textura globului și hărțile 2D globală/polară generate; D-11 și aprobarea creditării rămân deschise |
| Date de calitate | Hărțile NAC count și solar bins inspectate pe grila nativă de 15 m; nu sunt număr de impulsuri LOLA. GLDSIGM există, dar definiția sa nu este confirmată; D-19 rămâne deschisă |
| Reproducere | Achiziție selectivă, generare și verificare trecute într-o copie curată cu venv nou și versiuni fixate |
| Finalizare E05 | **Incompletă**: D-05/D-06/D-19 cer validare GEO și D-07 nu este decisă; manifestul este pentru un punct provizoriu |

Convergența orizontului și `d_max` sunt atribuite E09, nu cerințe noi pentru finalizarea E05. Alegerea și
implementarea celui de-al doilea sit/comparației apar la E12; D-07 trebuie totuși decisă conform proiectului.

## E05 — stare actuală, 2026-11-14

| Element | Stare | Dovezi / restanțe |
|---|---|---|
| Sursă reală și integritate | parțial | PGDA 104 Leibnitz Beta, CRC ZIP și SHA-256 local fixat; MD5 publicat al ZIP-ului complet nu a fost verificat |
| Raster calcul și eșantionare | implementat | Copie identică; interpolare biliniară cu NoData, NaN și margini necunoscute; teste sintetice și pixel real |
| Teren vizual și manifest | parțial | GeoTIFF 40/80 m, blocurile cu orice NoData rămân NoData; manifest validat față de Pydantic și JSON Schema |
| Primul sit D-07 | neconfirmat | Punct reprezentativ provizoriu, nu poziție de aterizare; PGDA 104 necesită aprobare pentru criteriul propus |
| Acoperire orizont | neconfirmată | `d_max` și convergența rămân deschise; fereastra locală testată nu le dovedește |
| Fundaluri, contur DEM, D-05/D-06/D-19 | incomplet | Conturul extinderii rasterului este generat; lipsesc globul și hărțile de fundal, iar deciziile GEO nu sunt închise |

## Actualizare 2026-11-14: retragerea IM-1 și IM-2

La cererea utilizatorului, IM-1 și IM-2 au fost eliminate din catalogul activ și din candidații D-07.
Catalogul are **10 intrări: 9 poziții efective și o țintă planificată**, inclusiv un singur sit CLPS (Blue Ghost 1).
Nu există încă un sit polar activ; selecția demonstrativă este goală și neconfirmată. E04, D-07 și D-10 rămân deschise.
E05 nu a început. Referințele la cele două situri în rapoartele și verificările precedente sunt istorice.
Rapoartele JSON arhivate rămân nemodificate: versiunea/hash-ul catalogului lor se referă la catalogul anterior,
nu la cel activ. Nu s-a efectuat o nouă reverificare în rețea a celor 10 poziții rămase.


Criteriile provin din [SPECIFICATIE.md](SPECIFICATIE.md) §2, §3.5, §10.3 și §19. Acest document este și tabelul
final al cerințelor P0 cerut la livrare.

**Stări permise:** „implementat și verificat”, „implementat, neverificat”, „incomplet”.
O cerință devine „implementat și verificat” numai cu o dovadă: un test rulat sau o verificare manuală datată.
Un screenshot sau o scenă decorativă nu este dovadă.

**Stare la 2026-11-14:** P0-07 este „implementat, neverificat” (E03, deschisă); P0-01 rămâne „incomplet” (E04, deschisă); celelalte cerințe P0 sunt „incomplet”.
Etapele E01–E03 au pus fundația tehnică, contractele și motorul astronomic (§7).

## P0 suplimentar — Earth–Moon–Sun (E10A)

**Obligatoriu**, solicitat de utilizator la 2026-11-14; nu bonus, nu parte din E08.
Stare: **neimplementat; verificări neexecutate**. Criteriile sunt în
[E10A_EARTH_MOON_SUN.md](E10A_EARTH_MOON_SUN.md): trei corpuri în 3D, distanțe între centre,
trasee calculate, sincronizare UTC, etichete de scară, proveniență, teste numerice și de browser,
includere în demonstrația offline. E17 trebuie să verifice și această cerință pentru închiderea MVP.

## 1. Cerințele P0

| ID | Cerință | Criteriu de acceptanță | Etapă | Stare | Dovadă |
|---|---|---|---|---|---|
| P0-01 | Catalog de situri | Catalogul conține situri Apollo, CLPS, alte misiuni și alte țări; fiecare poziție are sursă, dată a accesării și cadru; câmpurile necunoscute sunt goale și explicate | E04 | incomplet | Catalogul E04 are 10 intrări active cu surse deschise și reverificate (§7, E04), dar nu a fost verificat vizual de colegii de geografie și are lacune față de cerința „alte țări” (două misiuni internaționale). Vezi §7, E04 |
| P0-02 | Hartă 3D | Toate criteriile din §2 de mai jos | E07, E08, E12 | incomplet | — |
| P0-03 | Hartă 2D | Vedere polară sudică și globală; aceeași selecție și același timp ca în 3D; comutarea nu pierde starea | E11 | incomplet | — |
| P0-04 | Puncte custom | Un punct se poate alege prin clic (3D și 2D) și prin introducerea coordonatelor, cu validare; este marcat „custom” | E07, E11, E12 | incomplet | — |
| P0-05 | Comparație | 2–4 situri alăturate, aceiași indicatori în aceeași ordine, același interval și aceleași convenții; butonul Compare apare de la două situri | E12 | incomplet | — |
| P0-06 | Control temporal | Dată, oră UTC, interval, slider, redare și pauză; toate vederile urmează momentul curent | E07 | incomplet | — |
| P0-07 | Geometrie astronomică | Azimutul și elevația Soarelui și Pământului respectă toleranțele din [VALIDARE.md](VALIDARE.md) față de cazurile de referință | E03 | implementat, neverificat | Motorul `astro` este implementat. 22 de direcții se încadrează în pragurile **propuse** (separare max 4,75·10⁻⁷° față de pragul de 0,001°), dar T-01–T-03 nu sunt confirmate (D-12), iar D-01, D-02, D-03 și D-18 sunt deschise. Vezi §7, E03 |
| P0-08 | Orizont LOLA | Profil de orizont din relief real în zonele acoperite, cu indicator de calitate; datele lipsă nu sunt tratate ca altitudine zero | E09 | incomplet | — |
| P0-09 | Evenimente | Următoarea apariție și dispariție și timpul rămas, pentru ambele corpuri; cele patru situații de afișare din specificație | E10 | incomplet | — |
| P0-10 | Indicatori | Durata și procentul luminii, ferestrele de vizibilitate a Pământului, durata cu ambele criterii îndeplinite | E10 | incomplet | — |
| P0-11 | Moduri de utilizare | Modul simplu și modul expert afișează aceleași rezultate, la niveluri diferite de detaliu | E13 | incomplet | — |
| P0-12 | Trasabilitate | Sursele, modelele, versiunile și limitele sunt vizibile în interfață și în export | E13, E14 | incomplet | — |
| P0-13 | Demonstrație de rezervă | Scenariile precalculate rulează offline, inclusiv terenul 3D; combinațiile disponibile sunt indicate explicit | E15 | incomplet | — |
| P0-14 | Export | CSV pentru serii, JSON pentru configurație și metadate | E14 | incomplet | — |

## 2. Harta 3D — criterii obligatorii

Cerința P0-02 este îndeplinită numai când **toate** criteriile de mai jos sunt verificate. Un glob texturat
fără relief local nu este suficient. Excepția pentru dispozitive fără WebGL nu elimină cerința pentru dispozitivele compatibile.

Metodă: **A** — test automat; **M** — verificare manuală consemnată cu dată.

| ID | Criteriu | Metodă | Stare |
|---|---|---|---|
| 3D-01 | Harta 3D este vederea implicită la pornire, orientată spre polul sud | A | incomplet |
| 3D-02 | Globul lunar se poate roti, mări și deplasa; camera se poate reseta; nivelul de detaliu al globului este etichetat | A, M | incomplet |
| 3D-03 | Există teren local tridimensional generat din DEM real pentru cel puțin două situri polare demonstrative | A, M | incomplet |
| 3D-04 | „Mergi la sit” duce camera la situl ales; controalele și instrucțiunile pentru mouse și atingere sunt vizibile | A, M | incomplet |
| 3D-05 | Un clic pe glob sau pe teren selectează un punct și dă coordonate lunare corecte; gestul de rotire nu selectează | A | incomplet |
| 3D-06 | Selecția fără altitudine este semnalată ca fiind pe suprafața de referință | A | incomplet |
| 3D-07 | Latitudinea și longitudinea se pot introduce manual, sunt validate, iar punctul se poate adăuga la comparație | A | incomplet |
| 3D-08 | Situl activ și celelalte situri selectate au marcaje distincte, cu aceleași identificatoare și culori ca în comparație | A, M | incomplet |
| 3D-09 | Sunt disponibile vederea de sus, perspectiva oblică și vederea de la observator | A, M | incomplet |
| 3D-10 | Scara verticală implicită este 1×; orice exagerare este afișată permanent și nu modifică rezultatele | A | incomplet |
| 3D-11 | Observatorul este amplasat la altitudinea terenului plus înălțimea echipamentului | A | incomplet |
| 3D-12 | Transformările dintre cadrul lunar, cadrul local și scenă sunt documentate și testate, inclusiv semnul longitudinii și orientarea axelor | A | incomplet |
| 3D-13 | Direcțiile spre Soare și Pământ provin din același rezultat ca indicatorii și graficele; corpurile schematice sunt etichetate ca atare | A, M | incomplet |
| 3D-14 | Lumina urmează vectorul solar calculat; starea vizibil/ascuns vine din calculul numeric; limita umbrelor aproximative este afișată | A, M | incomplet |
| 3D-15 | Scena urmează sliderul UTC, redarea, data de început, durata și situl activ; rotirea camerei nu schimbă timpul sau rezultatele | A | incomplet |
| 3D-16 | Sunt afișate conturul acoperirii DEM, sursa, rezoluția și zonele `NoData`; golurile nu sunt completate | A, M | incomplet |
| 3D-17 | Mesh-ul vizual și datele de calcul își declară separat rezoluția; decupajul vizual nu limitează raza de căutare a orizontului | A | incomplet |
| 3D-18 | Terenul se încarcă progresiv sau pe niveluri de detaliu; resursele GPU sunt eliberate la schimbarea sitului | A | incomplet |
| 3D-19 | Există stări explicite pentru încărcare, eroare și lipsa datelor | A | incomplet |
| 3D-20 | Fără suport WebGL suficient, aplicația oferă harta 2D și explică indisponibilitatea 3D | A | incomplet |
| 3D-21 | Comutarea 3D/2D păstrează siturile selectate, momentul UTC și parametrii analizei | A | incomplet |
| 3D-22 | Scenariul offline include local codul, terenul, texturile și rezultatele; nu face cereri externe | A | incomplet |

## 3. Afișarea evenimentelor

| Situație | Afișare cerută | Stare |
|---|---|---|
| Corp vizibil și dispariție găsită | Timpul până la dispariție | incomplet |
| Corp deja ascuns | Starea „ascuns” și timpul până la apariție, dacă există | incomplet |
| Eveniment negăsit în interval | Mesajul că nu există eveniment în intervalul analizat | incomplet |
| Date insuficiente | Mesajul că evenimentul este indisponibil, cu motivul | incomplet |

## 4. Definiția MVP-ului

MVP-ul este complet numai după verificarea tuturor funcțiilor P0, când un utilizator poate:

| # | Capacitate | Cerințe acoperite |
|---|---|---|
| 1 | explora harta 3D implicită, cu glob lunar și relief DEM real pentru cel puțin două situri polare demonstrative | P0-02 |
| 2 | roti, mări și deplasa camera, selecta puncte în 3D și inspecta vederea de la observator | P0-02 |
| 3 | comuta 3D/2D fără pierderea selecției sau a timpului | P0-02, P0-03 |
| 4 | selecta între două și patru situri | P0-05 |
| 5 | adăuga un punct custom | P0-04 |
| 6 | alege și derula un interval UTC | P0-06 |
| 7 | vedea Soarele și Pământul față de orizont | P0-07, P0-08 |
| 8 | compara duratele și ferestrele de vizibilitate | P0-05, P0-10 |
| 9 | vedea timpul până la următoarea tranziție | P0-09 |
| 10 | identifica sursa și calitatea datelor | P0-12 |
| 11 | comuta între modul simplu și modul expert | P0-11 |
| 12 | exporta configurația și rezultatele | P0-14 |
| 13 | rula un scenariu demonstrativ offline, inclusiv terenul 3D și resursele locale | P0-13 |

## 5. Demonstrația principală

Scenariul de verificat cap-coadă, online și offline:

1. Aplicația pornește în harta 3D, la polul sud.
2. Se explorează relieful real pentru două situri.
3. Siturile se compară în același interval.
4. Se schimbă data de început.
5. Se arată cum relieful și mișcarea aparentă a Soarelui și Pământului modifică perioadele disponibile pentru activități la suprafață.

## 6. Bonusuri P1

Criteriile se detaliază la începutul etapei E18. Un bonus nu se începe cât timp o cerință P0 este incompletă.

| Bonus | Condiție minimă de acceptare |
|---|---|
| Traiectoria aparentă a Pământului | Denumirea principală „Earth apparent path / Libration”; forma rezultă din calcule |
| Eclipse | Tip propriu de eveniment; început, maxim, sfârșit; fracția discului solar ocultat; aproximațiile documentate |
| Întuneric | Intervale, cea mai lungă perioadă, cauza modelată; trunchierea marcată |
| Putere relativă | Indice între 0 și 1; înclinarea și azimutul panoului configurabile; aproximația binară declarată dacă este folosită |

## 7. Dovezi pe etape

Criteriile de finalizare ale etapelor din [BACKLOG.md](BACKLOG.md), cu dovada verificării.
**Stări:** „trecut” (rulat, cu rezultat bun), „eșuat”, „neexecutat” (cu motiv).

### E01 — Repository, GitHub, VS Code și CI (2026-11-14)

| Criteriu sau livrabil | Stare | Dovadă |
|---|---|---|
| Instalare din clonă curată după README, pe Windows | trecut | Clonă Git temporară în afara proiectului (CRLF, fără `.venv` și `node_modules`); comenzile PowerShell din README rulate exact: venv `py -3.13`, `pip install … --group …:dev` din wheels, `npm ci`, toate cu cod 0 |
| Lint, format, tipuri, teste și build în clona curată | trecut | Ruff check și format, mypy (3 fișiere), pytest 5/5, Prettier, oxlint, `tsc -b`, Vitest 2/2 și `vite build`, toate cu cod 0 |
| Build reproductibil | trecut | Build-ul din clonă și cel din repository au produs aceleași nume cu hash: `index-CQB0gKT6.js`, `index-D6iL3ZYY.css` |
| Lockfile-uri generate de managerii reali | trecut | `frontend/package-lock.json` (npm, lockfile v3); `backend/constraints.txt` (`pip freeze`) |
| Linterele opresc rularea la probleme | trecut | Fișier temporar cu o variabilă nefolosită: `npm run lint` a ieșit cu 1, iar fără el cu 0. Ruff și mypy au eșuat la primele rulări pe probleme reale, corectate apoi |
| Driverele COG și JPEG 2000 consemnate | trecut | `scripts/check_env.py` și testul `test_required_raster_drivers_available`: GTiff, COG, JP2OpenJPEG prezente (GDAL 3.12.2) |
| Versiuni în ARCHITECTURE, licențe în SOURCES | trecut | [ARCHITECTURE.md](ARCHITECTURE.md) §2, [SOURCES.md](SOURCES.md) §5 |
| Pagina se randează în browser | trecut | Server Vite local în Chrome (DevTools): titlu, descriere și anunțul de stadiu cu diacritice corecte; după eliminarea cererii `favicon.ico`, nicio eroare sau avertisment în consolă; toate cererile sunt locale |
| Configurația VS Code | parțial | Cele patru fișiere `.vscode/*.json` se parsează fără erori (verificare cu Node, după eliminarea comentariilor). Sarcinile și configurațiile de depanare nu au fost pornite din VS Code; comenzile pe care le apelează au fost rulate separat și trec |
| CI pe GitHub Actions | neexecutat | Nu există remote, iar crearea lui nu este autorizată (D-15). YAML-ul se parsează fără erori (Prettier), dar conformitatea cu schema GitHub Actions nu a fost verificată. Pașii rulează aceleași comenzi ca cele verificate local pe Windows; pe Ubuntu nu au fost rulați |
| Șabloane GitHub pentru issue și PR | neexecutat | Fișierele există; afișarea lor în GitHub cere remote |
| Validarea schemelor JSON în CI | neexecutat | Mutată la E02, când există schemele ([BACKLOG.md](BACKLOG.md)); adăugată la E02, vezi mai jos |

### E02 — Convenții comune și contracte (2026-11-14)

| Criteriu sau livrabil | Stare | Dovadă |
|---|---|---|
| Modulul `core` (unități, UTC, coordonate, ME, ENU, stereografic, cadre, erori) | trecut | `backend/lunarhorizon/core/`; `test_utc.py` (19), `test_coords.py` (103), `test_projection.py` (7) |
| Modulul `geo` din frontend, cu transformările către scena 3D | trecut | `frontend/src/geo/`; `scene.test.ts`: axe, orientare dreaptă, dus-întors, pol, ±180° |
| Vectori de test comuni Python ↔ TypeScript | trecut | `tests/vectors/conventions.json`, generat; `vectors.test.ts` îi verifică în TypeScript |
| Transformări dus-întors | trecut | Geografic ↔ ME ↔ ENU ↔ stereografic ↔ scenele 3D, sub T-04, inclusiv la ±90° și ±180° |
| Continuitate la ±180° | trecut | ME, proiecție și cadru local de o parte și de alta a antimeridianului; normalizarea 180 → -180 |
| Convenția la pol | trecut | La ±90°, „nordul” este meridianul dat și `azimuth_convention = pole_meridian`. Convenția rămâne provizorie (D-03) |
| Proiecția stereografică față de PROJ | trecut | Diferență ≤ 1 µm față de PROJ 9.7.1 pe 81 de puncte; parametrii coincid cu `IAU_2015:30135` |
| Concordanța Python ↔ TypeScript (T-05) | trecut | 93 de cazuri în `vectors.test.ts`: UTC, longitudine, latitudine, ME, bază ENU, azimut și elevație, cadru local, proiecție, constante |
| Testele detectează erori | trecut | Probă de mutație (semnul lui `y` în proiecție): 3 teste Python și 5 TypeScript au eșuat; după restaurare, trec |
| Scheme JSON: catalog, manifeste, rezultat, index de scenarii (plus cerere, stare, acoperire, erori) | trecut | `data/schemas/lunarhorizon.schema.json` (54 de definiții, 12 documente), generat din Pydantic |
| Modele Pydantic și tipuri TypeScript corespunzătoare | trecut | `backend/lunarhorizon/contracts/`; `frontend/src/contracts/generated.ts`; `contracts.test.ts` verifică fiecare proprietate |
| Codurile de eroare | trecut | `ErrorCode` (11 coduri), identic în Python, schemă și TS; fiecare cod are status HTTP |
| Zero, necunoscut, necalculat | trecut | Teste: zero fără motiv acceptat; `null` fără `quality.issues` respins; grup lipsă fără `not_computed` respins; grup prezent și declarat necalculat respins |
| Fixture-uri valide pentru Pydantic și JSON Schema; mutații respinse | trecut | 12 documente sintetice valide; 29 de mutații respinse de Pydantic, cele structurale și de JSON Schema |
| Sufixe de unitate în numele câmpurilor | trecut | Testul verifică schema generată; 5 excepții motivate (`status`, `level`, `coordinates`, `nodata_value`, `loc`) |
| T-04 și T-05 stabilite și respectate | trecut | [VALIDARE.md](VALIDARE.md) §2 și §5 |
| API.md înghețat ca versiune de schemă inițială | trecut | [API.md](API.md): versiunea 0.1.0; toate cele 91 de chei din exemple există în schemă (verificare automată) |
| Validarea schemelor adăugată în CI | parțial | Pașii `generate_contracts.py --check` și `contracts:check` sunt în `ci.yml`, iar pytest validează fixture-urile. Rulate local și în clona curată; pe GitHub neexecutat (fără remote) |
| Instalare și verificări din clonă curată după README (Windows) | trecut | Clonă cu CRLF: `pip --group` din lockfile-ul actualizat, `npm ci`, apoi toate verificările, cu cod 0 |

### E03 — Kerneluri și astronomie pentru un sit (2026-11-14)

**Stare: implementată, NEÎNCHEIATĂ** (după confirmarea astronomilor, comunicată de utilizator, rămân D-02 și T-01).
Criteriul de finalizare din [BACKLOG.md](BACKLOG.md) cere toleranțe
confirmate de colegii de astronomie și deciziile D-01, D-02, D-03 și D-18 închise. Niciuna nu este îndeplinită.

| Criteriu sau livrabil | Stare | Dovadă |
|---|---|---|
| Audit de compatibilitate cu materialul prototipului | trecut | [STATUS.md](STATUS.md), „Audit de compatibilitate E03”: D-02 contradictoriu (minor); D-18 și T-03 incomplete; restul compatibile ca propuneri |
| Manifestul kernelurilor și scriptul de descărcare cu sume de control | trecut | `data/manifests/kernels.json` (schema 0.2.0), `scripts/download_kernels.py`; 8 fișiere; MD5 NAIF și SHA-256 de referință potrivite; `--verify` fără rețea |
| Modulul `astro`: încărcarea profilului, acoperire, vectori, azimut, elevație, distanță, rază unghiulară | trecut | `backend/lunarhorizon/astro/`; acoperirea DE440 egală cu rezumatul NAIF; fișiere lipsă sau modificate refuzate (`KERNEL_MISSING`); momente din afara acoperirii refuzate cu limitele (`OUT_OF_EPHEMERIS_COVERAGE`) |
| Script Horizons care salvează cererea și răspunsul original | trecut | `scripts/query_horizons.py`; 26 de răspunsuri originale arhivate, cu URL, parametri, moment, status HTTP și SHA-256 (integritate verificată în teste) |
| Primele cazuri de referință care nu depind de catalog | parțial | R01–R04 și R09–R12, plus Apollo 11 (sit de referință) și un caz diagnostic la pol. R05–R08 cer siturile demonstrative (E04, D-07) și intervalul demonstrației (D-13) |
| Teste de timp: UTC, timestampuri fără zonă, limitele efemeridelor | trecut | E02 (UTC); E03: UTC ↔ ET, ET − UTC = 69,184 s, refuzul în afara acoperirii |
| Comparația cu Horizons (T-01, T-02) | trecut față de praguri **propuse** | 44 de comparații de direcții (`LT+S`, `CN+S`), max 4,75·10⁻⁷°; distanțe ≤ 6,8 m; vectori ICRF ≤ 2,29 m. Pragurile (0,001°, 0,1 km) sunt NEVALIDATE |
| Diferența dintre profiluri (T-03) | măsurat | Max 1,28·10⁻⁵°; prag propus 0,001°, NEVALIDAT |
| Verificări analitice independente de Horizons | trecut | Zenit din punctul sub-corp (±10⁻⁶°), cale SPICE alternativă (≤ 10⁻⁶ km), timp de lumină = D/c, rază unghiulară, convenția la pol, mărimea aberației |
| Azimutul nedefinit la zenit și nadir | trecut în `astro`; deschis în contract | `az_el_or_undefined` întoarce `None`; `BodySeries.azimuth_deg` nu acceptă `null` (E06) |
| Toleranțe confirmate de colegii de astronomie | **parțial** | Comunicat de utilizator: T-02 (0,1 km) și T-03 (0,001°) confirmate. **T-01 deschis**: 0,001° sau ≤ 1·10⁻⁵° (documentele păstrează ambele). Fără persoane și dată; nu există document-dovadă |
| D-01, D-02, D-03, D-18 închise și consemnate în SPEC_FIZICA | **parțial** | **D-01, D-03, D-18 confirmate** (comunicat de utilizator) și consemnate în SPEC_FIZICA/STATUS. **D-02 deschisă**: `LT+S` sau `CN+S` nu este ales. Alegerile rămase pentru E03: [STATUS.md](STATUS.md), „Ce mai lipsește pentru E03” |
| Testele cu kerneluri în CI | parțial | Jobul `astro` în `ci.yml`; rulat local; pe GitHub neexecutat (fără remote) |
| Clonă curată fără kerneluri | trecut | 199 trecute, 60 omise explicit (kerneluri), 0 eșuate; frontendul 162/162. Integritatea răspunsurilor arhivate a necesitat `data/reference/horizons/.gitattributes` (`-text`); după corectură, octeții sunt identici după clonare |
| Reverificare după E04 și confirmare | trecut | `pytest` 288/288 (inclusiv 60 cu kerneluri); `validate_e03.py` cu aceleași maxime; `download_kernels.py --verify` reușit. Nicio toleranță, caz sau rezultat așteptat modificat |

### E04 — Dovezi istorice înaintea retragerii IM-1/IM-2 (2026-11-14)

Starea activă este cea din actualizarea de la începutul documentului; tabelul de mai jos descrie catalogul anterior.

**Stare: implementată, NEÎNCHEIATĂ.** Criteriul de finalizare din [BACKLOG.md](BACKLOG.md) cere ca **geografii să fi verificat
vizual pozițiile** și ca **cele două situri polare demonstrative să fie alese**. Niciunul nu este îndeplinit.

| Criteriu sau livrabil | Stare | Dovadă |
|---|---|---|
| `data/catalog/sites.json` cu situri Apollo, polare, CLPS și internaționale | trecut, cu limită | 12 intrări: 6 Apollo; IM-1 și IM-2 (polare, CLPS); Blue Ghost 1 (CLPS); Chandrayaan-3 (poziție efectivă și țintă planificată); Chang'e 4. Limită: doar două misiuni „alte țări”; fără regiuni candidate |
| Fiecare poziție are sursă (URL, instituție, titlu, identificator, versiune, dată, locator, coordonate originale, convenții declarate) | trecut | Câmpul `position_sources`; testul `test_every_position_has_an_opened_original_with_locator_and_quote` |
| Pozițiile verificate la documentele originale | trecut | `scripts/verify_catalog_sources.py`: 0 eșecuri, 0 inaccesibile; produsul PDS LROC (SHA-256 `f0145e0b…`) redescărcat; citate găsite în 8 pagini HTML. 4 surse PDF verificate manual, neautomat |
| Apollo 11 verificat, inclusiv față de prototip | trecut | Identic cu prototipul (0 m); incertitudine publicată 0,3 m; altitudine −1926,289 m ([VALIDARE.md](VALIDARE.md) §7.3) |
| Ținta planificată și poziția efectivă distincte | trecut | `chandrayaan3_planned_target` ↔ `chandrayaan3_vikram` (369 m); IM-1, IM-2, Blue Ghost 1 au țintă doar ca regiune numită, fără coordonate inventate |
| Statutul misiunii verificat separat de statutul poziției | trecut | Câmpul `mission_status`; IM-2: ținta „Shackleton Connecting Ridge” din ianuarie 2024 documentată ca depășită de „Mons Mouton” (februarie 2025) |
| Convenții și conflicte | trecut, cu ipoteză | Longitudini est-pozitive normalizate din 0–360°; niciun conflict mediat; diferențele între surse păstrate. **Cadrul exact nu este declarat de nicio sursă**: adoptarea ca `MOON_ME_DE440_ME421` este o ipoteză în fiecare intrare |
| Valori necunoscute distincte de zero | trecut | `null` pentru agenție/operator Chang'e 4, incertitudinea țintei ISRO, altitudinea țintei; test dedicat |
| Validare structurală | trecut | `test_catalog.py`: 29 de teste (24 de mutații invalide respinse); schema 0.3.0; cititor `lunarhorizon.catalog` |
| Schema nu a fost relaxată | trecut | Schimbare minimă compatibilă (0.3.0): surse structurate, stare a verificării, notă de adopție, stare a misiunii, legătură țintă–poziție, selecție D-07 |
| Surse trecute în SOURCES | trecut | [SOURCES.md](SOURCES.md) §2.2 |
| **Colegii de geografie au verificat vizual pozițiile** | **incomplet** | Lista de verificare: [VALIDARE.md](VALIDARE.md) §7.6 |
| **Cele două situri polare demonstrative sunt alese (D-07)** | **incomplet** | Candidați neconfirmați: IM-2 „Athena” și IM-1 „Odysseus”; `demo_site_selection.status = unconfirmed`. Niciunul nu e în mozaicul de 5 m/pixel 87–90°S |
| D-10 confirmat de geografi | **incomplet** | Propunere implementată; neconfirmată |
| Lucrarea Icarus și PDF-ul LROC din 2016 | inaccesibile | HTTP 403 și 500; definiția incertitudinii nu a putut fi citită |
| Clonă curată fără kerneluri și fără date brute | trecut | 228 trecute, 60 omise explicit (kerneluri), 0 eșuate; `test_catalog.py` 29/29; frontend 166/166; Ruff, mypy și fișierele generate la zi |
