// User interface texts (English), by key. The interface language is English (decision of 2026-11-14);
// the key structure stays ready for other languages, without a language selector for now.
// Technical identifiers, API field names, original source titles and official site names are not
// translated.

export const en = {
  app: {
    title: 'LunarHorizon',
    tagline: 'Sun and Earth from any point on the Moon',
    independent: 'Independent project — not an official NASA product.',
  },
  zones: {
    catalog: 'Sites and parameters',
    globe: '3D lunar globe',
    summary: 'Active site',
    time: 'Time control',
  },
  common: {
    loading: 'Loading…',
    retry: 'Retry',
    undefined: 'Undefined',
    unknown: 'Unknown',
    notComputed: 'Not computed',
    yes: 'Yes',
    no: 'No',
    none: 'None',
    utc: 'UTC',
  },
  catalog: {
    southPolarOnly: 'South polar sites only (≤ 60° S)',
    terrainBadge: {
      terrain_available: 'Terrain available',
      terrain_not_downloaded: 'Terrain not downloaded',
      coverage_unverified: 'Coverage unverified',
      no_dem_coverage: 'No DEM coverage',
      frame_mismatch: 'Frame mismatch',
    } as Record<string, string>,
    heading: 'Site catalog',
    search: 'Search sites',
    searchPlaceholder: 'Name, mission or agency',
    loading: 'Loading the site catalog…',
    empty: 'No site matches the search.',
    error: 'The site catalog could not be loaded.',
    count: (shown: number, total: number) => `${shown} of ${total} sites`,
    mission: (status: string) => `Mission: ${status}`,
    positionKind: {
      actual: 'Actual position',
      planned_target: 'Planned target',
      representative_point: 'DEM representative point',
    } as Record<string, string>,
    missionStatus: {
      landed: 'Landed',
      impacted: 'Impacted',
      not_landed: 'Did not land',
      planned: 'Planned',
      unknown: 'Unknown status',
      not_applicable: 'Not applicable (no mission)',
    } as Record<string, string>,
  },
  point: {
    heading: 'Point by coordinates',
    hint: 'Or click the globe. Longitude is positive to the east.',
    latitude: 'Latitude (°)',
    longitude: 'Longitude (°E)',
    label: 'Label',
    defaultLabel: 'Selected point',
    use: 'Use these coordinates',
    latitudeError: 'Latitude must be a number between −90 and 90.',
    longitudeError: 'Longitude must be a number between −180 and 360.',
    labelError: 'Enter a label.',
  },
  coverage: {
    heading: 'DEM coverage',
    loading: 'Loading coverage…',
    error: 'Coverage could not be loaded.',
    temporal: (start: string, end: string, profile: string) =>
      `Ephemerides: ${start} – ${end} (kernel profile ${profile})`,
    noTerrain: 'No DEM product is available on this server.',
    product: (id: string, role: string, resolution: number) =>
      `${id} · ${role} · ${resolution} m/pixel`,
    extentNote:
      'Outline of the raster extent only — not a validated horizon coverage.',
    show: 'Show on globe',
    useRepresentative: 'Select its DEM representative point',
    frameNotes: {
      demPoint: (frame: string) =>
        `Request frame set to ${frame}, the frame declared by the DEM product (working hypothesis, not validated). The point's coordinates come from that DEM; no coordinate conversion is applied.`,
      reinterpreted: (frame: string) =>
        `The same latitude and longitude are now interpreted in ${frame}, the DEM's declared frame (working hypothesis). No coordinate conversion was performed: if the point was defined in another frame, this is not guaranteed to be the same physical position.`,
    },
  },
  params: {
    heading: 'Simulation',
    startDate: 'Start date (UTC)',
    startTime: 'Start time (UTC, 24 h)',
    duration: 'Duration',
    days: (n: number) => (n === 1 ? '1 day' : `${n} days`),
    observerHeight: 'Observer height above surface (m)',
    earthMinElevation: 'Earth minimum elevation (°)',
    frame: 'Reference frame',
    terrainMode: 'Horizon',
    idealized: 'Idealized — local terrain not included',
    dem: 'DEM terrain (not available yet)',
    run: 'Run simulation',
    running: 'Simulating…',
    needSelection: 'Select a site or a point first.',
    invalid: 'Check the highlighted parameters.',
    heightError: 'Enter a height of 0 m or more.',
    elevationError: 'Enter an elevation between −90° and 90°.',
    dateError: 'Enter a valid UTC date and time.',
    stale:
      'The parameters changed after the last run; the results below are for the previous parameters.',
  },
  selection: {
    heading: 'Selection',
    none: 'No site selected. Choose a site from the catalog or click the globe.',
    custom: 'Point chosen by the user',
    coordinates: 'Coordinates',
    frame: 'Frame',
    mission: 'Mission',
    agency: 'Agency / operator',
    country: 'Country',
    positionKind: 'Position type',
    missionStatus: 'Mission status',
    uncertainty: 'Horizontal uncertainty',
    elevation: 'Elevation (source value)',
    verification: 'Position verification',
    verificationStatus: {
      verified_at_original: 'Verified at the original source',
      incomplete: 'Verification incomplete',
      conflict_open: 'Open conflict between sources',
    } as Record<string, string>,
    sources: 'Position sources',
    accessed: (date: string) => `accessed ${date}`,
    localTerrain: 'Local terrain',
    localTerrainStatus: {
      none: 'Not checked.',
      loading: 'Checking DEM coverage…',
      error: 'DEM coverage could not be checked.',
      ready: 'Terrain available — see the “Local terrain” tab.',
      no_dem_coverage: 'No DEM coverage in the project’s DEM inventory.',
      coverage_unverified:
        'Coverage unverified: no inventoried DEM product covers this point; other products were not checked.',
      terrain_not_downloaded:
        'Terrain not downloaded: a DEM product covers this point, but its data are not on this server.',
      frame_mismatch:
        'Frame mismatch: the DEM here is declared in another reference frame; coordinates are not converted.',
    } as Record<string, string>,
    planNote:
      'A planned target or representative point is not a landing position.',
  },
  results: {
    heading: 'Sun and Earth',
    mode: 'Idealized — local terrain not included',
    idle: 'Run a simulation to see the Sun and Earth from this site.',
    queued: 'Simulation queued…',
    running: (percent: number) => `Simulating… ${percent}%`,
    at: (time: string) => `At ${time}`,
    sun: 'Sun',
    earth: 'Earth',
    elevation: 'Elevation',
    azimuth: 'Azimuth (0° = north, clockwise)',
    distance: 'Distance',
    sunVisible: 'Above the horizon',
    sunHidden: 'Below the horizon',
    earthVisible: 'In view',
    earthHidden: 'Not in view',
    visibilityUnknown: 'Visibility unknown',
    nextAppearance: (body: string, inText: string, at: string) =>
      `${body} appears in ${inText} · ${at}`,
    nextDisappearance: (body: string, inText: string, at: string) =>
      `${body} disappears in ${inText} · ${at}`,
    noMoreEvents: (body: string) =>
      `No further ${body} event in the simulated interval.`,
    summary: 'Interval totals',
    sunTotal: 'Sun above the horizon',
    earthTotal: 'Earth in view',
    bothTotal: 'Sun and Earth together',
    events: 'Events',
    noEvents: 'No event in the interval',
    appearance: 'appears',
    disappearance: 'disappears',
    undefinedAzimuth:
      'Azimuth is undefined at the zenith or nadir; no direction is drawn.',
    directions:
      'Arrows on the globe show the Sun (yellow) and Earth (blue) directions at the selected time.',
  },
  sky: {
    heading: 'Local sky',
    description: (sun: string, earth: string) =>
      `Sky dome seen from the site, north up and east right. Sun: ${sun}. Earth: ${earth}.`,
    belowHorizon: 'below the horizon',
    north: 'N',
    east: 'E',
    south: 'S',
    west: 'W',
  },
  quality: {
    heading: 'Provenance and limits',
    approximations: 'Approximations',
    limits: 'Limits',
    issues: 'Data notes',
    kernelProfile: 'Kernel profile',
    frame: 'Frame',
    correction: 'Aberration correction',
    computedAt: 'Computed at',
    appVersion: 'Application version',
    issueMessages: {
      'quality.idealized_reference_surface':
        'Terrain elevation is not used: the observer stands on the reference sphere.',
      'quality.azimuth_undefined_zenith_nadir':
        'Azimuth is undefined at the zenith or nadir for some samples.',
    } as Record<string, string>,
  },
  time: {
    slider: 'Time within the simulated interval',
    play: 'Play',
    pause: 'Pause',
    noResult: 'The time slider becomes available after a simulation.',
    position: (index: number, total: number) => `Step ${index} of ${total}`,
    step: (seconds: number) => `step ${seconds} s`,
  },
  globe: {
    label:
      'Interactive 3D globe of the Moon. Drag to rotate, scroll to zoom, right-drag to pan, click to choose a point.',
    resetCamera: 'Reset view',
    focusSelection: 'Focus on selection',
    webglUnavailable:
      'The 3D globe needs WebGL, which is not available in this browser. You can still select sites and run simulations from the panels.',
    loading: 'Preparing the 3D globe…',
    textureMissing:
      'The globe texture could not be loaded; the Moon is drawn without imagery.',
    lod: 'Detail: global texture 2048 × 1024 px (≈5.3 km/px at the equator) — imagery only, not local terrain.',
    pickedPoint: (lat: string, lon: string) => `Point ${lat}, ${lon}`,
    legend: {
      catalog: 'Catalog positions (landed or planned)',
      demPoint: 'DEM representative points (raster centres, not landing sites)',
      custom: 'Point entered or clicked',
      selected: 'Selected',
    },
  },
  views: {
    label: 'Map view',
    globe: 'Globe',
    terrain: 'Local terrain',
    terrainUnavailable: 'Local terrain (no DEM here)',
  },
  terrain: {
    label:
      'Local 3D terrain from the DEM. Drag to rotate, scroll to zoom, right-drag to pan, click the terrain to choose a point.',
    banner:
      'Local terrain is displayed; visibility calculations do not yet include terrain.',
    noSelection: 'Select a point inside a DEM raster to see its local terrain.',
    loading: 'Loading the local terrain…',
    unavailable: {
      no_dem_coverage:
        'No DEM coverage: no product of the project’s DEM inventory covers this selection. No relief is generated.',
      coverage_unverified:
        'Coverage unverified: no inventoried DEM product covers this south polar point, and other products were not checked. No relief is generated.',
      terrain_not_downloaded:
        'Terrain not downloaded: a DEM product covers this point, but its data are not on this server. No relief is generated.',
      frame_mismatch:
        'Frame mismatch: the DEM covering this point is declared in another reference frame, and coordinates are not converted between frames.',
    } as Record<string, string>,
    adoptFrame: (frame: string) =>
      `Interpret this point in ${frame} (no conversion)`,
    adoptFrameExplanation:
      'Only for a point you entered or clicked: its numbers are kept and re-interpreted in the DEM frame, not converted.',
    catalogFrameRefusal:
      'Catalog positions keep the frame of their source and are not re-interpreted in another frame; without a justified transformation, no terrain is shown.',
    error: 'The local terrain could not be loaded.',
    camera: {
      top: 'Top view',
      oblique: 'Oblique view',
      observer: 'Observer view',
    } as Record<string, string>,
    goToSite: 'Go to site',
    details: 'Terrain details and legend',
    exaggerationControl: 'Vertical exaggeration',
    exaggeration: (factor: number) =>
      `Vertical exaggeration: ${factor}× (display only; results unchanged)`,
    product: (product: string, visualM: number, calcM: number) =>
      `DEM ${product} · mesh ${visualM} m/pixel (visual level) · calculation raster ${calcM} m/pixel`,
    frame: (frame: string) =>
      `DEM frame ${frame} (working hypothesis, not validated); no frame conversion is applied.`,
    observer: (terrainM: number, equipmentM: number) =>
      `Observer: terrain ${terrainM.toFixed(1)} m + equipment ${equipmentM} m (heights above the reference sphere).`,
    observerUnknown:
      'Terrain height at this point is unknown (raster edge or no data); the observer is not placed.',
    observerNoHeight: 'Enter a valid observer height to place the observer.',
    frameMismatch: (simulation: string, terrain: string) =>
      `Sun and Earth directions are not drawn: the simulation used ${simulation}, the terrain is in ${terrain}. Coordinates are not converted between frames; run the simulation in ${terrain}.`,
    bodies: (sun: string, earth: string) =>
      `At the selected time: Sun ${sun}, Earth ${earth} (elevations from the API result).`,
    lightingSun: (time: string) =>
      `Lighting follows the computed Sun direction at ${time}.`,
    lightingSunBelow:
      'The Sun is below the idealized horizon: no direct light.',
    lightingNeutral:
      'Neutral display lighting (no Sun direction available) — not the Sun.',
    shadows:
      'Shadows are visual only; they are not horizon or visibility calculations.',
    representativeNote:
      'DEM representative point: the centre pixel of the product’s raster, chosen by LunarHorizon — not the official centre of the region, not a landing site and not an approved landing candidate.',
    representativeFallback: (terrainId: string) =>
      `${terrainId} — DEM representative point (raster centre)`,
    legend: {
      observer: 'Observer (green)',
      sun: 'Sun direction (yellow, schematic)',
      earth: 'Earth direction (blue, schematic)',
      extent: 'Raster extent (cyan)',
      noData: (count: number) =>
        `No data (red, gaps not filled): ${count} pixel${count === 1 ? '' : 's'}`,
    },
  },
  errors: {
    title: 'Something went wrong',
    network:
      'The LunarHorizon server could not be reached. Check that the backend is running on port 8000.',
    codes: {
      VALIDATION_ERROR: 'The request is not valid.',
      TOO_MANY_SITES: 'At most four sites can be simulated together.',
      INTERVAL_TOO_LONG:
        'The interval is longer than the configured limit (366 days).',
      UNSUPPORTED_FRAME:
        'Reference frame mismatch: this position is declared in another frame, and LunarHorizon does not convert coordinates between frames. Choose the frame in which the site is declared.',
      OUT_OF_EPHEMERIS_COVERAGE:
        'The interval is outside the time span covered by the ephemerides.',
      OUT_OF_DEM_COVERAGE:
        'DEM terrain is not available for this request. Horizons from the DEM are not computed yet, and the idealized mode is never used as a silent substitute — choose “Idealized — local terrain not included” explicitly.',
      SIMULATION_NOT_FOUND:
        'The simulation is no longer available on the server. Run it again.',
      KERNEL_MISSING:
        'The SPICE kernels are not loaded on the server (run scripts/download_kernels.py).',
      TERRAIN_DATA_MISSING: 'Required data files are missing on the server.',
      PRECOMPUTED_NOT_AVAILABLE:
        'This combination has no precomputed scenario.',
      INTERNAL_ERROR: 'The server reported an internal error.',
    } as Record<string, string>,
    coverageLimits: (start: string, end: string) =>
      `Available span: ${start} – ${end}.`,
    fields: (list: string) => `Fields: ${list}.`,
    unexpected: 'Unexpected response from the server.',
  },
  credits: {
    heading: 'Credits',
    texture:
      "Globe imagery: NASA's Scientific Visualization Studio, CGI Moon Kit (visualization Ernie Wright; LRO LROC WAC and LOLA data). Aesthetic product, not scientific data.",
    ephemerides:
      'Sun and Earth positions: NASA/JPL NAIF SPICE kernels via the LunarHorizon backend.',
    design:
      'Presentation ideas adapted from “Nasa-moon” by Kazi Ahammad Ullah (MIT License).',
  },
} as const

export type Messages = typeof en
