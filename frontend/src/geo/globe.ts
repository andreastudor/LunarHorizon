// Pure geometry for the global 3D map (no Three.js here, so everything is testable).
// It uses the same global scene convention as scene.ts: kilometres, Moon centre at the origin,
// north pole on +y, the 0° meridian on +z and 90°E on +x (docs/SPEC_FIZICA.md §10.1).
// The sphere is the visual reference sphere; picking returns latitude/longitude on it and never a
// terrain height (the globe texture is imagery, not a DEM).

import { REFERENCE_RADIUS_M } from './conventions.ts'
import {
  enuFromAzEl,
  enuToMe,
  geographicToMe,
  normalizeLongitudeDeg,
} from './coords.ts'
import { globalScenePointToGeographic, meToGlobalScene } from './scene.ts'
import type { Vec3 } from './vec3.ts'

export const MOON_RADIUS_KM = REFERENCE_RADIUS_M / 1000

/** Scene point (km) for a latitude/longitude, optionally above the sphere (km). */
export function geoToScene(
  latitudeDeg: number,
  longitudeDeg: number,
  heightKm = 0,
): Vec3 {
  return meToGlobalScene(
    geographicToMe(
      latitudeDeg,
      longitudeDeg,
      heightKm * 1000,
      REFERENCE_RADIUS_M,
    ),
  )
}

/** Latitude/longitude of a point picked on the globe (longitude in [−180, 180), east positive). */
export function sceneToGeo(point: Vec3): {
  latitudeDeg: number
  longitudeDeg: number
} {
  const geo = globalScenePointToGeographic(point, REFERENCE_RADIUS_M)
  return { latitudeDeg: geo.latitudeDeg, longitudeDeg: geo.longitudeDeg }
}

/** A direction (unit vector) in the global scene: the ME → scene axis permutation, without scaling. */
export const meDirectionToScene = ([x, y, z]: Vec3): Vec3 => [y, z, x]

/**
 * Direction from a site towards a body, from the azimuth and elevation returned by the API.
 * Returns null when the azimuth is undefined (zenith/nadir): no direction is invented.
 */
export function bodyDirectionScene(
  azimuthDeg: number | null,
  elevationDeg: number,
  latitudeDeg: number,
  longitudeDeg: number,
): Vec3 | null {
  if (azimuthDeg === null) return null
  return meDirectionToScene(
    enuToMe(enuFromAzEl(azimuthDeg, elevationDeg), latitudeDeg, longitudeDeg),
  )
}

export interface SphereMesh {
  positions: Float32Array
  normals: Float32Array
  uvs: Float32Array
  indices: Uint32Array
}

/**
 * Sphere with an equirectangular texture centred on the 0° meridian:
 * u = (longitude + 180) / 360 and v = (latitude + 90) / 180 (v = 0 at the south pole, which is the
 * image bottom when the texture is flipped vertically, the Three.js default).
 */
export function buildSphere(
  latitudeSegments: number,
  longitudeSegments: number,
): SphereMesh {
  const columns = longitudeSegments + 1
  const rows = latitudeSegments + 1
  const positions = new Float32Array(columns * rows * 3)
  const normals = new Float32Array(columns * rows * 3)
  const uvs = new Float32Array(columns * rows * 2)
  for (let row = 0; row < rows; row++) {
    const latitude = -90 + (180 * row) / latitudeSegments
    for (let column = 0; column < columns; column++) {
      const longitude = -180 + (360 * column) / longitudeSegments
      const index = row * columns + column
      const point = geoToScene(latitude, longitude)
      positions.set(point, index * 3)
      normals.set(
        point.map((value) => value / MOON_RADIUS_KM),
        index * 3,
      )
      uvs.set([column / longitudeSegments, row / latitudeSegments], index * 2)
    }
  }
  const indices = new Uint32Array(latitudeSegments * longitudeSegments * 6)
  let k = 0
  for (let row = 0; row < latitudeSegments; row++) {
    for (let column = 0; column < longitudeSegments; column++) {
      const a = row * columns + column
      const b = a + 1
      const c = a + columns
      const d = c + 1
      indices.set([a, b, d, a, d, c], k)
      k += 6
    }
  }
  return { positions, normals, uvs, indices }
}

/** Graticule polylines (meridians and parallels) slightly above the sphere. */
export function graticule(
  latitudeStepDeg: number,
  longitudeStepDeg: number,
  samples = 90,
  heightKm = 1,
): Vec3[][] {
  const lines: Vec3[][] = []
  for (let longitude = -180; longitude < 180; longitude += longitudeStepDeg) {
    const line: Vec3[] = []
    for (let i = 0; i <= samples; i++) {
      line.push(geoToScene(-90 + (180 * i) / samples, longitude, heightKm))
    }
    lines.push(line)
  }
  for (
    let latitude = -90 + latitudeStepDeg;
    latitude < 90;
    latitude += latitudeStepDeg
  ) {
    const line: Vec3[] = []
    for (let i = 0; i <= samples * 2; i++) {
      line.push(
        geoToScene(latitude, -180 + (360 * i) / (samples * 2), heightKm),
      )
    }
    lines.push(line)
  }
  return lines
}

/** GeoJSON ring of [longitude, latitude] positions as scene points. */
export function ringToScene(
  ring: readonly (readonly number[])[],
  heightKm = 0.5,
): Vec3[] {
  return ring.map(([longitude, latitude]) =>
    geoToScene(latitude, longitude, heightKm),
  )
}

export interface PointerSample {
  x: number
  y: number
  timeMs: number
}

/** A press and release close in space and time is a click; anything else is a drag (rotation). */
export function isClick(
  down: PointerSample,
  up: PointerSample,
  maxDistancePx = 5,
  maxDurationMs = 700,
): boolean {
  return (
    Math.hypot(up.x - down.x, up.y - down.y) <= maxDistancePx &&
    up.timeMs - down.timeMs <= maxDurationMs
  )
}

export interface CoordinateInput {
  latitudeDeg: number
  longitudeDeg: number
}

/** Validates manual coordinates; longitude may be given in [−180, 360) and is normalized. */
export function parseCoordinates(
  latitudeText: string,
  longitudeText: string,
): {
  value: CoordinateInput | null
  latitudeOk: boolean
  longitudeOk: boolean
} {
  const latitude = latitudeText.trim() === '' ? NaN : Number(latitudeText)
  const longitude = longitudeText.trim() === '' ? NaN : Number(longitudeText)
  const latitudeOk =
    Number.isFinite(latitude) && latitude >= -90 && latitude <= 90
  const longitudeOk =
    Number.isFinite(longitude) && longitude >= -180 && longitude < 360
  return {
    latitudeOk,
    longitudeOk,
    value:
      latitudeOk && longitudeOk
        ? {
            latitudeDeg: latitude,
            // Values already in [−180, 180) are kept exactly as typed.
            longitudeDeg:
              longitude >= 180 ? normalizeLongitudeDeg(longitude) : longitude,
          }
        : null,
  }
}
