# LunarHorizon — verificări CN+S și decizii propuse/adoptate

Data: 14 noiembrie 2026, Europe/Bucharest.
Autorul analizei: asistentul AI, la solicitarea utilizatorului. Nu reprezintă semnătura sau aprobarea atribuită unui astronom.

Utilizatorul confirmă că aplicația de pe alt computer implementează atât LT+S, cât și CN+S. Acea aplicație nu a fost inspectată aici. Verificările de mai jos se referă la prototipul local și la cereri noi Horizons, păstrate în `results/cns_decision_review/horizons/`.

## 1. Verificările efectuate

S-au recalculat 5 configurații sit–moment, fiecare pentru Soare și Pământ: Apollo 11, SCR și IM-2 la 2026-11-14 12:00 UTC; Apollo 11 la 2026-11-15 01:56:29.873658 UTC; SCR la 2026-11-17 22:40:49.996721 UTC. Ultimele două momente au fost alese la un minut după o trecere calculată a centrului Soarelui, respectiv Pământului, peste planul ideal. Nu sunt momente de răsărit fizic pe teren.

Configurație comună: DE440s, MOON_ME_DE440_ME421, observator la 2 m radial peste altitudinea DEM folosită anterior, corecție de recepție CN+S, fără refracție. Horizons: coord@301, aceleași coordonate și altitudine totală, AIRLESS, cantitățile 4 și 20. Datele UTC sunt convertite de SPICE. Se păstrează ipoteza alinierii coordonatelor ME/DE421 cu cadrul adoptat; verificarea nu confirmă independent localizarea landerelor.

- 10/10 comparații trecute la pragul 0,001°.
- Separare maximă CN+S/Horizons: **3,6053485372275007 × 10⁻⁷°**.
- Separare maximă LT+S/CN+S în aceleași cazuri: **2,6618504008434 × 10⁻⁷°**.
- Toate cele 10 comparații sunt și sub 0,00001°.
- Tabelul complet, cu poziții, înălțimi, momente, azimut/elevație și diferențe: `results/cns_decision_review/comparisons.csv` și `.json`.
- Rezultatele detaliate: `results/cns_decision_review/full_results.json`.
- Script reproductibil: `verify_cns_decisions.py`. Rulările ulterioare reutilizează răspunsurile din cache; o rundă nouă trebuie arhivată separat.

Nu este o validare exhaustivă a tuturor datelor, siturilor sau a aplicației de pe alt computer. Horizons și SPICE folosesc modele JPL înrudite, nu observații independente. Cele 30 de comparații istorice nu sunt prezentate ca reexecutate în această rundă.

## 2. D-02 — alegerea corecției aparente

**Aleg CN+S drept configurație implicită**, în limita delegării utilizatorului. LT+S rămâne disponibil pentru comparații și diagnostic; NONE rămâne geometria simultană.

Justificare: CN+S rezolvă convergent timpul de propagare și aplică aberația stelară. LT+S folosește o singură iterație pentru timpul de propagare. Ambele sunt potrivite pentru direcții aparente; apropierea numerică în aceste cazuri este de așteptat și nu dovedește că LT+S este defect. Preferința pentru CN+S elimină aproximația unei singure iterații din configurația științifică implicită. Are cost de calcul mai mare; nu s-a măsurat aici impactul asupra performanței aplicației.

Convenția este recepție, cu cadrul local evaluat la observator. Nu se folosesc XLT+S/XCN+S pentru această vizualizare a corpurilor recepționate. CN+S nu adaugă implicit devierea gravitațională a luminii, întârzieri relativiste sau un model de atmosferă.

Sursă: [NAIF — Aberration Corrections](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/abcorr.html), [spkcpo](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/spkcpo_c.html).

## 3. T-01 — pragul recomandat

**Recomand 0,001° ca prag maxim de acceptare pentru separarea direcțiilor față de Horizons**, numai pentru observatori, epoci, cadre și corecții compatibile. Aceasta este recomandarea pentru preferința exprimată de utilizator, nu o aprobare inventată a echipei.

0,001° = 3,6 secunde de arc. Este un prag rezonabil de integrare pentru MVP. Nu există motiv să îl respingem doar fiindcă reziduurile curente sunt mult mai mici. Dar este prea permisiv ca singurul detector de regresii: în cazurile actuale, el este de peste 2700 de ori mai mare decât reziduul maxim.

De aceea propun și un **prag de diagnostic de 0,00001°**, echivalent cu 0,036 secunde de arc, pentru setul fix de referințe și configurația versionată. O depășire cere investigație și apare distinct în raport, chiar dacă T-01 încă trece. Acest prag de diagnostic nu redefinește T-02/T-03 și nu se promovează automat la criteriu de acceptare pentru toate epocile.

Metrica: atan2(norm(cross(s_calc,s_ref)), dot(s_calc,s_ref)), cu direcții unitare și rezultat în grade. Azimutul și elevația se raportează separat, dar diferența azimutului singură nu este criteriul principal la zenit/nadir.

Pragul nu înseamnă eroare fizică garantată a orizontului, a incidenței pe teren sau a orei răsăritului. Convergența numerică a calculelor de contact/disc și incertitudinea DEM au nevoie de criterii separate. Nu muta pragul dacă o eroare apare; investighează întâi configurația, conversiile și referința.

## 4. D-04 — Soare vizibil dacă o parte din disc este vizibilă

**Cerință explicită a utilizatorului: Soarele este vizibil și când o parte din disc se vede, deși centrul este ascuns.** Criteriul vechi al centrului nu satisface această cerință.

Definiție: V_sun = (f_visible > 0), unde f_visible este fracția ariei aparente a discului solar neascunsă de masca de relief modelată. O atingere tangentă exactă are arie vizibilă zero și se tratează separat drept contact. Nu se introduce în ascuns un prag de tip 1% în locul lui zero.

Raza unghiulară se calculează la fiecare moment: rho = asin(R_sun / D_sun), cu raza fizică solară documentată și distanța topocentrică potrivită modelului. Nu folosi o rază unghiulară fixă pentru toate datele.

Pentru orizontul ideal e = 0, criteriul geometric de porțiune vizibilă este **e_center + rho > 0**. Discul este complet deasupra planului dacă e_center − rho >= 0, în sensul ariei, cu contactul tratat separat.

Pentru relief H(A), definește discul pe sfera direcțiilor:

    D = {u unitar: acos(u · s_center) <= rho}
    Omega_visible = integrala pe D a indicatorului [e(u) > H(A(u))] dOmega
    Omega_disk = 2*pi*(1-cos(rho))
    f_visible = Omega_visible / Omega_disk

Acesta este un model de disc circular cu mască de relief. Raza și centrul provin din geometria aparentă adoptată; aproximările rămase trebuie documentate. Fracția de arie aparentă nu este automat fracția exactă de flux energetic; variația strălucirii pe discul solar nu este inclusă.

**Nu folosi e_center + rho > H(A_center) drept criteriu exact pe relief neregulat.** O parte laterală poate fi vizibilă printr-o depresiune chiar dacă partea superioară pe azimutul centrului este ascunsă. Verifică întinderea discului în azimut și elevație.

Pentru implementarea ulterioară: eșantionare adaptivă sau integrare/decupare geometrică a discului față de profil, cu verificarea convergenței. Absența unor eșantioane vizibile pe o grilă rară nu dovedește că întreaga arie este ascunsă. În apropierea unui contact, dacă rezoluția nu permite clasificarea, returnează o stare de incertitudine numerică și limite ale fracției, nu un fals zero exact. Un profil la 1° nu este suficient în general pentru un disc de lățime unghiulară sub un grad.

Pentru interfață: ascuns / parțial vizibil / complet vizibil / nedeterminat, cu fracția estimată și calitatea calculului. „Orice parte vizibilă” nu înseamnă putere utilă pentru un panou: orientarea suprafeței și fracția de flux se calculează separat.

Dacă eclipsele nu sunt implementate, eticheta trebuie să fie „vizibilitate față de relief, eclipse neincluse”. Dacă sunt implementate ulterior, combinați masca reliefului cu masca eclipsei pe același disc; nu înmulțiți automat două fracții scalare.

**Stare actuală:** aceasta este o decizie de comportament. Prototipul existent încă are criteriul centrului; vizibilitatea parțială nu a fost implementată sau testată în această rundă. Implementarea revine etapei prevăzute în backlog, fără extinderea tacită a E03.

## 5. Pământ și înălțime observator

Recomand menținerea criteriului centrului Pământului cu prag implicit 0°, configurabil:

    e_earth > max(H(A_earth), e_min)

Când terenul lipsește, H = 0 este permis doar în modul idealizat etichetat. Dacă pragul se măsoară față de orizontul ideal, un centru aflat sub 0° nu trece criteriul chiar dacă orizontul topografic ar fi mai jos. Denumiți rezultatul „criteriu de vizibilitate geometrică spre centrul Pământului”; nu garantează comunicații și nu reprezintă fracția vizibilă a discului terestru. Aceasta este o recomandare separată, nu o aprobare nouă atribuită utilizatorului.

Cei 2 m radiali au fost configurația testelor. Nu consider confirmată aici o nouă decizie de produs despre înălțimea implicită; păstrați alegerea deja documentată a echipei.

## 6. Mesaj pentru Claude Code

```text
Actualizează documentația deciziilor LunarHorizon, fără a începe o etapă nouă.
Păstrează semnificația reală a ID-urilor din repository.

D-02: adoptăm CN+S implicit, prin alegerea tehnică delegată de utilizator
asistentului. LT+S rămâne disponibil pentru diagnostic; NONE pentru geometric.
Documentează recepția, cadrul la observator și limitele relativiste ale modelului.

T-01: propunerea rezultată din analiză este acceptare la separare <= 0,001°,
cu avertizare de diagnostic peste 0,00001° pentru setul fix de referințe.
Înregistrează propunerea și preferința utilizatorului cu statutul real;
nu inventa aprobarea astronomilor. Nu modifica T-02/T-03 prin această regulă.

D-04 Soare: cerința explicită a utilizatorului este orice arie pozitivă a
discului solar deasupra orizontului modelat, inclusiv vizibilitate parțială.
În modul ideal: e_center + asin(R_sun/D_sun) > 0.
Pe relief: verifică discul pe întinderea lui, nu doar azimutul centrului.
Contactul tangent nu este arie vizibilă pozitivă. Precizia algoritmului și
starea nedeterminată lângă contact se documentează separat de T-01.
Marchează implementarea acestui criteriu ca restantă până la implementare
și teste în etapa sa; nu declara că vechiul criteriu al centrului o satisface.

Analiza locală nouă are 10/10 comparații CN+S/Horizons trecute, cu maxim
3.6053485372275007e-7 grade; nu este validarea repository-ului de aici.
Preia dovezile din pachet și reexecută cazurile relevante în implementarea
curentă, cu aceleași coordonate, altitudini, UTC și convenții.
Păstrează răspunsurile Horizons și raportează separat noile rezultate.
Nu atribui analizei o semnătură sau aprobare umană inexistentă.

Nu închide E03 doar pe baza acestui mesaj: verifică toate criteriile ei,
deciziile restante și eventuala corectare a coordonatelor prin E04.
Nu începe E05/E09/E10, nu crea remote, nu face push și nu publica.
```
