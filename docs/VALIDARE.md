# Validare — toleranțe, rezultate și probleme

Cerințele vin din [SPECIFICATIE.md](SPECIFICATIE.md) §14. Acest document are trei roluri: fixează toleranțele
înaintea implementării fiecărui modul, descrie testele și consemnează rezultatele obținute efectiv.

**Stare la 2026-11-14 (după E04 și confirmarea E03): T-04 și T-05 sunt stabilite și respectate. T-02 și T-03 sunt
confirmate de astronomi (comunicat de utilizator); T-01 rămâne deschis între 0,001° și ≤ 1·10⁻⁵° (D-12). T-06–T-09 nu sunt stabilite. Testele de
coordonate, longitudine, timp, contracte și astronomie sunt scrise și trec; restul testelor din §4 aparțin
etapelor ulterioare.**

## 1. Reguli

- O toleranță se stabilește înainte de implementarea modulului pe care îl verifică și conține: mărimea comparată,
  valoarea, motivul, sursa de referință și condițiile în care comparația este validă.
- Precizia numerică a unui algoritm și acuratețea fizică a rezultatului se evaluează separat. O rădăcină găsită
  la o secundă nu arată că apusul este cunoscut fizic la o secundă.
- Un test trecut se consemnează numai după rulare, cu data și comanda. Testele nerulate se listează cu motivul.
- Horizons verifică geometria astronomică. Nu verifică profilul de orizont din relief.

## 2. Toleranțe

Valorile marcate `NEVALIDAT` sunt propuneri de pornire și rămân așa până la confirmarea colegilor de astronomie
sau geografie (**D-12**). T-04 și T-05 sunt toleranțe numerice de implementare: verifică aritmetica, nu fizica,
și au fost stabilite la E02. Convențiile pe care le aplică (raza D-05, proiecția D-06, convenția la pol D-03)
rămân provizorii. Valorile sunt și în `backend/lunarhorizon/core/reference_vectors.py` (`TOLERANCES`), de unde
le citesc testele din ambele limbaje.

| ID | Mărime comparată | Referință | Propunere de pornire | Motiv | Condiții de validitate | Stare |
|---|---|---|---|---|---|---|
| T-01 | Azimut și elevație Soare/Pământ (criteriu: separarea unghiulară a direcțiilor) | Horizons, coordonate aparente, observator pe Lună | Propunere la E03: ≤ 0,001° (pragul prototipului separat). Măsurat: ≤ 4,75·10⁻⁷° (`LT+S`), ≤ 2,68·10⁻⁷° (`CN+S`). Alternativă recomandată spre decizie: ≤ 1·10⁻⁵° (vezi §6) | Eroarea astronomică nu trebuie să domine criteriul de vizibilitate; cu cel puțin un ordin de mărime sub raza unghiulară a Soarelui (~0,27°) | Aceeași poziție, altitudine, cadru și moment; separarea, nu azimutul, lângă zenit | **DESCHIS**: documentele păstrează două valori (0,001° propus; ≤ 1·10⁻⁵° recomandat); confirmarea comunicată nu o alege (D-12) |
| T-02 | Distanța până la corp; vectorul geometric ICRF | Horizons (`delta` în km; vectori `NONE`, ICRF) | Propunere la E03: ≤ 0,1 km pentru ambele. Măsurat: \|ΔD\| ≤ 6,8 m (sub rezoluția de afișare a Horizons pentru Soare, ~10 m); \|Δv\| ≤ 2,29 m | Intră numai în raza unghiulară (ΔD/D ~ 10⁻⁸) | Aceeași corecție de timp de lumină; pentru vectori, momentul TDB raportat de Horizons | **CONFIRMAT** (comunicat de utilizator; fără persoane și dată): 0,1 km pentru distanță și pentru vector (D-12) |
| T-03 | Diferența dintre profilurile `de440_me421` și `de421` | Calcul propriu, aceleași cazuri | Propunere la E03: ≤ 0,001°. Măsurat: separare ≤ 1,28·10⁻⁵°, \|ΔD\| ≤ 3,3 m | Justifică alegerea profilului (D-01); ordinul de mărime corespunde rotației dintre cadrele ME raportate de NAIF (≤ 5,8·10⁻⁷ rad) | Interval comun de acoperire (1900–2050) | **CONFIRMAT** (comunicat de utilizator; fără persoane și dată): 0,001° (D-12) |
| T-04 | Conversii de coordonate dus-întors; proiecția față de PROJ | Identitate; PROJ 9.7.1 pentru proiecție | Unghiuri ≤ 1e-9°; lungimi ≤ 1e-6 m (1 µm) | Transformările sunt exacte analitic. 1e-9° ≈ 3·10⁻⁵ m pe suprafață; eroarea de rotunjire `float64` la raza lunară este ~2·10⁻¹⁰ m. Pragurile sunt cu 3–4 ordine peste rotunjire și cu 6 ordine sub pixelul DEM de 5 m | Longitudinea se compară ca distanță orizontală (Δlon·R·cos lat), fiindcă la pol nu este definită | STABILIT (E02), toleranță numerică |
| T-05 | Concordanța Python ↔ TypeScript | Vectorii comuni `tests/vectors/conventions.json` | Unghiuri ≤ 1e-9°; lungimi ≤ 1e-6 m; componente de versori și factori de scară ≤ 1e-12; texte și coduri de eroare identice | Aceeași formulă în două limbaje; diferențele de 1 ulp dintre bibliotecile matematice (CPython, V8) sunt cu ordine de mărime sub prag | Aceleași intrări; aceleași constante (verificate în test) | STABILIT (E02), toleranță numerică |
| T-06 | Elevația orizontului pe teren sintetic | Soluție analitică (obstacol cunoscut) | De stabilit, în raport cu `Δa` și pasul radial | Verifică algoritmul, nu DEM-ul | Teren sintetic fără `NoData` | NEVALIDAT |
| T-07 | Convergența orizontului (rezoluție, `d_max`, `Δa`) | Calcul propriu la parametri dublați | De stabilit; mult sub raza unghiulară a Soarelui | Alegerea parametrilor din D-08, D-09 | Per sit demonstrativ | NEVALIDAT |
| T-08 | Momentul unui eveniment — precizie numerică | Rafinare cu toleranță mai strictă | De stabilit | Separă eroarea numerică de cea fizică | — | NEVALIDAT |
| T-09 | Poziția obiectelor în scena 3D față de rezultat | Direcția calculată din `az`/`el` | La nivelul erorii `float32` | Scena nu introduce erori proprii | Exagerare verticală 1× | NEVALIDAT |

Acuratețea fizică a momentelor de apariție și dispariție nu are o referință independentă în acest plan.
Estimarea ei (sensibilitatea la `Δa`, la înălțimea observatorului, la incertitudinea DEM-ului din `toterr`)
se discută cu colegii și se consemnează în [LIMITATIONS.md](LIMITATIONS.md).

## 3. Cazuri de referință astronomice

Între 10 și 15 cazuri. Pentru fiecare se păstrează configurația Horizons, răspunsul original și rezultatul
aplicației. Matricea de mai jos fixează ce trebuie acoperit; siturile și momentele concrete se aleg la E03,
după stabilirea catalogului și a intervalului demonstrației.

| Caz | Tip de sit | Longitudine | Condiție urmărită |
|---|---|---|---|
| R01 | Nepolar | Est | Soare sus pe cer |
| R02 | Nepolar | Vest | Soare sus pe cer |
| R03 | Nepolar | Est | Soare aproape de orizont |
| R04 | Nepolar | Vest | Pământ aproape de orizont (lângă limb) |
| R05 | Lângă polul sud, sit demonstrativ 1 | — | Începutul intervalului demonstrației |
| R06 | Lângă polul sud, sit demonstrativ 1 | — | Sfârșitul intervalului demonstrației |
| R07 | Lângă polul sud, sit demonstrativ 2 | — | Începutul intervalului demonstrației |
| R08 | Lângă polul sud, sit demonstrativ 2 | — | Sfârșitul intervalului demonstrației |
| R09 | Lângă polul sud | Est | Soare aproape de orizont |
| R10 | Lângă polul sud | Vest | Pământ aproape de orizont |
| R11 | Lângă meridianul ±180° | — | Continuitatea longitudinii |
| R12 | Fața îndepărtată | — | Pământ sub orizont |

### Configurația Horizons propusă

| Parametru | Valoare | Observații |
|---|---|---|
| Endpoint | `https://ssd.jpl.nasa.gov/api/horizons.api` | Documentul API 1.3 |
| `COMMAND` | `'10'` (Soare), `'399'` (Pământ) | — |
| `EPHEM_TYPE` | `'OBSERVER'` | — |
| `CENTER` | `'coord@301'` | Sintaxa apare în manualul Horizons, nu în pagina API; se confirmă la prima interogare |
| `COORD_TYPE` | `'GEODETIC'` | — |
| `SITE_COORD` | `'<longitudine E, grade>,<latitudine, grade>,<altitudine, km>'` | Ordinea și unitățile sunt din manual |
| `QUANTITIES` | azimut și elevație aparente, diametru unghiular, distanță | Codurile numerice se confirmă din antetul răspunsului |
| `TIME_TYPE` | `'UT'` | — |
| `APPARENT` | `'AIRLESS'` | Fără refracție |
| `ANG_FORMAT`, `CSV_FORMAT` | `'DEG'`, `'YES'` | — |

De reținut din documentație: erorile Horizons pot veni cu HTTP 200, deci conținutul răspunsului se verifică;
caracterele rezervate din parametri se codifică URL.

**[ASTRO] D-18.** Înainte de comparare se confirmă din antetul răspunsului: suprafața de referință față de care
Horizons măsoară altitudinea pe Lună, cadrul folosit și convenția azimutului. Fără aceste trei potriviri,
diferențele nu pot fi interpretate.

**Constatat la E03** în antetele celor 26 de răspunsuri arhivate (verificat automat de
`test_horizons_configuration_matches_project_conventions`):

| Element | Antet Horizons | Proiect | Potrivire |
|---|---|---|---|
| Suprafața de referință | `Center radii : 1737.4, 1737.4, 1737.4 km` | Sfera R_ref = 1 737 400 m | Da: altitudinea geodetică Horizons coincide cu înălțimea față de sfera proiectului, iar latitudinea geodetică cu cea planetocentrică |
| Cadrul | `Center pole/equ : MEAN_ME (high precision)` | `MOON_ME_DE440_ME421` | Compatibil; realizarea exactă a cadrului Horizons nu este numită în antet. Datele (T-03) arată un acord de 30–50 de ori mai bun cu profilul DE440 decât cu DE421 |
| Longitudinea | `{East-longitude positive}` | Est pozitiv | Da |
| Azimutul | Nespecificat în antet; manual: „clockwise from north” | De la nord spre est | Da, confirmat numeric (ΔA ≤ 1,03·10⁻⁶° pe toate cazurile) |
| Refracția | `Atmos refraction: NO (AIRLESS)` | Fără refracție | Da |
| Efemeridele | `{source: DE441}` | de440s | Diferite (familia JPL); acordul nu este o validare independentă |
| Devierea luminii | `Rel. light bend : Sun, EARTH` | Nemodelată | Diferență de model, sub pragurile propuse |

Convenția azimutului la polul exact: în cazul diagnostic `p90_exact_south_pole` (longitudinea 0), azimutul
Horizons coincide cu convenția D-03 (ΔA = 5,7·10⁻⁹° pentru Soare). Asta nu demonstrează convenția Horizons
pentru alte longitudini la pol. Decizia D-18 rămâne a colegilor de astronomie.

### Cazurile E03 arhivate

Definite în `data/reference/horizons/cases.json`; cererile și răspunsurile originale sunt în același director.
Coordonatele au fost alese cu motorul propriu numai pentru a obține geometria cerută; valorile de referință
vin din Horizons. Cazurile R05–R08 cer siturile demonstrative (E04, D-07) și intervalul demonstrației (D-13).

| Caz | Matrice | Poziție, moment | Altitudine (suprafață + observator) |
|---|---|---|---|
| `a11_dem` | A11 | Apollo 11, 0,67416°N 23,47314°E, 2026-11-14T12:00Z | −1926,687 m (scalar DEM al prototipului, neverificat) + 2 m |
| `a11_catalog` | A11V | Același punct; și vectori ICRF | −1926 m (catalogul prototipului, neverificat) + 2 m |
| `r01_east_sun_high` | R01 | 1°S 115°E, 2026-11-14T12:00Z | 0 m (valoare de test) + 2 m |
| `r02_west_sun_near_zenith` | R02 | 0° 60°V, 2026-11-29T12:00Z | 0 + 2 m |
| `r03_east_sun_near_horizon` | R03 | 0° 31°E, 2026-11-14T12:00Z | 0 + 2 m |
| `r04_west_earth_near_horizon` | R04 | 0° 91,5°V, 2026-11-14T12:00Z | 0 + 2 m |
| `r09_pole_east_sun_near_horizon` | R09 | 89°S 45°E, 2026-11-14T12:00Z | 0 + 2 m |
| `r10_pole_west_earth_near_horizon` | R10 | 86°S 5°V, 2026-11-14T12:00Z | 0 + 2 m |
| `r11_antimeridian_east` / `_west` | R11 | 30°S 179,9999°E / 179,9999°V | 0 + 2 m |
| `r12_far_side_earth_below` | R12 | 15°N 150°V, 2026-11-14T12:00Z | 0 + 2 m |
| `p90_exact_south_pole` | diagnostic | 90°S, longitudine 0 | 0 + 2 m |

## 4. Teste necesare

Lista din specificație, cu etapa din [BACKLOG.md](BACKLOG.md) în care apare fiecare test.

| Domeniu | Test | Etapă | Stare |
|---|---|---|---|
| Coordonate | Conversie dus-întors între harta 2D, scena 3D și coordonate lunare; axe și unități | E02, E07, E11 | Parțial: lunar ↔ ME ↔ ENU ↔ stereografic ↔ scenele 3D scris și trecut (E02); harta 2D la E11, raycasting la E07 |
| Longitudine | Continuitate la ±180°; normalizare din [0, 360) | E02 | Scris, trecut (Python și TypeScript) |
| Poli | Convenția azimutului și a nordului la ±90°; dus-întors lângă pol | E02 | Scris, trecut (convenția rămâne provizorie, D-03) |
| Timp | UTC, respingerea timestampurilor fără zonă, conversii, limitele efemeridelor | E02, E03 | Scris, trecut: UTC (E02); UTC ↔ ET, ET − UTC = 69,184 s, acoperirea egală cu intervalul publicat de NAIF, refuzul momentelor din afara acoperirii (E03) |
| Contracte | Fixture-uri valide prin Pydantic și JSON Schema; mutații respinse; zero / necunoscut / necalculat; sufixe de unitate; fișiere generate la zi | E02 | Scris, trecut |
| Astronomie | Comparație cu referințele Horizons | E03 | Scris, trecut față de pragurile **propuse** (nevalidate): 22 de direcții × 2 corecții, 2 vectori ICRF, T-03; verificări analitice independente (zenit din punctul sub-corp, cale SPICE alternativă, timp de lumină, rază unghiulară, convenția la pol) |
| Kerneluri | Fișiere lipsă sau modificate refuzate; sume de control verificate | E03 | Scris, trecut |
| Orizont | Teren sintetic cu obstacol cunoscut; curbură | E09 | Nescris |
| DEM | `NoData` și margini; pixelul lipsă nu devine altitudine zero | E05, E09 | Nescris |
| Evenimente | Tranziții scurte, contacte aproape tangente, rafinare temporală | E10 | Nescris |
| Hartă 3D | Glob navigabil, teren DEM real, rotire/zoom, raycasting, observator pe teren, resetarea camerei | E07, E08 | Nescris |
| Sincronizare 3D | Schimbarea timpului sau a sitului actualizează corpurile și indicatorii; camera și exagerarea verticală nu modifică rezultatele | E08, E10 | Nescris |
| Calitate 3D | `NoData` vizibil, fallback WebGL explicit, stări de încărcare și eroare, resurse GPU eliberate, scenariu offline cu teren local | E08, E11, E15 | Nescris |
| Interfață | 2–4 situri sincronizate | E12 | Nescris |
| Concurență | Rezultatele vechi nu înlocuiesc selecția nouă | E06, E12 | Nescris |
| Offline | Scenariu precalculat complet funcțional, fără cereri externe | E15 | Nescris |
| Eclipse (dacă bonusul este implementat) | Fără suprapunere, parțială, totală | E18 | Nescris |
| Putere (dacă bonusul este implementat) | Panou orientat spre Soare, perpendicular, opus | E18 | Nescris |

## 5. Rezultate

Format pentru fiecare rulare: data, etapa, comanda, numărul de teste trecute și eșuate, abaterile maxime față
de toleranțe, trimitere la fișierele de referință.

| Data | Etapă | Comandă | Rezultat | Observații |
|---|---|---|---|---|
| 2026-11-14 | E01 | `python -m pytest` (în `backend/`) | 5 trecute, 0 eșuate | Teste de fum: Python 3.13, versiunea pachetului, `float64` implicit, CSPICE legat, drivere GDAL obligatorii. Nu verifică nicio mărime fizică |
| 2026-11-14 | E01 | `npm test` (în `frontend/`) | 2 trecute, 0 eșuate | Randarea componentei rădăcină. Nu verifică nicio mărime fizică |

Ambele rulări au fost repetate într-o clonă curată, pe Windows, cu același rezultat. Testele nu au fost rulate pe Linux.

| Data | Etapă | Comandă | Rezultat | Observații |
|---|---|---|---|---|
| 2026-11-14 | E02 | `python -m pytest` (în `backend/`) | 187 trecute, 0 eșuate | UTC (19), coordonate (103), proiecție (7), contracte (53), fum (5). Abaterea maximă față de PROJ și la dus-întors este sub pragurile T-04 (valoarea maximă nu este înregistrată numeric; testele verifică pragul) |
| 2026-11-14 | E02 | `npm test` (în `frontend/`) | 161 trecute, 0 eșuate | Concordanța cu vectorii (T-05), scenele 3D și proprietățile independente (T-04), acoperirea schemei de către tipuri, componenta rădăcină |
| 2026-11-14 | E02 | Probă de mutație: semnul lui `y` inversat în proiecție, în ambele limbaje | Python: 3 eșuate; TypeScript: 5 eșuate; după restaurare, toate trec | Arată că testele detectează o eroare reală de convenție, nu doar că trec |

Testele de proiecție compară implementarea cu PROJ, deci cu o referință independentă. Vectorii comuni au ieșiri
calculate de Python: confirmă concordanța dintre limbaje, nu corectitudinea Python, care este verificată separat.

**E03 (2026-11-14).** Raport complet, reproductibil fără rețea: `data/reference/horizons/e03_comparison.json`
(`scripts/validate_e03.py`).

| Data | Etapă | Comandă / verificare | Rezultat | Observații |
|---|---|---|---|---|
| 2026-11-14 | E03 | `scripts/download_kernels.py` | 8 fișiere descărcate de la NAIF; toate sumele așteptate se potrivesc | MD5 publicat de NAIF: `de440s.bsp`, `de421.bsp`. SHA-256 al descărcării anterioare a prototipului: toate cele 5 fișiere DE440. Fără sumă de referință: `moon_pa_de421_1900-2050.bpc`, `moon_080317.tf` |
| 2026-11-14 | E03 | `scripts/query_horizons.py` | 26 de cereri, toate HTTP 200 cu tabel; 0 erori | 24 de tabele de observator, 2 de vectori; răspunsurile originale arhivate cu SHA-256 |
| 2026-11-14 | E03 | `python -m pytest` (în `backend/`) | 259 trecute, 0 eșuate, 0 omise | 60 cu marcajul `kernels`: 44 de comparații de direcții (22 × 2 corecții), 2 vectori ICRF, 1 T-03, 1 diagnostic la pol și 12 verificări analitice, de acoperire și de erori; plus 12 teste E03 fără kerneluri (manifest, arhivă, antete D-18, azimut nedefinit) |
| 2026-11-14 | E03 | Comparație `de440_me421`, `LT+S`, 22 de direcții | Separare max 4,748·10⁻⁷° (`r02`, Pământ); \|ΔD\| max 6,8 m | ΔA max în valoare absolută 1,03·10⁻⁶° (R11, Pământ); Δe max 4,72·10⁻⁷° |
| 2026-11-14 | E03 | Comparație `de440_me421`, `CN+S`, 22 de direcții | Separare max 2,676·10⁻⁷°; \|ΔD\| pentru Pământ ≤ 0,15 m | `CN+S` este mai aproape de Horizons decât `LT+S` (relevant pentru D-02) |
| 2026-11-14 | E03 | Vectori geometrici ICRF, Apollo 11 | \|Δv\| = 2,288 m (Soare), 2,217 m (Pământ) | La momentul TDB raportat de Horizons |
| 2026-11-14 | E03 | T-03 (DE440 față de DE421) | Separare max 1,280·10⁻⁵°; \|ΔD\| max 3,3 m | Profilul DE421 față de Horizons: separare max 1,280·10⁻⁵° |
| 2026-11-14 | E03 | Clonă curată, fără kerneluri | Prima rulare: 1 eșec (SHA-256 al unui răspuns arhivat). După corectură: 199 trecute, 60 omise, 0 eșuate | Cauza: conversia finalurilor de linie de către Git (`text=auto`, `core.autocrlf=true`). Corectura: `data/reference/horizons/.gitattributes` cu `-text` pentru răspunsurile originale |
| 2026-11-14 | E03 | Sensibilitate (în memorie, fără modificarea codului): cadrul `IAU_MOON` în loc de ME; semnul longitudinii inversat | `IAU_MOON`: separare 2,2·10⁻⁴°–3,0·10⁻³°; longitudine inversată: ≥ 2·10⁻⁴° | Pragul propus de 0,001° nu ar detecta în toate cazurile o eroare de cadru `IAU_MOON` |

**Comparație cu rezultatele prototipului separat** (material de referință, nu dovadă de validare). Pentru
Apollo 11 (`a11_dem`), motorul acestui proiect reproduce valorile din Anexa D a promptului E03:
geometric 91,48569018441597° / −7,0722235559248°, aparent `CN+S` pentru Pământ
277,587180458052° / 64,31995263152103°. Acordul este așteptat: aceleași kerneluri (SHA-256 identice) și
aceeași metodă. Răspunsurile Horizons noi coincid cu valorile arhivate de prototip pentru același caz
(Soare 91,485714365° / −7,066568067°). Fișierele originale ale prototipului nu există pe acest calculator.

**Ce nu dovedesc aceste rezultate.** Acordul cu Horizons compară două implementări JPL (DE440s + ME DE440
local; DE441 + MEAN_ME la Horizons), nu observații independente. Precizia numerică, de ordinul 10⁻⁷°, nu este
incertitudinea fizică. Aceasta este dominată de poziția sitului (necunoscută, D-10), de altitudine și de model
(devierea luminii, criteriul centrului discului).

**Reverificare E03 după E04 și după confirmarea astronomilor (2026-11-14).** Rulări noi, ale implementării curente,
distincte de rezultatele prototipului separat: `python -m pytest` în `backend/` → **288 trecute**, 0 eșuate, 0 omise
(inclusiv cele 60 de teste cu kerneluri și 29 noi pentru catalog); `scripts/validate_e03.py` → aceleași maxime ca înainte
(separare 4,748·10⁻⁷° `LT+S`, 2,676·10⁻⁷° `CN+S`, T-03 1,280·10⁻⁵°, vectori 2,288 m); `scripts/download_kernels.py
--verify` → reușit, manifestul nemodificat. Singura modificare din date: `schema_version` din `data/manifests/kernels.json`
(0.2.0 → 0.3.0; structura manifestului nu s-a schimbat). Nicio toleranță, caz de referință sau rezultat așteptat nu a fost
modificat. Sensibilitate măsurată: înălțimea de suprafață a Apollo 11 (−1926,687 / −1926,0 / −1926,289 m) schimbă
direcțiile cu ≤ 2,5·10⁻⁸°; 8 m de înălțime a observatorului cu ≤ 5·10⁻⁷°.

## 6. Probleme deschise

| Problemă | Detalii | Decizie |
|---|---|---|
| Pragul T-01 propus (0,001°) este larg | Acordul obținut este de 4,75·10⁻⁷°. Un prag de 0,001° nu ar detecta sigur folosirea cadrului `IAU_MOON` (abatere de 2,2·10⁻⁴°–3,0·10⁻³°). Un prag de 1·10⁻⁵° ar separa clar acordul actual de o eroare de cadru, dar ar respinge profilul DE421 față de Horizons (1,28·10⁻⁵°) | D-12 [ASTRO] |
| Corecția aparentă | `LT+S` (propunerea proiectului) și `CN+S` diferă cu ~2,7·10⁻⁷° pentru Pământ; `CN+S` este mai aproape de Horizons. Niciuna nu modelează devierea gravitațională a luminii | D-02 [ASTRO] |
| Azimutul la zenit | Motorul E03 întoarce `None`; contractul 0.2.0 (`BodySeries.azimuth_deg`) nu acceptă `null` | Schimbare de schemă la E06 |

## 7. Catalogul siturilor (E04)

Două tipuri de verificare, tratate separat. Un catalog care trece prima nu este prin asta corect științific.

### 7.1. Validare structurală (automată, offline)

`backend/tests/test_catalog.py` (29 de teste), rulat și de CI în jobul `backend`. Verifică: validarea față de schema
Pydantic și JSON Schema; identificatori stabili și unici; coordonate și cadre în domeniu; ținta planificată și poziția
efectivă ca intrări distincte și legate reciproc; zero, necunoscut (`null`) și necalculat; proveniența obligatorie a
fiecărei poziții (document deschis, locator, citat, convenții declarate); coordonatele adoptate egale cu originalul
normalizat; incertitudinea egală cu cea publicată; coroborările în limita de 100 m (detectează un conflict, nu îl
mediază); selecția D-07 neconfirmată; respingerea a 24 de mutații invalide ale catalogului real; legătura cu cazurile
astronomice E03. Rezultat: 29/29 trecute; suita backend completă: 288 trecute.

### 7.2. Verificare la sursele originale (rețea)

`scripts/verify_catalog_sources.py --write-report`, rulat la 2026-11-14; rezultat arhivat în
`data/catalog/source_verification.json`: **0 eșecuri, 0 inaccesibile** pe 12 intrări. Concret: produsul PDS
(`ANTHROPOGENIC_OBJECTS_180.ZIP`, SHA-256 `f0145e0b…e4408b`) redescărcat, cu `LATITUDE`, `LONGITUDE`, `UNCERTAIN` și
`RADIUS` egale cu catalogul pentru cele 11 poziții efective; citatele din paginile HTML (LROC, NASA, ISRO) găsite
în textul paginilor. **Nu verifică automat** cele 4 surse PDF (kituri de presă NASA): au fost citite manual în sesiune,
iar citatele corespund textului extras. O verificare reușită arată că documentul original conține valorile din catalog;
nu arată că poziția este corectă fizic.

### 7.3. Apollo 11: poziția, convențiile și diferențele față de prototip

| Element | Valoare | Sursa și locul |
|---|---|---|
| Latitudine, longitudine (est pozitiv) | 0,67416°N, 23,47314°E | Produs PDS, înregistrarea `A11_LM` (`LATITUDE`, `LONGITUDE`); tabelul LROC din 2016, rândul „Apollo 11 LM”, dă aceleași valori |
| Incertitudine publicată | 0,3 m (câmpul `UNCERTAIN`; tabelul din 2016: 0,3) | Metoda și nivelul de încredere nu sunt definite în README; LROC afirmă separat o nesiguranță orbitală de ≈ ±15 m. Cele două nu au fost combinate și nu s-a dedus nimic din numărul de zecimale |
| Altitudine | −1926,289 m (RADIUS 1 735 473,711 m − 1 737 400 m); tabelul din 2016: −1926 m | Față de sfera de 1 737 400 m |
| Cadru | Produsul: `GCS_Moon_2000`, sferă de 1 737 400 m. Tabelul din 2016: „ME”. Realizarea (versiunea DE) **nu este declarată de nicio sursă** | Adoptarea ca `MOON_ME_DE440_ME421` este o **ipoteză** explicită (D-10) |
| Diferență față de prototip | **0 m** (coordonate identice) | Prototipul folosea aceleași valori |
| Altitudinea cazurilor E03 | `a11_catalog`: −1926,0 m (Δ = +0,29 m față de catalog); `a11_dem`: −1926,687 m (Δ = −0,40 m) | Cazurile E03 **nu au fost modificate**; testul `test_apollo11_position_matches_the_e03_reference_cases` verifică egalitatea coordonatelor și Δ < 1 m al altitudinii |

Efectul asupra E03: poziția Apollo 11 nu s-a schimbat, iar diferențele de altitudine (< 0,5 m din ~1,7·10⁶ m) sunt
cu mult sub orice prag de direcție. Referințele Horizons și rezultatele E03 rămân valabile pentru aceleași intrări;
nu a fost nevoie de reinterogări. Rezultatele E03 nu devin prin asta „validate pentru noile coordonate”: coordonatele
sunt aceleași.

### 7.4. Diferențe între catalog și valorile prototipului (în metri pe sfera de 1 737 400 m)

| Intrare | Distanță | Cauza documentată |
|---|---|---|
| Apollo 11, 12, 14, 15, 16, 17 | 0 m | Valori identice (prototipul le lua din aceeași sursă LROC) |
| IM-2 | 0,08 m | Prototipul: 29,1957°E (pagina LROC); produsul: 29,19567°E |
| Chang'e 4 | 2,1 m | 177,5885°E (pagina LROC din 2020) față de 177,5886°E (produs) |
| Blue Ghost 1 | 8,4 m | Prototipul: 18,562°N, 61,810°E (rotunjit); produsul: 18,5622°N, 61,8102°E; pagina LROC: 18,5623°N, 61,8103°E |
| Chandrayaan-3 | 14,2 m | Prototipul (sursă secundară NSSDCA) și pagina LROC din 2023: −69,3741°, 32,32°E; produsul actualizat: −69,374°, 32,3187°E. Depășește ușor incertitudinea publicată de 10 m; motivul relocalizării nu este documentat |
| IM-1 | 74,8 m | Prototipul: valorile rotunjite la două zecimale (−80,13°, 1,44°E), identice cu paginile LROC și NASA; produsul: −80,1276°, 1,4367°E. Rotunjirea de ±0,005° explică diferența |

Altitudinile derivate din `RADIUS` diferă de valorile DEM ale prototipului cu până la 11,5 m (IM-1) și 8,4 m
(Apollo 12). Altitudinea din catalog nu intră în calculele E03; diferențele nu au fost evaluate pentru E05.

### 7.5. Conflicte și puncte deschise

| Subiect | Constatare | Stare |
|---|---|---|
| Cadrul exact al coordonatelor | Nicio sursă nu numește realizarea cadrului (DE421/DE440). Produsul actual declară numai `GCS_Moon_2000`; pagina din 2016 declară „ME” fără realizare. NAIF raportează ≈ 0,5–1 m între realizările ME DE421 și DE440 | **Deschis** (D-10, geografie). Ipoteză consemnată în fiecare intrare |
| Semnificația `UNCERTAIN` | Definită doar ca „Uncertainty of the coordinates in meters”. Valorile 10,0 la mai multe intrări „NAC DTM” par nominale. Pagina Chang'e 4 dă 13 m (95% CI) față de 10 m în produs | Valorile publicate sunt păstrate separat; lucrarea Icarus este inaccesibilă |
| Poziții de țintă planificată | Numerică doar pentru Chandrayaan-3 (ISRO). IM-1, IM-2 și Blue Ghost 1 au doar regiuni numite | Fără coordonate inventate |
| „Shackleton Connecting Ridge” | Punctul prototipului este locația unui turn din studiu termic NASA Langley; kitul NASA din ianuarie 2024 listase „Shackleton Connecting Ridge” pentru IM-2, ulterior înlocuit cu Mons Mouton | Exclus din catalog (vezi `demo_site_selection.excluded`) |
| Regiuni candidate Artemis III | Documente oficiale cu geometrie neîncercate | Neincluse |
| Verificarea vizuală (criteriul E04) | Nu a fost făcută de colegii de geografie | **Deschis** |

### 7.6. Listă de verificare vizuală pentru colegii de geografie

Criteriul de finalizare E04 cere verificarea vizuală pe un produs adecvat. Pentru fiecare intrare: poziția din
`sites.json` pe LROC QuickMap sau Moon Trek, față de imaginea NAC citată în sursă.

| Intrare | Imagine NAC de referință (din surse) | Ce se verifică |
|---|---|---|
| `apollo11_lm` … `apollo17_lm` | pagina 938 nu citează imagini NAC individuale; imaginea se alege la verificare | Treapta de coborâre a modulului lunar la coordonatele din catalog |
| `im1_odysseus` | NAC M1463440322L | Landerul în craterul degradat de ~1 km (pagina 1360) |
| `im2_athena` | NAC M1496181900LR (și imaginea din pagina 1409) | Landerul într-un crater de ~20 m |
| `blueghost1_lander` | NAC M1495619099LR | Landerul pe marginea craterului de ~12 m |
| `chandrayaan3_vikram` | NAC M1447750764LR | Landerul în caseta albă de 338 m (pagina 1314) |
| `chandrayaan3_planned_target` | — | Zona primară de 4 km × 2,4 km din jurul valorii ISRO, față de poziția efectivă (369 m distanță) |
| `change4_lander` | NAC M1357657468LR | Landerul și urmele roverului Yutu-2 (pagina 1168) |

Procedură pentru verificator: deschide QuickMap sau Moon Trek într-un browser funcțional, activează produsul
georeferențiat și imaginea NAC corespunzătoare; introdu pe rând latitudinea și longitudinea estică din catalog,
confirmă cadrul și localizează vizual obiectul. Pentru Apollo alege și notează o imagine NAC identificabilă. Pentru
ținta Chandrayaan-3 compară cu zona ISRO și eticheteaz-o ca planificată, fără să o tratezi ca poziție efectivă.
Pentru fiecare intrare consemnează produsul, ID-ul imaginii, coordonatele, cadrul, rezultatul, diferența observată,
eventualele limite, data și persoana; păstrează capturi sau linkuri reproductibile. Nu marca rezultate fără inspecție.
Browserul interactiv al sesiunii nu este disponibil; pagina QuickMap consultată ca text cere JavaScript. Verificarea
nu a fost efectuată și criteriul E04 rămâne deschis.

### 7.7. Analiza preliminară PGDA 78 pentru candidații D-07

Pe baza raportului arhivat `data/catalog/pgda_coverage.json`, nu a unei noi descărcări. Distanțele sunt față de
dreptunghiurile proiectate, în planul stereografic, aproximative; nu sunt distanțe geodezice sau măsurători ale
pixelilor valizi. Transformarea adoptă provizoriu coordonatele catalogului în ME DE421, fără corecție de cadru.

| Raster | Extindere X/Y (km) | Rezoluție | Distanță IM-1 la dreptunghi (km) | Distanță IM-2 (km) |
|---|---|---|---:|---:|
| DM1 | 154–174 / 51,5–71,5 | 5 m/pixel | 271,43 | 101,65 |
| DM2 | 147–167 / 85–105 | 5 m/pixel | 239,76 | 77,29 |
| Haworth | −52,9–−23,1 / 75,6–105,4 | 5 m/pixel | 197,01 | 105,38 |
| LM1 | 2–22 / −2–18 | 5 m/pixel | 282,01 | 132,04 |
| LM2 | 2–22 / 47–67 | 5 m/pixel | 233,01 | 89,87 |
| LM3 | 4–24 / 37–57 | 5 m/pixel | 243,01 | 96,85 |

Toate cele șase declară `NoData = NaN`; ambele puncte sunt în afara fiecărei extinderi, deci nu a fost citit niciun
pixel la pozițiile candidaților (`valid_pixel = null`), nici evaluată proporția de date valide. Niciunul nu poate
furniza teren local pentru IM-1 sau IM-2. Celelalte 21 de rastere au eșuat cu HTTP 403; acoperirea lor rămâne
necunoscută. Pentru o selecție sunt necesare extinderi reale, pixelul și vecinătatea validă pentru fiecare sit,
masca NoData, calitatea/interpolarea și compararea iluminării/vizibilității pentru același interval. Un pixel valid
singur nu demonstrează acoperirea pentru orizont. Nu există dovezi suficiente pentru a recomanda primul sit.

### 7.8. Cadrele și limita verificării D-10

Toate cele 12 intrări au `frame_id = MOON_ME_DE440_ME421`, dar câmpul este cadrul intern **adoptat**, nu dovada
cadrului original. Pentru 11 poziții produsul LROC declară `GCS_Moon_2000`, cu sfera și meridianul său, fără a
identifica realizarea ME/DE. Pentru ținta planificată ISRO cadrul este nedeclarat. Catalogul păstrează coordonatele
originale, `frame_realization_stated = false` și o notă de adopție; validatorul cere egalitate cu originalul
normalizat, nu efectuează o transformare între cadre. Incertitudinea publicată este păstrată, dar incertitudinea
suplimentară a ipotezei nu este cuantificată; o diferență între două realizări cunoscute nu cuantifică un cadru
de sursă necunoscut. [NAIF](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/Tutorials/pdf/individual_docs/23_lunar-earth_pck-fk.pdf)
descrie cadrele ME ca specifice efemeridelor, cu DE440 ME apropiat de DE421 ME; aceasta nu dovedește cadrul LROC
sau ISRO. D-10 cere confirmarea cadrului ori acceptarea explicită a ipotezei și tratarea incertitudinii de către
geografie. Nota țintei ISRO afirmă greșit că broșura nu a fost deschisă; corecția catalogului trebuie să țină cont
de hash-ul catalogului din raportul PGDA și să nu fie interpretată ca schimbare a sursei primare.

### 7.9. Evaluare preliminară PGDA 104 (2026-11-14)

**Aria cerută.** Nu există încă o rază numerică fixată pentru calcul: `d_max`, produsul îndepărtat și pasul se
aleg prin convergență la D-08/D-09 ([SPEC_FIZICA.md](SPEC_FIZICA.md) §6.3, T-07). Calculul cere probe pe toate
azimuturile până la `d_max`, pe două niveluri de teren; lipsurile dau rezultat `partial` sau `no_data`. Decupajul
vizual este separat, iar dimensiunea sa se reglează la E08. Nu se poate valida o arie numerică nedefinită.

**Inventar și metodă.** [PGDA 104](https://pgda.gsfc.nasa.gov/products/104) indică 13 regiuni din 2022,
SDEM-uri rezultate din LOLA și LROC NAC, produse auxiliare și [Zenodo](https://zenodo.org/records/17954508)
ca arhivă. API-ul listează 13 ZIP-uri (26.559.678.852 octeți în total) și un README; MD5-urile sunt publicate de
Zenodo, dar arhivele integrale nu au fost descărcate sau verificate. HTTP Range a returnat 206. Din fiecare ZIP
s-au citit indexul și primul MiB decomprimat al rasterului `GLDELEV_005.tif`; metadatele tuturor celor 13 sunt în
`data/catalog/pgda104_extent_check.json` (hash-ul catalogului inclus). Nu s-au testat pixelii sau integritatea
integrală a rasterelor. Toate declară 5 m/pixel, NoData −3,4028234663852886e38 și proiecție stereografică
polară sudică Moon 2015, IAU:30135, sferă de 1.737.400 m. README-ul regiunii Leibnitz indică înălțimi față de
aceeași sferă. Eticheta proiecției singură nu confirmă realizarea cadrului fizic al coordonatelor.

**Rezultat pentru candidați.** Presupunând coordonatele catalogului compatibile cu cadrul raster, ambele puncte
se află în afara tuturor celor 13 dreptunghiuri raster. Cel mai apropiat dreptunghi de IM-2 este Leibnitz Beta
Plateau, la aproximativ 11,99 km în planul proiectat; de IM-1, Malapert Massif, la aproximativ 168,01 km.
Aceste distanțe nu sunt geodezice și nu cuantifică incertitudinea cadrului. Nu există pixel central în aceste
rastere; nu au fost verificate valori valide sau suprafețe complete în jurul candidaților. Nu se poate propune
IM-1 sau IM-2 drept primul sit pe baza PGDA 104. Nici iluminarea comparativă, nici vizibilitatea Pământului,
nici D-10 nu sunt confirmate de această verificare.

**Alternativă mai grosieră.** [PGDA 90](https://pgda.gsfc.nasa.gov/products/90) declară 80–90°S la 20 m/pixel,
respectiv 83–90°S la 10 m/pixel. Pe baza latitudinilor catalogului, IM-1 și IM-2 sunt în banda nominală de 20 m,
iar IM-2 și în cea de 10 m; extinderea reală, pixelii și NoData nu au fost inspectate. Nici 10 m, nici 20 m nu
îndeplinesc criteriul propus D-07 de 5 m/pixel. Produsele rămân eventuale surse pentru teren îndepărtat, după
verificarea compatibilității și decizia D-08; nu se aprobă relaxarea criteriilor.
