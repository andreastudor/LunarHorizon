# LunarHorizon — handoff pentru Claude Code

## Cerință nouă obligatorie: E10A — Earth–Moon–Sun

Decizie utilizator, 2026-11-14: tabul cu Soare, Pământ și Lună în 3D, trasee și distanțe între centre
este **P0**, nu bonus. Planificat, neimplementat. Se execută după E10 și înainte de E11; E08 rămâne
dedicată terenului local. E17 include această cerință. Specificație și verificări:
[E10A_EARTH_MOON_SUN.md](E10A_EARTH_MOON_SUN.md).
Reutilizează SPICE pentru vectori geometrici între centre la același moment; nu folosi distanțele
observatorului lunar ca distanțe între centre. Interfață în engleză, sincronizare temporală și
etichetă Not to scale. Inspirație: Nasa-moon, cu verificarea provenienței și licenței la implementare.
Această actualizare este numai de planificare, nu o implementare sau o validare științifică.


Actualizat 2026-11-14. Termen: **15 noiembrie 2026, ora 13:00 Europe/Bucharest**. Prioritate P0 până la E17;
E18 numai după P0. O etapă pe rând; următoarea etapă este **E08** (neînceput).

## Stare și istoric

- Ramura `e04-completare-dovezi`, fără remote; commit-urile sunt locale (`git log --oneline`): E05 închis tehnic, apoi E06.
- IM-1 și IM-2 au fost eliminate intenționat din catalog (10 intrări); nu le reintroduce.
- **E05: implementare tehnică finalizată; acceptare științifică restantă.** Deciziile D-05/D-06/D-07/D-10/D-11/D-19 au
  aprobare de produs a utilizatorului, nu validare [GEO]; vezi [E05_DECIZII.md](E05_DECIZII.md). Punctul Leibnitz Beta
  este reprezentativ și provizoriu, nu loc de aterizare. `GLDSIGM` rămâne neinterpretat. MD5-ul arhivei complete nu a
  fost verificat (CRC de membru ZIP și SHA-256 local au fost).
- **E06: implementare tehnică finalizată; acceptare științifică restantă.** API-ul FastAPI calculează numai modul
  `idealized_local_plane` (fără efectele terenului local); `dem` este refuzat. Detalii: [API.md](API.md) §8.
- E03 și E04 rămân deschise (D-02, T-01, D-07, D-10 etc.); nu au blocat implementarea tehnică E06.
- **Schema 0.4.0:** azimut `null` cu motiv la zenit/nadir (commit separat).
- **E07: încheiată tehnic** (inclusiv criteriul WebGL, prin testul Playwright `npm run test:e2e`); **acceptare
  științifică restantă**. Interfața este în
  **engleză** (decizia utilizatorului; documentele de cerințe actualizate). Vezi STATUS, ACCEPTANCE, VALIDARE.

## Instalare, pornire, verificare

Din rădăcina repository-ului, PowerShell (Python 3.13; `py` implicit este 3.15):

```powershell
cd backend
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install pip==26.2.1
.venv\Scripts\python -m pip install --only-binary=:all: -c constraints.txt --group dev
cd ..
$env:PYTHONUTF8 = '1'
backend\.venv\Scripts\python scripts\download_kernels.py          # kerneluri SPICE, necesare simulărilor
```

Pornirea aplicației: întâi API-ul (din `backend/`), apoi interfața (din `frontend/`):

```powershell
cd backend
$env:PYTHONUTF8 = '1'
.venv\Scripts\python -m uvicorn lunarhorizon.api.app:app --host 127.0.0.1 --port 8000
# alt terminal
cd frontend
npm.cmd install        # o singură dată
npm.cmd run dev        # http://localhost:5173 (proxy /api → 8000)
```

Globul cere `data\_cache\e05_auxiliary\globe.jpg` (scripts\download_e05_auxiliary.py + build_e05_auxiliary.py);
fără el, globul apare fără imagine, cu un mesaj. Documentația API: `http://127.0.0.1:8000/api/docs`.

Verificări:

```powershell
cd backend
.venv\Scripts\python -m pytest                      # 330 de teste la această dată; -m kernels cere kernelurile
.venv\Scripts\python -m ruff check . ..\scripts
.venv\Scripts\python -m ruff format --check . ..\scripts
.venv\Scripts\python -m mypy
cd ..
backend\.venv\Scripts\python scripts\generate_contracts.py --check
backend\.venv\Scripts\python scripts\verify_e05.py   # cere datele E05 din data\_raw și data\_cache
cd frontend
npm.cmd run format:check; npm.cmd run lint; npm.cmd run contracts:check; npm.cmd run typecheck; npm.cmd test; npm.cmd run build
npx.cmd playwright install chromium   # o singură dată
npm.cmd run test:e2e                  # WebGL în Chromium headless; pornește/reutilizează API și Vite
```

Cereri de probă (cu serverul pornit; `curl.exe` în PowerShell):

```powershell
curl.exe http://127.0.0.1:8000/api/health
curl.exe http://127.0.0.1:8000/api/coverage
curl.exe -H "content-type: application/json" -d "@request.json" http://127.0.0.1:8000/api/simulations   # 202 + id
curl.exe http://127.0.0.1:8000/api/simulations/<id>
```

Un `request.json` valid are forma din [API.md](API.md) §2.5 cu `"terrain_mode": "idealized_local_plane"`.

## Date E05

Descărcare și generare: `scripts\download_terrain.py [--verify]`, `download_e05_auxiliary.py`, `build_terrain.py`,
`build_e05_auxiliary.py`, apoi `verify_e05.py`. Produsele sunt în `data\_cache\` (exclus din Git); manifestele versionate
sunt în `data\manifests\` (`terrain_products.json`, `leibnitz_terrain.json`, `e05_auxiliary.json`). Serviciul listează un
produs DEM în `health`/`coverage` numai dacă `data\_cache\terrain\leibnitz_beta\calculation.tif` există.

## Limite și următoarea acțiune

- Cadrul `MOON_ME_DE421` din manifestul de teren este o ipoteză neconfirmată; nu a avut loc conversie de cadru.
  Coordonatele din catalog sunt adoptate în `MOON_ME_DE440_ME421` prin ipoteză (E04).
- Azimutul nedefinit este `null` cu motiv din schema 0.4.0 și apare „Undefined” în interfață.
- Cache-ul simulărilor este în memorie; limita duratei (366 de zile, D-20) și criteriile D-04/D-16 sunt provizorii.
- Acoperirea orizontului, `d_max` și convergența țin de E09; al doilea sit și comparația, de E12.
- E07: testul WebGL folosește SwiftShader și nu este încă în CI (cere textura E05 neversionată). 3D/2D (E11) și
  Compare (E12) nu fac parte din E07.
- **Primul pas E08:** servește static `visual_8.tif`/`visual_16.tif` și manifestul de teren (`GET /api/terrain/manifest`),
  apoi construiește în frontend scena locală (`LocalSceneFrame` din `geo/scene.ts`) pentru punctul Leibnitz Beta
  provizoriu, cu NoData vizibil și exagerare verticală numai vizuală; nu prezenta textura globală ca teren.
- Nu confunda terenul vizual cu rasterul de calcul; nu marca E05/E06 acceptate științific fără validările [GEO]/[ASTRO].
