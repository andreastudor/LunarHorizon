// Concordanța TypeScript ↔ Python (toleranța T-05) pe vectorii comuni din
// tests/vectors/conventions.json, generați de backend (scripts/generate_contracts.py).
import { describe, expect, it } from 'vitest'
import vectors from '../../../tests/vectors/conventions.json'
import {
  DEFAULT_FRAME,
  REFERENCE_RADIUS_M,
  REJECTED_FRAME_ALIASES,
  SCHEMA_VERSION,
  SUPPORTED_FRAMES,
  UNIT_SUFFIXES,
} from './conventions.ts'
import {
  CoordinateError,
  azElFromEnu,
  enuBasis,
  geographicToMe,
  meToLocalEnu,
  normalizeLongitudeDeg,
  validateLatitudeDeg,
} from './coords.ts'
import { SouthPolarStereographic } from './projection.ts'
import { UtcParseError, canonicalUtc } from './utc.ts'
import type { Vec3 } from './vec3.ts'

const T05 = vectors.tolerances['T-05']
const R = vectors.conventions.reference_radius_m

function expectClose(
  actual: readonly number[],
  expected: readonly number[],
  tol: number,
) {
  expect(actual).toHaveLength(expected.length)
  actual.forEach((value, i) => {
    expect(
      Math.abs(value - expected[i]),
      `componenta ${i}`,
    ).toBeLessThanOrEqual(tol)
  })
}

function reasonOf(action: () => unknown): string | undefined {
  try {
    action()
  } catch (error) {
    if (error instanceof UtcParseError || error instanceof CoordinateError)
      return error.reason
    throw error
  }
  return undefined
}

const angleDiffDeg = (a: number, b: number) =>
  Math.abs(((a - b + 540) % 360) - 180)

describe('convenții comune', () => {
  it('folosește aceleași constante ca backendul', () => {
    expect(SCHEMA_VERSION).toBe(vectors.schema_version)
    expect(REFERENCE_RADIUS_M).toBe(R)
    expect([...SUPPORTED_FRAMES]).toEqual(vectors.conventions.supported_frames)
    expect(DEFAULT_FRAME).toBe(vectors.conventions.default_frame)
    expect([...REJECTED_FRAME_ALIASES]).toEqual(
      vectors.conventions.rejected_frame_aliases,
    )
    expect([...UNIT_SUFFIXES]).toEqual(vectors.conventions.unit_suffixes)
  })

  it('are aceiași parametri ai proiecției stereografice', () => {
    const params = (proj4: string) =>
      Object.fromEntries(
        proj4
          .split(' ')
          .filter((token) => token.includes('='))
          .map((token) => {
            const [key, value] = token.slice(1).split('=')
            const number = Number(value)
            return [key, Number.isNaN(number) ? value : number]
          }),
      )
    expect(params(new SouthPolarStereographic().toProj4())).toEqual(
      params(vectors.conventions.polar_stereographic.proj4),
    )
  })
})

describe('UTC', () => {
  it.each(vectors.utc.valid)('$input → $canonical', ({ input, canonical }) => {
    expect(canonicalUtc(input)).toBe(canonical)
  })

  it.each(vectors.utc.invalid)(
    'respinge $input ($reason)',
    ({ input, reason }) => {
      expect(reasonOf(() => canonicalUtc(input))).toBe(reason)
    },
  )
})

describe('coordonate', () => {
  it.each(vectors.longitude_normalization)('longitudine $input', (testCase) => {
    if ('output' in testCase) {
      expect(normalizeLongitudeDeg(testCase.input)).toBe(testCase.output)
    } else {
      expect(reasonOf(() => normalizeLongitudeDeg(testCase.input))).toBe(
        testCase.error,
      )
    }
  })

  it.each(vectors.latitude_invalid)(
    'respinge latitudinea $input',
    ({ input, error }) => {
      expect(reasonOf(() => validateLatitudeDeg(input))).toBe(error)
    },
  )

  it.each(vectors.geographic_to_me)(
    'ME pentru ($latitude_deg, $longitude_deg, $height_m)',
    ({ latitude_deg, longitude_deg, height_m, me_m }) => {
      expectClose(
        geographicToMe(latitude_deg, longitude_deg, height_m, R),
        me_m,
        T05.length_m,
      )
    },
  )

  it.each(vectors.enu_basis)(
    'baza E, N, U în ($latitude_deg, $longitude_deg)',
    ({ latitude_deg, longitude_deg, east, north, up }) => {
      const basis = enuBasis(latitude_deg, longitude_deg)
      expectClose(basis.east, east, T05.unit_vector)
      expectClose(basis.north, north, T05.unit_vector)
      expectClose(basis.up, up, T05.unit_vector)
    },
  )

  it.each(vectors.az_el)(
    'azimut și elevație pentru $enu',
    ({ enu, azimuth_deg, elevation_deg }) => {
      const result = azElFromEnu(enu as unknown as Vec3)
      expect(result.azimuthDeg).toBeGreaterThanOrEqual(0)
      expect(result.azimuthDeg).toBeLessThan(360)
      expect(angleDiffDeg(result.azimuthDeg, azimuth_deg)).toBeLessThanOrEqual(
        T05.angle_deg,
      )
      expect(Math.abs(result.elevationDeg - elevation_deg)).toBeLessThanOrEqual(
        T05.angle_deg,
      )
    },
  )

  it.each(vectors.local_enu)('cadru local', ({ origin, point, enu_m }) => {
    const originMe = geographicToMe(
      origin.latitude_deg,
      origin.longitude_deg,
      origin.height_m,
      R,
    )
    const pointMe = geographicToMe(
      point.latitude_deg,
      point.longitude_deg,
      point.height_m,
      R,
    )
    expectClose(
      meToLocalEnu(
        pointMe,
        origin.latitude_deg,
        origin.longitude_deg,
        originMe,
      ),
      enu_m,
      T05.length_m,
    )
  })
})

describe('proiecția stereografică polară sudică', () => {
  const projection = new SouthPolarStereographic()

  it.each(vectors.polar_stereographic)(
    '($latitude_deg, $longitude_deg)',
    ({ latitude_deg, longitude_deg, x_m, y_m, scale_factor }) => {
      expectClose(
        projection.forward(latitude_deg, longitude_deg),
        [x_m, y_m],
        T05.length_m,
      )
      expect(
        Math.abs(projection.scale(latitude_deg) - scale_factor),
      ).toBeLessThanOrEqual(T05.scale_factor)
    },
  )
})
