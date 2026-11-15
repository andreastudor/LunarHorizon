# data/

Datele proiectului. Planul complet este în [docs/DATA_PLAN.md](../docs/DATA_PLAN.md).

| Subdirector | Conținut | În Git |
|---|---|---|
| `catalog/` | Catalogul siturilor, cu sursa fiecărei poziții | Da |
| `manifests/` | Manifestele kernelurilor și ale produselor de teren: URL, versiune, sumă de control | Da |
| `terrain/` | Terenul vizual și manifestele pentru siturile demonstrative | De decis (D-15) |
| `reference/` | Cazurile de validare: cererea Horizons, răspunsul original, valorile extrase | Da |
| `precomputed/` | Scenariile offline | De decis (D-15) |

Fișierele brute mari (DEM, kerneluri) și cache-ul nu intră în Git. Se obțin cu scripturile din `scripts/`
și vor fi excluse prin `.gitignore` la etapa E01.

Datele brute descărcate sunt fixate prin manifestele din `manifests/` (kerneluri, PGDA 104: `pgda104_acquisition.json`,
LOLA GDR pentru orizont, E09: `lola_gdr_acquisition.json`); scripturile de achiziție le verifică cu `--verify`.
