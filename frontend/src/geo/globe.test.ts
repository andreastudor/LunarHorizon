import { describe, expect, it } from 'vitest'
import {
  MOON_RADIUS_KM,
  bodyDirectionScene,
  buildSphere,
  geoToScene,
  isClick,
  parseCoordinates,
  ringToScene,
  sceneToGeo,
} from './globe.ts'

const close = (a: readonly number[], b: readonly number[], digits = 9) =>
  a.forEach((value, i) => expect(value).toBeCloseTo(b[i], digits))

describe('global scene axes', () => {
  it('puts 0°E on +z, 90°E on +x and the north pole on +y', () => {
    close(geoToScene(0, 0), [0, 0, MOON_RADIUS_KM])
    close(geoToScene(0, 90), [MOON_RADIUS_KM, 0, 0])
    close(geoToScene(0, -90), [-MOON_RADIUS_KM, 0, 0])
    close(geoToScene(90, 0), [0, MOON_RADIUS_KM, 0])
    close(geoToScene(-90, 0), [0, -MOON_RADIUS_KM, 0])
  })

  it('returns east-positive longitude for a picked point (sense of longitude)', () => {
    const east = sceneToGeo(geoToScene(10, 45))
    expect(east.latitudeDeg).toBeCloseTo(10, 9)
    expect(east.longitudeDeg).toBeCloseTo(45, 9)
    const west = sceneToGeo(geoToScene(-85.4266, -148))
    expect(west.latitudeDeg).toBeCloseTo(-85.4266, 9)
    expect(west.longitudeDeg).toBeCloseTo(-148, 9)
  })

  it('round-trips points, including the ±180° meridian, into [−180, 180)', () => {
    expect(sceneToGeo(geoToScene(20, 180)).longitudeDeg).toBeCloseTo(-180, 9)
    for (const [lat, lon] of [
      [0.67416, 23.47314],
      [-69.374, 32.3187],
      [-45.4562, 177.5886],
      [89.9, -10],
    ]) {
      const geo = sceneToGeo(geoToScene(lat, lon, 3))
      expect(geo.latitudeDeg).toBeCloseTo(lat, 9)
      expect(geo.longitudeDeg).toBeCloseTo(lon, 9)
    }
  })
})

describe('sphere mesh', () => {
  it('maps the equirectangular texture so that u follows east longitude', () => {
    const lonSegments = 8
    const latSegments = 4
    const mesh = buildSphere(latSegments, lonSegments)
    const columns = lonSegments + 1
    for (let row = 0; row <= latSegments; row++) {
      for (let column = 0; column <= lonSegments; column++) {
        const index = row * columns + column
        const point = [
          mesh.positions[index * 3],
          mesh.positions[index * 3 + 1],
          mesh.positions[index * 3 + 2],
        ] as const
        const u = mesh.uvs[index * 2]
        const v = mesh.uvs[index * 2 + 1]
        const geo = sceneToGeo(point)
        expect(geo.latitudeDeg).toBeCloseTo(-90 + 180 * v, 4)
        if (Math.abs(geo.latitudeDeg) < 89.9 && u > 0 && u < 1) {
          expect(geo.longitudeDeg).toBeCloseTo(-180 + 360 * u, 4)
        }
      }
    }
    expect(mesh.indices.length).toBe(latSegments * lonSegments * 6)
  })

  it('has outward faces (counter-clockwise seen from outside)', () => {
    const mesh = buildSphere(16, 32)
    const at = (i: number) => [
      mesh.positions[i * 3],
      mesh.positions[i * 3 + 1],
      mesh.positions[i * 3 + 2],
    ]
    const t = Math.floor(mesh.indices.length / 6 / 2) * 6
    const [a, b, c] = [
      mesh.indices[t],
      mesh.indices[t + 1],
      mesh.indices[t + 2],
    ].map(at)
    const ab = b.map((value, i) => value - a[i])
    const ac = c.map((value, i) => value - a[i])
    const normal = [
      ab[1] * ac[2] - ab[2] * ac[1],
      ab[2] * ac[0] - ab[0] * ac[2],
      ab[0] * ac[1] - ab[1] * ac[0],
    ]
    expect(
      normal[0] * a[0] + normal[1] * a[1] + normal[2] * a[2],
    ).toBeGreaterThan(0)
  })
})

describe('body directions from the API azimuth and elevation', () => {
  it('points east for azimuth 90°, elevation 0° at 0°N 0°E', () => {
    close(bodyDirectionScene(90, 0, 0, 0)!, [1, 0, 0])
  })

  it('points north (+y) for azimuth 0°, elevation 0° at the equator', () => {
    close(bodyDirectionScene(0, 0, 0, 0)!, [0, 1, 0])
  })

  it('points along the local vertical for elevation 90° with a defined azimuth', () => {
    const up = geoToScene(-60, 120).map((value) => value / MOON_RADIUS_KM)
    close(bodyDirectionScene(45, 90, -60, 120)!, up)
  })

  it('returns no direction when the azimuth is undefined', () => {
    expect(bodyDirectionScene(null, 89.9999, -89.9, 0)).toBeNull()
  })
})

describe('click versus drag', () => {
  it('treats a short, still press as a click and a movement as rotation', () => {
    const down = { x: 100, y: 100, timeMs: 0 }
    expect(isClick(down, { x: 102, y: 101, timeMs: 150 })).toBe(true)
    expect(isClick(down, { x: 140, y: 100, timeMs: 150 })).toBe(false)
    expect(isClick(down, { x: 100, y: 100, timeMs: 2000 })).toBe(false)
  })
})

describe('manual coordinates', () => {
  it('validates ranges and normalizes longitude to [−180, 180)', () => {
    expect(parseCoordinates('-85.4266', '31.7442').value).toEqual({
      latitudeDeg: -85.4266,
      longitudeDeg: 31.7442,
    })
    expect(parseCoordinates('10', '350').value?.longitudeDeg).toBeCloseTo(
      -10,
      12,
    )
    expect(parseCoordinates('91', '0').latitudeOk).toBe(false)
    expect(parseCoordinates('0', '360').longitudeOk).toBe(false)
    expect(parseCoordinates('', '').value).toBeNull()
    expect(parseCoordinates('abc', '0').latitudeOk).toBe(false)
  })
})

describe('coverage outline', () => {
  it('converts a GeoJSON ring of [lon, lat] to scene points', () => {
    const points = ringToScene(
      [
        [31.7, -85.4],
        [32.0, -85.4],
        [31.7, -85.4],
      ],
      0,
    )
    expect(sceneToGeo(points[1]).longitudeDeg).toBeCloseTo(32, 9)
    expect(sceneToGeo(points[1]).latitudeDeg).toBeCloseTo(-85.4, 9)
  })
})
