# E10A, E11 și comparația E12 — 2026-11-15

## Implementare

E10A continuă modificările locale existente peste `88b26f0`. API nou `POST /api/system/series`,
contract aditiv `SystemRequest` / `SystemSeries` versiunea 1.0.0, fără schimbarea simulării 0.8.0.
SPICE: centre SUN/EARTH/MOON, origine SUN, axe J2000, corecție NONE, epoci UTC convertite prin SPICE.
Distanțele provin din norma diferenței vectorilor în km; nu sunt distanțe de la observator.
Cache limitat la patru serii în backend și două în frontend, cu anularea cererilor depășite.
Scena: corpuri colorate (fără orientări de texturi inventate), linii, trasee deschise pe intervalul
încărcat, focus și zoom, UTC comun. 1 unitate = 2.000.000 km; deplasarea Lunii față de Pământ
exagerată 80×; razele sunt ilustrative. «Not to scale» permanent. Exportul JSON include metadatele.

E11: OpenLayers **10.11.0**, versiune fixată, BSD-2-Clause. Proiecții proprii `LUNAR:GEOGRAPHIC`
(grade cu metri/grad lunar) și `LUNAR:SOUTH` (stereografică, R=1.737.400 m, lon0=0°, pol sud).
Transformările refolosesc formulele proiectului verificate în E02; nu se atribuie EPSG terestre.
Fundalul NASA SVS E05 existent este reproiectat vizual în browser. Marcaje, clic, contururi DEM,
comutare global/polar și selecție comună cu globul. Cadrele surselor rămân declarate în catalog;
proiecția vizuală nu reprezintă o conversie între realizările ME. Eșecul inițial WebGL activează
2D cu explicație. Nu se folosesc servicii cartografice externe sau CDN.

E12: adăugarea selecției curente (catalog sau punct custom) într-o listă de 2–4 situri distincte,
cu refuz explicit al cadrelor diferite. Compare trimite **o singură cerere multisite** motorului
existent, cu același interval UTC, mod DEM/idealizat, înălțime, prag Pământ și criteriu solar.
Coloanele prezintă aceiași indicatori, necunoscutele separat, grafice pe aceeași scară și benzi
temporale. Activarea unei coloane schimbă situl scenei comune fără a reseta sliderul.
Modificarea listei invalidează rezultatul; răspunsurile vechi sunt ignorate prin `useSimulation`.
Schimbarea parametrilor marchează rezultatul ca vechi; Compare recalculează toate siturile.
Punctele fără DEM primesc eroarea backendului; nu se trece tacit la orizont idealizat.

## Limite și acceptare

- E10A: validarea independentă cu Horizons geometric și acceptarea ASTRO rămân deschise.
  Verificarea normelor față de vectorul SPICE direct are toleranță numerică 10⁻⁶ km, justificată
  de scăderea vectorilor heliocentrici în virgulă mobilă; nu este toleranță științifică validată.
- E15 încă trebuie să includă datele sistemului și comparația în scenarii offline; nu sunt
  declarate gata prin existența unui cache în memorie sau a exportului JSON.
- D-07/D-08/D-09/D-10 și acceptările GEO/ASTRO restante nu se închid prin implementarea UI.
  Leibnitz Beta și Connecting Ridge sunt puncte reprezentative DEM, nu locuri de aterizare.
- Nu există clasament automat sau afirmație că un sit este «mai sigur»; se compară indicatorii
  calculați în ipotezele documentate (inclusiv lipsa eclipselor).
- Validarea manuală pe telefon fizic rămâne E17. Testele automate nu o înlocuiesc.

## Surse tehnice consultate

- NAIF `spkpos`: https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/spkpos_c.html
- OpenLayers Projection: https://openlayers.org/en/latest/apidoc/module-ol_proj_Projection-Projection.html
- Creditarea NASA SVS și proveniența DEM/kernelurilor rămân cele din SOURCES și manifeste.
  Nu s-au importat materiale noi din Nasa-moon pentru aceste etape.

## Verificări

`backend/tests/test_system.py`: norme, simetrie, translație, epoci duplicate, două epoci SPICE
cu centrele comparate cu vectorul direct MOON/EARTH. `test_api.py`: contract, cache, lipsa
kernelurilor și epoca în afara acoperirii. Contractele sunt regenerate din Pydantic.
Frontend: transformare schematică, proiecții polare la seam/pol, cerere comună 2–4 situri,
refuz cadre incompatibile/duplicate. Testele App existente verifică ignorarea rezultatelor vechi.
Playwright: `system.spec.ts`, `map-comparison.spec.ts`; servere dedicate 8001/5174, fără reutilizarea
serverelor de dezvoltare, pentru a nu testa o versiune API veche. Rezultatele finale în VALIDARE.

Verificare finală: 4/4 teste browser trecute, inclusiv două situri DEM pe o zi și terenul activ.
E12 este funcțională pentru acest scenariu; 3–4 situri și schimbarea datei rămân de verificat
cap-coadă, la fel ca validarea științifică. E10A are Horizons geometric restant. Vezi VALIDARE.
