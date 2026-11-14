# E05 — propuneri de decizie, neaprobate

Toate propunerile rămân deschise. Metadatele și rezultatele sunt în [VALIDARE.md](VALIDARE.md).
O decizie de produs nu înlocuiește validarea [GEO] cerută de proiect.

| Decizie | Propunere și dovadă | Efect și incertitudine | Cine confirmă |
|---|---|---|---|
| D-05: referință verticală | Sfera de 1.737.400 m pentru rasterul PGDA 104 Leibnitz; raza este în CRS, înălțimile față de sferă în README-ul din ZIP | Altitudinile folosesc aceeași rază ca proiectul; compatibilitatea cu alte DEM-uri nu este demonstrată | Validare GEO |
| D-06: proiecție | Folosește parametrii citiți: stereografică polară sudică, latitudine origine −90°, meridian 0°, rază 1.737.400 m, X/Y în metri, pixel 5 m | Permite proiecția și eșantionarea; CRS-ul nu dovedește singur realizarea fizică ME/DE | Validare GEO |
| D-07: sursă și primul punct | Acceptă pentru prima demonstrație **ca punct reprezentativ provizoriu**, nu ca loc de aterizare, pixelul Leibnitz Beta (−85,4266039743°, 31,7441821732°E) din PGDA 104; acesta este un SDEM 5 m din LOLA și LROC, diferit de produsele 78/81 propuse inițial | Deblochează fluxul pentru primul punct; 16 × 16 km de raster, fereastră 201 × 201 validă. Calitatea și cadrul rămân limitate; al doilea sit, diferențele de iluminare și vizibilitate nu sunt demonstrate. Fără `d_max` nu se afirmă orizont complet | Acordul utilizatorului pentru schimbarea sursei/cerinței; validare GEO a siturilor și datelor |
| D-10: cadru | Păstrează provizoriu `MOON_ME_DE421` ca ipoteză, vizibilă în proveniență; nu pretinde conversie | Permite pregătire locală; sursa nu declară explicit realizarea în GeoTIFF, iar incertitudinea cadrului nu este cuantificată | Validare GEO; D-10 rămâne deschis |
| D-19: calitate | Expune separat hărțile de număr imagini NAC și benzi de azimut solar, la rezoluția lor reală de 15 m; zero este o valoare, nu NoData. Nu le numi număr de măsurători LOLA și nu atribui praguri sau precizie necunoscute | Păstrează proveniența și evită o clasificare falsă; definiția exactă a `GLDSIGM` și o hartă LOLA LDEC compatibilă trebuie clarificate | Validare GEO pentru criteriul/interpretarea de calitate |
| D-11: fundal | Folosește provizoriu NASA SVS CGI Moon Kit 2K pentru glob și hărțile 2D generate | Descărcare mică și utilizare offline; produs estetic, latitudinile polare completate din albedo LOLA, nu suport științific; credit și condiții în SOURCES | Acord de produs; confirmare GEO/creditare D-11 prevăzută de proiect |

`d_max`, convergența și alegerea produsului de teren îndepărtat sunt D-08/D-09 și E09, nu criterii de închidere
E05. E05 trebuie însă să descrie corect întinderea disponibilă și lipsurile, fără să afirme acoperire completă.
