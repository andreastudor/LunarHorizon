# Backlog — etapele de implementare

Etapele sunt ordonate astfel încât să existe cât mai devreme **un sit polar funcțional cap-coadă** (jalonul M1),
apoi **două situri polare cu relief real și comparație** (jalonul M2). Harta 3D apare de la primele etape de
interfață și rămâne cerință P0 până la final.

Fiecare etapă se încheie cu verificările ei rulate, cu [STATUS.md](STATUS.md) actualizat și cu o notă despre ce a rămas.
Deciziile D-xx sunt în [STATUS.md](STATUS.md); testele și toleranțele T-xx în [VALIDARE.md](VALIDARE.md).

## Privire de ansamblu

| Etapă | Titlu | Depinde de | Jalon |
|---|---|---|---|
| E00 | Planificare și organizare | — | Încheiată |
| E01 | Repository, GitHub, VS Code și CI | E00 | Încheiată local; acțiunile GitHub externe restante |
| E02 | Convenții comune și contracte | E01 | Încheiată local; CI pe GitHub neexecutat |
| E03 | Kerneluri și astronomie pentru un sit | E02 | Implementată; neîncheiată: așteaptă D-01, D-02, D-03, D-18 și toleranțele T-01–T-03 |
| E04 | Catalog minim verificat | E02 | Implementată; neîncheiată: lipsesc verificarea vizuală a geografilor, D-07 și D-10 |
| E05 | Datele de teren pentru primul sit polar | E02 | |
| E06 | API și simulare în modul idealizat | E03, E04 | |
| E07 | Interfața de bază și harta 3D globală | E05, E06 | |
| E08 | Teren 3D local pentru primul sit | E05, E07 | |
| E09 | Orizont din DEM | E05, E06 | |
| E10 | Vizibilitate, evenimente și indicatori | E08, E09 | **M1** |
| E11 | Harta 2D sincronizată și fallback WebGL | E07 | |
| E12 | Al doilea sit polar, puncte custom și comparație | E10 | **M2** |
| E13 | Mod simplu/expert, trasabilitate, limbi | E12 | |
| E14 | Export | E12 | |
| E15 | Scenarii precalculate și mod offline | E12 | |
| E16 | Deployment și documentația de pornire | E15 | |
| E17 | Închiderea cerințelor P0 | E11, E13–E16 | **MVP** |
| E18 | Bonusuri P1 | E17 | |

E03, E04 și E05 pot avansa în paralel, pe roluri (fizică, cartografie, programare).

---

## E01 — Repository, GitHub, VS Code și CI

- **Obiectiv.** Un mediu de lucru reproductibil, cu versiuni fixate și verificări automate.
- **Dependențe.** E00. Pentru partea de GitHub: decizia D-15 și confirmarea explicită a utilizatorului înainte de crearea unui remote.
- **Livrabil.**
  - `.gitignore` (date brute, kerneluri, cache, medii virtuale, rezultate de build) și `.editorconfig`.
  - `backend/pyproject.toml` cu versiuni fixate; mediu virtual; Ruff și verificare de tipuri.
  - `frontend/` inițializat cu Vite, React și TypeScript; `package-lock.json`; oxlint (linterul șablonului oficial, în locul ESLint din planul inițial) și Prettier.
  - `.vscode/`: extensii recomandate, setări, sarcini și configurații de depanare pentru backend și frontend.
  - `.github/workflows/ci.yml`: lint, tipuri, teste unitare și build pentru backend și frontend. Șabloane pentru issue și pull request. Validarea schemelor JSON se adaugă în CI la E02, când există schemele.
  - Un script de verificare a mediului, care afișează versiunile instalate și driverele raster disponibile (COG, JPEG 2000).
  - `README.md` completat cu comenzile reale de instalare și rulare.
- **Teste.** Un test de fum pe fiecare parte (importul bibliotecilor științifice; randarea componentei rădăcină). Toate verificările din CI rulate local.
- **Criteriu de finalizare.** Dintr-o clonă curată, comenzile din README instalează dependențele și trec lint, teste și build pe Windows. Versiunile fixate sunt consemnate în [ARCHITECTURE.md](ARCHITECTURE.md) și licențele în [SOURCES.md](SOURCES.md). Prezența sau lipsa driverelor COG și JPEG 2000 este consemnată.

## E02 — Convenții comune și contracte

- **Obiectiv.** O singură definiție a unităților, timpului, coordonatelor și schemelor, folosită de toate modulele.
- **Dependențe.** E01. D-05 și D-06 pot rămâne provizorii, cu raza de referință și parametrii proiecției configurabili.
- **Livrabil.**
  - Modulul `core`: unități, analiza timpului UTC, validarea și normalizarea coordonatelor, transformările lat/lon ↔ ME ↔ stereografic ↔ cadru local.
  - Modulul `geo` din frontend, cu aceleași transformări plus cele către scena 3D.
  - Vectori de test comuni pentru Python și TypeScript.
  - Scheme JSON pentru catalog, manifeste, rezultatul simulării și indexul scenariilor; modele Pydantic și tipuri TypeScript corespunzătoare; codurile de eroare.
- **Teste.** Conversii dus-întors; continuitate la ±180°; convenția la pol; concordanța Python ↔ TypeScript; proiecția stereografică față de PROJ; validarea schemelor, adăugată și în CI.
- **Criteriu de finalizare.** Toleranțele T-04 și T-05 sunt stabilite, iar testele le respectă. [API.md](API.md) este înghețat ca versiune de schemă inițială.

## E03 — Kerneluri și astronomie pentru un sit

- **Obiectiv.** Azimutul și elevația Soarelui și Pământului pentru un punct lunar și un moment UTC, verificate față de Horizons.
- **Dependențe.** E02. Acces la NAIF și la Horizons. Deciziile D-01, D-02, D-03, D-18.
- **Livrabil.**
  - Manifestul kernelurilor și scriptul de descărcare cu sume de control.
  - Modulul `astro`: încărcarea profilului, acoperire temporală, vectori, azimut, elevație, distanță, rază unghiulară.
  - Un script care interoghează Horizons și salvează cererea și răspunsul original.
  - Primele cazuri de referință din [VALIDARE.md](VALIDARE.md) §3 care nu depind de catalog.
- **Teste.** Timp (UTC, timestampuri fără zonă, limitele efemeridelor); comparația cu Horizons (T-01, T-02); diferența dintre profilurile de kerneluri (T-03).
- **Criteriu de finalizare.** Cazurile de referință respectă toleranțele confirmate de colegii de astronomie. D-01, D-02, D-03 și D-18 sunt închise și consemnate în [SPEC_FIZICA.md](SPEC_FIZICA.md).

## E04 — Catalog minim verificat

- **Obiectiv.** Un catalog mic, în care fiecare poziție are sursă.
- **Dependențe.** E02. Deciziile D-07 și D-10.
- **Livrabil.** `data/catalog/sites.json` cu situri Apollo, situri polare (inclusiv cele două demonstrative), câteva misiuni CLPS și internaționale; sursele trecute în [SOURCES.md](SOURCES.md); restul cazurilor de referință din [VALIDARE.md](VALIDARE.md) §3.
- **Teste.** Validarea față de schemă; coordonate în domeniu; ținta planificată și poziția efectivă ca intrări distincte; niciun câmp completat fără sursă.
- **Criteriu de finalizare.** Colegii de geografie au verificat vizual pozițiile pe un produs adecvat. Cele două situri polare demonstrative sunt alese.

## E05 — Datele de teren pentru primul sit polar

- **Obiectiv.** Relief real, pregătit separat pentru calcul și pentru afișare, plus fundalurile hărților.
- **Dependențe.** E02. Decizia D-07. Acces la PGDA. Spațiu pe disc pentru fișierele brute (mozaicul are 3,3 GB).
- **Livrabil.**
  - Scripturile de descărcare și inspecție; manifestul produsului cu metadatele reale citite din fișier.
  - Rasterul de calcul pentru primul sit; modulul de eșantionare cu tratarea `NoData` și a marginilor.
  - Terenul vizual pe niveluri de detaliu și manifestul de teren.
  - Conturul acoperirii DEM; textura globului și fundalurile 2D.
- **Teste.** Verificarea sumelor de control; valoarea eșantionată într-un pixel cunoscut coincide cu rasterul; `NoData` rămâne `NoData`; marginile nu produc valori; manifestul respectă schema.
- **Criteriu de finalizare.** D-05, D-06 și D-19 sunt închise pe baza metadatelor reale. Manifestul de teren al primului sit este valid, iar dimensiunea terenului vizual este consemnată.

## E06 — API și simulare în modul idealizat

- **Obiectiv.** Fluxul cerere → calcul → rezultat, complet, fără relief.
- **Dependențe.** E03, E04.
- **Livrabil.** Aplicația FastAPI cu `health`, `sites`, `coverage`, `simulations`; simulări asincrone; cache; serii temporale; `provenance` și `quality`; erori în formatul stabilit.
- **Teste.** Teste de contract pentru fiecare endpoint; erori de validare și de acoperire temporală; aceeași cerere întoarce aceeași simulare; apeluri concurente către SPICE.
- **Criteriu de finalizare.** O simulare pentru un sit în modul idealizat întoarce un rezultat complet, conform schemei.

## E07 — Interfața de bază și harta 3D globală

- **Obiectiv.** Ecranul principal cu harta 3D ca vedere implicită și controlul timpului.
- **Dependențe.** E05 (textură), E06.
- **Livrabil.**
  - Cele patru zone ale ecranului; starea comună; sursa de date API.
  - Globul lunar: rotire, zoom, deplasare, resetarea camerei, orientare inițială spre polul sud, grilă de coordonate, marcaje, conturul acoperirii DEM, eticheta nivelului de detaliu.
  - Selecție prin raycasting cu distincția clic/rotire; introducere manuală a coordonatelor, cu validare.
  - Controlul temporal: dată, oră UTC, interval, slider, redare și pauză.
  - Direcțiile spre Soare și Pământ la situl activ, din rezultatul simulării.
- **Teste.** Transformările scenă ↔ coordonate lunare; teste de interfață pentru selecția din catalog, clicul pe glob, slider fără cereri noi, ignorarea rezultatelor depășite. Verificarea timpurie a randării WebGL în mediul de test.
- **Criteriu de finalizare.** Utilizatorul selectează un punct în 3D, pornește o simulare, iar derularea timpului actualizează direcțiile afișate.

## E08 — Teren 3D local pentru primul sit

- **Obiectiv.** Relieful real al primului sit polar, explorabil și sincronizat cu timpul.
- **Dependențe.** E05, E07.
- **Livrabil.**
  - Endpointul `terrain/manifest`.
  - Scena locală: mesh din DEM, zone `NoData` vizibile, observator la altitudinea terenului plus înălțimea echipamentului, direcții Soare/Pământ, lumină orientată după vectorul solar.
  - Vedere de sus, perspectivă oblică și vedere de la observator; acțiunea „Mergi la sit”.
  - Controlul exagerării verticale, cu afișare permanentă.
  - Stări de încărcare, eroare și lipsă de date; eliberarea resurselor GPU la schimbarea sitului.
- **Teste.** Pozițiile vârfurilor față de vectorii de test; altitudinea observatorului; exagerarea și camera nu modifică rezultatele (T-09); numărul de resurse GPU după schimbarea sitului; teste de interfață.
- **Criteriu de finalizare.** Primul sit are relief real în 3D, iar corpurile și lumina urmează sliderul.

## E09 — Orizont din DEM

- **Obiectiv.** Profilul de orizont calculat din relief, cu indicator de calitate.
- **Dependențe.** E05, E06. Deciziile D-08 și D-09.
- **Livrabil.** Algoritmul de orizont pe două niveluri de teren; produsul îndepărtat pregătit; cache pentru profil; modul `dem` în simulări; studiul de convergență consemnat în [VALIDARE.md](VALIDARE.md); graficul profilului.
- **Teste.** Teren sintetic cu obstacol cunoscut și cu curbură (T-06); `NoData` și margini; convergența la rezoluție, rază și pas azimutal (T-07).
- **Criteriu de finalizare.** Profilul primului sit este calculat, cu parametri aleși prin convergență și cu acoperirea declarată. D-08 și D-09 sunt închise.

## E10 — Vizibilitate, evenimente și indicatori — jalonul M1

- **Obiectiv.** Un sit polar funcțional cap-coadă.
- **Dependențe.** E08, E09. Decizia D-04.
- **Livrabil.**
  - Criteriile de vizibilitate; detectarea și rafinarea evenimentelor; indicatorii.
  - Rezumatul sitului activ; vederea locală a cerului; graficul elevațiilor; benzile temporale; timpul până la următoarea tranziție.
  - Indicatoarele vizibil/ascuns în scena 3D, citite din rezultat.
  - Afișarea celor patru situații din [SPECIFICATIE.md](SPECIFICATIE.md) §10.3.
- **Teste.** Funcții-criteriu sintetice cu tranziții scurte și contacte aproape tangente (T-08); intervale trunchiate; consistența duratelor; stările interfeței.
- **Criteriu de finalizare (M1).** Pentru un sit polar cu date reale: teren 3D, observator, moment UTC, direcții Soare/Pământ, orizont, evenimente și indicatori funcționează împreună, iar verificările geometrice sunt consemnate.

## E11 — Harta 2D sincronizată și fallback WebGL

- **Obiectiv.** Vederea alternativă 2D, cu aceeași selecție și același timp.
- **Dependențe.** E07.
- **Livrabil.** Harta OpenLayers polară sudică și globală, cu proiecții lunare explicite; marcaje, selecție prin clic, conturul acoperirii DEM; comutatorul 3D/2D care păstrează selecția, momentul UTC și parametrii; pornire în 2D, cu explicație, pe dispozitive fără WebGL suficient.
- **Teste.** Conversie dus-întors 2D ↔ coordonate lunare ↔ 3D; păstrarea stării la comutare; fallback WebGL simulat.
- **Criteriu de finalizare.** Același punct selectat în 2D și în 3D dă aceleași coordonate, iar comutarea nu pierde nimic.

## E12 — Al doilea sit polar, puncte custom și comparație — jalonul M2

- **Obiectiv.** Două situri polare cu relief real, comparate în același interval.
- **Dependențe.** E10.
- **Livrabil.** Terenul și orizontul celui de-al doilea sit; adăugarea punctelor custom la comparație; butonul Compare; ecranul de comparație cu 2–4 coloane și aceiași indicatori în aceeași ordine; o scenă 3D comună care urmărește situl activ; aranjament pentru mobil; culori și identificatoare comune.
- **Teste.** 2–4 situri sincronizate; un rezultat vechi nu înlocuiește selecția nouă; scări comune la graficele comparate; punct custom în afara acoperirii DEM.
- **Criteriu de finalizare (M2).** Două situri polare cu relief real se compară pe același interval, iar scena 3D și coloanele rămân sincronizate la derularea timpului și la schimbarea datei de început.

## E13 — Mod simplu/expert, trasabilitate, limbi

- **Obiectiv.** Aceleași rezultate, prezentate pe două niveluri, cu sursele și limitele vizibile.
- **Dependențe.** E12. Decizia D-17.
- **Livrabil.** Comutatorul simplu/expert conform [SPECIFICATIE.md](SPECIFICATIE.md) §3.4; panoul de proveniență și calitate; rezumatul limitelor; texte în engleză prin chei, cu structura pentru alte limbi (decizia din 2026-11-14).
- **Teste.** Ambele moduri afișează valori provenite din același rezultat; fiecare sursă folosită apare în interfață; nicio cheie de text lipsă.
- **Criteriu de finalizare.** Un utilizator poate identifica sursa și calitatea datelor pentru orice valoare afișată.

## E14 — Export

- **Obiectiv.** Rezultate și configurație exportabile, cu metadate.
- **Dependențe.** E12.
- **Livrabil.** Export CSV pentru serii și JSON pentru configurație și metadate, conform [API.md](API.md) §7.
- **Teste.** Antete cu unități; JSON-ul exportat respectă schema; exportul funcționează fără backend.
- **Criteriu de finalizare.** Un fișier exportat este suficient pentru a regăsi parametrii și sursele rezultatului.

## E15 — Scenarii precalculate și mod offline

- **Obiectiv.** Demonstrația de rezervă, complet locală.
- **Dependențe.** E12. Deciziile D-13 și D-15.
- **Livrabil.** Scriptul de precalculare, care folosește motorul backendului; scenariile demonstrației (două situri polare, două date de început); indexul scenariilor; sursa de date statică; bannerul și lista combinațiilor disponibile.
- **Teste.** Scenariul rulează fără backend și fără nicio cerere externă (verificat prin interceptarea rețelei); combinația neprecalculată afișează starea corespunzătoare; rezultatul static este identic cu cel live pentru aceiași parametri.
- **Criteriu de finalizare.** Demonstrația principală se poate parcurge integral cu rețeaua oprită, inclusiv terenul 3D.

## E16 — Deployment și documentația de pornire

- **Obiectiv.** Aplicația poate fi pornită de altcineva și publicată când echipa hotărăște.
- **Dependențe.** E15. Decizia D-15.
- **Livrabil.** În `deploy/`: build-ul static al demonstrației și configurația de container pentru aplicația completă. README final cu instalare, descărcarea datelor, pornire, build, teste și demo.
- **Teste.** Build curat urmat de pornire după README pe o mașină fără starea de dezvoltare; verificarea că aplicația construită nu cere resurse de la CDN.
- **Criteriu de finalizare.** O persoană din echipă pornește aplicația numai pe baza README-ului. Publicarea se face numai cu acordul explicit al utilizatorului.

## E17 — Închiderea cerințelor P0 — MVP

- **Obiectiv.** Fiecare cerință P0 verificată și consemnată.
- **Dependențe.** E11, E13, E14, E15, E16.
- **Livrabil.** Tabelul P0 din [ACCEPTANCE.md](ACCEPTANCE.md) completat cu starea și dovada fiecărei cerințe; [VALIDARE.md](VALIDARE.md) cu rezultatele rulate; [LIMITATIONS.md](LIMITATIONS.md) actualizat; corecții de performanță și accesibilitate.
- **Teste.** Toată suita; parcurgerea manuală a demonstrației principale; verificare pe un dispozitiv mobil.
- **Criteriu de finalizare.** Toate cerințele P0 sunt „implementat și verificat” sau au o stare incompletă declarată explicit. MVP-ul nu se declară complet cât timp harta 3D sau altă cerință P0 este incompletă.

## E18 — Bonusuri P1

Numai după E17 și în ordinea din specificație. Fiecare bonus își fixează întâi convențiile în
[SPEC_FIZICA.md](SPEC_FIZICA.md) §11 și toleranțele în [VALIDARE.md](VALIDARE.md).

| Subetapă | Bonus | Teste cerute |
|---|---|---|
| E18a | Traiectoria aparentă a Pământului (librație) | Pozițiile provin din aceeași serie ca indicatorii |
| E18b | Eclipse solare văzute de pe Lună | Fără suprapunere, parțială, totală; ordinea corpurilor pe linia de vedere |
| E18c | Rezumat avansat al intervalelor de întuneric | Intervale trunchiate; cea mai lungă perioadă |
| E18d | Putere solară relativă | Panou orientat spre Soare, perpendicular, opus |

Funcțiile P2 rămân în secțiunea „Future work” a aplicației.

---

## Corespondența cu planul de 48 de ore

Calendarul din [SPECIFICATIE.md](SPECIFICATIE.md) §17 este orientativ.

| Interval | Etape |
|---|---|
| H0–H3 | E01, E02; începutul E04 și E05 |
| H3–H8 | E03, E04, E06 |
| H8–H14 | E05, E07, E08, E11 |
| H14–H20 | E09, E10 (M1) |
| H20–H28 | E12 (M2), E13 |
| H28–H32 | E14, E17; E18 numai dacă P0 este complet |
| H32–H40 | E15, E16, stabilizare |
| H40–H48 | Repetiții, test offline, depunere, rezervă |

La H20, dacă orizontul din DEM nu funcționează, aplicația rămâne utilizabilă în modul idealizat, cerința
se consemnează ca incompletă, iar prioritatea următoare este recuperarea reliefului real pentru scenariile polare.
