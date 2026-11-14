## Ce schimbă

<!-- Descriere scurtă. Trimite la etapa din docs/BACKLOG.md (de exemplu E05). -->

Etapă: E__

## Verificări rulate

<!-- Bifează numai ce ai rulat efectiv. Pentru ce nu ai rulat, spune de ce. -->

- [ ] Backend: `ruff check`, `ruff format --check`, `mypy`, `pytest`
- [ ] Frontend: `format:check`, `lint`, `typecheck`, `test`, `build`
- [ ] Verificare manuală în browser (dacă schimbarea afectează interfața)

## Documentație

- [ ] `docs/STATUS.md` actualizat
- [ ] `docs/ACCEPTANCE.md` / `docs/VALIDARE.md` actualizate cu dovezi reale, dacă e cazul
- [ ] Surse noi trecute în `docs/SOURCES.md`; limite noi în `docs/LIMITATIONS.md`

## Reguli de proiect

- [ ] Fără secrete, medii virtuale sau date brute mari în commit
- [ ] Datele sintetice sunt etichetate (`synthetic_`) și nu înlocuiesc datele reale
- [ ] `NoData` și valorile necunoscute nu devin zero
- [ ] Harta 3D rămâne cerință P0 și vederea implicită
- [ ] Deciziile `[ASTRO]` / `[GEO]` atinse au fost confirmate de colegi sau sunt marcate ca deschise
