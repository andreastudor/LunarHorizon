// E07 interface tests with a synthetic data source and a fake globe (no WebGL in jsdom).
// All data here is synthetic and exists only in tests.

import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App.tsx'
import { ApiError, type DataSource } from './api/dataSource.ts'
import type {
  Catalog,
  Coverage,
  SimulationRequest,
  SimulationResult,
  SimulationStatus,
  Site,
  TerrainManifest,
  TerrainSample,
} from './contracts/generated.ts'
import {
  WebGLUnavailableError,
  type GlobeFactory,
  type GlobeOptions,
  type GlobeState,
  type TerrainFactory,
  type TerrainSceneState,
} from './globe/types.ts'
import { en } from './i18n/en.ts'

afterEach(cleanup)

const NOW = new Date('2026-11-14T10:00:00Z')

function syntheticSite(
  id: string,
  name: string,
  lat: number,
  lon: number,
): Site {
  return {
    id,
    name,
    mission: 'synthetic_mission',
    agency: 'synthetic_agency',
    operator: null,
    country: null,
    status: 'landed',
    mission_status: 'landed',
    geometry_type: 'point',
    position_kind: 'actual',
    latitude_deg: lat,
    longitude_deg: lon,
    frame_id: 'MOON_ME_DE440_ME421',
    original_coordinates: null,
    horizontal_uncertainty_m: 3,
    elevation_m: null,
    elevation_reference: null,
    related_site_id: null,
    planned_target_note: null,
    source_url: 'https://example.invalid/synthetic',
    accessed_at: '2026-11-14',
    position_sources: [
      {
        used_for: 'position',
        institution: 'synthetic_institution',
        title: 'synthetic_source_title',
        url: 'https://example.invalid/synthetic',
        identifier: null,
        version_or_update: null,
        published: null,
        accessed_at: '2026-11-14',
        locator: 'synthetic',
        access: 'opened_original',
        coordinates: null,
        declared_frame: null,
        frame_realization_stated: false,
        published_uncertainty_m: null,
        uncertainty_definition: null,
        quote: null,
        file_sha256: null,
      },
    ],
    position_verification: 'verified_at_original',
    adoption_note: 'synthetic',
    description_ro: null,
    description_en: null,
    terrain_available: false,
  }
}

const CATALOG: Catalog = {
  schema_version: '0.5.0',
  catalog_version: 'synthetic',
  sites: [
    syntheticSite('synthetic_a', 'synthetic_site_alpha', 0.5, 23.5),
    syntheticSite('synthetic_b', 'synthetic_site_beta', -69.4, 32.3),
  ],
  demo_site_selection: {
    decision_id: 'D-07',
    status: 'unconfirmed',
    confirmed_site_ids: [],
    candidates: [],
    excluded: [],
    criteria: [],
  },
} as unknown as Catalog

const COVERAGE: Coverage = {
  schema_version: '0.5.0',
  temporal: {
    start_utc: '1849-12-25T23:59:18.816Z',
    end_utc: '2150-01-21T23:58:50.816Z',
    kernel_profile: 'de440_me421',
  },
  terrain: [
    {
      product_id: 'synthetic_dem',
      role: 'near',
      resolution_m: 5,
      footprint: {
        type: 'Polygon',
        coordinates: [
          [
            [31, -85.5],
            [32, -85.5],
            [32, -85.2],
            [31, -85.5],
          ],
        ],
      },
      min_latitude_deg: -85.5,
      max_latitude_deg: -85.2,
    },
  ],
}

function syntheticResult(
  request: SimulationRequest,
  siteRef: string,
  sunAzimuth: (number | null)[] = [90, 100, 110],
): SimulationResult {
  const times = [
    '2026-11-14T00:00:00Z',
    '2026-11-14T01:00:00Z',
    '2026-11-14T02:00:00Z',
  ]
  const body = (azimuth: (number | null)[], elevation: number[]) => ({
    azimuth_deg: azimuth,
    elevation_deg: elevation,
    distance_km: [1.5e8, 1.5e8, 1.5e8],
    angular_radius_deg: [0.27, 0.27, 0.27],
    horizon_elevation_deg: [0, 0, 0],
    visible: elevation.map((e) => e >= 0),
  })
  return {
    schema_version: '0.5.0',
    request: Object.assign(
      {
        frame_id: 'MOON_ME_DE440_ME421',
        start_utc: '2026-11-14T00:00:00Z',
        end_utc: '2026-11-14T02:00:00Z',
        observer_height_m: 2,
        solar_criterion: 'disc_center',
        earth_criterion: { kind: 'center_above_horizon', min_elevation_deg: 0 },
        terrain_mode: 'idealized_local_plane',
        panel: null,
      },
      request,
      { series_step_s: 3600 },
    ) as SimulationRequest,
    sites: [
      {
        site_ref: siteRef,
        label: 'synthetic',
        kind: 'catalog',
        catalog_id: siteRef,
        latitude_deg: 0.5,
        longitude_deg: 23.5,
        frame_id: 'MOON_ME_DE440_ME421',
        terrain_elevation_m: null,
        observer_height_m: 2,
        on_reference_surface: true,
        azimuth_convention: 'standard',
        coordinates_rounded: false,
      },
    ],
    series: [
      {
        site_ref: siteRef,
        step_s: 3600,
        time_utc: times,
        sun: body(sunAzimuth, [-1.25, 10.5, 20.75]),
        earth: body([200, 201, 202], [45, 45.5, 46]),
      },
    ],
    events: [
      {
        site_ref: siteRef,
        sun: {
          status: 'found',
          reason: null,
          events: [
            {
              body: 'sun',
              type: 'appearance',
              cause: 'idealized_horizon',
              time_utc: '2026-11-14T00:07:00Z',
              azimuth_deg: 91,
              elevation_deg: 0,
              obstacle_distance_m: null,
              refinement_tolerance_s: 0.001,
            },
          ],
        },
        earth: { status: 'none_in_interval', reason: null, events: [] },
      },
    ],
    summary: [
      {
        site_ref: siteRef,
        sun_visible_duration_s: 6780,
        sun_visible_fraction: 6780 / 7200,
        earth_visible_duration_s: 7200,
        both_visible_duration_s: 6780,
        sun_intervals: [],
        earth_windows: [],
      },
    ],
    horizon: [],
    terrain: [],
    provenance: {
      app_version: '0.1.0',
      computed_at_utc: '2026-11-14T10:00:00Z',
      source_mode: 'live',
      kernel_profile: { profile_id: 'de440_me421', files: [] },
      frame_id: 'MOON_ME_DE440_ME421',
      aberration_correction: 'LT+S',
      body_radii_km: {},
      dem_products: [],
      horizon_parameters: {},
      event_parameters: {},
      criteria: {},
    },
    quality: {
      issues: [],
      not_computed: [],
      approximations: ['synthetic approximation'],
      limits: ['synthetic limit'],
    },
  }
}

interface Deferred<T> {
  promise: Promise<T>
  resolve: (value: T) => void
}

function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((r) => {
    resolve = r
  })
  return { promise, resolve }
}

// Synthetic terrain: a 4 × 4 grid over the representative point's raster (tests only).
const TERRAIN_MANIFEST = {
  schema_version: '0.5.0',
  terrain_id: 'synthetic_terrain',
  source: {
    product_id: 'synthetic_dem',
    url: 'https://example.invalid/synthetic',
    sha256: null,
    citation: 'synthetic',
  },
  frame_id: 'MOON_ME_DE421',
  crs: { proj4: null, wkt: null },
  reference_radius_m: 1737400,
  vertical: {
    units: 'm',
    reference: 'synthetic',
    exaggeration_default_factor: 1,
  },
  calc_resolution_m: 5,
  local_origin: {
    latitude_deg: -85.4266,
    longitude_deg: 31.7442,
    elevation_m: 6398.92,
  },
  bounds: { x_min_m: 65000, x_max_m: 81000, y_min_m: 110000, y_max_m: 126000 },
  nodata: { present: false, encoding: 'NaN', area_fraction: 0 },
  interpolated_pixels: { flagged: false, note: 'synthetic' },
  lods: [
    {
      level: 0,
      visual_resolution_m: 4000,
      width_px: 4,
      height_px: 4,
      heights_path: 'synthetic.tif',
      encoding: 'synthetic',
      sha256: '0'.repeat(64),
    },
  ],
} as unknown as TerrainManifest

const outsideDem = () =>
  new ApiError(
    404,
    {
      type: 'urn:lunarhorizon:problem:out-of-dem-coverage',
      title: 'x',
      status: 404,
      detail: 'synthetic',
      code: 'OUT_OF_DEM_COVERAGE',
    },
    'outside',
  )

function terrainMethods(calls: { terrain: number }) {
  return {
    terrainManifest: async (latitudeDeg: number): Promise<TerrainManifest> => {
      calls.terrain += 1
      if (latitudeDeg > -80) throw outsideDem()
      return TERRAIN_MANIFEST
    },
    terrainElevation: async (
      _id: string,
      latitudeDeg: number,
      longitudeDeg: number,
    ): Promise<TerrainSample> => {
      calls.terrain += 1
      return {
        schema_version: '0.5.0',
        terrain_id: 'synthetic_terrain',
        product_id: 'synthetic_dem',
        frame_id: 'MOON_ME_DE421',
        latitude_deg: latitudeDeg,
        longitude_deg: longitudeDeg,
        x_m: 73000,
        y_m: 118000,
        elevation_m: 6398.92,
        reason: null,
        calc_resolution_m: 5,
        method: 'bilinear',
      }
    },
    terrainLod: async () => {
      calls.terrain += 1
      return {
        width: 4,
        height: 4,
        heights: Float32Array.from({ length: 16 }, (_, i) => 6390 + i),
      }
    },
  }
}

function fakeTerrain() {
  const states: TerrainSceneState[] = []
  const cameras: string[] = []
  const factory: TerrainFactory = () => ({
    update: (state) => states.push(state),
    setCamera: (mode) => cameras.push(mode),
    goToSite: () => cameras.push('site'),
    dispose: vi.fn(),
  })
  return { factory, states, cameras }
}

function fakeSource(overrides: Partial<DataSource> = {}) {
  const calls = { start: [] as SimulationRequest[], status: 0, terrain: 0 }
  const source: DataSource = {
    globeTextureUrl: '/synthetic/globe.jpg',
    ...terrainMethods(calls),
    sites: async () => CATALOG,
    coverage: async () => COVERAGE,
    startSimulation: async (request) => {
      calls.start.push(request)
      return { id: 'sim-synthetic', status: 'queued', cache_hit: false }
    },
    simulation: async (): Promise<SimulationStatus> => {
      calls.status += 1
      const request = calls.start[calls.start.length - 1]
      const siteRef =
        'site_id' in request.sites[0] ? request.sites[0].site_id : 'custom-1'
      return {
        id: 'sim-synthetic',
        status: 'done',
        progress: null,
        error: null,
        result: syntheticResult(request, siteRef),
      }
    },
    ...overrides,
  }
  return { source, calls }
}

function fakeGlobe() {
  const states: GlobeState[] = []
  let options: GlobeOptions | null = null
  const focus = vi.fn()
  const factory: GlobeFactory = (_container, opts) => {
    options = opts
    return {
      update: (state) => states.push(state),
      resetCamera: vi.fn(),
      focus,
      dispose: vi.fn(),
    }
  }
  return {
    factory,
    states,
    focus,
    pick: (lat: number, lon: number) => options?.onPick(lat, lon),
  }
}

async function renderApp(source: DataSource, globe = fakeGlobe()) {
  render(
    <App
      dataSource={source}
      globeFactory={globe.factory}
      now={NOW}
      pollMs={0}
    />,
  )
  await screen.findByText('synthetic_site_alpha')
  return globe
}

describe('E07 main screen', () => {
  it('shows the four zones, the catalog and the coverage, in English', async () => {
    const { source } = fakeSource()
    await renderApp(source)
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe(
      en.app.title,
    )
    for (const zone of Object.values(en.zones)) {
      expect(screen.getByLabelText(zone)).toBeDefined()
    }
    expect(await screen.findByText(/synthetic_dem/)).toBeDefined()
    expect(screen.getAllByText(en.results.mode).length).toBeGreaterThan(0)
    // The interface text is English: no Romanian diacritics anywhere.
    expect(document.body.textContent ?? '').not.toMatch(/[ăâîșțĂÂÎȘȚşţ]/)
  })

  it('selects a catalog site and shows its details and sources', async () => {
    const { source } = fakeSource()
    const globe = await renderApp(source)
    fireEvent.click(screen.getByText('synthetic_site_beta'))
    const summary = screen.getByLabelText(en.zones.summary)
    expect(within(summary).getByText('synthetic_site_beta')).toBeDefined()
    expect(within(summary).getByText(/69\.4000° S, 32\.3000° E/)).toBeDefined()
    expect(within(summary).getByText('synthetic_source_title')).toBeDefined()
    await waitFor(() => expect(globe.focus).toHaveBeenCalledWith(-69.4, 32.3))
    const marker = globe.states
      .at(-1)
      ?.markers.find((m) => m.id === 'synthetic_b')
    expect(marker?.selected).toBe(true)
  })

  it('turns a click on the globe into an east-positive point selection', async () => {
    const { source } = fakeSource()
    const globe = await renderApp(source)
    act(() => globe.pick(-85.4266, -148.25))
    const summary = screen.getByLabelText(en.zones.summary)
    expect(within(summary).getByText(/85\.4266° S, 148\.2500° W/)).toBeDefined()
    expect(globe.states.at(-1)?.markers.some((m) => m.kind === 'custom')).toBe(
      true,
    )
  })

  it('validates manual coordinates before selecting', async () => {
    const { source } = fakeSource()
    await renderApp(source)
    fireEvent.change(screen.getByLabelText(en.point.latitude), {
      target: { value: '95' },
    })
    fireEvent.change(screen.getByLabelText(en.point.longitude), {
      target: { value: '10' },
    })
    fireEvent.click(screen.getByText(en.point.use))
    expect(screen.getByText(en.point.latitudeError)).toBeDefined()
    fireEvent.change(screen.getByLabelText(en.point.latitude), {
      target: { value: '-10' },
    })
    fireEvent.change(screen.getByLabelText(en.point.longitude), {
      target: { value: '350' },
    })
    fireEvent.click(screen.getByText(en.point.use))
    const summary = screen.getByLabelText(en.zones.summary)
    expect(within(summary).getByText(/10\.0000° S, 10\.0000° W/)).toBeDefined()
  })

  it('runs a simulation, shows the API values and moves time without new requests', async () => {
    const { source, calls } = fakeSource()
    const globe = await renderApp(source)
    fireEvent.click(screen.getByText('synthetic_site_alpha'))
    fireEvent.click(screen.getByText(en.params.run))
    await screen.findByText(en.results.at('2026-11-14 00:00:00 UTC'))
    expect(calls.start).toHaveLength(1)
    expect(calls.start[0]).toMatchObject({
      sites: [{ site_id: 'synthetic_a' }],
      frame_id: 'MOON_ME_DE440_ME421',
      start_utc: '2026-11-14T00:00:00Z',
      end_utc: '2026-12-14T00:00:00Z',
      terrain_mode: 'idealized_local_plane',
    })
    const sunCard = screen.getByRole('article', { name: en.results.sun })
    expect(within(sunCard).getByText('-1.25°')).toBeDefined()
    expect(within(sunCard).getByText(en.results.sunHidden)).toBeDefined()
    const statusCalls = calls.status
    fireEvent.change(screen.getByLabelText(en.time.slider), {
      target: { value: '2' },
    })
    expect(
      screen.getByText(en.results.at('2026-11-14 02:00:00 UTC')),
    ).toBeDefined()
    expect(within(sunCard).getByText('20.75°')).toBeDefined()
    expect(calls.start).toHaveLength(1)
    expect(calls.status).toBe(statusCalls)
    const directions = globe.states.at(-1)?.directions
    expect(directions?.sun).not.toBeNull()
    expect(directions?.earth).not.toBeNull()
  })

  it('ignores a result that arrives after the selection changed', async () => {
    const pending = deferred<SimulationStatus>()
    const { source } = fakeSource({ simulation: () => pending.promise })
    await renderApp(source)
    fireEvent.click(screen.getByText('synthetic_site_alpha'))
    fireEvent.click(screen.getByText(en.params.run))
    await screen.findByText(en.results.queued)
    fireEvent.click(screen.getByText('synthetic_site_beta'))
    const request = {
      sites: [{ site_id: 'synthetic_a' }],
    } as unknown as SimulationRequest
    await act(async () => {
      pending.resolve({
        id: 'sim-synthetic',
        status: 'done',
        progress: null,
        error: null,
        result: syntheticResult(request, 'synthetic_a'),
      })
      await pending.promise
    })
    expect(screen.queryByText(/At 2026-11-14/)).toBeNull()
    expect(screen.getByText(en.results.idle)).toBeDefined()
  })

  it('explains a refused DEM request in English without falling back', async () => {
    const sent: SimulationRequest[] = []
    const { source, calls } = fakeSource({
      startSimulation: async (request) => {
        sent.push(request)
        throw new ApiError(
          422,
          {
            type: 'urn:lunarhorizon:problem:out-of-dem-coverage',
            title: 'x',
            status: 422,
            detail: 'detaliu în română',
            code: 'OUT_OF_DEM_COVERAGE',
          },
          'refused',
        )
      },
    })
    await renderApp(source)
    fireEvent.click(screen.getByText('synthetic_site_alpha'))
    fireEvent.change(screen.getByLabelText(en.params.terrainMode), {
      target: { value: 'dem' },
    })
    fireEvent.click(screen.getByText(en.params.run))
    expect(
      await screen.findByText(en.errors.codes.OUT_OF_DEM_COVERAGE, {
        exact: false,
      }),
    ).toBeDefined()
    expect(screen.queryByText(/detaliu/)).toBeNull()
    expect(sent.map((r) => r.terrain_mode)).toEqual(['dem'])
    // No polling and no idealized request was made in its place.
    expect(calls.status).toBe(0)
    expect(screen.queryByText(/At 2026-11-14/)).toBeNull()
  })

  it('shows an undefined azimuth as “Undefined” and draws no direction', async () => {
    const { source } = fakeSource({
      simulation: async (): Promise<SimulationStatus> => ({
        id: 'sim-synthetic',
        status: 'done',
        progress: null,
        error: null,
        result: syntheticResult(
          {
            sites: [{ site_id: 'synthetic_a' }],
          } as unknown as SimulationRequest,
          'synthetic_a',
          [null, null, null],
        ),
      }),
    })
    const globe = await renderApp(source)
    fireEvent.click(screen.getByText('synthetic_site_alpha'))
    fireEvent.click(screen.getByText(en.params.run))
    const sunCard = await screen.findByRole('article', { name: en.results.sun })
    expect(within(sunCard).getByText(en.common.undefined)).toBeDefined()
    expect(screen.getByText(en.results.undefinedAzimuth)).toBeDefined()
    expect(globe.states.at(-1)?.directions?.sun).toBeNull()
  })

  it('reports an unavailable WebGL without blocking the panels', async () => {
    const { source } = fakeSource()
    const globe = fakeGlobe()
    globe.factory = () => {
      throw new WebGLUnavailableError()
    }
    render(<App dataSource={source} globeFactory={globe.factory} now={NOW} />)
    expect(await screen.findByText(en.globe.webglUnavailable)).toBeDefined()
    expect(await screen.findByText('synthetic_site_alpha')).toBeDefined()
  })

  it('shows a catalog loading error and retries', async () => {
    let attempts = 0
    const { source } = fakeSource({
      sites: async () => {
        attempts += 1
        if (attempts === 1) throw new TypeError('network down')
        return CATALOG
      },
    })
    render(
      <App dataSource={source} globeFactory={fakeGlobe().factory} now={NOW} />,
    )
    expect(await screen.findByText(en.catalog.error)).toBeDefined()
    fireEvent.click(screen.getByText(en.common.retry))
    expect(await screen.findByText('synthetic_site_alpha')).toBeDefined()
  })
})

describe('E08 local terrain', () => {
  async function openRepresentative(
    source: DataSource,
    terrain = fakeTerrain(),
  ) {
    render(
      <App
        dataSource={source}
        globeFactory={fakeGlobe().factory}
        terrainFactory={terrain.factory}
        now={NOW}
        pollMs={0}
      />,
    )
    await screen.findByText('synthetic_site_alpha')
    fireEvent.click(await screen.findByText(en.coverage.useRepresentative))
    await screen.findByText(en.terrain.representativeNote)
    return terrain
  }

  it('loads the real-terrain view for the representative point, in the DEM frame', async () => {
    const { source } = fakeSource()
    const terrain = await openRepresentative(source)
    expect(screen.getByText(en.terrain.banner)).toBeDefined()
    expect(screen.getByText(en.terrain.exaggeration(1))).toBeDefined()
    const state = terrain.states.at(-1)!
    expect(state.mesh?.vertexCount).toBe(16)
    expect(state.mesh?.indices.length).toBe(9 * 6)
    expect(state.observer?.eye[1]).toBeCloseTo(
      (state.observer?.ground[1] ?? 0) + 2,
      6,
    )
    // No result yet: no directions are drawn.
    expect(state.sun).toBeNull()
    expect(
      (screen.getByLabelText(en.params.frame) as HTMLSelectElement).value,
    ).toBe('MOON_ME_DE421')
    expect(
      screen.getByText(en.coverage.frameAdopted('MOON_ME_DE421')),
    ).toBeDefined()
  })

  it('changes the exaggeration without rebuilding the mesh or calling the API', async () => {
    const { source, calls } = fakeSource()
    const terrain = await openRepresentative(source)
    const mesh = terrain.states.at(-1)?.mesh
    const before = calls.terrain
    fireEvent.change(screen.getByLabelText(en.terrain.exaggerationControl), {
      target: { value: '3' },
    })
    expect(screen.getByText(en.terrain.exaggeration(3))).toBeDefined()
    const state = terrain.states.at(-1)!
    expect(state.exaggeration).toBe(3)
    expect(state.mesh).toBe(mesh)
    expect(calls.terrain).toBe(before)
  })

  it('draws the Sun and Earth from the result only when the frames match, without rebuilding', async () => {
    const { source, calls } = fakeSource()
    const terrain = await openRepresentative(source)
    fireEvent.click(screen.getByText(en.params.run))
    await screen.findByText(/At the selected time/)
    expect(calls.start[0].frame_id).toBe('MOON_ME_DE421')
    const mesh = terrain.states.at(-1)?.mesh
    expect(terrain.states.at(-1)?.sun).not.toBeNull()
    fireEvent.change(screen.getByLabelText(en.time.slider), {
      target: { value: '2' },
    })
    const state = terrain.states.at(-1)!
    expect(state.mesh).toBe(mesh)
    expect(state.sunElevationDeg).toBe(20.75)
    // Changing the frame afterwards makes the shown result incompatible: no arrows.
    fireEvent.change(screen.getByLabelText(en.params.frame), {
      target: { value: 'MOON_ME_DE440_ME421' },
    })
    fireEvent.click(screen.getByText(en.params.run))
    await screen.findByText(/Sun and Earth directions are not drawn/)
    expect(terrain.states.at(-1)?.sun).toBeNull()
  })

  it('reports a selection without DEM and generates no relief', async () => {
    const { source } = fakeSource()
    const terrain = fakeTerrain()
    render(
      <App
        dataSource={source}
        globeFactory={fakeGlobe().factory}
        terrainFactory={terrain.factory}
        now={NOW}
      />,
    )
    fireEvent.click(await screen.findByText('synthetic_site_alpha'))
    fireEvent.click(screen.getByRole('tab', { name: /Local terrain/ }))
    expect(await screen.findByText(en.terrain.unavailable)).toBeDefined()
    expect(terrain.states.every((state) => state.mesh === null)).toBe(true)
  })

  it('ignores a terrain response that arrives after the selection changed', async () => {
    let release!: (value: TerrainManifest) => void
    const pending = new Promise<TerrainManifest>((resolve) => {
      release = resolve
    })
    const calls = { terrain: 0 }
    const methods = terrainMethods(calls)
    const { source } = fakeSource({
      terrainManifest: (latitudeDeg) =>
        latitudeDeg < -80 ? pending : methods.terrainManifest(latitudeDeg),
    })
    const terrain = fakeTerrain()
    render(
      <App
        dataSource={source}
        globeFactory={fakeGlobe().factory}
        terrainFactory={terrain.factory}
        now={NOW}
      />,
    )
    await screen.findByText('synthetic_site_alpha')
    fireEvent.change(screen.getByLabelText(en.point.latitude), {
      target: { value: '-85.4' },
    })
    fireEvent.change(screen.getByLabelText(en.point.longitude), {
      target: { value: '31.7' },
    })
    fireEvent.click(screen.getByText(en.point.use))
    fireEvent.click(screen.getByRole('tab', { name: /Local terrain/ }))
    await screen.findByText(en.terrain.loading)
    fireEvent.click(screen.getByText('synthetic_site_alpha'))
    await screen.findByText(en.terrain.unavailable)
    await act(async () => {
      release(TERRAIN_MANIFEST)
      await pending
    })
    expect(screen.getByText(en.terrain.unavailable)).toBeDefined()
    expect(terrain.states.every((state) => state.mesh === null)).toBe(true)
  })

  it('shows a loading error with Retry', async () => {
    let attempts = 0
    const calls = { terrain: 0 }
    const methods = terrainMethods(calls)
    const { source } = fakeSource({
      terrainLod: async () => {
        attempts += 1
        if (attempts === 1) throw new ApiError(503, null, 'synthetic')
        return methods.terrainLod()
      },
    })
    const terrain = fakeTerrain()
    render(
      <App
        dataSource={source}
        globeFactory={fakeGlobe().factory}
        terrainFactory={terrain.factory}
        now={NOW}
      />,
    )
    await screen.findByText('synthetic_site_alpha')
    fireEvent.click(await screen.findByText(en.coverage.useRepresentative))
    expect(
      await screen.findByText(en.terrain.error, { exact: false }),
    ).toBeDefined()
    fireEvent.click(screen.getByText(en.common.retry))
    await screen.findByText(en.terrain.representativeNote)
    expect(terrain.states.at(-1)?.mesh?.vertexCount).toBe(16)
  })
})
