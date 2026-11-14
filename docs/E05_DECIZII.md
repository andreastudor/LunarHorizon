# E05 — decizii de produs și validări științifice rămase

Actualizat 2026-11-14. Utilizatorul (responsabilul de produs) a aprobat **pentru implementare** variantele de mai
jos. Aprobarea este o decizie de produs; **nu este validare [GEO] sau [ASTRO]** și nu se atribuie vreunui specialist.
Metadatele și rezultatele sunt în [VALIDARE.md](VALIDARE.md).

| Decizie | Aprobare de produs (utilizator) | Ce rămâne nevalidat științific | Validare [GEO] |
|---|---|---|---|
| D-07: sursă și prim punct | PGDA 104 și punctul reprezentativ Leibnitz Beta Plateau (−85,4266039743°, 31,7441821732°E) pentru **prima demonstrație provizorie**. Nu este loc de aterizare și nu este o selecție validată a două situri | Adecvarea punctului și a produsului pentru comparația finală (E12) | restantă |
| D-05: referință verticală | Sfera de 1.737.400 m, din CRS-ul rasterului; înălțimile sunt față de această sferă (README-ul arhivei) | Echivalența cu alte DEM-uri/geoizi nu este demonstrată | restantă |
| D-06: proiecție | Proiecția citită din raster: stereografică polară sudică, latitudine origine −90°, meridian 0°, X/Y în metri, pixel 5 m | CRS-ul nu dovedește singur realizarea fizică a cadrului | restantă |
| D-10: cadru | `MOON_ME_DE421` rămâne **ipoteză neconfirmată**, vizibilă în manifeste; nicio echivalență cu alte cadre, nicio conversie fictivă | Realizarea cadrului sursei și incertitudinea | restantă; D-10 rămâne deschisă |
| D-19: calitate | Numărul de imagini NAC (`GLDMASK`) și categoriile de azimut solar (`GLDSBCT`) se arată separat, la rezoluția nativă de 15 m, fără praguri inventate; nu sunt număr de măsurători LOLA | Semnificația operațională/pragurile de calitate; definiția `GLDSIGM` | restantă |
| D-11: fundal | Fundaluri NASA SVS (CGI Moon Kit 2K) provizoriu, numai pentru afișare; credit „NASA's Scientific Visualization Studio" și limitele de rezoluție în [SOURCES.md](SOURCES.md) | Produs estetic; nu este suport științific; polii sunt completați din albedo LOLA mai grosier | acord de creditare/GEO restant |

## GLDSIGM (investigație limitată la 30 de minute, 2026-11-14)

README-ul din arhivă numește produsul de incertitudine `GLDISGM`, iar ZIP-ul conține `A310_GLDSIGM_005.tif`
(5 m/pixel, NoData −1). Au fost consultate pagina PGDA 104, înregistrarea Zenodo 17954508 și README-ul de regiuni
al înregistrării: **niciuna nu definește** `GLDSIGM`/`GLDISGM`, unitatea sau semnificația. Articolul de referință
(DOI 10.3847/PSJ/ae5b70) nu a fost parcurs integral în intervalul alocat. Concluzie: **semnificație neconfirmată**.
Rasterul rămâne arhivat și nu primește interpretare; este exclus din indicatorii de calitate validați
(`quality_indicators.gldsigm.status` din manifestul auxiliar). Lucrul independent nu este blocat.

## Rezoluția produselor auxiliare

Rezoluția se citește din transformarea fiecărui GeoTIFF, nu din sufixul „005” al numelui: `GLDMASK` și `GLDSBCT`
15 m/pixel (1066 × 1066), `GLDSIGM` și `GLDELEV` 5 m/pixel (3200 × 3200). Pagina PGDA 104 și înregistrarea Zenodo
afirmă generic 5 m/pixel; rasterele efective diferă pentru cele două hărți de contribuție, deci se folosesc valorile
citite din fișier.

## Tipuri de sume de control

| Tip | Ce este | Starea |
|---|---|---|
| CRC al membrului ZIP | Verificat de `zipfile` la citirea fiecărui membru | verificat |
| SHA-256 local | Calculat de proiect după prima achiziție și fixat în scripturi/manifeste; **nu este publicat de furnizor** | verificat la fiecare rulare `verify_e05.py` |
| MD5 publicat de furnizor | Publicat pe Zenodo pentru **arhiva completă** (Leibnitz Beta: `b0a606e6a4ce73faf2ea68c91ce0b93e`) | **neverificat**: arhiva completă (1,05 GB) nu a fost descărcată; s-a extras numai prin HTTP Range |

`d_max`, convergența și alegerea produsului de teren îndepărtat sunt D-08/D-09 și E09, nu criterii de închidere E05.
