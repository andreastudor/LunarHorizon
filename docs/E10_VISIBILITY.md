# E10 — vizibilitate, evenimente și indicatori (jalonul M1)

Stare 2026-11-15: **încheiată tehnic pentru un sit polar real (Leibnitz Beta, punct reprezentativ DEM), cap-coadă:
teren → orizont → geometrie astronomică → vizibilitate → evenimente → indicatori → afișare sincronizată.**
Acceptarea științifică rămâne restantă (vezi „Rămâne deschis”). E10A nu a fost începută.

Decizii folosite (confirmate de astronomi, comunicate de utilizator în conversația din 2026-11-15; numele și data
evaluării nefurnizate): D-02 `CN+S`, T-01 (0,001°; diagnostic 0,00001°), D-04 (disc cu arie pozitivă vizibilă).
Pământul folosește criteriul documentat al centrului, cu `e_min` implicit 0°, configurabil. D-08/D-09 [GEO] rămân
deschise; parametrii orizontului sunt propuneri tehnice.

## Criteriile (implementare: `backend/lunarhorizon/simulation/visibility.py`)

**Soare (D-04).** Centrul (A_c, e_c) și raza ρ = asin(R_☉/D) vin din același rezultat CN+S, la fiecare moment
(R_☉ = 695 700 km din `pck00011.tpc`). În planul tangent al cerului (x = ΔA·cos e_c, y = e):

- `g = max_x [y_sus(x) − H(A(x))]` — aria vizibilă este pozitivă dacă și numai dacă g > 0 (H continuă); contactul
  tangent (g = 0) nu este vizibilitate. Se evaluează pe 128 de coloane și în toate eșantioanele profilului din disc,
  deci și deschiderile laterale: criteriul `e_c + ρ > H(A_c)` nu este folosit.
- `h = min_x [y_jos(x) − H(A(x))]` — complet vizibil dacă h > ε.
- Fracția = aria neascunsă / aria discului (coloane), cu incertitudine = sensibilitatea la H ± ε plus diferența
  față de jumătate din coloane. Este fracție de arie aparentă, nu flux și nu putere. Eclipsele nu sunt incluse.
- În modul idealizat H ≡ 0, deci criteriul devine `e_c + ρ > 0` (testat față de segmentul circular analitic).

**Pământ.** `e_P > max(H(A_P), e_min)`; prezentat ca „vizibilitate geometrică spre centrul Pământului”, nu legătură
radio. Cauza raportată: `terrain` sau `elevation_threshold` (idealizat: `idealized_horizon`).

**Stări nedeterminate (niciodată „ascuns” sau zero):** `no_data` (lipsesc eșantioane de orizont pe disc sau la
azimutul Pământului), `partial_data` (profil parțial: H real ≥ valoare; ascunderea este sigură, vizibilitatea nu),
`near_threshold` (|g| ≤ ε, cu ε = max(10⁻⁶°, rugozitatea locală a profilului) — metoda nu poate distinge o porțiune
foarte mică de un contact tangent). Stările expuse: Soare `hidden` / `partially_visible` / `fully_visible` /
`undetermined`; Pământ `visible` / `hidden` / `undetermined`, fiecare cu motiv.

**Orizontul folosit.** Modul DEM folosește profilul E09 recalculat la pasul azimutal **0,025°** (14 400 de azimuturi,
același algoritm; eșantioanele de 0,5° sunt un subset exact), calculat în job și păstrat în cache (prima dată ≈ 16 s
pentru Leibnitz). Profilul de 0,5° rămâne cel afișat. Interpolarea unui profil grosier nu poate exclude obstacole
înguste: de aceea pasul fin a fost ales prin convergență; obstacolele mai înguste decât pasul rămân o limită.

## Evenimente și intervale (`simulation/timeline.py`)

Scanare pe grilă (DEM: 60 s Soare, 300 s Pământ; idealizat: 300 s / 600 s), subdiviziune până la 1 s acolo unde
criteriul *poate* atinge pragul între eșantioane (estimare Lipschitz din pantele vecine, factor 2), bisecție la
1 ms. Evenimente: `appearance`, `disappearance` și `tangent_contact` (atinge banda nedecidabilă și revine), fiecare cu
corpul, cauza, criteriul, momentul UTC, fereastra `[window_start, window_end]` în care starea nu poate fi decisă și
calitatea `refined` / `window`. La granițele zonelor fără date nu se creează evenimente; dacă lipsesc date și nu
există evenimente, starea grupului este `unavailable` cu motiv. Evenimentele nu se deduc din seria sliderului.

Intervalele `visible` / `hidden` / `unknown` ale fiecărui corp partiționează intervalul cerut (fără goluri sau
suprapuneri; validat în contract), cu `truncated_start` / `truncated_end`. Indicatorii (durata Soarelui vizibil,
inclusiv parțial; a Pământului; a ambelor; duratele necunoscute separat; fracția din interval) vin din aceste
intervale, nu din serie.

## Contracte, API, cache

Schema **0.8.0**: `BodySeries.state`, `state_reason`, `visible_fraction`, `visible_uncertainty_fraction`;
`Event.type` include `tangent_contact`, plus `criterion`, `window_start_utc`, `window_end_utc`, `quality`, cauza
`elevation_threshold`; `SiteSummary` are `sun_unknown_duration_s`, `earth_unknown_duration_s`,
`both_unknown_duration_s`, `sun_timeline`, `earth_timeline` (`StateInterval`); `solar_criterion =
"disc_positive_area"` (valoarea `disc_center` nu mai este acceptată). Modul `dem` calculează acum vizibilitatea,
evenimentele și indicatorii (nimic în `not_computed`). Proveniența declară criteriile, `eclipses = not_included`,
corecția, parametrii orizontului, pasul fin, cheile de cache ale profilurilor și parametrii evenimentelor.

Identitatea cache-ului simulărilor = cererea + `engine_identity()` (corecție, versiunea schemei, parametrii
orizontului și ai profilului fin, versiunea algoritmului `e10.1`, pașii de scanare, toleranțele, ε, coloanele).
Un rezultat cu alt criteriu, altă corecție sau altă versiune nu se reutilizează. Profilurile de orizont au propria
cheie (poziție, cadru, înălțime, produse și SHA-256, parametri).

## Interfața (engleză)

Cardurile Sun/Earth la momentul sliderului (stare, motiv, fracția ± incertitudine, orizontul la azimut), combinația
celor patru situații numai când ambele stări sunt determinate (altfel „Combination undetermined”), următorul eveniment
rafinat și timpul rămas („Currently hidden”, „No event within the simulated interval”, „Event unavailable: …”,
fereastra de incertitudine), totalurile (inclusiv necunoscute), graficul elevațiilor cu orizontul la azimutul
fiecărui corp (numai seria de afișare), benzile temporale Sun / Earth / Both din intervalele backendului, cu
evenimentele și cursorul sliderului, și indicatoarele din scena 3D locală citite din rezultat. Sliderul și Play
folosesc rezultatul încărcat (fără cereri noi). Etichete: „DEM terrain horizon” / „Idealized — local terrain not
included”, „Visibility with respect to terrain only; eclipses are not included.”

## Convergență și toleranțe (`scripts/visibility_convergence.py` → `data/reference/visibility/e10_convergence.json`)

Leibnitz Beta, 30 de zile, modul DEM; o singură variabilă pe rând față de bază (0,025°, 60 s, 128 coloane):

| Parametru | Comparație | Deplasarea maximă a evenimentelor | Δ durată Soare vizibil | Δ fracție (max) | Necunoscut (Soare) |
|---|---|---|---|---|---|
| Pas profil | 0,05° → 0,025° | 0,036 s (Soare), 0,039 s (Pământ) | 7,2 s | 8·10⁻⁵ | 33,3 s → 18,8 s |
| Pas profil | 0,0125° → 0,025° | 0,017 s, 0,003 s | 4,6 s | 3·10⁻⁵ | 9,7 s → 18,8 s |
| Scanare Soare | 120 s → 60 s | 0 | 0 | 0 | identic |
| Scanare Soare | 30 s → 60 s | 0,001 s | 0 | 0 | identic |
| Coloane disc | 64 → 128 / 256 → 128 | — | — | 2,5·10⁻⁴ / 1,0·10⁻⁴ | — |

Diferențele de durată cad în ferestrele `near_threshold`, care scad odată cu pasul profilului: metoda le raportează
ca necunoscute, nu ca precizie inventată. Timpi: profil fin 16 s prima dată (cache apoi), simulare 30 de zile 5–9 s
(aproximativ 52 000 de evaluări ale criteriilor). Toleranța de 1 ms este precizie numerică a rădăcinii pentru modelul
folosit, nu incertitudine fizică (DEM, efemeride, D-08/D-09).

## Rezultatul real (Leibnitz Beta, 2026-11-15 → 2026-12-15, echipament 2 m)

| Eveniment | Moment (UTC) | Fereastră | Azimut / elevație centru | Obstacol |
|---|---|---|---|---|
| Soare — apariție | 2026-11-25T08:26:57.879Z | 0,26 s | 316,72° / 4,85° | 210 m |
| Soare — dispariție | 2026-12-12T06:23:10.361Z | 18,6 s | 111,11° / −0,24° | 325 m |
| Pământ — apariție | 2026-11-19T03:20:42.302Z | 0,13 s | 321,05° / 5,59° | 220 m |
| Pământ — dispariție | 2026-11-28T08:59:59.017Z | 0,11 s | 332,42° / 6,60° | 235 m |

Soare vizibil 405,93 h (56,4 %), necunoscut 18,8 s; Pământ vizibil 221,65 h; ambele 72,55 h. Acesta este un
singur punct: nu validează celelalte 12 regiuni DEM.

## Teste și verificări rulate

Backend 396/396 (noi: `test_visibility.py` — segment analitic, ascuns/complet, contact tangent, deschidere laterală
cu coloana centrală ascunsă, deschidere peste 0°/360°, NoData pe disc, profil parțial ca limită inferioară, Pământ,
tranziție scurtă între eșantioane, contact aproape tangent, fără evenimente la granițele datelor lipsă, stabilitatea
duratelor și a momentelor față de pasul de scanare, obstacol controlat față de modul idealizat, identitatea
cache-ului; `test_horizon.py` — simulare DEM reală cap-coadă: partiție, sume de durate, evenimente față de linia de
stare, stările seriei față de intervale, repetabilitate; `test_simulation_idealized.py` actualizat la D-04), Ruff,
mypy, contracte 0.8.0. Frontend 227/227 (noi: combinațiile, starea nedeterminată distinctă, fracția parțială,
textele evenimentelor, benzile, indicatoarele scenei), formatare, oxlint, `tsc`, build. Playwright 6/6 (nou
`visibility.spec.ts`: la 8 poziții ale sliderului, cardul Soarelui, banda sub cursor și indicatorul din scena 3D au
aceeași stare, la fel pentru Pământ; fără cereri noi la mutarea sliderului; fără erori în consolă). Captură de ecran
verificată vizual.

## Rămâne deschis

- Acceptarea științifică: verificarea evenimentelor pe teren real față de o referință independentă; D-08/D-09 [GEO];
  D-10 (cadrul DEM); D-14 (înălțimea echipamentului); D-19 (măsurători reale în calitate).
- T-06–T-09 rămân neconfirmate ca toleranțe; valorile de mai sus sunt propuneri tehnice.
- Eclipsele nu sunt incluse; fracția vizibilă nu este putere solară.
- Obstacolele mai înguste decât pasul profilului fin (0,025°) nu pot fi excluse.
- Un singur sit verificat cap-coadă (Leibnitz Beta); celelalte 12 regiuni nu sunt validate prin aceasta.
- E10A nu a fost începută.
