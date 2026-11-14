# Specificație — LunarHorizon

> **Proveniență.** Secțiunile 1–20 reproduc specificația primită de la echipă în fișierul
> `PROMPT_CLAUDE_CODE_LUNARHORIZON_3D.md` (preluat la 2026-11-14). Acest document este contractul
> de cerințe. Deciziile de proiectare luate pe baza lui se află în celelalte documente din `docs/`.
>
> **Modificări de redactare față de sursă** (cerințele, criteriile și separarea P0/P1/P2 sunt neschimbate):
>
> 1. Preambulul „Instrucțiuni de execuție” a devenit secțiunea 0, „Principii obligatorii”.
>    Directivele de tip „începe implementarea acum” au fost scoase; ordinea de lucru este în [BACKLOG.md](BACKLOG.md).
> 2. Din linkuri a fost eliminat parametrul de urmărire `utm_source`.
> 3. §3.2, pasul 4: formularea a fost clarificată (total 2–4 situri).
> 4. §15: documentele de proiect stau în `docs/`; au fost adăugate `deploy/` și documentele noi.
> 5. §20: a fost eliminată fraza finală care cerea pornirea imediată a implementării.
>
> **Harta 3D.** Sursa tratează deja harta 3D drept cerință P0 și vedere principală. La preluare am
> căutat pasaje care o plasează la bonusuri sau o declară opțională și nu am găsit niciunul. Singura
> mențiune „opțională” (§5.1) privește integrarea React a bibliotecii Three.js, nu harta.

## 0. Principii obligatorii

- Harta 3D este cerință P0 și vederea principală implicită. Include atât explorare globală, cât și teren local tridimensional bazat pe DEM real în zonele acoperite. Harta 2D rămâne o vedere alternativă sincronizată.
- Un glob texturat fără relief local, o imagine statică sau un plan cu textură nu îndeplinesc cerința de hartă 3D. Harta 3D nu se mută la bonusuri, iar MVP-ul nu se declară complet fără ea.
- Se construiește mai întâi un flux complet pentru un sit polar: teren 3D real, observator, moment UTC, direcții Soare/Pământ, orizont și indicatori; apoi se extinde la comparația între 2–4 situri.
- Datele astronomice și relieful au surse verificabile. Nu se inventează coordonate, rezultate Horizons, fișiere SPICE, API-uri, acoperire LOLA sau rezultate ale testelor. Datele sintetice sunt permise pentru teste și demonstrații etichetate explicit.
- Calculele numerice provin din motorul științific. Umbrele și iluminarea randate în browser sunt vizualizări și nu reprezintă singure calculul vizibilității.
- Dacă o resursă externă nu este accesibilă, se implementează adaptorul și starea de eroare, se documentează blocajul și se continuă părțile independente. Un fallback idealizat nu înseamnă că integrarea LOLA sau cerința de relief 3D real este finalizată.
- Documentația actuală și compatibilitatea dependențelor se verifică înainte de integrare; versiunile utilizate se fixează. Sursele enumerate în specificație sunt puncte de pornire, nu dovezi că au fost accesate.
- Interfața implicită este în română, cu structură pregătită pentru engleză. Identificatorii tehnici ai surselor și exporturilor rămân neambigui.
- După fiecare etapă se rulează verificările relevante și se remediază erorile observate. Raportul final spune exact ce funcționează, comenzile de pornire, testele executate și cerințele încă incomplete.

Harta 3D face parte din MVP pe tot parcursul proiectului.

---

## 1. Obiectiv și domeniu

Construiește o aplicație web pentru proiectul **NASA Space Apps Challenge — Lunar Landing Site Navigator**.

Aplicația trebuie să ajute utilizatorul să răspundă la următoarele întrebări.

1. Unde se află Soarele și Pământul pe cer, văzute dintr-un anumit punct lunar?
2. Cum se schimbă pozițiile lor în perioada selectată?
3. Când sunt ascunse de relieful local?
4. Cât durează intervalele de lumină și de întuneric?
5. Cât timp rămâne până la următoarea dispariție a Soarelui sau a Pământului?
6. Care dintre siturile selectate oferă condițiile preferate pentru intervalul analizat?

Publicul include persoane fără pregătire tehnică, elevi, astronomi și cercetători. Interfața trebuie să permită înțelegerea rapidă a rezultatelor și inspectarea metodei de calcul.

**Domeniul inițial este analiza condițiilor la suprafață.** Data de „început al misiunii” reprezintă momentul din care analizăm operațiunile la sol. Calcularea unei ferestre de lansare sau a unei traiectorii de coborâre rămâne în afara acestei versiuni.

## 2. Priorități

### P0 — MVP obligatoriu

| Funcție | Rezultat cerut |
|---|---|
| Catalog de situri | Apollo, CLPS, alte misiuni și alte țări, cu surse verificabile |
| Hartă 3D — obligatoriu P0 | Vedere principală implicită asupra polului sud, glob lunar navigabil și teren local din DEM real; rotire, zoom, deplasare, selectare de puncte și sincronizare temporală |
| Hartă 2D | Vedere alternativă polară sudică și globală, sincronizată cu selecția și timpul din 3D |
| Puncte custom | Selectare prin clic și introducere manuală a coordonatelor |
| Comparație | 2–4 situri alăturate |
| Control temporal | Dată, oră UTC, interval, slider, redare și pauză |
| Geometrie astronomică | Azimutul și elevația Soarelui și Pământului |
| Orizont LOLA | Profil local de relief în zonele cu date disponibile |
| Evenimente | Următoarea apariție/dispariție și timp rămas |
| Indicatori | Durata luminii și ferestrele de vizibilitate a Pământului |
| Moduri de utilizare | Simplu și expert |
| Trasabilitate | Surse, modele, versiuni și limite vizibile |
| Demonstrație de rezervă | Scenarii precalculate disponibile offline |

### P1 — Bonusuri, în această ordine

1. Traiectoria aparentă a Pământului produsă de librație.
2. Eclipse solare văzute de pe Lună.
3. Rezumat avansat al intervalelor de întuneric.
4. Putere solară relativă.

MVP-ul va calcula deja intervalele necesare pentru durata luminii. Bonusul pentru întuneric adaugă prezentarea lor detaliată, durata maximă și evidențierea perioadelor problematice.

### P2 — Direcții ulterioare

- Efectele termice asupra sistemelor.
- Depunerea prafului și degradarea panourilor.
- Poziții stelare.
- Analiza pantelor și obstacolelor pentru aterizare.
- Analiza incertitudinii într-o elipsă de aterizare.
- Evaluarea comunicațiilor cu stații terestre concrete.

Aceste funcții apar în secțiunea „Future work” până când există un model implementat și verificat.

## 3. Experiența utilizatorului

### 3.1. Ecranul principal

Organizează interfața în patru zone.

| Zonă | Conținut |
|---|---|
| Stânga | Catalog, căutare, filtre, situri selectate |
| Centru | Hartă 3D implicită, marcaje, relief, conturul acoperirii DEM și comutator 3D / 2D |
| Dreapta | Rezumatul sitului activ și vedere locală a cerului |
| Jos | Interval temporal, moment curent, slider și redare |

Adaugă un buton clar **Compare** când sunt selectate minimum două situri.

### 3.2. Flux principal

1. Utilizatorul explorează harta 3D, alege un sit din catalog sau selectează un punct pe teren; poate comuta și la harta 2D.
2. Aplicația afișează numele ori coordonatele punctului.
3. Utilizatorul îl adaugă la comparație.
4. Mai selectează între unul și trei situri, pentru un total de 2–4.
5. Alege începutul și durata analizei.
6. Primește rezultatele pentru același interval și aceleași convenții.
7. Derulează timpul, iar terenul 3D, direcțiile Soare/Pământ, vederea cerului, graficele și indicatorii se actualizează sincronizat.
8. Deschide modul expert sau exportă rezultatele.

### 3.3. Ecranul de comparație

Pentru fiecare sit afișează o coloană cu aceiași indicatori, în aceeași ordine.

- Nume, misiune și coordonate.
- Tipul orizontului folosit și acoperirea datelor.
- Elevația Soarelui la momentul curent.
- Elevația Pământului la momentul curent.
- Starea vizibilității fiecărui corp.
- Timp până la următoarea dispariție.
- Durata luminii în interval.
- Durata vizibilității Pământului în interval.
- Grafic temporal.
- Profil de orizont și pozițiile corpurilor.

Pe desktop, arată 2–4 coloane. Pe mobil, păstrează accesibile aceleași informații printr-un aranjament vertical sau file.

### 3.4. Mod simplu și mod expert

| Mod simplu | Mod expert |
|---|---|
| Explicații în limbaj obișnuit | Azimut și elevație numerică |
| „Soare vizibil” | Criteriul exact de vizibilitate |
| „Pământ ascuns de relief” | Profilul orizontului și marja unghiulară |
| Durate și grafice clare | Pas temporal și toleranță numerică |
| Sursa principală | ID-uri de produse și versiuni |
| Rezumatul limitelor | Cadre, efemeride și parametri |

Ambele moduri folosesc aceleași rezultate.

### 3.5. Harta 3D — cerință obligatorie P0

Construiește o hartă 3D interactivă, integrată în fluxul principal al aplicației, cu două scări de explorare:

1. **Vedere globală:** glob lunar, coordonate, marcaje pentru situri, orientare inițială spre polul sud și navigare către situl ales. Dacă globul folosește doar geometrie sferică și o textură, etichetează nivelul său de detaliu; relieful local rămâne obligatoriu separat.
2. **Vedere locală:** teren tridimensional generat din date DEM reale pentru zonele polare acoperite, cu poziția observatorului și direcțiile spre Soare și Pământ. Pentru demonstrația finală, pregătește teren real pentru minimum două situri polare comparate.

Funcționalități obligatorii:

- Rotire, zoom, deplasare, resetarea camerei și acțiune „Mergi la sit”. Adaugă controale vizibile și instrucțiuni scurte pentru mouse și atingere.
- Selectare prin raycasting pe glob sau teren și conversie corectă în coordonate lunare; distinge clicul de gestul de rotire. La lipsa altitudinii, arată că selecția este pe suprafața de referință.
- Introducere manuală de latitudine și longitudine, validare și adăugare a punctului custom la comparație.
- Marcaje clare pentru situl activ și celelalte situri selectate; aceleași identificatoare și culori în hartă și comparație.
- Vedere de sus și perspectivă oblică asupra terenului; vedere de la observator pentru inspectarea orizontului.
- Scară verticală reală implicită, 1×. Orice exagerare verticală se afișează permanent și afectează exclusiv reprezentarea vizuală; calculele folosesc geometria reală.
- Observator amplasat folosind altitudinea terenului și înălțimea echipamentului. Documentează unitățile, axele și transformarea dintre cadrul lunar, cadrul local și scena 3D.
- Folosește o origine locală pentru teren când este necesar pentru precizia randării. Transformările către cadrul de calcul trebuie testate, inclusiv semnul longitudinii și orientarea axelor.
- Direcțiile spre Soare și Pământ provin din același rezultat astronomic ca indicatorii și graficele. Corpurile desenate schematic au etichete care explică dimensiunile și distanțele nereale din vizualizare.
- Iluminare orientată după vectorul solar calculat și indicatoare pentru vizibil/ascuns. Dacă umbrele sunt aproximative, precizează limita; ele nu înlocuiesc testul numeric față de profilul orizontului.
- Sincronizare cu sliderul UTC, redare/pauză, data de început, durata și situl activ. Rotirea camerei nu schimbă timpul sau rezultatele fizice.
- Afișarea conturului acoperirii DEM, sursei, rezoluției și zonelor `NoData`. Nu completa golurile cu altitudini inventate.
- Mesh-ul vizual poate fi simplificat pentru performanță; calculele orizontului folosesc produsul și rezoluția declarate separat. Decupajul vizual nu limitează automat raza de căutare a obstacolelor.
- Încărcare progresivă, niveluri de detaliu sau simplificare, cache pentru teren și eliberarea resurselor GPU când schimbi situl. Evită încărcarea întregului DEM de mare rezoluție în browser.
- Stări explicite pentru încărcare, eroare și lipsa datelor. Pe dispozitive fără suport WebGL suficient, oferă 2D ca fallback și explică indisponibilitatea 3D; această excepție nu elimină cerința 3D pentru dispozitive compatibile.
- Păstrează selecția siturilor, momentul UTC și parametrii analizei la comutarea 3D / 2D.

Pentru comparație este suficientă o scenă 3D comună ce urmărește situl activ, alături de cele 2–4 coloane sincronizate. Nu este obligatorie randarea simultană a patru scene costisitoare.

Scenariul offline trebuie să includă local codul necesar, mesh-urile sau datele de teren, texturile folosite și rezultatele precalculate pentru siturile și intervalele declarate. Nu trebuie să depindă de CDN-uri sau cereri externe în timpul demonstrației.

Cerința 3D este îndeplinită numai când utilizatorul poate explora globul, inspecta relieful real al siturilor demonstrative, selecta un punct și vedea pozițiile corpurilor actualizate odată cu timpul. Testele de acceptanță sunt obligatorii; un screenshot sau o scenă decorativă nu reprezintă dovada funcționalității.

## 4. Rolul resurselor

| Resursă | Utilizare în proiect |
|---|---|
| LROC QuickMap | Inspecția siturilor, reperelor, imaginilor și metadatelor straturilor |
| NASA Moon Trek | Explorare cartografică, verificare vizuală și identificarea produselor utile |
| JPL Horizons | Valori astronomice de referință și verificarea configurației observatorului |
| Canadian Space Agency | Context educațional și informații despre explorarea lunară |
| LOLA / NASA PGDA | Modele digitale de teren și informații despre calitatea lor |
| Documentația misiunilor | Coordonate, statut, ținte și puncte efective de aterizare |

QuickMap și Moon Trek sunt aplicații interactive. Accesul la interfața lor nu confirmă automat existența unui serviciu reutilizabil pentru toate datele afișate. Verifică separat serviciile, descărcările și condițiile fiecărui produs.

Folosește pagina CSA pentru context despre explorarea lunară și verifică documentația API Horizons înainte de interogări programatice. [Canadian Space Agency](https://www.asc-csa.gc.ca/eng/astronomy/moon-exploration/)

Pentru fiecare sursă utilizată, păstrează URL-ul, data accesării, autorul sau instituția, identificatorul produsului și condițiile de creditare.

## 5. Arhitectură propusă

### 5.1. Componente

| Componentă | Alegere propusă |
|---|---|
| Frontend | React + TypeScript + Vite |
| Hartă 2D | OpenLayers, cu proiecții lunare explicite |
| Grafice | Plotly |
| Vedere locală a cerului | SVG sau Canvas |
| Backend | Python + FastAPI |
| Motor astronomic | SPICE prin SpiceyPy |
| Verificare astronomică | JPL Horizons |
| Procesarea terenului | GDAL, Rasterio, NumPy |
| Hartă 3D — din prima etapă a MVP | Three.js, cu integrare React opțională; glob lunar și mesh-uri locale din DEM, convenții lunare explicite |
| Catalog | JSON sau CSV versionat |
| Cache | Fișiere pe disc sau SQLite |
| Teste | Pytest și teste de interfață pentru fluxurile principale |

Acestea sunt alegeri inițiale de proiectare. La început, verifică instalarea și compatibilitatea versiunilor în mediul echipei.

### 5.2. Fluxul datelor

1. Frontendul trimite siturile, intervalul și opțiunile.
2. Backendul validează datele și verifică acoperirea temporală și geografică.
3. Obține altitudinea și profilul orizontului.
4. Calculează pozițiile Soarelui și Pământului.
5. Determină intervalele de vizibilitate și evenimentele.
6. Salvează rezultatul în cache.
7. Returnează serii temporale, indicatori și metadate.

Pentru siturile și intervalele demonstrației, pregătește aceleași rezultate în fișiere statice.

**În modul offline, punctele și datele disponibile trebuie indicate explicit.** Dacă utilizatorul alege o combinație neprecalculată și backendul lipsește, afișează această stare.

### 5.3. Performanță

- Solicită calculul după confirmarea selecției sau după o scurtă pauză a utilizatorului.
- Sliderul folosește datele deja încărcate.
- Calculele costisitoare de orizont rulează separat de actualizările vizuale.
- Cererile depășite de o selecție mai nouă trebuie anulate sau ignorate.
- Cheia cache-ului include coordonatele, înălțimea observatorului, intervalul, criteriile și versiunile modelelor.
- Eventuala rotunjire spațială pentru cache trebuie documentată și reflectată în coordonatele efectiv calculate.

## 6. Catalogul siturilor

### 6.1. Câmpuri minime

| Câmp | Semnificație |
|---|---|
| `id` | Identificator stabil |
| `name` | Numele sitului |
| `mission` | Misiunea asociată |
| `agency`, `operator`, `country` | Organizația, operatorul și țara |
| `status` | Aterizat, planificat, candidat, impact sau custom |
| `geometry_type` | Punct sau regiune |
| `latitude_deg`, `longitude_deg` | Coordonatele în cadrul adoptat |
| `frame_id` | Cadrul de coordonate |
| `original_coordinates` | Coordonatele și cadrul din sursă |
| `horizontal_uncertainty_m` | Incertitudinea disponibilă |
| `source_url` | Sursa poziției |
| `accessed_at` | Data accesării |
| `description_ro`, `description_en` | Descriere scurtă |

Altitudinea, când este disponibilă, trebuie însoțită de referința sa.

### 6.2. Reguli

- Folosește coordonate din surse oficiale sau produse documentate.
- Păstrează distinct ținta planificată și poziția efectivă.
- Pentru regiuni candidate, afișează poligonul disponibil. Un punct reprezentativ trebuie etichetat ca atare.
- Marchează explicit un punct selectat de utilizator drept custom.
- Un câmp necunoscut rămâne `null`, cu explicație în interfață.
- Verifică vizual pozițiile pe produsele adecvate.

Pentru primul demo, propun un catalog mic, verificat, cu situri Apollo, câteva situri polare și misiuni internaționale. Extinderea se face după funcționarea completă a comparației.

## 7. Coordonate și timp

### 7.1. Cadru lunar

Adoptă un singur cadru pentru calculele interne și documentează transformările.

Verifică în metadatele produsului compatibilitatea cadrului propus pentru DEM-ul polar: **`MOON_ME`, asociat DE421**. Mozaicul LOLA 87–90°S este distribuit la 5 m/pixel în proiecție stereografică polară sudică, cu această referință. [South Pole LOLA DEM Mosaic](https://pgda.gsfc.nasa.gov/products/81)

În `SPEC_FIZICA.md`, precizează separat

- cadrul de orientare al Lunii;
- convenția latitudinii;
- longitudinea pozitivă spre est și intervalul ales;
- proiecția hărții;
- raza sau modelul formei de referință;
- referința altitudinilor;
- efemeridele și fișierele de orientare folosite.

Un nume generic de cadru nu este suficient pentru reproductibilitate.

### 7.2. Timp

- Interfața, cererile și exporturile folosesc UTC.
- Timestampurile includ `Z` sau un offset explicit.
- Conversia spre timpul intern cerut de SPICE se face prin biblioteca astronomică.
- Acoperirea temporală a fișierelor trebuie verificată înainte de calcul.
- Datele din afara acoperirii primesc un mesaj clar.
- Data de aterizare istorică și începutul simulării sunt câmpuri separate.

## 8. Motorul astronomic

Pentru fiecare sit și moment, calculează

- vectorul spre Soare;
- vectorul spre Pământ;
- distanțele;
- azimutul și elevația fiecărui corp;
- razele unghiulare necesare;
- convenția corecțiilor aplicate.

Definește azimutul de la nord, crescând spre est. Definește elevația față de planul local adoptat. Documentează comportamentul la polul exact, unde direcția nord necesită o convenție explicită.

Pentru observator, folosește poziția terenului și înălțimea echipamentului deasupra lui.

În verificările cu Horizons, salvează cererea și răspunsul original. Parametrii pentru observator, timp și tipul coordonatelor trebuie configurați explicit. Documentația API expune separat aceste opțiuni. [ssd-api.jpl.nasa.gov](https://ssd-api.jpl.nasa.gov/doc/horizons.html)

## 9. Orizontul din relief LOLA

### 9.1. Pregătirea terenului

Pentru fiecare produs DEM, păstrează

- identificatorul și URL-ul;
- cadrul și proiecția;
- rezoluția;
- unitățile verticale;
- valoarea `NoData`;
- referința altitudinilor;
- informațiile despre interpolare și calitate.

Decupajul trebuie să includă relieful care poate influența orizontul. La pol, un decupaj foarte mic poate omite obstacole importante din depărtare.

### 9.2. Algoritmul

Pentru fiecare azimut în jurul observatorului

1. Eșantionează terenul pe direcția respectivă.
2. Transformă punctele într-o geometrie tridimensională comună.
3. Calculează elevația aparentă a terenului din poziția observatorului.
4. Păstrează elevația maximă și distanța obstacolului care o produce.
5. Marchează acoperirea incompletă sau datele lipsă.

Ține cont de curbura Lunii. Alege distanța de căutare și pasul azimutal prin teste de convergență.

**Un pixel lipsă nu reprezintă teren la altitudinea zero.** Un profil incomplet trebuie să producă un indicator de calitate corespunzător.

### 9.3. Mod de rezervă

Dacă terenul lipsește, permite explicit `idealized_local_plane`, cu orizontul la 0°.

Afișează permanent mesajul „Local terrain not included”. Acest mod simplifică modelul și permite explorarea astronomică.

## 10. Vizibilitate și timp până la dispariție

### 10.1. Criteriul pentru Soare

Pentru MVP, propun criteriul **centrului discului deasupra profilului orizontului**, afișat în interfață.

Definește

\[
c(t)=e(t)-H(a(t))
\]

unde \(e\) este elevația centrului, \(a\) azimutul și \(H\) profilul terenului.

Criteriul este îndeplinit când \(c(t)>0\).

Ca extensie, calculează fracția discului vizibil prin eșantionarea discului pe profilul terenului. Aproximația cu marginea superioară trebuie etichetată, mai ales când relieful variază pe lățimea discului.

### 10.2. Criteriul pentru Pământ

Pentru MVP, folosește centrul Pământului și un prag minim de elevație setabil.

Condiția propusă este

\[
e_{\mathrm{Earth}}(t)>\max\!\left(H(a_{\mathrm{Earth}}(t)),e_{\min}\right)
\]

Afișează rezultatul ca **vizibilitate geometrică spre Pământ**. O legătură radio cu o stație anume necesită modelarea poziției acelei stații și a echipamentelor.

### 10.3. Detectarea evenimentelor

- Caută toate tranzițiile criteriului în interval.
- Folosește eșantionare adaptivă și rafinare în apropierea orizontului.
- Verifică și intervalele scurte sau contactele apropiate de tangentă, care pot fi ratate de eșantioane rare.
- Păstrează evenimentele separat de punctele folosite la desenarea graficului.
- Nu deduce momentul apusului doar din interpolarea unui grafic orar.

Definește comportamentul interfeței astfel.

| Situație | Afișare |
|---|---|
| Corp vizibil și dispariție găsită | Timp până la dispariție |
| Corp deja ascuns | „Currently hidden” și timpul până la apariție, dacă există |
| Eveniment negăsit în interval | „No event within the analysed interval” |
| Date insuficiente | „Event unavailable” și motivul |

O eclipsă va avea un tip propriu de eveniment. Dispariția din cauza terenului și ocultarea de către Pământ trebuie să poată fi explicate separat.

## 11. Indicatori și grafice

### 11.1. Indicatori obligatorii

- Elevație curentă Soare și Pământ.
- Durată cu criteriul solar îndeplinit.
- Procent din interval cu lumină, conform criteriului ales.
- Ferestre de vizibilitate spre Pământ.
- Următoarele apariții și dispariții.
- Durată cu ambele criterii îndeplinite simultan.

### 11.2. Grafice

1. Elevația Soarelui și a Pământului în timp.
2. Benzi temporale pentru lumină și vizibilitatea Pământului.
3. Profilul orizontului în funcție de azimut.
4. Vedere locală a cerului cu repere nord, est, sud și vest.

Folosește aceeași scară pentru graficele comparate sau indică explicit diferențele. Culorile propuse sunt ambră pentru Soare și albastru pentru Pământ. Adaugă simboluri și etichete pentru accesibilitate.

Dacă discurile sunt mărite pentru lizibilitate, afișează că dimensiunile sunt schematice.

## 12. Bonusuri

### 12.1. Traiectoria aparentă a Pământului

Afișează pozițiile în azimut și elevație pe intervalul ales, cu culoare sau marcaje temporale.

Folosește denumirea principală **„Earth apparent path / Libration”**. Dacă apare termenul „analemă”, explică perioada și regula de eșantionare. Forma curbei rezultă din calcule.

### 12.2. Eclipse

Determină suprapunerea aparentă a discurilor Soarelui și Pământului din poziția observatorului lunar.

- Verifică ordinea corpurilor pe linia de vedere.
- Calculează fracția discului solar ocultat.
- Identifică începutul, maximul și sfârșitul evenimentului.
- Folosește razele unghiulare calculate la momentul respectiv.
- Documentează aproximațiile geometrice.

Pentru energia directă, combină masca terenului cu masca eclipsei pe același disc solar. Două fracții scalare de vizibilitate înmulțite pot reprezenta greșit suprapunerea.

### 12.3. Întuneric

Afișează intervalele, cea mai lungă perioadă și cauza modelată.

Dacă o perioadă începe înainte sau continuă după intervalul analizat, marchează durata ca trunchiată la limita simulării.

### 12.4. Putere relativă

Implementează

\[
P_{\mathrm{rel}}(t)=\max(0,\mathbf{n}\cdot\mathbf{s}(t))\,f_{\mathrm{visible}}(t)
\]

unde \(\mathbf{n}\) este normala panoului, \(\mathbf{s}\) direcția unitară spre Soare, iar \(f_{\mathrm{visible}}\) fracția vizibilă modelată.

Permite configurarea înclinării și azimutului panoului. Arată rezultatul ca indice între 0 și 1 sau procent.

Dacă folosești numai un criteriu binar de iluminare, declară această aproximație. Etichetează integrarea indicelui în timp în unitățile corespunzătoare, de exemplu ore echivalente la putere relativă maximă.

## 13. Contracte de date și API

### 13.1. Cerere de simulare

Include cel puțin

- lista siturilor și coordonatele efective;
- cadrul coordonatelor;
- începutul și sfârșitul UTC;
- înălțimea observatorului;
- criteriul solar;
- criteriul pentru Pământ și elevația minimă;
- modul de teren;
- configurația panoului, când este activă.

### 13.2. Răspuns

| Grup | Conținut |
|---|---|
| `sites` | Situri și coordonate efectiv folosite |
| `series` | Poziții, vizibilitate și alte rezultate temporale |
| `events` | Apariții, dispariții și eclipse |
| `summary` | Durate și indicatori |
| `horizon` | Profil și acoperire |
| `terrain` | Referința manifestului/mesh-ului, DEM, rezoluție vizuală și de calcul, acoperire, cadru, unități, origine locală și limite |
| `provenance` | Surse, versiuni și configurație |
| `quality` | Date lipsă, aproximații și limite |

Păstrează distinct valorile zero, valorile necunoscute și funcțiile necalculate.

### 13.3. Endpointuri propuse

| Endpoint | Rol |
|---|---|
| `GET /api/sites` | Catalog |
| `GET /api/coverage` | Acoperire DEM și temporală |
| `GET /api/terrain/manifest` | Metadate și resurse de teren disponibile pentru zona cerută; parametri validați și documentați |
| `POST /api/simulations` | Pornirea sau recuperarea unei simulări |
| `GET /api/simulations/{id}` | Stare și rezultat |
| `GET /api/health` | Disponibilitatea serviciului |

Exportul trebuie să includă CSV pentru seriile numerice și JSON pentru configurația completă și metadate.

## 14. Validare

### 14.1. Referințe

Pregătește 10–15 cazuri astronomice care includ

- situri nepolare;
- situri apropiate de polul sud;
- Soare aproape de orizont;
- Pământ aproape de orizont;
- longitudini estice și vestice;
- începutul și sfârșitul intervalului de demo.

Pentru fiecare caz, păstrează configurația Horizons, răspunsul original și rezultatul aplicației.

Horizons verifică geometria astronomică. Pentru profilul LOLA, folosește verificări geometrice, produse adecvate și cazuri sintetice.

### 14.2. Toleranțe

Înaintea implementării fiecărui modul, echipa stabilește în `VALIDARE.md`

- mărimea comparată;
- toleranța numerică;
- motivul alegerii;
- sursa de referință;
- condițiile în care comparația este validă.

Acuratețea fizică a rezultatului trebuie evaluată separat de precizia numerică a algoritmului. O rădăcină găsită la o secundă nu dovedește că apusul este cunoscut fizic la o secundă.

### 14.3. Teste necesare

| Domeniu | Test |
|---|---|
| Coordonate | Conversie dus-întors între harta 2D, scena 3D și coordonate lunare; verificarea axelor și unităților |
| Hartă 3D | Glob navigabil, teren DEM real, rotire/zoom, raycasting, observator pe teren și resetarea camerei |
| Sincronizare 3D | Schimbarea timpului/sitului actualizează corpurile și indicatorii; camera și exagerarea verticală nu modifică rezultatele |
| Calitate 3D | NoData vizibil, fallback WebGL explicit, încărcare/erori, resurse GPU eliberate și scenariu offline cu teren local |
| Longitudine | Continuitate la ±180° |
| Timp | UTC, conversii și limitele efemeridelor |
| Astronomie | Comparație cu referințele Horizons |
| Orizont | Teren sintetic cu obstacol cunoscut |
| DEM | Gestionarea `NoData` și a marginilor |
| Evenimente | Tranziții scurte și rafinarea temporală |
| Eclipse, dacă bonusul este implementat | Fără suprapunere, suprapunere parțială și totală |
| Putere, dacă bonusul este implementat | Panou orientat spre Soare, perpendicular și opus |
| Interfață | 2–4 situri sincronizate |
| Concurență | Rezultatele vechi nu înlocuiesc selecția nouă |
| Offline | Scenariu precalculat complet funcțional |

## 15. Organizarea repository-ului

| Director sau fișier | Conținut |
|---|---|
| `frontend/` | Interfață |
| `backend/` | API și calcule |
| `scripts/` | Descărcare și preprocesare |
| `data/catalog/` | Catalogul siturilor |
| `data/manifests/` | Referințe și metadate |
| `data/terrain/` | Decupaje/mesh-uri pentru demo, metadate și niveluri de detaliu; fișierele mari se descarcă reproductibil |
| `data/reference/` | Cazuri de validare |
| `data/precomputed/` | Scenarii offline |
| `tests/` | Teste |
| `deploy/` | Configurații de build și publicare |
| `README.md` | Instalare, pornire și demo |
| `CLAUDE.md` | Reguli scurte pentru Claude Code |
| `docs/SPECIFICATIE.md` | Acest document |
| `docs/ARCHITECTURE.md` | Module, fluxuri și decizii tehnice |
| `docs/SPEC_FIZICA.md` | Convenții și formule |
| `docs/API.md` | Contracte de date și endpointuri |
| `docs/DATA_PLAN.md` | Produse de date, preprocesare și stocare |
| `docs/BACKLOG.md` | Etapele de implementare |
| `docs/ACCEPTANCE.md` | Criterii de acceptanță și starea cerințelor P0 |
| `docs/VALIDARE.md` | Toleranțe, rezultate și probleme |
| `docs/SOURCES.md` | Surse și credite |
| `docs/LIMITATIONS.md` | Limite și acoperire |
| `docs/STATUS.md` | Starea curentă și decizii deschise |

Fișierele mari de teren se gestionează prin descărcări reproductibile și manifeste cu versiuni și checksumuri, conform soluției de stocare aleasă de echipă.

## 16. Instrucțiuni de lucru pentru Claude Code

1. Inspectează repository-ul și instrucțiunile existente.
2. Confirmă dependențele și accesul la date înainte de integrare.
3. Creează întâi un flux complet pentru un sit polar și un interval, inclusiv teren 3D real și direcții astronomice sincronizate.
4. Validează geometria înainte de extinderea interfeței.
5. Implementează module mici și rulează verificările relevante după schimbări.
6. Păstrează convențiile în configurații comune.
7. Documentează fiecare modul în câteva rânduri pentru echipă.
8. Marchează datele simulate și funcțiile incomplete.
9. Încheie fiecare etapă cu rezultatul verificabil și ce mai lipsește.
10. Înregistrează în `CLAUDE.md` deciziile convenite, inclusiv UTC, cadrele și cerințele de validare.

## 17. Plan de lucru pentru 48 de ore

Calendarul este orientativ și trebuie raportat la programul real al evenimentului.

| Interval | Livrabil | Criteriu de trecere |
|---|---|---|
| H0–H3 | Specificație fizică, structură, date selectate | Convențiile și sursele sunt documentate |
| H3–H8 | Un sit, Soare/Pământ, referințe | Geometria trece verificările |
| H8–H14 | Hartă 3D globală și locală, hartă 2D, catalog, coordonate custom, timp | Se poate selecta un punct în 3D și simula; primul sit are relief real |
| H14–H20 | LOLA, relief 3D, orizont și evenimente | Un sit polar funcționează cap-coadă, cu date reale și verificări geometrice |
| H20–H28 | Comparație 2–4 situri, teren 3D pentru două situri polare, moduri simplu/expert | Rezultatele și scena 3D sunt sincronizate |
| H28–H32 | Închiderea cerințelor P0; bonusuri numai dacă P0 este complet | Harta 3D și toate cerințele MVP sunt verificate înaintea bonusurilor |
| H32–H40 | Stabilizare, exporturi, documentație, video | Demo reproductibil |
| H40–H46 | Repetiții, test offline și depunere | Materialele sunt pregătite și verificate |
| H46–H48 | Rezervă | Corecții critice, conform termenului real |

La H20, dacă orizontul LOLA încă nu funcționează, echipa păstrează aplicația utilizabilă cu modul idealizat și consemnează cerința incompletă. Prioritatea următoare este recuperarea reliefului real și a orizontului pentru scenariile polare. Nu elimina harta 3D și nu declara MVP-ul complet cât timp cerințele sale P0 sunt incomplete.

## 18. Responsabilitățile echipei

| Rol | Livrabil și responsabilitate |
|---|---|
| Cartografie și date | Catalog verificat, DEM, proiecții, repere și acoperire |
| Fizică și validare | Convenții, referințe, toleranțe și verificarea rezultatelor |
| Programare cu Claude Code | Backend, interfață, integrare și teste |
| Design și prezentare | Identitate vizuală, texte, demo și video |
| Testare și coordonare | Scenarii de utilizare, surse, probleme și checklist de depunere |

Povestea IM-2 poate deveni un studiu de caz în prezentare după verificarea surselor. Aplicația trebuie să distingă rezultatele propriei simulări de cauzele documentate ale rezultatului unei misiuni.

## 19. Definiția finală a MVP-ului

MVP-ul este complet numai după verificarea tuturor funcțiilor P0, când un utilizator poate

- explora harta 3D implicită, cu glob lunar și relief DEM real pentru minimum două situri polare demonstrative;
- roti, mări și deplasa camera, selecta puncte în 3D și inspecta vederea de la observator;
- comuta 3D / 2D fără pierderea selecției sau a timpului;
- selecta între două și patru situri;
- adăuga un punct custom;
- alege și derula un interval UTC;
- vedea Soarele și Pământul față de orizont;
- compara duratele și ferestrele de vizibilitate;
- vedea timpul până la următoarea tranziție;
- identifica sursa și calitatea datelor;
- comuta între modul simplu și expert;
- exporta configurația și rezultatele;
- rula un scenariu demonstrativ offline, inclusiv terenul 3D și resursele locale necesare.

**Demonstrația principală** pornește în harta 3D la polul sud, explorează relieful real pentru două situri, le compară în același interval și apoi schimbă data de început. Echipa arată cum relieful și mișcarea aparentă a Soarelui și Pământului modifică perioadele disponibile pentru activități la suprafață.

---
## 20. Livrarea finală

Livrează:

1. Aplicația funcțională și codul sursă organizat, cu frontend și backend integrate.
2. Scripturi și comenzi exacte pentru instalare, descărcarea datelor, pornire, build și teste; instrucțiuni adecvate sistemului de operare detectat.
3. Un scenariu reproductibil pentru minimum două situri polare cu relief real, comparație și hartă 3D sincronizată, disponibil și offline în limitele declarate.
4. Documentația convențiilor fizice, provenienței datelor, acoperirii și limitelor, inclusiv diferența dintre geometria de randare și cea de calcul.
5. Rezultatele verificărilor executate efectiv. Pentru testele neexecutate, precizează motivul; nu raporta teste drept trecute fără rulare.
6. Un tabel final al cerințelor P0 cu stările „implementat și verificat”, „implementat, neverificat” sau „incomplet”, plus fișierele ori verificările care susțin fiecare stare.
