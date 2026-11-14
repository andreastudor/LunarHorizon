# Stare
## E05 — închidere tehnică, 2026-11-14 (preluare de la Codex)

**Implementare tehnică finalizată; acceptare științifică restantă.** Stare reverificată: 289 teste backend trecute
(cu kerneluri) și `scripts/verify_e05.py` trecut, fără recreare de date. Utilizatorul a aprobat de produs, pentru
implementare, D-07 (punct reprezentativ provizoriu Leibnitz Beta, nu loc de aterizare), D-05/D-06/D-10 (sfera de
1.737.400 m și proiecția citite din raster; `MOON_ME_DE421` rămâne ipoteză, fără conversii), D-19 (NAC și categorii de
azimut separate, fără praguri, nu număr LOLA) și D-11 (fundaluri NASA SVS provizorii). Acestea nu sunt validări
[GEO]/[ASTRO]. `GLDSIGM` (investigat 30 de minute: nicio sursă consultată nu îl definește) rămâne neinterpretat și
exclus din indicatorii validați. Rezoluția auxiliarelor este citită din raster (15 m pentru GLDMASK/GLDSBCT). MD5-ul
publicat al arhivei complete nu este verificat; CRC-ul membrilor și SHA-256 local sunt. Detalii: [E05_DECIZII.md](E05_DECIZII.md),
[ACCEPTANCE.md](ACCEPTANCE.md). Restanțe E05: validările [GEO] D-05/D-06/D-10/D-19, D-11 creditare, D-07 final.


## E05 — progres suplimentar, 2026-11-14

Au fost achiziționate selectiv trei produse auxiliare PGDA 104 și textura globală NASA SVS 2K; s-au pregătit
fundaluri 2D globale și polare, un manifest de proveniență și scriptul `scripts/verify_e05.py`. S-a reprodus
achiziția și generarea într-o copie curată și într-un mediu virtual nou cu dependențele fixate. Rezultatele și
condițiile de creditare sunt în VALIDARE și SOURCES. **E05 rămâne parțială:** D-05, D-06 și D-19 nu sunt validate,
iar D-07 nu este decisă. Propunerile concrete și limitele sunt în [E05_DECIZII.md](E05_DECIZII.md).

Acoperirea până la `d_max`, produsul îndepărtat și convergența sunt D-08/D-09, E09; nu sunt adăugate ca
test de închidere E05. Extinderea DEM și datele lipsă trebuie totuși afișate onest. Al doilea sit și comparația
sunt cerințe ulterioare E12, deși D-07 privește alegerea celor două situri.

## E05 — implementare parțială (2026-11-14)

Există un raster real NASA PGDA 104 pentru Leibnitz Beta Plateau și un punct **reprezentativ provizoriu**, nu
loc de aterizare și nu selecție D-07 confirmată. `scripts/download_terrain.py` descarcă numai membrul ZIP prin
HTTP Range, verifică CRC ZIP și SHA-256 fixat după prima achiziție (nu MD5-ul arhivei întregi). `scripts/build_terrain.py`
produce o copie neschimbată pentru calcul și două rastere vizuale separate; `terrain/sampling.py` tratează NoData,
NaN, zero și marginile. Manifestele sunt în `data/manifests/`; datele mari sunt în `data/_raw/` și `data/_cache/`.

Raster 5 m/pixel, 16 × 16 km, punctul ales −85,4266039743°, 31,7441821732°E; 201 × 201 pixeli în jurul lui
sunt valizi. Nu se afirmă acoperire completă pentru orizont: `d_max` nu este stabilit. PGDA 104 diferă de produsele
propuse la D-07, iar `MOON_ME_DE421` este o ipoteză, nu un cadru confirmat. D-05, D-06, D-19, D-07, D-10 și E04
rămân deschise. Există conturul geografic al extinderii rasterului, nu o garanție a acoperirii orizontului.
Lipsesc fundalurile globale/2D și un al doilea sit; E05 nu este finalizată.
Verificări și limite: [VALIDARE.md](VALIDARE.md) și [HANDOFF_CLAUDE.md](HANDOFF_CLAUDE.md).

## Actualizare 2026-11-14: retragerea IM-1 și IM-2

La cererea utilizatorului, IM-1 și IM-2 au fost eliminate din catalogul activ și din candidații D-07.
Catalogul are **10 intrări: 9 poziții efective și o țintă planificată**, inclusiv un singur sit CLPS (Blue Ghost 1).
Nu există încă un sit polar activ; selecția demonstrativă este goală și neconfirmată. E04, D-07 și D-10 rămân deschise.
La momentul retragerii E05 nu începuse; situația curentă este în secțiunea de mai sus. Referințele la cele două situri în rapoartele și verificările precedente sunt istorice.
Rapoartele JSON arhivate rămân nemodificate: versiunea/hash-ul catalogului lor se referă la catalogul anterior,
nu la cel activ. Nu s-a efectuat o nouă reverificare în rețea a celor 10 poziții rămase.


Actualizat: 2026-11-14 (după E04 și confirmarea E03).

## Unde suntem

**E03 (kerneluri și astronomie pentru un sit) rămâne DESCHISĂ**, deși astronomii au confirmat convențiile și
configurația de referință (comunicare a utilizatorului, vezi „Confirmarea E03”). Confirmarea nu alege între variantele
pe care documentele le păstrează încă; alegerile care lipsesc sunt listate exact în „Ce mai lipsește pentru E03”.
**E04 (catalog minim verificat) este implementată, dar NU este încheiată**: poziția fiecărei intrări a fost
verificată la documentul original, însă colegii de geografie nu au verificat vizual pozițiile (criteriu obligatoriu), iar
cele două situri demonstrative nu sunt alese (D-07). E01 și E02 sunt încheiate local. Pe GitHub, CI-ul nu a rulat
niciodată (fără remote). Dovezile sunt în [ACCEPTANCE.md](ACCEPTANCE.md) §7, iar rezultatele în
[VALIDARE.md](VALIDARE.md) §5 și §7.

| Există | Nu există încă |
|---|---|
| Documentele de proiectare (E00); mediul de lucru, CI, VS Code (E01) | Funcții de produs: hartă 3D, orizont, API, comparație |
| `core` / `geo`, contracte, schema JSON (acum 0.3.0), tipuri TS generate (E02) | DEM, texturi (E05) |
| Kerneluri NAIF verificate; motorul `astro`; 26 de referințe Horizons arhivate (E03) | Server backend și `/api/health` (E06) |
| Catalog de 10 intrări (6 Apollo, 1 CLPS, 2 internaționale și o țintă planificată), cu proveniență; cititor; script de reverificare la surse (E04) | Verificarea vizuală a pozițiilor de către geografi; alegerea siturilor demonstrative (D-07); aprobarea D-10 |
| 288 de teste Python (60 cu kerneluri) și 166 TypeScript | Alegerile E03 listate mai jos; remote GitHub, rulare CI |

Fișierele E00–E04 sunt în commit-ul local `4fcac8c`; `971c8ca` adaugă o verificare exploratorie PGDA și raportul
parțial. Ramura curentă este `e04-completare-dovezi`. Kernelurile (~62 MB) stau în `data/kernels/`, în afara Git.
Nu există remote configurat și CI GitHub nu a rulat.

### Istoric anterior retragerii: verificarea dovezilor PGDA și a surselor

- Raportul `data/catalog/pgda_coverage.json` este incomplet: 27 rastere listate, 6 citite și 21 cu HTTP 403.
  Pentru cele șase citite, ambele puncte se află în afara extinderii; nu se poate concluziona pentru celelalte 21.
  Hash-ul corespundea catalogului de la data raportului, anterior retragerii siturilor. Cadrul DE421 este o ipoteză, iar acoperirea unui pixel nu dovedește acoperirea orizontului.
- Broșura ISRO, pagina 6, coroborează coordonatele **țintei planificate** Chandrayaan-3, nu poziția efectivă.
  USGS publică grile pentru regiunile Artemis din 2024, dar descărcarea geometriei a fost blocată de verificarea site-ului.
  Lucrarea Icarus și PDF-ul LROC au răspuns anterior cu HTTP 403, respectiv 500.
- E04, D-07 și D-10 rămân deschise: verificarea vizuală cerută și alegerea susținută de acoperire nu sunt demonstrate.

### Istoric anterior retragerii: investigația pentru deblocarea E05

**Actualizare PGDA 104:** metadatele rasterelor de elevație din toate cele 13 arhive au fost citite prin HTTP
Range; IM-1 și IM-2 se află în afara tuturor extinderilor, sub ipoteza de cadru consemnată. Nu există bază pentru
o propunere D-07 privind aceste două situri. `d_max` nu are încă valoare numerică stabilită; analiza, sursele și
limitele sunt în [VALIDARE.md](VALIDARE.md) §7.9 și `data/catalog/pgda104_extent_check.json`. PGDA 90 este mai
grosier decât 5 m/pixel. E05 nu a început; D-07 și D-10 rămân deschise.

Cele șase rastere citite sunt la 5 m/pixel și au NoData NaN, dar IM-1 și IM-2 sunt în afara fiecărei extinderi;
niciun pixel la sit nu a fost citit. Distanțele și limitele analizei sunt în [VALIDARE.md](VALIDARE.md) §7.7.
Restul de 21 au răspuns cu 403; nu se poate deduce acoperirea lor. Nu există bază suficientă pentru alegerea
primului sit. D-10 rămâne deschis: cadrul sursei nu este demonstrat și transformarea nu este făcută (§7.8).
Browserul interactiv este indisponibil; verificarea vizuală nu a fost efectuată, iar procedura este în §7.6.

Au fost identificate produse alternative descrise în [SOURCES.md](SOURCES.md): NASA PGDA 104 cu arhive SDEM
de 5 m/pixel, PGDA 90 cu DEM-uri mai grosiere și QuickMap ca sursă a regiunilor USGS. Niciunul nu a fost inspectat
la nivel de pixel sau geometrie în această etapă. PGDA 104 nu este produsul 78 sau 81 numit în criteriul propus D-07;
acceptarea sa și compatibilitatea pentru calcul ar necesita o decizie documentată. Următorul pas: obținerea legitimă
a datelor ori a metadatelor de extindere pentru situri și verificarea pixelilor/NoData, apoi decizia D-07 și D-10.

## Confirmarea E03 (comunicată de utilizator)

Utilizatorul a comunicat că astronomii au confirmat **convențiile, configurația de referință și criteriile de
validare discutate pentru E03**. Persoanele, data și forma confirmării nu au fost furnizate și nu sunt înregistrate;
nu există un document-dovadă în repository. Acest paragraf este singura consemnare.

Efectul asupra deciziilor, numai în măsura în care conținutul lor este lipsit de ambiguitate în documente:

| ID | Stare după confirmare | Temei |
|---|---|---|
| D-01 | **Confirmată** (comunicat): profil implicit `de440_me421`, `de421` ca verificare încrucișată | O singură configurație în documente; kerneluri și manifest fără ambiguitate |
| D-03 | **Confirmată** (comunicat): planul local perpendicular pe direcția radială; la pol, nordul = meridianul longitudinii date; azimut nedefinit la zenit și nadir | O singură configurație în SPEC_FIZICA §4 și §5.1 |
| D-18 | **Confirmată** (comunicat): configurația Horizons și potrivirile din VALIDARE §3 (sferă de 1737,4 km, `MEAN_ME`, longitudine estică, fără refracție) | Un singur set de parametri, cu dovezi din 26 de antete |
| D-02 | **Rămâne deschisă** | Documentele păstrează `LT+S` (implicit provizoriu) și `CN+S` (mai aproape de Horizons); confirmarea nu spune care este alegerea |
| D-12 | **Parțial**: T-02 și T-03 confirmate (valori unice: 0,1 km, respectiv 0,001°); T-01 deschis; T-04 și T-05 stabilite la E02; T-06–T-09 neconfirmate | T-01 are două valori în documente (0,001° propus; ≤ 1·10⁻⁵° recomandat) |

## Ce mai lipsește pentru E03

Criteriul de finalizare din [BACKLOG.md](BACKLOG.md) cere D-01, D-02, D-03 și D-18 închise și toleranțe confirmate.
Rămân patru alegeri, toate numite exact:

1. **D-02:** care corecție aparentă este cea de referință, `LT+S` sau `CN+S`. Implicitul din cod și din SPEC_FIZICA este `LT+S`.
2. **T-01:** valoarea numerică a pragului: 0,001° sau ≤ 1·10⁻⁵°. Rezultatele curente trec ambele (maxim 4,75·10⁻⁷°), dar pragul de 0,001° nu ar detecta sigur folosirea cadrului `IAU_MOON` (abateri de 2,2·10⁻⁴°–3,0·10⁻³°).
3. **Înălțimea de suprafață de referință a Apollo 11.** Documentele păstrează trei valori: −1926,687 m (`a11_dem`, scalar DEM din prototip), −1926,0 m (`a11_catalog`, catalogul prototipului) și −1926,289 m (catalogul E04, din `RADIUS` LROC). Nu influențează numeric rezultatele: diferențele dintre ele schimbă direcțiile cu ≤ 2,5·10⁻⁸°. Alegerea este una de documentare.
4. **Înălțimea observatorului:** 2 m este folosită în toate cazurile E03, dar este decizia D-14 (ECHIPĂ, „propunere”), care nu este închisă. O creștere de 8 m schimbă direcțiile cu ≤ 5·10⁻⁷°.

Nicio toleranță nu a fost modificată și niciun rezultat așteptat nu a fost schimbat. Verificările obligatorii E03 au fost
rulate din nou în implementarea actuală (după E04): suita completă 288/288, inclusiv cele 60 de teste cu kerneluri;
`scripts/validate_e03.py` cu aceleași maxime ca înainte (4,748·10⁻⁷°, 2,676·10⁻⁷°, 1,280·10⁻⁵°, 2,288 m); și
`scripts/download_kernels.py --verify` reușit. Aceste rezultate sunt ale implementării curente, distincte de cele ale
prototipului separat.

## Istoric: rezultatul E04 înaintea retragerii siturilor

| Verificare | Rezultat |
|---|---|
| Intrări | 12: Apollo 11, 12, 14, 15, 16, 17 (modulul lunar); IM-1, IM-2, Blue Ghost 1 (CLPS); Chandrayaan-3 (poziție efectivă și țintă planificată, intrări distincte); Chang'e 4 |
| Tipuri de poziții | 11 poziții efective, 1 țintă planificată numerică (ISRO). 0 regiuni, 0 puncte reprezentative. IM-1, IM-2, Blue Ghost 1: ținta planificată este doar o regiune numită, fără coordonate (consemnat în `planned_target_note`) |
| Reverificare la sursele originale (rețea) | 0 eșecuri, 0 inaccesibile; produsul PDS LROC (actualizat 2026-08-14) redescărcat, SHA-256 verificat; citate găsite în paginile HTML |
| Surse PDF (kituri NASA CLPS) | citite manual în sesiune; nu se verifică automat |
| Apollo 11 | 0,67416°N, 23,47314°E: **identic cu prototipul** (0 m); incertitudine publicată 0,3 m; altitudine −1926,289 m. E03 neafectată (cazurile nu au fost modificate) |
| Diferențe față de prototip | IM-1 74,8 m (rotunjirea prototipului); Chandrayaan-3 14,2 m; Blue Ghost 1 8,4 m; Chang'e 4 2,1 m; IM-2 0,08 m; Apollo 0 m |
| Validare structurală | 29 de teste, trecute; schema a trecut la 0.3.0 |
| Clonă curată, fără kerneluri și fără date brute | trecut: 228 trecute, 60 omise explicit, 0 eșuate; frontend 166/166 |
| Verificare vizuală de către colegii de geografie | **neexecutată** (criteriu obligatoriu) |
| Alegerea siturilor demonstrative (D-07) | **neexecutată** |

Constatări:

- **Punctul „Shackleton Connecting Ridge” din prototip nu este un sit.** Documentul sursă (NASA NTRS 20240009936, pagina 8) este un studiu termic al unui turn; coordonatele au fost „chosen to match available average seasonal surface temperature flight data from LRO”. Nu intră în catalog.
- **O țintă mai veche nu mai descrie planul:** kitul NASA din ianuarie 2024 listează „Shackleton Connecting Ridge” pentru IM-2; kitul din februarie 2025 și LROC dau Mons Mouton, respectiv 84,79°S, 29,2°E.
- Nicio sursă nu numește realizarea cadrului (DE421/DE440). Adoptarea ca `MOON_ME_DE440_ME421` este o **ipoteză**, consemnată în fiecare intrare.
- Niciun sit din catalog nu se află în mozaicul PGDA de 5 m/pixel (87–90°S). Criteriul 1 al D-07 (DATA_PLAN §3.1) nu poate fi îndeplinit cu intrările actuale decât dacă un DEM PGDA 78 acoperă IM-1 sau IM-2 (de verificat la E05).
- Lucrarea Icarus (Wagner et al.) și PDF-ul LROC din 2016 sunt inaccesibile; definiția coloanei de incertitudine nu a putut fi citită.
- Schema de date a trecut la 0.3.0: intrarea de catalog primește surse structurate, starea verificării, nota de adopție, starea misiunii, legătura țintă–poziție și starea selecției D-07 ([API.md](API.md)).

## Rezultatul E03

| Verificare | Rezultat |
|---|---|
| Audit de compatibilitate cu materialul prototipului | făcut (secțiunea de mai jos) |
| Descărcarea kernelurilor și verificarea sumelor (MD5 NAIF, SHA-256 de referință) | trecut, 8/8 |
| Acoperirea profilului DE440 față de rezumatul publicat de NAIF | identică |
| Interogări Horizons, cu răspunsurile originale arhivate | 26/26 HTTP 200, 0 erori |
| Direcții față de Horizons, 22 de cazuri × 2 corecții | separare max 4,75·10⁻⁷° (`LT+S`), 2,68·10⁻⁷° (`CN+S`); prag propus 0,001°, nevalidat |
| Distanțe și vectori ICRF față de Horizons | \|ΔD\| ≤ 6,8 m; \|Δv\| ≤ 2,29 m; prag propus 0,1 km, nevalidat |
| T-03, DE440 față de DE421 | max 1,28·10⁻⁵°; prag propus 0,001°, nevalidat |
| Verificări analitice independente de Horizons | trecut |
| Ruff, mypy, pytest (259), frontend (162 de teste, build) | trecut |
| Instalare și toate verificările într-o clonă curată (fără kerneluri) | trecut: 199 de teste trecute, 60 omise explicit; frontendul 162/162. Prima clonă a găsit o eroare reală: Git convertea finalurile de linie ale răspunsurilor Horizons arhivate și le schimba octeții. Corectată cu `data/reference/horizons/.gitattributes` (`-text`), fără a atinge `.gitattributes` de la rădăcină |
| Jobul CI `astro` pe GitHub | neexecutat: nu există remote |
| Confirmarea colegilor pentru D-01, D-02, D-03, D-18, T-01–T-03 | **lipsă**: E03 rămâne deschisă |

Constatări:

- Motorul reproduce exact valorile prototipului pentru Apollo 11. Este de așteptat: aceleași kerneluri (SHA-256 identice) și aceeași metodă. Nu este o validare suplimentară.
- `CN+S` este mai aproape de Horizons decât `LT+S` (Pământ: 2,7·10⁻⁷° față de 4,7·10⁻⁷°). Este un argument tehnic pentru D-02, nu o decizie.
- Horizons folosește DE441, cadrul `MEAN_ME (high precision)`, raza 1737,4 km și devierea gravitațională a luminii. Profilul DE421 se abate de la Horizons de ~30–50 de ori mai mult decât DE440, un argument tehnic pentru D-01.
- Pragul propus T-01 de 0,001° nu ar detecta sigur folosirea cadrului `IAU_MOON` (abateri de 2,2·10⁻⁴°–3,0·10⁻³°). Recomandare spre decizie: ≤ 1·10⁻⁵° ([VALIDARE.md](VALIDARE.md) §6).
- Contractul de date nu poate transmite un azimut nedefinit (zenit/nadir); schimbarea de schemă se face la E06.
- Schema de date a trecut la 0.2.0: manifestul de kerneluri distinge sumele calculate de sumele de referință ([API.md](API.md)).

## Rezultatul E02

| Verificare | Rezultat |
|---|---|
| Dus-întors, ±180°, poli, proiecție față de PROJ (T-04) | trecut |
| Concordanța Python ↔ TypeScript pe vectorii comuni (T-05) | trecut |
| Contracte: fixture-uri prin Pydantic și JSON Schema, mutații, zero / necunoscut / necalculat, sufixe de unitate | trecut |
| Fișierele generate (schemă, vectori, tipuri TS) la zi | trecut |
| Probă de mutație (eroare de semn introdusă intenționat) | detectată în ambele limbaje |
| Ruff, mypy, oxlint, Prettier, TypeScript, build | trecut |
| Instalare și toate verificările într-o clonă curată (Windows) | trecut |
| CI pe GitHub Actions | neexecutat: nu există remote |

Constatări:

- `IAU_2015:30135` din PROJ 9.7.1 are exact parametrii provizorii ai proiecției. Asta nu confirmă CRS-ul fișierelor PGDA (D-06 rămâne deschisă).
- Precizia comună a timpului este milisecunda (limita lui `Date` din JavaScript). Secunda intercalară `:60` este respinsă la intrare și consemnată în [LIMITATIONS.md](LIMITATIONS.md).
- Regulile dintre câmpuri („`null` cere motiv”, „grup prezent sau declarat necalculat”) nu se pot exprima în JSON Schema; le impun validatorii Pydantic din backend.
- Dependențe noi, fixate: Pydantic 2.14.3 (rulare), jsonschema 4.26.0 și json-schema-to-typescript 16.0.0 (dezvoltare).

## Rezultatul E01

| Verificare | Rezultat |
|---|---|
| Instalare după README într-o clonă curată (Windows, PowerShell) | trecut |
| Ruff, mypy, pytest (5 teste de fum) | trecut |
| Prettier, oxlint, TypeScript, Vitest (2 teste de fum), build Vite | trecut; build reproductibil (aceleași hash-uri) |
| Pagina în browser (Chrome, server Vite local) | trecut; consolă fără erori după eliminarea cererii `favicon.ico` |
| Sarcinile și configurațiile de depanare pornite din VS Code | neexecutat |
| CI pe GitHub Actions (Ubuntu și Windows) | neexecutat: nu există remote |

Constatări care schimbă planul:

- Wheel-ul Rasterio 1.5.2 include GDAL 3.12.2 cu driverele **COG**, **JP2OpenJPEG** și **PDS**; utilitarele GDAL în linie de comandă nu sunt necesare.
- Pachetele binare SpiceyPy (CSPICE N0067) și Rasterio există pentru Python 3.13 pe Windows.
- Șablonul oficial Vite folosește **oxlint**, nu ESLint, iar TypeScript este la 7.0; planul a fost ajustat ([ARCHITECTURE.md](ARCHITECTURE.md) §2).
- Lockfile-ul backendului este un fișier de constrângeri generat cu `pip freeze`; `pip lock` este experimental și dependent de platformă.
- Consola Windows (cp1250) nu poate afișa „ț”; `check_env.py` înlocuiește caracterele neafișabile, iar sarcinile VS Code și CI setează `PYTHONUTF8=1`.

## Restanțe externe (E01–E04)

Pentru publicarea ulterioară sunt necesare:

1. Crearea remote-ului GitHub și primul push.
2. Prima rulare a CI pe GitHub Actions (Ubuntu și Windows, plus jobul `astro`) și corectarea eventualelor diferențe pe Ubuntu.
3. Verificarea afișării template-urilor de issue și pull request.
4. E00–E04 sunt deja în commit-ul local `4fcac8c`; verificarea și publicarea commit-urilor ulterioare rămân separate.

## Pași exacți pentru închiderea E03

Rămân numai cele patru alegeri din „Ce mai lipsește pentru E03”. Când sunt comunicate:

1. **D-02:** dacă alegerea este `CN+S`, se schimbă `DEFAULT_APPARENT_CORRECTION`
   (`backend/lunarhorizon/astro/bodies.py`) și se rulează `scripts/validate_e03.py`; dacă este `LT+S`, nu se schimbă
   codul. În ambele cazuri se actualizează SPEC_FIZICA §5 și §5.1 (se scoate „provizoriu”).
2. **T-01:** se actualizează `PROPOSED_TOLERANCES["T-01_separation_deg"]` (`backend/lunarhorizon/astro/reference.py`) și
   se redenumește constanta din „propuse” în „confirmate”; testele rămân aceleași. Rezultatele curente trec ambele valori.
3. **Înălțimea de referință a Apollo 11 și înălțimea observatorului:** se consemnează alegerea în SPEC_FIZICA §4;
   cazurile `a11_dem` și `a11_catalog` rămân ca intrări de test sau se retrag, fără a le modifica valorile.
4. D-01, D-03 și D-18 sunt deja consemnate ca „confirmate (comunicat)”; E03 se marchează încheiată în
   [ACCEPTANCE.md](ACCEPTANCE.md) §7 și P0-07 se actualizează. Nu sunt necesare interogări Horizons noi, cât timp nu se
   schimbă pozițiile, altitudinile sau momentele cazurilor.

## Pași exacți pentru închiderea E04

1. **Verificarea vizuală** de către colegii de geografie, pe QuickMap sau Moon Trek, cu lista din
   [VALIDARE.md](VALIDARE.md) §7.6. Rezultatul se consemnează în STATUS și în ACCEPTANCE §7 (E04).
2. **D-07:** alegerea celor două situri polare demonstrative. Candidații documentați (neconfirmați) sunt în
   `demo_site_selection` din `data/catalog/sites.json`. După alegere: `status` devine `confirmed`, iar
   `confirmed_site_ids` primește cele două identificatoare, apoi se regenerează schema (`generate_contracts.py`) și se
   rulează testele (testul care cere `unconfirmed` se actualizează odată cu decizia).
3. **D-10:** confirmarea conținutului catalogului, a surselor pozițiilor și a ipotezei de cadru (`MOON_ME_DE440_ME421`
   pentru coordonate care nu declară realizarea). Dacă se cere o altă tratare, se modifică notele de adopție.

## Următoarea etapă eligibilă

**E05 — Datele de teren pentru primul sit polar** are ca unică dependență E02 (îndeplinită) și are nevoie de D-07,
deci nu poate începe complet până la alegerea siturilor demonstrative. **E06** depinde de E03 și E04, deci așteaptă
închiderea lor. Nu am început E05.

## Mediul observat (2026-11-14)

| Unealtă | Stare |
|---|---|
| Python | 3.13.16 (`py -3.13`); lansatorul `py` are 3.15 ca versiune implicită, neschimbată |
| Mediul virtual al proiectului | `backend\.venv`, Python 3.13.16, pip 26.2.1 |
| Node, npm | 26.13.1 (LTS), 11.20.0 |
| Git, Git LFS | 2.56.0, 3.8.1; `core.autocrlf=true` la nivel de sistem |
| PowerShell | `npm` rulează ca `npm.ps1`; politica `CurrentUser` este `RemoteSigned` |
| Utilitare GDAL, Conda, Docker, GitHub CLI | Neinstalate; niciunul necesar până la E16 |

Repository-ul Git este `Desktop\LunarHorizon\LunarHorizon` (ramura `main`, un commit, fără remote).
Folderul părinte nu este repository și conține `graphify-out/`, lăsat neatins.

## Decizii deschise

**[ASTRO]** — de confirmat cu colegii de astronomie. **[GEO]** — cu colegii de geografie. **[ECHIPĂ]** — decizie de proiect.
Propunerile sunt puncte de pornire, nu rezultate validate.

| ID | Cine | Întrebare | Propunere | Blochează |
|---|---|---|---|---|
| D-01 | ASTRO | Ce profil de kerneluri folosim: DE440 (`MOON_ME_DE440_ME421`) sau DE421 (`MOON_ME_DE421`)? | **CONFIRMATĂ (comunicat de utilizator; fără persoane și dată)**: DE440 implicit, DE421 ca verificare încrucișată. Dovezi E03: DE440 față de Horizons ≤ 4,75·10⁻⁷°, DE421 ≤ 1,28·10⁻⁵°; DE421 acoperă doar 1900–2050 | — |
| D-02 | ASTRO | Ce corecții de aberație definesc direcția „aparentă”? | **DESCHISĂ**: documentele păstrează `LT+S` (implicit actual) și `CN+S`; confirmarea comunicată nu alege. Dovezi E03: `CN+S` este mai aproape de Horizons (2,68·10⁻⁷° față de 4,75·10⁻⁷°); niciuna nu include devierea gravitațională a luminii | E03 (închidere) |
| D-03 | ASTRO | Planul local este perpendicular pe direcția radială? Ce convenție de azimut folosim la pol? | **CONFIRMATĂ (comunicat)**: da; nordul = meridianul longitudinii date; azimut nedefinit la zenit/nadir. Dovezi E03: la polul exact, cu longitudinea 0, Horizons dă același azimut (ΔA = 5,7·10⁻⁹°) | — |
| D-04 | ASTRO | Criteriul solar al centrului discului este acceptabil pentru MVP? Ce prag minim de elevație are Pământul implicit? | Da; 0° | E10 |
| D-05 | GEO | Raza de referință și referința înălțimilor din DEM-uri | 1 737 400 m, de confirmat din metadate | E05, E09 |
| D-06 | GEO | Parametrii proiecției stereografice ai produselor PGDA | De citit din fișiere | E05 |
| D-07 | GEO | Care sunt cele două situri polare demonstrative? | **DESCHISĂ.** IM-1/IM-2 retrase la cererea utilizatorului; lista activă de candidați este goală. Sunt necesare poziții citabile și verificarea DEM pentru alte situri. | E04 (închidere), E05 |
| D-08 | GEO | Ce produs îndepărtat și ce rază de căutare folosim la orizont? | Produs LOLA GDR polar; ales prin convergență | E09 |
| D-09 | GEO, ASTRO | Pasul azimutal și pasul radial ale orizontului | Alese prin convergență | E09 |
| D-10 | GEO | Conținutul catalogului și sursele pozițiilor; tratarea cadrelor istorice | **Implementat ca propunere, neconfirmat de geografi**: 10 intrări active verificate la documentele originale (produs PDS LROC actual ca sursă primară). Cadrul: nicio sursă nu numește realizarea (DE); adoptarea ca `MOON_ME_DE440_ME421` este o ipoteză consemnată în fiecare intrare. Fără regiuni candidate; ținte planificate numerice numai pentru Chandrayaan-3 | E04 (închidere) |
| D-11 | GEO | Textura globului și fundalurile 2D; texte de creditare | Mozaicul LROC WAC; umbrirea PGDA | E05 |
| D-12 | ASTRO, GEO | Toleranțele T-01 – T-09 | T-04, T-05 stabilite (E02). **T-02 (0,1 km) și T-03 (0,001°) confirmate (comunicat)**. **T-01 deschis**: 0,001° (propus) sau ≤ 1·10⁻⁵° (recomandat). T-06–T-09 neconfirmate | E03 (T-01); E09–E10 |
| D-13 | ASTRO | Intervalele demonstrației (date de început, durată) | Intervale cu evenimente pentru ambele corpuri | E15 |
| D-14 | ECHIPĂ | Înălțimea implicită a echipamentului | 2 m | E06 |
| D-15 | ECHIPĂ | Remote GitHub și vizibilitate; găzduire; unde stau terenul vizual și scenariile (Git LFS sau descărcare) | — | E01 (parțial), E15, E16 |
| D-16 | ECHIPĂ | Rămânem la Plotly pentru grafice? | Da, încărcat la cerere | E10 |
| D-17 | ECHIPĂ | Mesajele date în engleză în specificație se traduc în interfața românească? | Da, prin chei de text | E13 |
| D-18 | ASTRO | Potrivirea configurației Horizons: referința altitudinii, cadrul, convenția azimutului | **CONFIRMATĂ (comunicat)**. Dovezi E03, din antetele celor 26 de răspunsuri: raze 1737,4 km (aceeași sferă), `MEAN_ME (high precision)`, longitudine estică, fără refracție, DE441, cu devierea luminii; azimutul confirmat numeric ([VALIDARE.md](VALIDARE.md) §3) | — |
| D-19 | GEO | Cum intră pixelii interpolați ai DEM-ului în indicatorul de calitate? | Folosirea hărții numărului de măsurători | E05, E09 |
| D-20 | ECHIPĂ | Durata maximă a intervalului și pasul minim al seriei în modul live | De stabilit după primele măsurători de performanță | E06 |

## Audit de compatibilitate E03 (2026-11-14, înaintea implementării)

Compară deciziile proiectului cu materialul unui prototip separat. Materialul a fost primit ca anexe ale
promptului E03; fișierele originale ale prototipului (căile `C:\Users\Erikutzu\…`) nu există pe acest calculator.
Rezultatele prototipului nu sunt aprobări ale colegilor și nici teste trecute în acest repository.

| ID | Definiția din proiect | Sursa și starea existentă | Dovezi din materialul prototipului | Evaluare | Ce mai trebuie decis sau verificat | Lucrări E03 dependente |
|---|---|---|---|---|---|---|
| D-01 | Profilul de kerneluri: DE440 (`MOON_ME_DE440_ME421`) implicit, DE421 (`MOON_ME_DE421`) ca verificare încrucișată | SPEC_FIZICA §3.1; propunere [ASTRO], neconfirmată | Același profil DE440 (de440s, `moon_pa_de440_200625.bpc`, `moon_de440_250416.tf`); fără calcule DE421 | Compatibil | Confirmarea astronomilor; diferența dintre profiluri (T-03) | Manifestul, încărcarea profilului, T-03 |
| D-02 | Corecțiile de aberație pentru direcția „aparentă”: propunere `LT+S` | SPEC_FIZICA §5; propunere [ASTRO], neconfirmată | Prototipul folosește `CN+S` (timp de lumină convergent + aberație stelară), fără devierea gravitațională a luminii | Contradictoriu (minor): `LT+S` față de `CN+S` | Alegerea astronomilor. E03 păstrează `LT+S` ca implicit provizoriu, implementează ambele și măsoară diferența față de Horizons | Calculul aparent, T-01 |
| D-03 | Planul local perpendicular pe direcția radială; la pol, „nordul” este meridianul longitudinii date | SPEC_FIZICA §4; implementat la E02, provizoriu [ASTRO] | Aceeași definiție a planului și aceeași convenție la pol; azimutul este nedefinit (`None`) la zenit și nadir | Compatibil, cu o lacună: `core` întoarce azimut 0 la zenit | E03 raportează azimutul ca nedefinit la zenit/nadir. Contractul `BodySeries.azimuth_deg` nu acceptă `null`: decizie de schemă la E06 | Calculul az/el; testul polului |
| D-18 | Potrivirea configurației Horizons: referința altitudinii, cadrul, convenția azimutului, confirmate din antetul primului răspuns | VALIDARE §3; deschisă [ASTRO] | Antetele prototipului ar indica DE441 și un cadru lunar „mean Earth” de înaltă precizie; răspunsurile originale nu sunt accesibile aici | Incomplet | Citirea antetelor din răspunsurile noi (raza centrului, cadrul, efemeridele); confirmarea astronomilor | Interogările Horizons, interpretarea T-01 |
| T-01 | Azimut și elevație Soare/Pământ față de Horizons; „de stabilit; cu cel puțin un ordin de mărime sub raza unghiulară a Soarelui” | VALIDARE §2; NEVALIDAT | Prag software de 0,001° pe separarea unghiulară; maximum 3,36·10⁻⁷° pe 30 de comparații | Compatibil ca propunere (0,001° ≪ 0,027°) | Pragul trebuie confirmat (D-12). Pragul prototipului nu este o toleranță aprobată | Testele de comparație cu Horizons |
| T-02 | Distanța până la corp față de Horizons; „de stabilit; intră numai în raza unghiulară” | VALIDARE §2; NEVALIDAT | Prag de 0,1 km pentru vectori geometrici; maximum 2,22 m pe 6 comparații | Compatibil ca propunere | Pragul trebuie confirmat (D-12) | Distanțele și razele unghiulare |
| T-03 | Diferența dintre profilurile `de440_me421` și `de421`; justifică D-01 | VALIDARE §2; NEVALIDAT | Fără date | Incomplet | Măsurarea la E03; pragul trebuie confirmat | Profilul DE421 |

Verificarea convențiilor:

| Convenție | Proiect | Prototip | Horizons (manual și API) | Evaluare |
|---|---|---|---|---|
| Cadrul lunar | `MOON_ME_DE440_ME421`, nume explicit | Același | Cadru „mean Earth” pentru Moon; de confirmat din antet (D-18) | Compatibil; Horizons de verificat |
| Efemeride | de440s (DATA_PLAN) | de440s | DE441 (după prototip; de confirmat) | Familii JPL diferite; acordul nu este o validare independentă |
| Latitudine | Planetocentrică, pe sferă | Planetocentrică | „Geodetic” pe elipsoidul lunar; identică pe o sferă | Compatibil dacă raza din antet este 1737,4 km (D-18) |
| Longitudine | Est pozitiv, [-180, 180) | Est pozitiv | Est pozitiv pentru Lună (excepție prograde, manual) | Compatibil |
| Altitudine | Față de sfera R = 1 737 400 m (D-05, provizoriu) | La fel | Față de elipsoidul de referință al centrului | Compatibil dacă razele coincid (D-18) |
| Unități | m, grade, s; km și radiani numai la interfața SPICE | m local, km SPICE | km la `SITE_COORD` | Compatibil |
| UTC → ET | Numai prin SPICE (`str2et`) cu LSK | La fel; parser limitat la 1962–2149 | `TIME_TYPE=UT` | Compatibil; restricția 1962–2149 a prototipului nu se preia: E03 verifică acoperirea reală SPK/PCK |
| Azimut și elevație | De la nord spre est; elevația față de planul radial | La fel | Azimut de la nord în sensul acelor de ceasornic, deci spre est; fără refracție pe Lună | Compatibil |
| Înălțimea observatorului | 2 m (D-14, propunere) | 2 m radial | Inclusă în altitudinea din `SITE_COORD` | Compatibil |

Decizii tehnice luate în E03 în limitele autorizării, fără aprobarea colegilor:

- **Situl de referință E03 este Apollo 11** (0,67416°N, 23,47314°E), o alegere de implementare. Altitudinea lui este un parametru de test explicit, preluat din materialul prototipului: suprafața la −1926,6870392689982 m (scalar din DEM-ul prototipului, neverificat aici) sau −1926 m (valoarea din catalogul prototipului) pentru comparația vectorilor. Observatorul este la +2 m. Cele două configurații nu se amestecă.
- **Corecția aparentă implicită rămâne `LT+S`** (propunerea proiectului pentru D-02). `CN+S` este disponibilă și se compară cu Horizons.

## Verificări rămase de făcut

Puncte încă neconfirmate:

- parametrii proiecției, raza de referință și valoarea `NoData` ale produselor PGDA;
- organizarea pe blocuri a mozaicului de 3,3 GB (pentru citirea de ferestre la distanță);
- pagina și condițiile de creditare ale mozaicului LROC WAC;
- QuickMap, Moon Trek, pagina CSA: încă necitite (verificarea vizuală este a colegilor de geografie). Documentația misiunilor: citită parțial la E04 (kituri NASA CLPS, ISRO, LROC; vezi [SOURCES.md](SOURCES.md) §2.2);
- lucrarea Icarus Wagner et al. (2017), PDF-ul LROC din 2016 și broșura ISRO: inaccesibile sau neîncercate;
- documentele cu geometria regiunilor candidate Artemis III: neîncercate.

Rezolvate la E03: `naif0012.tls` este cel mai recent LSK publicat; `de421.bsp` este disponibil în
`spk/planets/a_old_versions/` (MD5 publicat); semnăturile SpiceyPy folosite sunt confirmate în versiunea
instalată; sintaxa Horizons `coord@301` cu `SITE_COORD` și cantitățile 4 și 20 funcționează (26 de răspunsuri valide).

## Blocaje

- **Închiderea E03:** depinde de patru alegeri (D-02, T-01, înălțimea de referință a Apollo 11, înălțimea observatorului/D-14).
  Nu este un blocaj tehnic: implementarea și dovezile sunt gata.
- **Închiderea E04:** depinde de verificarea vizuală a geografilor, de D-07 și de D-10.
- **Materialul prototipului:** fișierele originale (căile `C:\Users\Erikutzu\…`) nu există pe acest calculator.
  Au fost folosite anexele promptului; referințele Horizons au fost reinterogate, iar pozițiile catalogului verificate la surse.
- **Lucrarea Icarus și PDF-ul LROC din 2016:** inaccesibile (HTTP 403, respectiv 500).
- **Rularea CI:** blocată de lipsa remote-ului (acțiune externă neautorizată).

## Jurnal

| Data | Etapă | Ce s-a făcut |
|---|---|---|
| 2026-11-14 | E00 | Structura de directoare; documentele de proiectare; verificarea surselor și a versiunilor. Fără cod, fără instalări, fără date descărcate |
| 2026-11-14 | E01 | Mediul backend (Python 3.13, pip, Ruff, mypy, pytest) și frontend (Node 26, npm, Vite, React, TypeScript, oxlint, Prettier, Vitest); teste de fum; `check_env.py`; `.gitignore`, `.editorconfig`; VS Code; CI; template-uri GitHub; README și CONTRIBUTING. Verificat într-o clonă curată și în browser. Fără commit, fără remote |
| 2026-11-14 | E02 | `core` și `geo`: UTC, coordonate, ENU, proiecție, scene 3D; contracte Pydantic, schema JSON 0.1.0, tipuri TS generate, coduri de eroare; vectori comuni și fixture-uri sintetice; T-04 și T-05 stabilite; API.md înghețat; verificări de contract în CI. 187 + 161 de teste trecute, inclusiv în clona curată. Fără commit, fără remote |
| 2026-11-14 | E03 (implementată, deschisă) | Audit de compatibilitate; manifestul kernelurilor (schema 0.2.0) și descărcarea verificată a 8 kerneluri NAIF; modulul `astro` (profil, acoperire, UTC ↔ ET, direcții, distanțe, raze unghiulare, vectori ICRF); 26 de interogări Horizons arhivate; comparații T-01/T-02/T-03 față de praguri propuse; job CI `astro`. 259 + 162 de teste trecute. Așteaptă deciziile [ASTRO]. Fără commit, fără remote |
| 2026-11-14 | E04 (implementată, deschisă) și confirmarea E03 | Catalog de 12 intrări (`data/catalog/sites.json`) cu proveniență structurată, verificat la documentele originale; schema 0.3.0; cititor `lunarhorizon.catalog`; `scripts/verify_catalog_sources.py` și raportul arhivat; 29 de teste noi. Confirmarea astronomilor (comunicată de utilizator) consemnată pentru D-01, D-03, D-18, T-02, T-03; D-02 și T-01 rămân deschise. Verificările E03 rerulate: 288 de teste Python, rezultate neschimbate. Fără commit, fără remote |
