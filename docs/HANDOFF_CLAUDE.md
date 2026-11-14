# LunarHorizon — handoff pentru Claude Code

Actualizat 2026-11-14. Termen: **15 noiembrie 2026, ora 13:00 Europe/Bucharest**. Prioritate P0 până la E17;
E18 numai după P0. O etapă pe rând; nu începe E06 înainte de evaluarea explicită a dependențelor.

## Stare și istoric

- Ramura `e04-completare-dovezi`; E00–E04 inițiale în `4fcac8c`, modificările premergătoare în `1a65a7d`.
- `0a0815d` elimină IM-1 și IM-2 din catalogul activ; nu le reintroduce. Catalogul are 10 intrări.
- E05 este **parțial implementată** în commit-ul care conține acest fișier (`git log -1`). D-07, D-10 și E04
  rămân deschise. Rezultatele istorice despre cele două situri retrase nu sunt blocaje pentru alte situri.
- E03 este implementată, dar deschisă: vezi STATUS pentru D-02, T-01 și celelalte alegeri.

## Date și comenzi

Din rădăcina repository-ului, în PowerShell:

```powershell
$env:PYTHONUTF8 = '1'
backend\.venv\Scripts\python scripts\download_terrain.py
backend\.venv\Scripts\python scripts\download_terrain.py --verify
backend\.venv\Scripts\python scripts\build_terrain.py
cd backend
.venv\Scripts\python -m pytest
.venv\Scripts\python -m ruff check . ..\scripts
.venv\Scripts\python -m ruff format --check . ..\scripts
.venv\Scripts\python -m mypy
cd ..\frontend
npm.cmd run dev
```

Pagina Vite este numai componenta rădăcină; API-ul nu este încă implementat. Instalarea completă și verificările
frontend sunt în README. Testele backend au trecut 289/289 în această sesiune, cu kerneluri; Ruff și mypy au trecut.

Date oficiale [PGDA 104](https://pgda.gsfc.nasa.gov/products/104), Leibnitz Beta Plateau, din arhiva
[Zenodo](https://zenodo.org/records/17954508). Se extrage prin HTTP Range numai `A310_GLDELEV_005.tif`, în
`data/_raw/pgda104/` (exclus din Git); CRC-ul membrului se verifică la extragere și SHA-256 este fixat după prima
descărcare. MD5-ul publicat pentru arhiva întreagă nu a fost verificat. Produsele generate sunt în
`data/_cache/terrain/leibnitz_beta/`: `calculation.tif`, `visual_8.tif`, `visual_16.tif` și manifestul vizual.
Manifestele versionate sunt `data/manifests/terrain_products.json` și `data/manifests/leibnitz_terrain.json`.

## Limite și următoarea acțiune

- Punctul provizoriu al rasterului este −85,4266039743°, 31,7441821732°E. Nu este poziție de aterizare și nu a
  fost aprobat ca sit D-07; PGDA 104 nu este unul dintre produsele numite în propunerea D-07.
- Cadrul `MOON_ME_DE421` din manifest este o ipoteză de lucru neconfirmată; nu a avut loc conversie de cadru.
  NoData și zona testată sunt consemnate în VALIDARE; `d_max` și acoperirea orizontului nu sunt confirmate.
- De terminat E05: evaluarea și aprobarea siturilor și sursei, D-05/D-06/D-19, verificarea conturului generat,
  textura globului și fundalurile 2D, datele de calitate și verificarea produselor într-o instalare curată.
- Următorul pas concret: inspectează produsul de calitate/număr de imagini PGDA 104 pentru punctul provizoriu,
  validează sursa și cadrul cu geografia, apoi alege al doilea sit și pregătește fundalurile oficiale. Nu confunda
  terenul vizual cu rasterul de calcul și nu marchează E05 completă fără criteriile din BACKLOG.
- E06 depinde de E03 și E04 conform backlog-ului; înaintea finalizării ei rămân deciziile E03 și verificările E04.
