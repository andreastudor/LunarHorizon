// Data source for the interface (docs/ARCHITECTURE.md: "sursa de date API"). The live source talks to
// the FastAPI backend through the `/api` prefix (proxied by Vite in development). Errors keep the
// stable `code` of the Problem document; the interface turns codes into English messages.

import type {
  Catalog,
  Coverage,
  Problem,
  SimulationAccepted,
  SimulationRequest,
  SimulationStatus,
  TerrainManifest,
  TerrainSample,
} from '../contracts/generated.ts'

export class ApiError extends Error {
  readonly status: number
  readonly problem: Problem | null

  constructor(status: number, problem: Problem | null, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.problem = problem
  }
}

/** The network or the server could not be reached at all. */
export class NetworkError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'NetworkError'
  }
}

export interface DataSource {
  sites(signal?: AbortSignal): Promise<Catalog>
  coverage(signal?: AbortSignal): Promise<Coverage>
  startSimulation(
    request: SimulationRequest,
    signal?: AbortSignal,
  ): Promise<SimulationAccepted>
  simulation(id: string, signal?: AbortSignal): Promise<SimulationStatus>
  /** Terrain manifest of the DEM raster containing the point (404 OUT_OF_DEM_COVERAGE otherwise). */
  terrainManifest(
    latitudeDeg: number,
    longitudeDeg: number,
    signal?: AbortSignal,
  ): Promise<TerrainManifest>
  /** Terrain height at a point, sampled from the calculation raster. */
  terrainElevation(
    terrainId: string,
    latitudeDeg: number,
    longitudeDeg: number,
    signal?: AbortSignal,
  ): Promise<TerrainSample>
  /** Heights of a visual level of detail (row 0 = north, NaN = NoData). */
  terrainLod(
    terrainId: string,
    level: number,
    signal?: AbortSignal,
  ): Promise<TerrainLodData>
  /** URL of the globe texture served by the backend (E05 product, NASA SVS). */
  readonly globeTextureUrl: string
}

export interface TerrainLodData {
  width: number
  height: number
  heights: Float32Array
}

const isProblem = (value: unknown): value is Problem =>
  typeof value === 'object' &&
  value !== null &&
  'code' in value &&
  'status' in value &&
  'detail' in value

async function requestJson<T>(url: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(url, init)
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError')
      throw error
    throw new NetworkError(String(error))
  }
  let body: unknown = null
  try {
    body = await response.json()
  } catch {
    body = null
  }
  if (!response.ok) {
    throw new ApiError(
      response.status,
      isProblem(body) ? body : null,
      `HTTP ${response.status} for ${url}`,
    )
  }
  if (body === null) {
    throw new ApiError(response.status, null, `Empty response for ${url}`)
  }
  return body as T
}

async function requestHeights(
  url: string,
  signal?: AbortSignal,
): Promise<TerrainLodData> {
  let response: Response
  try {
    response = await fetch(url, { signal })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError')
      throw error
    throw new NetworkError(String(error))
  }
  if (!response.ok) {
    let body: unknown = null
    try {
      body = await response.json()
    } catch {
      body = null
    }
    throw new ApiError(
      response.status,
      isProblem(body) ? body : null,
      `HTTP ${response.status} for ${url}`,
    )
  }
  const width = Number(response.headers.get('X-Width'))
  const height = Number(response.headers.get('X-Height'))
  const buffer = await response.arrayBuffer()
  // The server sends float32 little-endian; DataView keeps this independent of the platform.
  const view = new DataView(buffer)
  const heights = new Float32Array(buffer.byteLength / 4)
  for (let i = 0; i < heights.length; i++)
    heights[i] = view.getFloat32(i * 4, true)
  if (!(width > 0 && height > 0) || heights.length !== width * height) {
    throw new ApiError(
      response.status,
      null,
      `Inconsistent heights from ${url}`,
    )
  }
  return { width, height, heights }
}

export function createApiDataSource(baseUrl = '/api'): DataSource {
  return {
    globeTextureUrl: `${baseUrl}/assets/globe.jpg`,
    sites: (signal) => requestJson<Catalog>(`${baseUrl}/sites`, { signal }),
    coverage: (signal) =>
      requestJson<Coverage>(`${baseUrl}/coverage`, { signal }),
    startSimulation: (request, signal) =>
      requestJson<SimulationAccepted>(`${baseUrl}/simulations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
        signal,
      }),
    terrainManifest: (latitudeDeg, longitudeDeg, signal) =>
      requestJson<TerrainManifest>(
        `${baseUrl}/terrain/manifest?latitude_deg=${latitudeDeg}&longitude_deg=${longitudeDeg}`,
        { signal },
      ),
    terrainElevation: (terrainId, latitudeDeg, longitudeDeg, signal) =>
      requestJson<TerrainSample>(
        `${baseUrl}/terrain/elevation?terrain_id=${encodeURIComponent(terrainId)}` +
          `&latitude_deg=${latitudeDeg}&longitude_deg=${longitudeDeg}`,
        { signal },
      ),
    terrainLod: (terrainId, level, signal) =>
      requestHeights(
        `${baseUrl}/terrain/${encodeURIComponent(terrainId)}/lods/${level}`,
        signal,
      ),
    simulation: (id, signal) =>
      requestJson<SimulationStatus>(
        `${baseUrl}/simulations/${encodeURIComponent(id)}`,
        { signal },
      ),
  }
}
