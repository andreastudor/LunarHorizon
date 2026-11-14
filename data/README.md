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

Toate subdirectoarele sunt goale deocamdată. Nicio dată nu a fost descărcată.
