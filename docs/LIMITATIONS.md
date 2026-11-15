# Limite și acoperire

Limitele cunoscute ale modelului și ale datelor, așa cum rezultă din proiectare. Documentul se actualizează
la fiecare etapă; ce apare aici trebuie să fie vizibil și în interfață, în rezumatul limitelor (modul simplu)
și în detaliu (modul expert).

Stare la 2026-11-14: aplicația nu este implementată. Limitele de mai jos sunt cele ale proiectului, nu constatări din rulare.

## 1. Domeniu

- Aplicația analizează condițiile la suprafață. Nu calculează ferestre de lansare sau traiectorii de coborâre.
- Vizibilitatea Pământului este geometrică. Nu modelează stații terestre, antene sau bugete de legătură.
- Aplicația nu explică rezultatul unei misiuni reale. Rezultatele simulării se prezintă separat de cauzele documentate ale unui eveniment de misiune.

## 2. Model astronomic

- Criteriul solar din MVP folosește centrul discului. Soarele are o rază unghiulară de aproximativ un sfert de grad, deci lumina parțială de la marginea discului nu este reprezentată. La poli, unde Soarele se mișcă aproape paralel cu orizontul, aceasta poate deplasa semnificativ momentele evenimentelor.
- Nu există refracție (Luna nu are atmosferă) și nu se modelează lumina împrăștiată sau reflectată de relief ori de Pământ.
- Suprafața de referință este o sferă. „Planul local” este perpendicular pe direcția radială, nu pe verticala gravitațională și nu urmează panta terenului.
- Raza unghiulară a Pământului folosește raza ecuatorială; turtirea este ignorată.
- La polul exact, azimutul depinde de o convenție (meridianul longitudinii date). În apropierea polului, azimutul este foarte sensibil la poziție.
- Momentele de timp au precizie de milisecundă în contracte și în interfață. Secunda intercalară `:60` nu poate
  fi introdusă ca text; momentele din interiorul ei nu sunt reprezentabile în formatul UTC al aplicației.
- Rezultatele sunt valabile numai în acoperirea temporală a kernelurilor încărcate: 1849-12-25 – 2150-01-21 pentru profilul implicit, cu o marjă de 600 s la capete. Pentru date viitoare, conversia UTC presupune că nu se adaugă secunde intercalare după 2017-01-01 (`naif0012.tls`); o secundă adăugată ulterior ar decala timpul cu 1 s.
- Diferența dintre cadrele mean-Earth ale DE421 și DE440 este, conform NAIF, de ordinul unui metru pe suprafață. Măsurat la E03: direcțiile Soarelui și Pământului diferă între profiluri cu cel mult 1,3·10⁻⁵°.
- Direcția aparentă include timpul de lumină și aberația stelară (`LT+S`, provizoriu; `CN+S` disponibilă), dar nu devierea gravitațională a luminii, pe care Horizons o aplică. Diferența față de Horizons este de ordinul 10⁻⁷°.
- Efemeridele locale (DE440s) diferă de cele folosite de Horizons (DE441). Acordul cu Horizons compară două implementări JPL; nu este o validare independentă și nu măsoară incertitudinea fizică.
- La zenit și la nadir azimutul nu este definit; motorul îl raportează ca nedefinit. Din schema 0.4.0 (E07) azimutul nedefinit este transmis ca `null` cu motiv în `quality.issues` și afișat „Undefined”; nu este înlocuit cu zero.
- Modul idealizat are orizontul plan la 0° și nu include efectele terenului local. Modul `dem` (E09–E10) calculează orizontul, vizibilitatea, evenimentele și indicatorii față de relief; o cerere fără orizont disponibil este refuzată, nu înlocuită.
- Vizibilitatea privește numai relieful: eclipsele nu sunt incluse. Fracția vizibilă a discului solar este o fracție de arie aparentă, nu putere solară. Pământul: linie de vedere geometrică spre centru, nu legătură radio.
- E10: obstacolele mai înguste decât pasul profilului fin (0,025°) nu pot fi excluse; perioadele nedecidabile (date lipsă sau parțiale, contacte aproape tangente) sunt raportate separat. Un singur sit (Leibnitz Beta) a fost verificat cap-coadă.
- Terenul local E08 este afișare: umbrele nu decid vizibilitatea; indicatoarele din scenă vin din rezultatul numeric (E10). Umbrele, lumina și exagerarea verticală sunt vizuale. Mesh-ul folosește nivelul de 40 m/pixel; detaliile sub 40 m nu apar în 3D.
- Rasterul Leibnitz Beta nu are NoData, deci afișarea golurilor (pătrate roșii, fără triunghiuri) este verificată numai pe date sintetice. Terenul acoperă 16 × 16 km; în afara lui nu se generează relief.
- Cadrul terenului (`MOON_ME_DE421`) este o ipoteză; direcțiile se desenează numai când simularea folosește același cadru. Observatorul din simulare rămâne pe sfera de referință: altitudinea terenului (≈ 6,4 km) nu intră încă în calculul direcțiilor (paralaxa estimată ≈ 0,001° pentru Pământ, estimare neverificată).
- Evenimentele se caută pe o grilă de scanare (≥ 900 s) și se rafinează la 1 ms; două treceri între eșantioane vecine nu sunt detectate. Cache-ul simulărilor este în memorie și se pierde la repornire.
- Coordonatele și altitudinile siturilor sunt intrări. Pentru Apollo 11, cazul de referință E03 folosește valori preluate din materialul unui prototip, neverificate în acest proiect; incertitudinea poziției sitului nu este propagată.

## 3. Relief și orizont

- E09: parametrii orizontului (`d_max` 300 km, `Δa` 0,5°, pași 5 m / 120 m, produsul `LDEM_75S_120M`) sunt propuneri tehnice (D-08/D-09 deschise). Convergența față de rezoluția apropiată nu este demonstrabilă (5 m este cel mai fin produs; 10 → 5 m schimbă până la 0,070°), iar terenul dincolo de grila îndepărtată nu este verificat. Integritatea fișierelor LOLA la sursă nu este verificabilă (PDS nu publică sume de control).
- Orizontul din relief există numai unde sunt încărcate produse DEM. În prima versiune, relieful de 5 m/pixel acoperă regiunea polară sudică (87–90°S) și siturile cu DEM propriu.
- Produsele PGDA umplu pixelii goi prin interpolare. O parte din relief este deci estimată, nu măsurată. Harta numărului de măsurători arată unde.
- Orizontul depinde de raza de căutare. Obstacolele aflate dincolo de datele încărcate nu sunt văzute de algoritm; azimuturile afectate sunt marcate `partial`.
- Profilul este eșantionat cu un pas azimutal finit și interpolat liniar. Trăsăturile mai înguste decât pasul pot fi netezite.
- Un pixel lipsă nu este tratat ca teren la altitudine zero. Unde lipsesc date, vizibilitatea este raportată ca necunoscută.
- Combinarea a două produse DEM (apropiat și îndepărtat) presupune compatibilitatea lor de cadru și de referință verticală, care trebuie verificată.
- Modul idealizat (`idealized_local_plane`) nu conține relief: orizontul este la 0° în toate direcțiile. Nu ține cont nici de coborârea orizontului pentru un observator ridicat deasupra sferei.

## 4. Evenimente și indicatori

- Momentul unui eveniment are o precizie numerică (toleranța rafinării) și o acuratețe fizică mult mai slabă, dată de DEM, de pasul azimutal, de criteriu și de înălțimea observatorului. Interfața nu prezintă momentele cu o precizie pe care modelul nu o are.
- Evenimentele foarte scurte sau aproape tangente pot fi ratate dacă sunt mai scurte decât rezoluția căutării.
- Intervalele care depășesc capetele analizei sunt trunchiate și marcate ca atare; durata lor reală nu este cunoscută.
- Eclipsele nu fac parte din MVP. Până la implementarea bonusului, o eclipsă nu apare ca întrerupere a luminii.

## 5. Vizualizare

- Mesh-ul 3D este o simplificare a DEM-ului, pentru afișare. Nu este folosit în calcule.
- Iluminarea și umbrele din scenă sunt aproximative și acoperă numai decupajul vizual. Starea vizibil/ascuns provine din calculul numeric.
- Soarele și Pământul sunt simboluri schematice; dimensiunile și distanțele din scenă nu sunt reale.
- Globul este o sferă texturată, cu nivel de detaliu declarat. Relieful real apare numai în vederea locală.
- Exagerarea verticală, când este activată, schimbă numai aspectul. La valori diferite de 1×, unghiurile văzute în scenă nu mai corespund celor calculate.
- Un clic pe glob dă un punct pe suprafața de referință, fără altitudine.
- Pe dispozitive fără suport WebGL suficient, harta 3D nu este disponibilă și aplicația folosește harta 2D.

## 6. Moduri de funcționare

- Modul precalculat (offline) conține numai siturile, intervalele și parametrii declarați în indexul scenariilor. Orice altă combinație este indisponibilă fără backend.
- Modul live depinde de fișierele locale ale backendului (kerneluri și rastere). Lipsa lor este raportată, nu compensată.
- Backendul rulează ca un singur proces și nu este dimensionat pentru mulți utilizatori simultan.

## 7. Catalog

- Pozițiile siturilor au incertitudinea declarată de sursă, când aceasta există. Un câmp necunoscut rămâne necompletat.
- Coordonatele istorice pot proveni din alt cadru decât cel intern; conversia și incertitudinea ei sunt documentate per sit.
- Pentru regiunile candidate, punctul afișat este unul reprezentativ, etichetat ca atare.

- Poziția fiecărei intrări a fost verificată la documentul original, dar **nu vizual** de colegii de geografie.
- Nicio sursă nu declară realizarea cadrului lunar (DE421/DE440). Adoptarea coordonatelor ca `MOON_ME_DE440_ME421` este o
  ipoteză; NAIF raportează între realizările ME o diferență de ordinul unui metru.
- Incertitudinea poziției este cea publicată de LROC (câmpul `UNCERTAIN`, de la 0,3 m la 10 m); metoda și nivelul de încredere
  nu sunt definite în documentele accesibile, iar lucrarea Icarus de referință nu a putut fi citită. LROC afirmă separat o
  nesiguranță orbitală de ≈ ±15 m. Valorile nu se combină și nu se deduc din numărul de zecimale.
- Ținta planificată are coordonate numerice doar pentru Chandrayaan-3. Pentru IM-1, IM-2 și Blue Ghost 1 sursele dau numai
  regiuni numite (Malapert A, Mons Mouton, Mons Latreille); aplicația nu inventează un punct pentru ele.
- Catalogul conține 12 intrări și nu include regiuni candidate; nu este un inventar al misiunilor lunare.
- Siturile demonstrative polare nu sunt alese (D-07), iar niciun sit din catalog nu este în mozaicul de 5 m/pixel 87–90°S.
- Dacă o poziție este actualizată de LROC (cum s-a întâmplat la Chandrayaan-3, ≈ 14 m), rezultatele deja calculate pentru
  valoarea veche nu devin valabile pentru cea nouă.

## 8. În afara versiunii curente

Efecte termice, praf și degradarea panourilor, poziții stelare, analiza pantelor și a obstacolelor pentru
aterizare, incertitudinea într-o elipsă de aterizare și comunicațiile cu stații terestre concrete apar ca
direcții ulterioare până când există un model implementat și verificat.
