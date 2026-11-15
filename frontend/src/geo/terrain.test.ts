import { describe, expect, it } from 'vitest'
import type { TerrainManifest } from '../contracts/generated.ts'
import {
  bodyDirectionLocal,
  buildTerrainMesh,
  observerScene,
  pixelCenter,
  projectionOf,
  terrainFrame,
  truePoint,
  visualPoint,
  type HeightGrid,
} from './terrain.ts'

// Synthetic manifest and grids (tests only); georeference shaped like the PGDA 104 product.
const MANIFEST = {
  schema_version: '0.8.0',
  terrain_id: 'synthetic_terrain',
  frame_id: 'MOON_ME_DE421',
  reference_radius_m: 1_737_400,
  calc_resolution_m: 5,
  local_origin: {
    latitude_deg: -85.42660397429984,
    longitude_deg: 31.74418217323797,
    elevation_m: 6398.92,
  },
  bounds: {
    x_min_m: 65000,
    x_max_m: 81000,
    y_min_m: 110000,
    y_max_m: 126000,
  },
} as unknown as TerrainManifest

function grid(
  width: number,
  height: number,
  fill: (r: number, c: number) => number,
): HeightGrid {
  const heights = new Float32Array(width * height)
  for (let r = 0; r < height; r++)
    for (let c = 0; c < width; c++) heights[r * width + c] = fill(r, c)
  return {
    width,
    height,
    heights,
    resolutionM: 16000 / width,
    xMinM: 65000,
    yMaxM: 126000,
  }
}

const vertex = (positions: Float32Array, index: number) =>
  [
    positions[index * 3],
    positions[index * 3 + 1],
    positions[index * 3 + 2],
  ] as const

describe('terrain mesh from the DEM grid', () => {
  it('places each vertex at the projected pixel centre and its height (metres)', () => {
    const g = grid(8, 8, (r, c) => 6000 + 10 * r + c)
    const mesh = buildTerrainMesh(g, MANIFEST)
    const frame = terrainFrame(MANIFEST)
    const projection = projectionOf(MANIFEST)
    for (const [row, column] of [
      [0, 0],
      [3, 5],
      [7, 7],
    ]) {
      const index = row * 8 + column
      const geo = frame.sceneToGeographic(vertex(mesh.positions, index))
      const [x, y] = pixelCenter(g, row, column)
      const expected = projection.inverse(x, y)
      // float32 positions: ≈ 1 mm, i.e. better than 1e-6° here.
      expect(geo.latitudeDeg).toBeCloseTo(expected.latitudeDeg, 6)
      expect(geo.longitudeDeg).toBeCloseTo(expected.longitudeDeg, 6)
      expect(geo.heightM).toBeCloseTo(g.heights[index], 1)
    }
    expect(mesh.minHeightM).toBe(6000)
    expect(mesh.maxHeightM).toBe(6077)
  })

  it('keeps true horizontal spacing (projection scale removed) and orientation', () => {
    const g = grid(400, 400, () => 6398.92)
    const mesh = buildTerrainMesh(g, MANIFEST)
    const a = vertex(mesh.positions, 200 * 400 + 200)
    const east = vertex(mesh.positions, 200 * 400 + 201)
    const south = vertex(mesh.positions, 201 * 400 + 200)
    const spacing = Math.hypot(east[0] - a[0], east[1] - a[1], east[2] - a[2])
    // 40 m on the projection plane; scale factor k = 2/(1 − sin φ) ≈ 1.0016 at 85.4°S on the
    // sphere, and the surface is 6398.92 m above it, so distances grow by (R + h) / R.
    const k = projectionOf(MANIFEST).scale(MANIFEST.local_origin.latitude_deg)
    const radius = MANIFEST.reference_radius_m
    expect(spacing).toBeCloseTo(((40 / k) * (radius + 6398.92)) / radius, 2)
    // A raster row further down is further south: larger scene z (north is −z).
    expect(south[2]).toBeGreaterThan(a[2])
  })

  it('excludes NoData from triangles, keeps zero as a real height, and marks the gaps', () => {
    const g = grid(5, 5, (r, c) =>
      r === 2 && c === 2 ? NaN : r === 0 ? 0 : 100,
    )
    const mesh = buildTerrainMesh(g, MANIFEST)
    // 16 cells; the 4 cells touching the NoData vertex have no triangles.
    expect(mesh.indices.length).toBe((16 - 4) * 6)
    for (const index of mesh.indices) expect(index).not.toBe(12)
    expect(Number.isNaN(mesh.positions[12 * 3])).toBe(true)
    expect(mesh.noDataVertices).toBe(1)
    expect(mesh.noDataPositions.length).toBe(6 * 3)
    // Row 0 has height 0 (a real value) and stays valid and triangulated.
    expect(mesh.validVertices).toBe(24)
    expect(mesh.minHeightM).toBe(0)
    expect([...mesh.indices].some((index) => index < 5)).toBe(true)
  })

  it('has no triangles across a single-row edge and a closed outline along the border', () => {
    expect(
      buildTerrainMesh(
        grid(4, 1, () => 1),
        MANIFEST,
      ).indices.length,
    ).toBe(0)
    const mesh = buildTerrainMesh(
      grid(4, 3, () => 1),
      MANIFEST,
    )
    expect(mesh.outline.length / 3).toBe(2 * 4 + 2 * 3 - 4)
  })

  it('faces up (+y) for flat terrain', () => {
    const mesh = buildTerrainMesh(
      grid(3, 3, () => 6398.92),
      MANIFEST,
    )
    const [a, b, c] = [mesh.indices[0], mesh.indices[1], mesh.indices[2]].map(
      (i) => vertex(mesh.positions, i),
    )
    const ab = [b[0] - a[0], b[1] - a[1], b[2] - a[2]]
    const ac = [c[0] - a[0], c[1] - a[1], c[2] - a[2]]
    expect(ab[2] * ac[0] - ab[0] * ac[2]).toBeGreaterThan(0)
  })
})

describe('observer', () => {
  it('stands at the terrain height plus the equipment height', () => {
    const { ground, eye } = observerScene(
      MANIFEST,
      MANIFEST.local_origin.latitude_deg,
      MANIFEST.local_origin.longitude_deg,
      MANIFEST.local_origin.elevation_m,
      2,
    )
    ground.forEach((value) => expect(value).toBeCloseTo(0, 6))
    expect(eye[0]).toBeCloseTo(0, 6)
    expect(eye[1]).toBeCloseTo(2, 6)
    expect(eye[2]).toBeCloseTo(0, 6)
  })
})

describe('vertical exaggeration is visual only', () => {
  it('does not change the mesh data and is undone exactly for picking', () => {
    const g = grid(6, 6, (r, c) => 6000 + r * c)
    const first = buildTerrainMesh(g, MANIFEST)
    const second = buildTerrainMesh(g, MANIFEST)
    expect(second.positions).toEqual(first.positions)
    const point = vertex(first.positions, 14)
    expect(visualPoint(point, 1)).toEqual([...point])
    expect(visualPoint(point, 5)[1]).toBeCloseTo(point[1] * 5, 6)
    truePoint(visualPoint(point, 5), 5).forEach((value, i) =>
      expect(value).toBeCloseTo(point[i], 9),
    )
  })
})

describe('body directions in the local scene axes', () => {
  const { latitude_deg: lat, longitude_deg: lon } = MANIFEST.local_origin
  const close = (a: readonly number[] | null, b: number[]) =>
    b.forEach((value, i) => expect(a?.[i]).toBeCloseTo(value, 9))

  it('maps north to −z, east to +x, south to +z and the zenith to +y at the origin', () => {
    close(bodyDirectionLocal(MANIFEST, 0, 0, lat, lon), [0, 0, -1])
    close(bodyDirectionLocal(MANIFEST, 90, 0, lat, lon), [1, 0, 0])
    close(bodyDirectionLocal(MANIFEST, 180, 0, lat, lon), [0, 0, 1])
    close(bodyDirectionLocal(MANIFEST, 270, 0, lat, lon), [-1, 0, 0])
    close(bodyDirectionLocal(MANIFEST, 123, 90, lat, lon), [0, 1, 0])
  })

  it('rotates the observer frame exactly when the observer is away from the origin', () => {
    const projection = projectionOf(MANIFEST)
    const [x, y] = projection.forward(lat, lon)
    const offset = projection.inverse(x + 5000, y)
    const direction = bodyDirectionLocal(
      MANIFEST,
      0,
      90,
      offset.latitudeDeg,
      offset.longitudeDeg,
    )!
    expect(Math.hypot(...direction)).toBeCloseTo(1, 12)
    // The local zenith 5 km away differs from the origin zenith by ≈ 5 km / R (≈ 0.16°).
    const angle = Math.acos(direction[1]) * (180 / Math.PI)
    expect(angle).toBeGreaterThan(0.1)
    expect(angle).toBeLessThan(0.25)
  })

  it('returns no direction for an undefined azimuth', () => {
    expect(bodyDirectionLocal(MANIFEST, null, 89.99, lat, lon)).toBeNull()
  })
})
