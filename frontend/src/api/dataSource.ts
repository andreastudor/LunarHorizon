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
  /** URL of the globe texture served by the backend (E05 product, NASA SVS). */
  readonly globeTextureUrl: string
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
    simulation: (id, signal) =>
      requestJson<SimulationStatus>(
        `${baseUrl}/simulations/${encodeURIComponent(id)}`,
        { signal },
      ),
  }
}
