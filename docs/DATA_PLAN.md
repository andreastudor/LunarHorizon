# Planul datelor

Ce date folosește LunarHorizon, de unde vin, cum se prelucrează și unde se păstrează. Sursele și starea
verificării lor sunt în [SOURCES.md](SOURCES.md). Nicio dată nu a fost descărcată încă.

## 1. Principii

- Fiecare fișier extern are o intrare într-un manifest: identificator, URL, instituție, data accesării, dimensiune, SHA-256, licență sau condiții de creditare.
- Fișierele mari nu intră în Git. Se obțin prin scripturi de descărcare reproductibile, care verifică suma de control.
- Dacă sursa publică sume de control, scriptul le compară. Altfel, suma calculată la prima descărcare se înregistrează în manifest și se verifică la descărcările următoare.
- Datele sintetice sunt permise numai în teste și în demonstrații etichetate explicit. Au prefixul `synthetic_` și nu apar în catalogul de producție.
- Niciun pas de prelucrare nu completează golurile cu altitudini inventate.

## 2. Produse externe

### 2.1. Kerneluri SPICE (NAIF)

| Fișier | Rol | Profil | Stare |
|---|---|---|---|
| `de440s.bsp` | Efemeride Soare, Pământ, Lună; acoperire 1849-12-26 – 2150-01-22 | `de440_me421` | Descărcat (E03); MD5 publicat de NAIF potrivit; acoperire calculată egală cu rezumatul NAIF |
| `moon_pa_de440_200625.bpc` | Orientarea Lunii (DE440) | `de440_me421` | Descărcat (E03); SHA-256 egal cu descărcarea anterioară a prototipului |
| `moon_de440_250416.tf` | Cadrele `MOON_PA_DE440`, `MOON_ME_DE440_ME421` | `de440_me421` | Descărcat (E03); SHA-256 egal cu descărcarea anterioară a prototipului |
| `pck00011.tpc` | Constante și raze ale corpurilor | ambele | Descărcat (E03); SHA-256 egal cu descărcarea anterioară a prototipului |
| `naif0012.tls` | Conversia UTC ↔ ET | ambele | Descărcat (E03); cel mai recent LSK publicat de NAIF (verificat 2026-11-14) |
| `de421.bsp` | Efemeride pentru controlul încrucișat | `de421` | Descărcat (E03) din `spk/planets/a_old_versions/`; MD5 publicat de NAIF potrivit |
| `moon_pa_de421_1900-2050.bpc` | Orientarea Lunii (DE421), 1900–2050 | `de421` | Descărcat (E03); fără sumă de referință disponibilă |
| `moon_080317.tf` | Cadrele `MOON_PA_DE421`, `MOON_ME_DE421` | `de421` | Descărcat (E03); fără sumă de referință disponibilă |

Mărimile, SHA-256, MD5, momentele descărcării și acoperirile sunt în `data/manifests/kernels.json`. Fișierele
stau în `data/kernels/` (în afara Git) și se obțin cu `scripts/download_kernels.py`; `--verify` le verifică
fără rețea.

Alegerea profilului implicit este decizia **[ASTRO] D-01**.

### 2.2. Relief apropiat — PGDA, 5 m/pixel

| Produs | Conținut | Fișiere relevante |
|---|---|---|
| PGDA 81, „South Pole LOLA DEM Mosaic” | 87–90°S, mozaic din 97 de câmpuri de 20×20 km | `ldem_87s_5mpp.tif` (3,3 GB), `ldec_87s_5mpp.tif` (140 MB, număr de măsurători), `ldem_87s_5mpp_hillshade.tif` (820 MB), `ldsm_87s_5mpp.tif` (4,9 GB, pante) |
| PGDA 78, „High-Resolution LOLA Topography for Lunar South Pole Sites” | DEM-uri individuale de sit | `*_final_adj_5mpp_surf.tif`, `*_5mpp_ldec.tif`, `*_5mpp_toterr.tif` (incertitudine verticală), `*_5mpp_slp.tif` |

Declarat de sursă: proiecție stereografică polară sudică, X/Y în metri, convenție „pixel-registered”,
cadru „MOON_ME of ephemeris DE421”, înălțimi în metri, pixelii goi umpluți prin interpolare.

Nedeclarat de sursă și de citit din fișiere la E05: parametrii proiecției, raza de referință, referința
înălțimilor, valoarea `NoData`, organizarea pe blocuri, coordonatele centrelor siturilor.

### 2.3. Relief îndepărtat — LOLA GDR (PDS)

Setul `LRO-L-LOLA-4-GDR-V1.0` conține produse polare stereografice. În directorul `polar/jp2` există, pentru
polul sud, între altele: `LDEM_80S_20M` (aproximativ 268 MB), `LDEM_75S_30M` (299 MB), `LDEM_75S_60M` (103 MB)
și `LDEM_60S_60M` (386 MB), în format JPEG 2000 cu etichetă PDS.

**[GEO] D-08.** Produsul îndepărtat se alege după testele de convergență ale orizontului. De verificat înainte
de folosire: cadrul și referința verticală ale acestor produse față de cele PGDA, factorul de scalare al
valorilor din etichetă și suportul JPEG 2000 din unealta de citire.

**E09 (2026-11-15):** se folosesc versiunile PDS3 `.IMG` + `.LBL` (directorul `polar/img/`), nu JPEG 2000.
`LDEM_75S_120M` (116 MB) este nivelul îndepărtat înregistrat; `LDEM_75S_60M` (465 MB) a fost descărcat numai pentru
studiul de rezoluție. Eticheta declară ME DE421, sfera de 1 737 400 m, `HEIGHT = DN · 0,5`; compatibilitatea cu PGDA
104 a fost măsurată (−0,29 ± 1,56 m). Achiziție: `scripts/acquire_lola_gdr.py`. Alegerea rămâne propunere (D-08).

### 2.4. Globul și fundalurile de hartă

| Nevoie | Candidat | Stare |
|---|---|---|
| Textura globului | Mozaicul global LROC WAC, 100 m/pixel (USGS Astrogeology; aproximativ 5,5 GB), reeșantionat la o textură mică | Găsit prin căutare; pagina produsului și condițiile de creditare nu au fost citite |
| Relief global pentru glob (opțional) | Produs LOLA GDR global la rezoluție mică | Neverificat |
| Fundal 2D polar | Umbrirea reliefului de la PGDA 81, reeșantionată | Fișierul există pe pagina produsului |
| Fundal 2D global | Aceeași sursă ca textura globului | — |

**[GEO] D-11** confirmă produsele și textele de creditare. Fundalurile se pregătesc local; aplicația nu
depinde de servicii de hărți externe.

## 3. Situri

### 3.1. Situri polare demonstrative

Cerința este teren real pentru cel puțin două situri polare comparate. **[GEO] D-07** alege siturile.
Criterii propuse:

1. ambele au acoperire de 5 m/pixel (în mozaicul 87–90°S sau ca DEM de sit PGDA 78);
2. condițiile de iluminare și de vizibilitate a Pământului diferă vizibil între ele, pentru o comparație cu sens;
3. numele și poziția au o sursă citabilă.

Candidați din lista PGDA 78: „Connecting ridge” (Site01), „Shackleton rim” (Site04), „de Gerlache rim” (Site11),
„Peak near Shackleton” (Site07). Coordonatele lor nu apar pe pagină și se iau din fișiere.

**Decizie utilizator, 2026-11-14:** IM-1 și IM-2 au fost eliminate din catalog și din selecția D-07.
Nu există încă situri polare active sau candidați confirmați. Criteriile de mai sus rămân de evaluat.
Rapoartele PGDA 78/104 pentru cele două poziții retrase sunt dovezi istorice, nu blocaje ale viitoarei selecții.
Repository-ul Ahammad204/Nasa-moon poate furniza piste și surse pentru alte situri (vezi SOURCES).
Coordonatele sale aproximative trebuie verificate la sursa originală și în DEM înainte de adoptare.

### 3.2. Catalogul

Fișier unic versionat, `data/catalog/sites.json`, cu schema din [SPECIFICATIE.md](SPECIFICATIE.md) §6.1 și
extensiile din [API.md](API.md) §2.2 (schema 0.3.0). Primul catalog (E04) este mic; pozițiile au fost verificate la
documentele originale, nu și vizual de geografi. Sursa primară a pozițiilor efective este produsul PDS LROC
„Anthropogenic (man-made) Features on the Moon” ([SOURCES.md](SOURCES.md) §2.2):

| Categorie | Conținut vizat | Sursa pozițiilor |
|---|---|---|
| Apollo | Cele șase situri de aterizare (modulul lunar) | Implementat: produs PDS LROC; coroborare cu tabelul LROC din 2016 |
| Polare | De ales; catalogul activ nu conține situri polare | D-07 rămâne deschisă |
| CLPS | Blue Ghost 1; ținta planificată doar ca regiune numită | Implementat: produs PDS LROC; kituri de presă NASA CLPS |
| Alte țări | Chandrayaan-3 (poziție efectivă și țintă planificată ISRO), Chang'e 4 | Implementat: produs PDS LROC; pagina ISRO pentru țintă |

**[GEO] D-10.** Nicio coordonată nu intră în catalog fără URL, data accesării și cadrul din sursă. Coordonatele
istorice pot fi într-un cadru diferit; conversia către cadrul intern se documentează în `original_coordinates`,
iar dacă nu se poate face riguros, incertitudinea se declară. Pozițiile se verifică vizual pe QuickMap sau Moon Trek.

## 4. Prelucrarea terenului

```
descărcare ──► inspecție ──► raster de calcul ──► teren vizual ──► manifest
(sumă de        (CRS, NoData,   (decupaj, format     (niveluri de     (surse, rezoluții,
 control)        blocuri)        cu citire pe         detaliu,         sume de control)
                                 ferestre)            mască NoData)
```

| Pas | Script (în `scripts/`) | Rezultat |
|---|---|---|
| 1. Descărcare | `download_kernels`, `download_terrain` | Fișiere brute în `data/_raw/` (în afara Git), verificate |
| 2. Inspecție | `inspect_raster` | Metadatele reale, scrise în manifestul produsului |
| 3. Raster de calcul | `build_calc_raster` | Raster la rezoluția sursei, organizat pentru citire pe ferestre; fără reeșantionare a valorilor |
| 4. Teren vizual | `build_visual_terrain` | Hărți de înălțimi pe niveluri de detaliu, mască `NoData`, manifest de teren |
| 5. Fundaluri | `build_basemaps` | Textura globului și fundalurile 2D |
| 6. Precalculare | `precompute_scenario` | Rezultate statice pentru scenariile demonstrative |

- Rasterul de calcul păstrează valorile sursei. Orice reproiectare sau reeșantionare se declară în manifest.
- Terenul vizual se obține prin mediere pe blocuri din rasterul de calcul și își declară rezoluția. Nu este folosit de niciun calcul.
- Uneltele sunt descrise în [ARCHITECTURE.md](ARCHITECTURE.md) §7.

## 5. Unde se păstrează fiecare lucru

| Loc | Conținut | În Git |
|---|---|---|
| `data/catalog/` | Catalogul și schema lui | Da |
| `data/manifests/` | Manifestele kernelurilor și ale produselor de teren | Da |
| `data/reference/` | Cazurile Horizons: cererea, răspunsul original, valorile extrase | Da (text, mic) |
| `data/terrain/` | Terenul vizual și manifestele pentru siturile demonstrative | De decis (D-15): Git LFS sau descărcare reproductibilă |
| `data/precomputed/` | Scenariile offline | De decis (D-15), aceeași soluție |
| `data/_raw/`, `data/_cache/`, `data/kernels/` | Fișiere brute, cache, kerneluri | Nu; create de scripturi, excluse prin `.gitignore` |
| `tests/fixtures/` | Teren sintetic mic și vectori de test | Da |

Git LFS este instalat local, iar repository-ul are deja secțiunea LFS în configurație. Folosirea lui depinde
de limitele găzduirii alese.

## 6. Scenarii precalculate

Un scenariu declară siturile, intervalul UTC, parametrii și fișierele lui. Pentru demonstrația finală:
cel puțin două situri polare cu teren real, același interval, plus o a doua dată de început pentru pasul
„schimbă data de început” din demonstrație.

**[ASTRO] D-13.** Intervalele demonstrației (data de început, durata) se aleg astfel încât să conțină
evenimente pentru ambele corpuri și să se încadreze în acoperirea kernelurilor.

## 7. Cazuri de referință

Structura din `data/reference/horizons/<id_caz>/`: cererea trimisă (toți parametrii), răspunsul original
nemodificat, valorile extrase și data interogării. Matricea cazurilor este în [VALIDARE.md](VALIDARE.md) §3.
Aceste fișiere se obțin prin interogări reale; nu se scriu de mână.
