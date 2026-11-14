// Transformările scenelor 3D și proprietățile independente ale modulului geo (toleranța T-04).
import { describe, expect, it } from 'vitest'
import vectors from '../../../tests/vectors/conventions.json'
import { REFERENCE_RADIUS_M as R } from './conventions.ts'
import {
  azElFromEnu,
  azimuthConvention,
  enuBasis,
  enuFromAzEl,
  geographicToMe,
  meToGeographic,
  type Geographic,
} from './coords.ts'
import { SouthPolarStereographic } from './projection.ts'
import {
  LocalSceneFrame,
  directionToLocalScene,
  enuToLocalScene,
  globalSceneToMe,
  globalScenePointToGeographic,
  localSceneToEnu,
  meToGlobalScene,
} from './scene.ts'
import { cross, norm, sub, type Vec3 } from './vec3.ts'

const T04 = vectors.tolerances['T-04']

function expectVec(actual: Vec3, expected: Vec3, tol: number) {
  actual.forEach((value, i) =>
    expect(Math.abs(value - expected[i])).toBeLessThanOrEqual(tol),
  )
}

const horizontalErrorM = (a: Geographic, b: Geographic) => {
  const dLon = Math.abs(((a.longitudeDeg - b.longitudeDeg + 540) % 360) - 180)
  return (
    ((dLon * Math.PI) / 180) *
    (R + b.heightM) *
    Math.cos((b.latitudeDeg * Math.PI) / 180)
  )
}

describe('scena globală (km, centrul Lunii)', () => {
  it('pune polul nord pe +y, meridianul 0 pe +z și 90°E pe +x', () => {
    expectVec(
      meToGlobalScene(geographicToMe(90, 0, 0, R)),
      [0, R / 1000, 0],
      1e-9,
    )
    expectVec(
      meToGlobalScene(geographicToMe(0, 0, 0, R)),
      [0, 0, R / 1000],
      1e-9,
    )
    expectVec(
      meToGlobalScene(geographicToMe(0, 90, 0, R)),
      [R / 1000, 0, 0],
      1e-9,
    )
  })

  it('păstrează orientarea dreaptă: img(X) × img(Y) = img(Z)', () => {
    // Vectori de 1000 m, ca imaginile în scenă (km) să fie versori.
    const [ex, ey, ez] = [
      meToGlobalScene([1000, 0, 0]),
      meToGlobalScene([0, 1000, 0]),
      meToGlobalScene([0, 0, 1000]),
    ]
    expectVec(cross(ex, ey), ez, 1e-15)
  })

  it('transformă dus-întors și convertește un punct ales pe glob', () => {
    for (const [lat, lon] of [
      [-89.9, 179.999999],
      [-89.9, -179.999999],
      [-45, 170],
      [12.5, -60],
    ]) {
      const pointMe = geographicToMe(lat, lon, 0, R)
      expectVec(
        globalSceneToMe(meToGlobalScene(pointMe)),
        pointMe,
        T04.length_m,
      )
      const picked = globalScenePointToGeographic(meToGlobalScene(pointMe), R)
      expect(Math.abs(picked.latitudeDeg - lat)).toBeLessThanOrEqual(
        T04.angle_deg,
      )
      expect(
        horizontalErrorM(picked, {
          latitudeDeg: lat,
          longitudeDeg: lon,
          heightM: 0,
        }),
      ).toBeLessThanOrEqual(T04.length_m)
      expect(Math.abs(picked.heightM)).toBeLessThanOrEqual(T04.length_m)
    }
  })
})

describe('scena locală (m, origine pe teren)', () => {
  it('pune estul pe +x, zenitul pe +y și nordul pe -z', () => {
    expectVec(enuToLocalScene([1, 0, 0]), [1, 0, 0], 0)
    expectVec(enuToLocalScene([0, 0, 1]), [0, 1, 0], 0)
    expectVec(enuToLocalScene([0, 1, 0]), [0, 0, -1], 0)
    expectVec(localSceneToEnu(enuToLocalScene([3, -4, 5])), [3, -4, 5], 0)
  })

  it('păstrează orientarea dreaptă: img(E) × img(N) = img(U)', () => {
    const [east, north, up] = [
      enuToLocalScene([1, 0, 0]),
      enuToLocalScene([0, 1, 0]),
      enuToLocalScene([0, 0, 1]),
    ]
    expectVec(cross(east, north), up, 1e-15)
  })

  it('desenează direcțiile din azimut și elevație', () => {
    expectVec(directionToLocalScene(0, 0), [0, 0, -1], 1e-15)
    expectVec(directionToLocalScene(90, 0), [1, 0, 0], 1e-15)
    expectVec(directionToLocalScene(180, 0), [0, 0, 1], 1e-15)
    expectVec(directionToLocalScene(0, 90), [0, 1, 0], 1e-15)
  })

  it('așază originea în (0, 0, 0) și transformă dus-întors, inclusiv la ±180° și la pol', () => {
    const origins: Geographic[] = [
      { latitudeDeg: -89.5, longitudeDeg: 179.99, heightM: 1500 },
      { latitudeDeg: -90, longitudeDeg: 0, heightM: 0 },
      { latitudeDeg: -87.2, longitudeDeg: -45, heightM: -800 },
    ]
    for (const origin of origins) {
      const frame = new LocalSceneFrame(origin, R)
      expectVec(frame.geographicToScene(origin), [0, 0, 0], T04.length_m)
      for (const point of [
        { latitudeDeg: -89.45, longitudeDeg: -179.99, heightM: 1600 },
        { latitudeDeg: -89.99, longitudeDeg: 90, heightM: 0 },
        { latitudeDeg: -87.25, longitudeDeg: -44.9, heightM: -700 },
      ]) {
        const scene = frame.geographicToScene(point)
        const back = frame.sceneToGeographic(scene)
        expect(
          Math.abs(back.latitudeDeg - point.latitudeDeg),
        ).toBeLessThanOrEqual(T04.angle_deg)
        expect(Math.abs(back.heightM - point.heightM)).toBeLessThanOrEqual(
          T04.length_m,
        )
        expect(horizontalErrorM(back, point)).toBeLessThanOrEqual(T04.length_m)
        // Transformare rigidă: distanța față de origine se păstrează.
        const distanceMe = norm(
          sub(
            geographicToMe(
              point.latitudeDeg,
              point.longitudeDeg,
              point.heightM,
              R,
            ),
            frame.originMe,
          ),
        )
        expect(Math.abs(norm(scene) - distanceMe)).toBeLessThanOrEqual(
          T04.length_m,
        )
      }
    }
  })
})

describe('proprietăți independente ale modulului geo', () => {
  it('convenția la pol: nordul arată spre meridianul dat', () => {
    for (const lon of [0, 90, -135]) {
      expectVec(enuBasis(-90, lon).north, geographicToMe(0, lon, 0, 1), 1e-15)
    }
    expect(azimuthConvention(-90)).toBe('pole_meridian')
    expect(azimuthConvention(-89.999999)).toBe('standard')
  })

  it('azimut și elevație dus-întors', () => {
    for (const az of [0, 1, 89, 180, 271.5, 359.999]) {
      for (const el of [-89, 0, 45]) {
        const back = azElFromEnu(enuFromAzEl(az, el))
        expect(
          Math.abs(((back.azimuthDeg - az + 540) % 360) - 180),
        ).toBeLessThanOrEqual(1e-9)
        expect(Math.abs(back.elevationDeg - el)).toBeLessThanOrEqual(1e-9)
      }
    }
  })

  it('geografic → ME → geografic, la poli și la ±180°', () => {
    for (const lat of [-90, -89.999999, -60, 0, 89.9, 90]) {
      for (const lon of [-180, -179.999999, 0, 179.999999]) {
        for (const h of [-9000, 0, 11000]) {
          const back = meToGeographic(geographicToMe(lat, lon, h, R), R)
          expect(Math.abs(back.latitudeDeg - lat)).toBeLessThanOrEqual(
            T04.angle_deg,
          )
          expect(Math.abs(back.heightM - h)).toBeLessThanOrEqual(T04.length_m)
          expect(
            horizontalErrorM(back, {
              latitudeDeg: lat,
              longitudeDeg: lon,
              heightM: h,
            }),
          ).toBeLessThanOrEqual(T04.length_m)
        }
      }
    }
  })

  it('proiecția: dus-întors și continuitate la ±180°', () => {
    const projection = new SouthPolarStereographic()
    for (const lat of [-90, -89, -85, -70]) {
      for (const lon of [-180, -90, 0, 45, 179.999999]) {
        const [x, y] = projection.forward(lat, lon)
        const back = projection.inverse(x, y)
        expect(Math.abs(back.latitudeDeg - lat)).toBeLessThanOrEqual(
          T04.angle_deg,
        )
      }
    }
    const east = projection.forward(-80, 179.999999)
    const west = projection.forward(-80, -179.999999)
    expect(Math.hypot(east[0] - west[0], east[1] - west[1])).toBeLessThan(1)
    expect(projection.inverse(0, 0)).toEqual({
      latitudeDeg: -90,
      longitudeDeg: 0,
    })
  })
})
