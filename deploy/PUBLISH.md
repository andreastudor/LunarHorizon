# Publicarea aplicației complete

Publicarea a fost autorizată de utilizator la 2026-11-15. Repository-ul este privat;
publicarea site-ului nu autorizează implicit schimbarea vizibilității codului.
Nu există încă un backend public configurat. Fișierul Docker este pregătit, dar nu a fost
construit într-un motor Docker local (Docker nu este instalat aici).

## Varianta simplă: un server pentru UI și API

Un serviciu care poate rula containere Linux (Render, Railway sau un VPS) poate construi
direct ramura `e04-completare-dovezi` folosind `deploy/Dockerfile`, cu contextul `.`.
Conectează repository-ul în contul de găzduire și verifică planul/costul înainte de creare.
Nu a fost creat niciun serviciu plătit de această implementare.

```sh
docker build -f deploy/Dockerfile -t lunarhorizon .
docker run --rm -p 8000:8000 lunarhorizon
```

Deschide `http://localhost:8000`. Furnizorul public trebuie să ofere HTTPS.
Portul intern este `$PORT` (implicit 8000), health check `/api/health`.
Construirea descarcă kernelurile, textura, cele 13 DEM-uri și nivelul îndepărtat LOLA,
verifică produsele și se oprește dacă o sursă refuză descărcarea. Datele mari nu intră în Git.
Resursele necesare trebuie măsurate pe serviciul ales; nu există un test de capacitate publică.

Rulează **un singur proces Uvicorn și o singură replică**: joburile și ID-urile simulărilor
sunt locale procesului. Cache-urile se pierd la redeploy; utilizatorii rerulează simularea.
Nu porni `vite dev` sau `vite preview` în producție. Backendul servește `frontend/dist`.
Acest deployment nu implementează offline E15 și nu închide acceptarea științifică.

## Opțional: interfața pe GitHub Pages

1. Publică întâi serverul complet de mai sus și verifică `/api/health`:
   `status=ok`, `kernels_loaded=true`, toate cele 13 produse de teren disponibile.
2. Pe backend setează `LUNAR_ALLOWED_ORIGINS=https://andreastudor.github.io` și redeploy.
   Aceasta este originea, fără `/LunarHorizon/`. CORS expune dimensiunile rasterelor binare.
3. În GitHub, Settings → Secrets and variables → Actions → Variables, adaugă
   `LUNAR_API_BASE_URL=https://ADRESA-BACKENDULUI/api` (URL public, nu secret).
4. Settings → Pages → Source: GitHub Actions. Un repository privat necesită un plan GitHub
   care permite Pages privat; alternativ utilizatorul poate autoriza separat publicarea codului.
5. Împinge un commit pe `e04-completare-dovezi`. Workflow-ul `pages.yml` validează sănătatea
   API-ului, rulează testele/build-ul și publică artefactul la adresa furnizată de deploy-pages.
   În lipsa adresei API jobul este omis, pentru a nu publica o interfață nefuncțională.
   `main` nu este modificată; o lansare manuală workflow_dispatch cere workflow-ul pe ramura implicită.
6. Verifică fără autentificare: catalog, glob/textură, Earth–Moon–Sun, o simulare și un DEM.
   Doar după acest control considerăm publicarea efectuată.

Build local echivalent pentru Pages (PowerShell):

```powershell
$env:LUNAR_BASE_PATH = '/LunarHorizon/'
$env:VITE_API_BASE_URL = 'https://ADRESA-BACKENDULUI/api'
npm.cmd --prefix frontend run build
Remove-Item Env:LUNAR_BASE_PATH, Env:VITE_API_BASE_URL
```

Configurația locală implicită folosește în continuare `/api` și Vite proxy.
Nu pune chei de acces în variabile `VITE_*`: acestea sunt publice în JavaScript.

Surse: [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages),
[Vite deployment](https://vite.dev/guide/static-deploy.html#github-pages),
[FastAPI pe Render](https://render.com/docs/deploy-fastapi).
