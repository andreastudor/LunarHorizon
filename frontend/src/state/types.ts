// Shared interface state (docs/ARCHITECTURE.md: "starea comună"). The camera is not part of it.

import type { ErrorDescription } from '../api/errors.ts'
import type { FrameId } from '../geo/conventions.ts'

export type Loadable<T> =
  | { status: 'loading' }
  | { status: 'ready'; data: T }
  | { status: 'error'; error: ErrorDescription }

export type Selection =
  | { kind: 'catalog'; siteId: string }
  | {
      kind: 'custom'
      label: string
      latitudeDeg: number
      longitudeDeg: number
    }
  | null

export type TerrainModeChoice = 'idealized_local_plane' | 'dem'

/** Form values as typed by the user (strings until validated). */
export interface SimulationParams {
  startDate: string
  startTime: string
  durationDays: number
  observerHeightM: string
  earthMinElevationDeg: string
  frameId: FrameId
  terrainMode: TerrainModeChoice
}
