// Contract between the React interface and the imperative 3D globe controller
// (docs/ARCHITECTURE.md: Three.js in an imperative scene controller wrapped by a thin component).
// Only types live here, so the interface and its tests never import Three.js.

import type { TerrainMesh } from '../geo/terrain.ts'
import type { Vec3 } from '../geo/vec3.ts'

export interface GlobeMarker {
  id: string
  latitudeDeg: number
  longitudeDeg: number
  kind: 'catalog' | 'custom'
  selected: boolean
}

export interface GlobeCoverage {
  id: string
  /** GeoJSON ring of [longitude, latitude] positions. */
  ring: readonly (readonly number[])[]
}

export interface GlobeDirections {
  latitudeDeg: number
  longitudeDeg: number
  /** Unit vectors in the global scene; null when the azimuth is undefined. */
  sun: Vec3 | null
  earth: Vec3 | null
}

export interface GlobeState {
  markers: GlobeMarker[]
  coverage: GlobeCoverage[]
  directions: GlobeDirections | null
}

export interface GlobeOptions {
  textureUrl: string
  onPick: (latitudeDeg: number, longitudeDeg: number) => void
  onTextureError: () => void
}

export interface GlobeHandle {
  update(state: GlobeState): void
  resetCamera(): void
  focus(latitudeDeg: number, longitudeDeg: number): void
  dispose(): void
}

export type GlobeFactory = (
  container: HTMLElement,
  options: GlobeOptions,
) => GlobeHandle

export class WebGLUnavailableError extends Error {
  constructor() {
    super('WebGL is not available')
    this.name = 'WebGLUnavailableError'
  }
}

// --- Local terrain scene (E08) ------------------------------------------------------------------

export type TerrainCameraMode = 'top' | 'oblique' | 'observer'

export interface TerrainSceneState {
  /** Rebuilt on the GPU only when this object changes (not when time or exaggeration change). */
  mesh: TerrainMesh | null
  /** True scene metres (not exaggerated). */
  observer: { ground: Vec3; eye: Vec3 } | null
  /** Unit vectors in local scene axes; null when unknown, undefined azimuth or frame mismatch. */
  sun: Vec3 | null
  earth: Vec3 | null
  sunElevationDeg: number | null
  exaggeration: number
}

export interface TerrainOptions {
  /** A click (not a drag) on the terrain, in true scene metres. */
  onPick: (point: Vec3) => void
}

export interface TerrainHandle {
  update(state: TerrainSceneState): void
  setCamera(mode: TerrainCameraMode): void
  goToSite(): void
  dispose(): void
}

export type TerrainFactory = (
  container: HTMLElement,
  options: TerrainOptions,
) => TerrainHandle
