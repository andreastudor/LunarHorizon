# Specificație fizică — convenții și formule

Acest document fixează convențiile folosite de toate modulele. Cerințele vin din
[SPECIFICATIE.md](SPECIFICATIE.md) §7–§12. Ce este marcat **[ASTRO]** sau **[GEO]** trebuie confirmat de
colegii de astronomie, respectiv geografie, înainte ca modulul respectiv să fie declarat validat;
registrul deciziilor (D-xx) este în [STATUS.md](STATUS.md).

Nimic din acest document nu este un rezultat validat. Valorile numerice sunt fie citate din surse
(cu trimitere la [SOURCES.md](SOURCES.md)), fie propuneri de pornire etichetate ca atare.

**Implementare (E02).** §1, §2 (fără partea SPICE), §3.2, §3.3, §4 și §10.1 sunt implementate identic în
`backend/lunarhorizon/core/` și `frontend/src/geo/`. Concordanța lor este verificată pe vectorii comuni
`tests/vectors/conventions.json` (toleranțele T-04 și T-05 din [VALIDARE.md](VALIDARE.md)). Implementarea
urmează convențiile; ea nu confirmă deciziile provizorii D-05 și D-06 (geografie). D-01 și D-03 au fost
confirmate ulterior de astronomi (comunicat de utilizator, vezi [STATUS.md](STATUS.md)). Conversia UTC → ET și
rotațiile între cadre cer kerneluri și rămân pentru E03.

## 1. Unități și notații

| Mărime | Unitate internă | Sufix în API și fișiere |
|---|---|---|
| Unghiuri | grade zecimale | `_deg` |
| Lungimi, altitudini, înălțimi | metri | `_m` |
| Distanțe până la Soare și Pământ | kilometri | `_km` |
| Durate | secunde | `_s` |
| Momente de timp | UTC, ISO 8601 cu `Z` | `_utc` |
| Fracții | adimensional, 0–1 | `_fraction` |

- SPICE lucrează în kilometri și radiani. Conversia se face într-un singur loc, la granița modulului astronomic.
- Calculele backendului folosesc `float64`. `float32` apare numai în datele de randare.
- Fiecare câmp numeric din API poartă unitatea în nume. Nu există câmpuri de tip „elevation” fără sufix.

## 2. Timp

- Interfața, cererile, răspunsurile și exporturile folosesc UTC. Formatul este `YYYY-MM-DDTHH:MM:SSZ`
  (fracțiuni de secundă opționale, cel mult 3 cifre: precizia comună Python și TypeScript este milisecunda).
  La intrare se acceptă și un offset explicit, care se convertește în UTC. Un timestamp fără `Z` sau offset
  este respins. Forma canonică este în UTC, cu `Z`, fără zerouri finale în fracțiune; formatarea rotunjește
  la cea mai apropiată milisecundă. Anii acceptați sunt 0001–9999, inclusiv după conversia offsetului.
- Secunda intercalară `:60` este respinsă la intrare (`leap_second_unsupported`): tipurile de dată din Python
  și JavaScript nu o pot reprezenta. Dacă un eveniment cade într-o astfel de secundă, el se raportează prin
  timpul SPICE (E03). Aceasta este o limită documentată.
- Timpul intern este ET al SPICE (secunde TDB de la J2000), obținut numai prin SPICE (`str2et`), cu kernelul
  de secunde intercalare încărcat. Nu se face aritmetică proprie UTC↔TDB.
- Pentru date viitoare, SPICE presupune că nu apar secunde intercalare noi după ultima din kernel. Aceasta este o limită documentată.
- Înaintea oricărui calcul se verifică acoperirea temporală a efemeridelor și a kernelului de orientare
  (`spkcov`, `pckcov`). Un interval din afara acoperirii produce eroarea `OUT_OF_EPHEMERIS_COVERAGE`, cu limitele reale în mesaj.
- Data istorică a aterizării (câmp de catalog) și începutul simulării (parametru al cererii) sunt câmpuri separate.

## 3. Cadrul lunar

### 3.1. Alegerea cadrului

Cadrul intern unic este cadrul lunar fix **Mean Earth / Polar Axis (ME)**, centrat în centrul de masă al Lunii.
Motivul: produsele LOLA de la PGDA declară „MOON_ME reference frame of ephemeris DE421”, iar Horizons
folosește pentru Lună tot cadrul mean-Earth.

`IAU_MOON` nu se folosește. Comentariile din kernelul `moon_080317.tf` arată diferențe de până la aproximativ
155 m față de cadrul ME bazat pe DE (interval 2000–2020).

Numele generic `MOON_ME` este un alias care indică alt cadru în funcție de kernelul de cadre încărcat.
Codul și proveniența folosesc întotdeauna numele explicit.

| Profil de kerneluri | Cadru explicit | Kernel de cadre | Orientare (PCK binar) | Efemeride |
|---|---|---|---|---|
| `de440_me421` (propus implicit) | `MOON_ME_DE440_ME421` | `moon_de440_250416.tf` | `moon_pa_de440_200625.bpc` | `de440s.bsp` |
| `de421` (control încrucișat) | `MOON_ME_DE421` | `moon_080317.tf` | `moon_pa_de421_1900-2050.bpc` | `de421.bsp` |

Numele cadrelor și perechile de fișiere sunt citite din comentariile kernelurilor NAIF (accesate 2026-11-14).
Kernelul DE440 afirmă că diferența dintre cadrul său ME și cadrul ME al DE421 corespunde unei deplasări de
puțin peste 1 m pe suprafață în 1900–2051 și de aproximativ 53 cm în 2000–2040.

**[ASTRO] D-01 — CONFIRMATĂ** (comunicat de utilizator; fără persoane și dată). Profilul `de440_me421` pentru
calcule, cu profilul `de421` rulat pe aceleași cazuri de referință ca verificare. Dovezi E03: diferența dintre
profiluri este ≤ 1,28·10⁻⁵° în direcție (T-03, prag confirmat 0,001°); `de421.bsp` este disponibil, cu acoperire 1900–2050.

Profilul complet (nume de fișiere, URL-uri, sume de control, acoperire) stă în `data/manifests/kernels.json`
și apare în `provenance` la fiecare rezultat.

### 3.2. Coordonate pe suprafață

- Latitudine planetocentrică `lat_deg`, pozitivă spre nord, în [−90, 90].
- Longitudine pozitivă spre est, `lon_deg`, normalizată intern în [−180, 180). La intrare se acceptă și
  [0, 360); normalizarea este explicită, iar răspunsul conține valoarea normalizată.
- Suprafața de referință este o sferă de rază `R_ref`. Pe o sferă, latitudinea planetocentrică și cea planetografică coincid.
- Altitudinea `h` este înălțimea față de sfera de referință, pe direcția radială.

**[GEO] D-05.** Valoarea propusă este `R_ref = 1 737 400 m`, convenția obișnuită a produselor LOLA. Pagina PGDA
și fișierul ei README nu precizează raza sau referința înălțimilor. Valoarea se confirmă din metadatele
fișierelor GeoTIFF și din documentația LOLA înainte de primul calcul cu teren.

Conversia în coordonate carteziene ME:

```
u(lat, lon) = ( cos(lat)·cos(lon),  cos(lat)·sin(lon),  sin(lat) )
r(lat, lon, h) = (R_ref + h) · u(lat, lon)
```

### 3.3. Proiecții de hartă

Produsele polare PGDA sunt în proiecție stereografică polară sudică, cu X/Y în metri și convenția
„pixel-registered” (coordonatele sunt centrele pixelilor). Pagina nu dă parametrii proiecției.

Forma presupusă, pe sferă, cu scară adevărată la pol și meridian central 0°:

```
rho = 2·R_ref·tan(45° + lat/2)        (lat negativ în sud; rho = 0 la pol)
x = rho·sin(lon)
y = rho·cos(lon)

invers:  rho = sqrt(x² + y²),  lat = −90° + 2·atan(rho / (2·R_ref)),  lon = atan2(x, y)
factor de scară:  k = 2 / (1 + sin|lat|)
```

**[GEO] D-06.** Parametrii reali (latitudinea de origine, meridianul central, scara, raza) se citesc din fiecare
GeoTIFF și se scriu în manifest. Formulele de mai sus se folosesc numai dacă metadatele le confirmă, iar
implementarea se testează față de PROJ. Codul `IAU_2015:30135` („Moon (2015) - Sphere / Ocentric / South Polar”)
există în registrul IAU; echivalența lui cu CRS-ul fișierelor trebuie verificată, nu presupusă.

Constatare la E02: în PROJ 9.7.1 (inclus în Rasterio), `IAU_2015:30135` are exact parametrii provizorii de mai
sus (`+proj=stere +lat_0=-90 +lon_0=0 +k=1 +R=1737400`). Implementarea proprie coincide cu PROJ până la
1 µm pe o grilă 90°S–30°S, inclusiv la ±180° (testul `test_forward_matches_proj`). Rămâne deschis dacă
fișierele PGDA folosesc același CRS (D-06).

Distanțele din planul proiecției nu sunt distanțe reale (`k ≠ 1` în afara polului). Algoritmul de orizont
transformă fiecare eșantion în coordonate carteziene ME înainte de orice calcul geometric.

Harta 2D globală folosește o proiecție echidistantă cilindrică pe aceeași sferă. Definiția exactă se stabilește în etapa E11.

## 4. Cadrul local al observatorului

Pentru un observator la `(lat, lon)`, baza locală exprimată în ME este:

```
E = ( −sin(lon),            cos(lon),           0        )
N = ( −sin(lat)·cos(lon),  −sin(lat)·sin(lon),  cos(lat) )
U = u(lat, lon)
```

- „Planul local adoptat” este planul perpendicular pe direcția radială `U` în punctul observatorului.
  Nu este panta terenului și nu este verticala gravitațională.
- Azimutul se măsoară de la nord și crește spre est: `az = atan2(d·E, d·N) mod 360°`.
- Elevația: `el = asin(d·U)`, unde `d` este versorul direcției observator → corp.
- Poziția observatorului: `r_obs = (R_ref + h_teren + h_echipament) · U`, unde `h_teren` vine din DEM-ul de
  calcul prin interpolare biliniară. În modul idealizat, `h_teren` vine tot din DEM dacă există, altfel este 0 și este marcat ca atare.

**Convenția la pol.** La `|lat| = 90°` direcția nord nu este definită geometric. Formulele de mai sus rămân
evaluabile cu longitudinea dată de utilizator (implicit 0°): la polul sud, „nord” este direcția orizontală spre
meridianul `lon`. Răspunsul marchează cazul cu `azimuth_convention: "pole_meridian"`. **[ASTRO] D-03 — CONFIRMATĂ** (comunicat
de utilizator): definiția planului local și convenția la pol.

**[ECHIPĂ] D-14.** Înălțimea implicită a echipamentului nu este dată de specificație. Propunere de pornire: 2 m, configurabilă.

## 5. Direcțiile spre Soare și Pământ

Pentru fiecare sit și moment se calculează vectorul observator → corp în cadrul ME, apoi azimutul, elevația,
distanța și raza unghiulară.

- Observatorul are poziție constantă în cadrul lunar fix. Funcția SPICE propusă este `spkcpo`, cu
  poziția observatorului dată în cadrul ME explicit și rezultatul exprimat în același cadru la epoca observatorului.
  Semnătura exactă din SpiceyPy se confirmă în etapa E03.
- Proiecția pe baza `E, N, U` se face în cod propriu (NumPy), cu formulele din §4, ca să nu fie nevoie de câte un cadru topocentric per sit.
- **[ASTRO] D-02 — `CN+S` implicit (confirmată de astronomi, comunicată de utilizator în această conversație (2026-11-15)).** Numele evaluatorilor și data evaluării lor nu au fost furnizate. Direcția aparentă folosește
  `CN+S` (timp de lumină convergent și aberație stelară), în convenția de recepție, cu cadrul local evaluat la
  observator. `LT+S` (o singură iterație a timpului de lumină) rămâne numai pentru diagnostic; `NONE` este geometria
  simultană (inclusiv viitorul tab E10A). Nu se folosesc `XLT+S`/`XCN+S`. Nu sunt incluse devierea gravitațională a
  luminii, întârzierile relativiste sau un model de atmosferă. Configurația este centralizată în
  `core.conventions.APPARENT_CORRECTION`; cheia cache-ului simulărilor include corecția.
- Luna nu are atmosferă: nu se aplică refracție.
- Raza unghiulară: `theta = asin(R_corp / d)`, cu `R_corp` citit din kernelul PCK text încărcat (`bodvrd`) și
  înregistrat în proveniență. Pentru Pământ se folosește raza ecuatorială; turtirea este ignorată în MVP (limită documentată).

Comportament de reținut pentru eșantionare: la poli, azimutul Soarelui parcurge 360° într-o lună sinodică
(în jur de 0,5° pe oră), iar elevația rămâne mică. Pământul rămâne într-o zonă restrânsă a cerului și se mișcă lent din cauza librației.

### 5.1. Implementare (E03)

Implementat în `backend/lunarhorizon/astro/`. Convențiile de mai jos sunt cele adoptate efectiv. Astronomii au confirmat (comunicat de
utilizator) convențiile și configurația de referință; cele marcate încă „provizoriu” (D-02, D-05, D-06) nu sunt închise.
Alegerile deschise pentru E03 sunt în [STATUS.md](STATUS.md), „Ce mai lipsește pentru E03”.

**Kerneluri și cadru** (`kernels.py`, `data/manifests/kernels.json`). Profilul implicit `de440_me421` se
încarcă după `kclear`, în ordinea: `naif0012.tls`, `pck00011.tpc`, `de440s.bsp`, `moon_pa_de440_200625.bpc`,
`moon_de440_250416.tf`. Cadrul de calcul este `MOON_ME_DE440_ME421` (D-01 confirmată). Profilul `de421`
(`MOON_ME_DE421`) se folosește numai pentru T-03. Înaintea încărcării, SHA-256-ul fiecărui fișier local trebuie
să fie cel din manifest.

**Acoperire** = intersecția acoperirilor SPK pentru corpurile 10, 3, 399, 301 și PCK pentru cadrul
`MOON_PA_DE440` (clasa 31008). Valoare calculată: 1849-12-25T23:59:18.816Z – 2150-01-21T23:58:50.816Z, identică
cu intervalul ET publicat de NAIF pentru `de440s.bsp`. Un moment cerut trebuie să fie la cel puțin 600 s de
capete, fiindcă timpul de lumină spre Soare este de ~500 s. Altfel se produce `OUT_OF_EPHEMERIS_COVERAGE`,
cu limitele în context. Profilul DE421 acoperă 1900–2050, limitat de kernelul de orientare.

**Timp** (`timeconv.py`). UTC canonic → `str2et` pe forma ISO fără zonă; ET → UTC cu `et2utc`. Pentru momente
de după ultima secundă intercalară din `naif0012.tls` (2017-01-01), SPICE presupune că nu se adaugă altele;
Horizons face aceeași presupunere („the last known leap-second is used as a constant”).

**Observator.** `r_obs = (R_ref + h_suprafață + h_observator) · u(lat, lon)` în cadrul ME, în km la interfața
SPICE. Ambele altitudini sunt explicite; nu există valoare implicită.

**Direcție.** `spkcpo(corp, et, cadru ME, "OBSERVER", corecție, r_obs, "MOON", cadru ME)`: vectorul
observator → corp, exprimat în cadrul ME la epoca observatorului. Versorul este proiectat pe E, N, U (§4).
Azimutul și elevația se calculează ca în §4. **Azimutul este nedefinit (`None`)** când componenta orizontală a
versorului este ≤ 10⁻¹² (zenit sau nadir). Elevația rămâne definită: `el = atan2(u, √(e² + n²))`.

**Corecții.** `NONE` (geometric), `CN+S` (implicit, D-02 confirmată) și `LT+S` (diagnostic). Ambele variante
aparente includ timpul de lumină și aberația stelară. Niciuna nu include devierea gravitațională a luminii,
pe care Horizons o aplică (`Rel. light bend : Sun, EARTH`).

**Distanță, rază unghiulară.** `D = ‖v‖` (km); `ρ = asin(R_corp / D)`, cu raza ecuatorială din `pck00011.tpc`
(Soare 695 700 km, Pământ 6 378,1366 km). Turtirea Pământului este ignorată.

**Vectori ICRF** (numai pentru verificarea cu Horizons). `spkcpo` cu ieșire în `J2000`, care desemnează în SPICE
realizarea ICRF a efemeridelor JPL.

## 6. Orizontul din relief

### 6.1. Definiție

`H(a)` este elevația maximă a terenului văzut din poziția observatorului pe direcția de azimut `a`,
în aceleași convenții ca §4. Fiecare azimut reține și distanța până la obstacolul care dă maximul și o stare de calitate.

### 6.2. Algoritm

Pentru fiecare azimut `a_k`, cu pas `Δa`:

1. Se parcurg distanțele `d_j` de la `d_min` la `d_max`, pe cercul mare care pleacă din observator pe azimutul `a_k`
   (problema geodezică directă pe sferă). Pasul radial pornește de la rezoluția DEM-ului și poate crește cu distanța.
2. Punctul `(lat_j, lon_j)` se proiectează în CRS-ul DEM-ului și se citește `h_j` prin interpolare biliniară.
3. `p_j = (R_ref + h_j) · u(lat_j, lon_j)`; elevația aparentă este `asin( (p_j − r_obs)·U / |p_j − r_obs| )`.
   Curbura Lunii este inclusă prin construcție, fiindcă totul se calculează în coordonate carteziene.
4. Se păstrează maximul și distanța la care apare.
5. Eșantioanele `NoData` sau din afara acoperirii nu intră în maxim și nu sunt tratate ca altitudine zero. Se numără separat.

Starea de calitate per azimut:

| Stare | Semnificație |
|---|---|
| `complete` | Toate eșantioanele până la `d_max` au date |
| `partial` | Lipsesc eșantioane; maximul real poate fi mai mare decât cel raportat |
| `no_data` | Nu există niciun eșantion valid |

Între azimuturile eșantionate, `H(a)` se interpolează liniar, cu continuitate la 0°/360°.

### 6.3. Raza de căutare și sursele de teren

Un vârf aflat la înălțimea `h_v` deasupra sferei poate depăși orizontul geometric al unui observator aflat la
înălțimea `h_o` până la o distanță de aproximativ

```
d ≈ sqrt(2·R_ref·h_o) + sqrt(2·R_ref·h_v)
```

Pentru relief de ordinul kilometrilor, distanța ajunge la ordinul a o sută de kilometri și mai mult. Mozaicul
de 5 m/pixel acoperă numai 87–90°S, adică aproximativ 91 km în jurul polului. De aceea calculul orizontului
folosește două niveluri de teren:

| Nivel | Produs candidat | Rol |
|---|---|---|
| Apropiat | PGDA, 5 m/pixel (mozaicul 87–90°S sau DEM-ul de sit) | Relieful din jurul observatorului |
| Îndepărtat | Produs polar LOLA GDR mai larg (de exemplu `LDEM_80S_20M` sau `LDEM_75S_30M`) | Obstacole dincolo de acoperirea produsului apropiat |

**[GEO] D-08, D-09.** Produsul îndepărtat, `d_max`, `Δa` și pasul radial se aleg prin teste de convergență
(dublarea rezoluției sau a razei schimbă `H(a)` sub un prag stabilit în [VALIDARE.md](VALIDARE.md)). Compatibilitatea
de cadru și de referință verticală între produsul PGDA și produsul GDR se verifică înainte de a le combina.

Pixelii interpolați: PGDA precizează că pixelii goi din harta de înălțimi sunt umpluți prin interpolare. Harta
de număr de măsurători (`ldec`) arată unde există măsurători reale. **[GEO] D-19** stabilește dacă și cum intră aceasta în indicatorul de calitate.

### 6.4. Modul idealizat

`terrain_mode = "idealized_local_plane"` înseamnă `H(a) = 0°` pentru orice azimut. Coborârea orizontului
datorată înălțimii observatorului pe sferă este ignorată. Interfața afișează permanent mesajul de teren
neinclus. Modul permite explorarea astronomică și nu ține loc de integrare LOLA.

## 7. Criterii de vizibilitate

| Corp | Criteriu MVP | Parametri |
|---|---|---|
| Soare | O parte cu arie pozitivă a discului solar este neascunsă de masca de relief (§7.1) | `solar_criterion = "disc_positive_area"` |
| Pământ | `e_P(t) > max( H(a_P(t)), e_min )` | `earth_min_elevation_deg`, configurabil |

- Rezultatul pentru Pământ se numește **vizibilitate geometrică spre Pământ**. Nu este o evaluare a unei legături radio.
- Dacă `H(a)` are starea `no_data` la azimutul corpului, vizibilitatea este `null`, cu motivul în `quality`. Nu este `false`.
- Dacă starea este `partial`, vizibilitatea se calculează și se marchează ca incertă.
- **[ASTRO] D-04 — criteriul solar al discului extins (confirmată de astronomi, comunicată de utilizator în această conversație (2026-11-15)).** Numele evaluatorilor și data evaluării lor nu au fost furnizate. Soarele este vizibil
  dacă orice porțiune cu arie pozitivă a discului se află deasupra orizontului modelat, chiar dacă centrul este
  ascuns. Contactul tangent exact nu este arie pozitivă. Criteriul centrului (`disc_center`) nu mai este folosit.
  Pentru Pământ rămâne criteriul centrului cu `e_min` implicit 0°, configurabil. Implementarea: E10 (§7.1).
- Vizibilitatea privește numai relieful; eclipsele nu sunt incluse. Fracția vizibilă este fracția de arie aparentă
  a discului, nu fracția de flux și nu putere solară.

### 7.1. Implementare (E10)

Detaliat în [E10_VISIBILITY.md](E10_VISIBILITY.md); cod în `simulation/visibility.py`.

- Discul: centrul și ρ = asin(R_☉/D) din rezultatul CN+S la fiecare moment; model de disc în planul tangent al
  cerului (eroare relativă de ordinul ρ²). `g = max_x[y_sus(x) − H(A(x))]` decide aria pozitivă (g > 0); contactul
  tangent nu este vizibilitate; `h = min_x[y_jos(x) − H(A(x))] > ε` înseamnă complet vizibil. Fracția: integrare pe
  128 de coloane, cu incertitudine din H ± ε și din integrare.
- H(A): în modul DEM, profilul E09 la pasul azimutal fin 0,025° (ales prin convergență), liniar între eșantioane;
  în modul idealizat H ≡ 0, deci criteriul este `e_c + ρ > 0`.
- Nedeterminat (nu „ascuns”, nu zero): lipsă de date pe disc (`no_data`), profil parțial — limită inferioară —
  când discul nu este sigur ascuns (`partial_data`), |g| ≤ ε cu ε = max(10⁻⁶°, rugozitatea locală a profilului)
  (`near_threshold`).
- Pământ: `e > max(H(A), e_min)`, aceleași reguli pentru date lipsă sau parțiale.

## 8. Evenimente

Un eveniment este o schimbare de semn a funcției-criteriu. Tipuri: `appearance`, `disappearance` și (E10)
`tangent_contact`, per corp, cu cauza `terrain`, `idealized_horizon` sau `elevation_threshold`. Eclipsele (P1) au tip
propriu.

**Implementare E10** (`simulation/timeline.py`): grilă de 60 s (Soare) / 300 s (Pământ) în modul DEM, 300 s / 600 s
în modul idealizat; subdiviziune până la 1 s unde criteriul poate atinge pragul între eșantioane (estimare Lipschitz
cu factor 2); bisecție la τ = 1 ms. Fiecare eveniment are fereastra în care starea nu poate fi decisă (|g| ≤ ε) și
calitatea `refined` / `window`. Granițele zonelor fără date nu creează evenimente. Intervalele vizibil / ascuns /
necunoscut partiționează intervalul cerut.

Detectare:

1. Eșantionare grosieră cu pas `Δt_c`. Pasul se alege astfel încât azimutul corpului să avanseze cu cel mult
   jumătate din `Δa` între două eșantioane, ca o trăsătură a orizontului să nu fie sărită.
2. Între două eșantioane cu semn diferit, rădăcina se rafinează prin bisecție sau metoda Brent până la toleranța numerică `τ`.
3. Extremele locale ale lui `c(t)` apropiate de zero se reeșantionează fin, pentru contactele aproape tangente și intervalele scurte.
4. Evenimentele se stochează separat de seria folosită la grafice. Niciun eveniment nu se deduce din interpolarea seriei.

Toleranța `τ` descrie precizia numerică a rădăcinii. Acuratețea fizică a momentului depinde de DEM, de pasul
azimutal, de criteriu și de efemeride și se evaluează separat ([VALIDARE.md](VALIDARE.md)).

Intervalele care încep înainte de începutul analizei sau continuă după sfârșitul ei se marchează `truncated_start` / `truncated_end`.

## 9. Indicatori

Toți indicatorii se calculează din evenimentele rafinate, nu din seria de afișare:

- durata și procentul din interval cu criteriul solar îndeplinit;
- ferestrele de vizibilitate geometrică spre Pământ și durata lor totală;
- durata cu ambele criterii îndeplinite simultan;
- următoarea apariție și dispariție pentru fiecare corp, raportate la momentul curent.

## 10. Geometria de calcul și geometria de randare

Aceste două geometrii sunt separate prin proiectare.

| | Calcul | Randare |
|---|---|---|
| Unde | Backend | Browser |
| Date | Raster DEM la rezoluția declarată, `float64` | Mesh sau hartă de înălțimi simplificată, `float32` |
| Întindere | Până la `d_max`, pe două niveluri de teren | Decupaj local în jurul sitului |
| Scară verticală | Întotdeauna reală | 1× implicit; exagerarea este numai vizuală și se afișează permanent |
| Vizibilitate | Test numeric față de `H(a)` | Lumină direcțională și umbre aproximative, cu rol ilustrativ |

Manifestul de teren declară separat `calc_resolution_m` și `visual_resolution_m`. Indicatorul vizibil/ascuns din
scenă citește rezultatul numeric, niciodată starea umbrelor.

### 10.1. Transformări către scena 3D

Three.js folosește un sistem de coordonate drept, cu axa Y în sus.

Scena globală, în kilometri, cu centrul Lunii în origine:

```
(x_s, y_s, z_s) = ( Y_ME, Z_ME, X_ME )
```

Polul nord este pe `+y_s`, meridianul 0° pe `+z_s`, iar 90°E pe `+x_s`.

Scena locală, în metri, cu originea `O` pe suprafața terenului în punctul de referință al sitului:

```
(x_s, y_s, z_s) = ( e, u, −n ),   unde (e, n, u) = componentele lui (r − r_O) pe baza E, N, U din O
```

- Vârfurile mesh-ului se obțin din `(x, y, h)` stereografic → ME → local, deci curbura se păstrează în randare.
- Originea locală evită pierderea de precizie `float32` la coordonate de ordinul razei lunare.
- Un clic pe glob dă un punct pe sfera de referință și este marcat `on_reference_surface: true`. Un clic pe
  teren dă `(lat, lon)`; altitudinea folosită la calcul se recitește din DEM-ul de calcul pe backend.
- Direcțiile spre Soare și Pământ se desenează din `az`/`el` primite de la API: `d = sin(az)·cos(el)·E + cos(az)·cos(el)·N + sin(el)·U`.
  Corpurile sunt simboluri schematice; dimensiunile și distanțele din scenă nu sunt reale și sunt etichetate.

Testele obligatorii pentru aceste transformări (semnul longitudinii, orientarea axelor, dus-întors 2D ↔ 3D ↔ lunar)
sunt în [VALIDARE.md](VALIDARE.md) și folosesc aceiași vectori de test în Python și TypeScript.

Implementate la E02 în `frontend/src/geo/scene.ts`: ambele scene păstrează orientarea dreaptă
(img(X) × img(Y) = img(Z), respectiv img(E) × img(N) = img(U)). Transformările dus-întors scenă ↔ lunar
respectă T-04, inclusiv la pol și la ±180°. Lipsește încă testul 2D ↔ 3D: harta 2D se implementează la E11.

## 11. Bonusuri (P1) — definiții

Formulele și cerințele sunt cele din [SPECIFICATIE.md](SPECIFICATIE.md) §12. Convențiile de mai sus li se aplică neschimbate.
Detaliile de calcul (suprapunerea discurilor, masca combinată teren + eclipsă, orientarea panoului) se
fixează aici înainte de implementarea fiecărui bonus, după încheierea cerințelor P0.
