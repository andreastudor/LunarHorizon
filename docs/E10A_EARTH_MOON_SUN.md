# E10A — Earth–Moon–Sun: tab 3D obligatoriu P0

## Decizie și încadrare

Solicitat de utilizator la 2026-11-14 ca funcție importantă a aplicației, **nu bonus**.
Stare: planificat, neimplementat și neverificat. Nu modifică E08 (teren local 3D).
Ordine de execuție: E08 → E09 → E10 → **E10A** → E11 și restul planului.
Dependențe tehnice: motorul E03, API/contracte E06 și interfața E07. E10 precedă această etapă
pentru a finaliza mai întâi fluxul principal cu relief. E17 include obligatoriu acceptarea E10A.

## Experiența utilizatorului

- Tab nou **Earth–Moon–Sun**, separat de globul lunar și de terenul local; interfață în engleză.
- Trei corpuri în 3D, etichete Sun/Earth/Moon, rotire, zoom, resetare și focalizare pe fiecare corp.
- Linii și distanțe pentru Earth–Moon, Sun–Earth și Sun–Moon, în km, etichetate **Center-to-center distance**.
- Același moment UTC, slider și Play/Pause ca în aplicația principală; comutarea taburilor păstrează timpul
  și selecția sitului. Mișcarea sliderului consumă seria încărcată, fără cereri repetate pe fiecare cadru.
- Vedere schematică lizibilă, cu **Not to scale** permanent vizibil. Regula de scalare a distanțelor și
  razelor se documentează; numerele afișate provin din calcule, nu din geometria scalată a scenei.
- Trasee orbitale calculate din efemeride, cu interval UTC explicit; nu cercuri inventate și nu trasee
  parțiale închise artificial. Alegerea originii de afișare și a intervalului trebuie să fie clară.
- Stări de încărcare, lipsă de kerneluri/date, interval neacoperit și WebGL indisponibil.

## Calcule și contracte

- Reutilizare SPICE și kerneluri verificate; fără un al doilea motor astronomic.
- Pozițiile **centrelor** se calculează la același moment ET, convertit din UTC prin SPICE, în același
  cadru inerțial explicit (propunere tehnică: J2000) și cu aceeași origine explicită.
- Pentru geometria simultană a sistemului se folosesc vectori geometrici cu corecția **NONE**;
  convenția se documentează în SPEC_FIZICA și în metadatele rezultatului, distinct de LT+S/CN+S
  folosite pentru observația aparentă de la suprafață. Acceptarea ASTRO se consemnează separat.
- Distanța între centre: d_AB(t) = ||r_B(t) - r_A(t)||, în km, din vectorii nescalati.
- Nu reutiliza `BodySeries.distance_km` al sitului lunar ca distanță între centre și nu reconstrui
  pozițiile sistemului din azimutul/elevația unui observator local.
- Originea camerei poate fi recentrată pentru precizie numerică, fără modificarea datelor fizice.
- Orientarea texturilor corpurilor necesită transformări explicite; nu amesteca axele inerțiale cu
  cele ale cadrelor solidare corpurilor. Nu prezenta rotații decorative ca orientări astronomice calculate.
- Înainte de cod, definește contractul minim: timp, poziții în km, origine, cadru, corecție,
  profil/kerneluri, distanțe și acoperire temporală. Actualizează versiunea și regenerează tipurile dacă este necesar.
- Extinde scenariile E15 pentru funcționarea tabului în demonstrația offline și exportul E14 unde este aplicabil.
- Nu modifica rezultatele locale de vizibilitate, orizontul DEM sau criteriile evenimentelor prin această scenă.

## Referință de design și surse

https://github.com/Ahammad204/Nasa-moon este referința indicată de utilizator pentru inspirație vizuală
și piste de date. La implementare inspectează conținutul real, fixează commit-ul și verifică licența
materialelor reutilizate. Nu presupune că repository-ul implementează deja această vedere completă.
Datele și imaginile noi trebuie să aibă proveniență și creditare; verifică sursele primare NASA/NAIF/USGS.
Folosește componentele și materialele existente când sunt potrivite; nu importa automat alte pagini.

## Criterii de acceptare

Toate sunt **neexecutate** la introducerea cerinței:

1. Tabul afișează cele trei corpuri, navigarea și cele trei distanțe între centre pentru momentul selectat.
2. Distanțele API corespund normelor vectorilor; se verifică unitățile, simetria d_AB=d_BA și
   invarianta la translația comună a originii. Toleranțele numerice se justifică înainte de acceptare.
3. Se compară cazuri reprezentative cu o referință Horizons configurată geometric, cu aceleași
   epoci, centre și convenții. Diferențele de efemeride se documentează; nu se inventează acord sau validare ASTRO.
4. Schimbarea timpului actualizează pozițiile și distanțele; comutarea tabului nu pierde selecția.
5. Zoom-ul, focalizarea și scalarea vizuală nu modifică valorile fizice. Etichetele de scară și UTC sunt vizibile.
6. Traseele sunt legate de intervalele și datele calculate; erorile de acoperire sunt explicite.
7. Test Playwright de randare reală și interacțiune, fără erori JS neașteptate; verificare manuală a lizibilității.
8. Contracte regenerate/verificate, teste relevante și build reușite; resurse GPU eliberate la schimbarea tabului.
9. Proveniența și creditele sunt vizibile; scenariul offline E15 include tabul și datele sale.

Implementarea tehnică și acceptarea științifică se raportează separat. E17 nu declară P0 complet
cât timp această funcție obligatorie este neimplementată sau criteriile obligatorii sunt neîndeplinite.
