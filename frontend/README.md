# frontend/

Interfața aplicației: React, TypeScript și Vite, cu Three.js pentru harta 3D (vederea implicită) și
OpenLayers pentru harta 2D sincronizată.

De la E01 conține configurația Vite, React și TypeScript, oxlint, Prettier, Vitest și componenta rădăcină;
comenzile sunt în [README.md](../README.md). Organizarea prevăzută (`app`, `state`, `data`, `geo`, `map3d`,
`map2d`, `sky`, `charts`, `compare`, `export`, `i18n`) este descrisă în
[docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) §5–§6.

De reținut: nicio componentă vizuală nu recalculează poziții sau vizibilitate; toate citesc același
rezultat de simulare. Mesh-ul, umbrele și exagerarea verticală sunt numai pentru afișare.
