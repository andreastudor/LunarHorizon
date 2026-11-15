// Pure geometry of the local terrain scene (E08), without Three.js, so everything is testable.
//
// Local scene (docs/SPEC_FIZICA.md §10.1, scene.ts): metres, origin on the terrain at the manifest's
// local origin, east on +x, up (zenith) on +y, north on −z. Every vertex is the exact position of a
// visual-raster pixel centre: projected (x, y) → latitude/longitude through the south polar
// stereographic projection of the manifest, height above the reference sphere from the raster, then
// lunar ME → local ENU → scene. The mesh is therefore in true metres (curvature included).
//
// Vertical exaggeration is applied only by `visualY`/`visualPoint`, never to the mesh data, the
// observer sample or the directions: it changes the picture, not the results (T-09).

import type { TerrainManifest } from '../contracts/generated.ts'
import { enuFromAzEl, enuToMe, meToEnu } from './coords.ts'
import { SouthPolarStereographic } from './projection.ts'
import { LocalSceneFrame, enuToLocalScene } from './scene.ts'
import type { Vec3 } from './vec3.ts'

/** Heights of one visual level of detail: row 0 is the northern edge, column 0 the western edge. */
export interface HeightGrid {
  width: number
  height: number
  /** Metres above the reference sphere; NaN = NoData. */
  heights: Float32Array
  resolutionM: number
  xMinM: number
  yMaxM: number
}

export interface TerrainMesh {
  vertexCount: number
  /** Scene positions in metres (not exaggerated); NaN for NoData vertices. */
  positions: Float32Array
  /** Two triangles per cell whose four corners are valid; NoData cells get none. */
  indices: Uint32Array
  validVertices: number
  noDataVertices: number
  /** Flat squares marking NoData pixels, drawn at `noDataLevelM` (visual marker, not a height). */
  noDataPositions: Float32Array
  noDataLevelM: number
  /** Raster border at the terrain height (minimum height where NoData), closed loop. */
  outline: Float32Array
  minHeightM: number
  maxHeightM: number
  /** Scene extent of the raster (metres). */
  extentM: number
}

export function terrainFrame(manifest: TerrainManifest): LocalSceneFrame {
  return new LocalSceneFrame(
    {
      latitudeDeg: manifest.local_origin.latitude_deg,
      longitudeDeg: manifest.local_origin.longitude_deg,
      heightM: manifest.local_origin.elevation_m,
    },
    manifest.reference_radius_m,
  )
}

export function projectionOf(
  manifest: TerrainManifest,
): SouthPolarStereographic {
  return new SouthPolarStereographic({
    radiusM: manifest.reference_radius_m,
    centralMeridianDeg: 0,
    scaleFactor: 1,
    status: 'provisional',
  })
}

/** Projected coordinates of a pixel centre. */
export function pixelCenter(
  grid: HeightGrid,
  row: number,
  column: number,
): [number, number] {
  return [
    grid.xMinM + (column + 0.5) * grid.resolutionM,
    grid.yMaxM - (row + 0.5) * grid.resolutionM,
  ]
}

/** Scene position of a projected point at a given height above the reference sphere. */
export function projectedToScene(
  frame: LocalSceneFrame,
  projection: SouthPolarStereographic,
  xM: number,
  yM: number,
  heightM: number,
): Vec3 {
  const { latitudeDeg, longitudeDeg } = projection.inverse(xM, yM)
  return frame.geographicToScene({ latitudeDeg, longitudeDeg, heightM })
}

export function buildTerrainMesh(
  grid: HeightGrid,
  manifest: TerrainManifest,
): TerrainMesh {
  const frame = terrainFrame(manifest)
  const projection = projectionOf(manifest)
  const { width, height, heights } = grid
  const count = width * height
  if (heights.length !== count) {
    throw new Error(`expected ${count} heights, got ${heights.length}`)
  }
  let minHeight = Infinity
  let maxHeight = -Infinity
  let valid = 0
  for (const value of heights) {
    if (Number.isFinite(value)) {
      valid += 1
      if (value < minHeight) minHeight = value
      if (value > maxHeight) maxHeight = value
    }
  }
  if (valid === 0) {
    minHeight = manifest.local_origin.elevation_m
    maxHeight = minHeight
  }

  const positions = new Float32Array(count * 3)
  for (let row = 0; row < height; row++) {
    for (let column = 0; column < width; column++) {
      const index = row * width + column
      const value = heights[index]
      if (!Number.isFinite(value)) {
        positions.set([NaN, NaN, NaN], index * 3)
        continue
      }
      const [x, y] = pixelCenter(grid, row, column)
      positions.set(projectedToScene(frame, projection, x, y, value), index * 3)
    }
  }

  const triangles: number[] = []
  for (let row = 0; row < height - 1; row++) {
    for (let column = 0; column < width - 1; column++) {
      const nw = row * width + column
      const ne = nw + 1
      const sw = nw + width
      const se = sw + 1
      if (
        Number.isFinite(heights[nw]) &&
        Number.isFinite(heights[ne]) &&
        Number.isFinite(heights[sw]) &&
        Number.isFinite(heights[se])
      ) {
        // Counter-clockwise seen from above (+y): front faces point up.
        triangles.push(sw, se, ne, sw, ne, nw)
      }
    }
  }

  // NoData markers: the pixel footprint, flat, just below the lowest valid height.
  const noDataLevel = minHeight - 1
  const markers: number[] = []
  const half = grid.resolutionM / 2
  for (let row = 0; row < height; row++) {
    for (let column = 0; column < width; column++) {
      if (Number.isFinite(heights[row * width + column])) continue
      const [x, y] = pixelCenter(grid, row, column)
      const corners = [
        [x - half, y - half],
        [x + half, y - half],
        [x + half, y + half],
        [x - half, y + half],
      ].map(([cx, cy]) =>
        projectedToScene(frame, projection, cx, cy, noDataLevel),
      )
      for (const i of [0, 1, 2, 0, 2, 3]) markers.push(...corners[i])
    }
  }

  const border: [number, number][] = []
  for (let column = 0; column < width; column++) border.push([0, column])
  for (let row = 1; row < height; row++) border.push([row, width - 1])
  for (let column = width - 2; column >= 0; column--)
    border.push([height - 1, column])
  for (let row = height - 2; row > 0; row--) border.push([row, 0])
  const outline: number[] = []
  for (const [row, column] of border) {
    const value = heights[row * width + column]
    const [x, y] = pixelCenter(grid, row, column)
    outline.push(
      ...projectedToScene(
        frame,
        projection,
        x,
        y,
        Number.isFinite(value) ? value + 2 : noDataLevel,
      ),
    )
  }

  return {
    vertexCount: count,
    positions,
    indices: Uint32Array.from(triangles),
    validVertices: valid,
    noDataVertices: count - valid,
    noDataPositions: Float32Array.from(markers),
    noDataLevelM: noDataLevel,
    outline: Float32Array.from(outline),
    minHeightM: minHeight,
    maxHeightM: maxHeight,
    extentM: Math.max(width, height) * grid.resolutionM,
  }
}

/** Ground point and eye of the observer: terrain height (API sample) plus the equipment height. */
export function observerScene(
  manifest: TerrainManifest,
  latitudeDeg: number,
  longitudeDeg: number,
  terrainElevationM: number,
  equipmentHeightM: number,
): { ground: Vec3; eye: Vec3 } {
  const frame = terrainFrame(manifest)
  return {
    ground: frame.geographicToScene({
      latitudeDeg,
      longitudeDeg,
      heightM: terrainElevationM,
    }),
    eye: frame.geographicToScene({
      latitudeDeg,
      longitudeDeg,
      heightM: terrainElevationM + equipmentHeightM,
    }),
  }
}

/**
 * Direction towards a body seen from the observer, in local scene axes. The API azimuth/elevation
 * refer to the observer's own ENU frame; it is rotated exactly into the ENU frame of the scene
 * origin (ME → ENU), so a few kilometres of offset do not bend the arrows. Null azimuth → null.
 */
export function bodyDirectionLocal(
  manifest: TerrainManifest,
  azimuthDeg: number | null,
  elevationDeg: number,
  observerLatitudeDeg: number,
  observerLongitudeDeg: number,
): Vec3 | null {
  if (azimuthDeg === null) return null
  const me = enuToMe(
    enuFromAzEl(azimuthDeg, elevationDeg),
    observerLatitudeDeg,
    observerLongitudeDeg,
  )
  return enuToLocalScene(
    meToEnu(
      me,
      manifest.local_origin.latitude_deg,
      manifest.local_origin.longitude_deg,
    ),
  )
}

/** Visual height only: exaggeration around the scene origin height (y = 0). */
export const visualY = (y: number, exaggeration: number): number =>
  y * exaggeration

export const visualPoint = ([x, y, z]: Vec3, exaggeration: number): Vec3 => [
  x,
  visualY(y, exaggeration),
  z,
]

/** Converts a picked visual point back to true scene metres (undoes the exaggeration). */
export const truePoint = ([x, y, z]: Vec3, exaggeration: number): Vec3 => [
  x,
  y / exaggeration,
  z,
]

export const EXAGGERATION_OPTIONS = [1, 2, 3, 5, 10] as const
