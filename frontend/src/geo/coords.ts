// Coordonate lunare și cadrul local al observatorului; oglinda lui
// backend/lunarhorizon/core/coords.py (docs/SPEC_FIZICA.md §3.2 și §4).
// Longitudine pozitivă spre est, normalizată în [-180, 180); azimut de la nord spre est în
// [0, 360); elevație față de planul perpendicular pe direcția radială. La |lat| = 90°,
// „nordul” este direcția spre meridianul longitudinii date (convenție provizorie D-03).

import { degToRad, radToDeg, dot, type Vec3 } from './vec3.ts'

export type CoordinateErrorReason =
  | 'not_finite'
  | 'latitude_out_of_range'
  | 'longitude_out_of_range'
  | 'zero_vector'

export class CoordinateError extends Error {
  readonly reason: CoordinateErrorReason

  constructor(reason: CoordinateErrorReason, value: unknown) {
    super(`${reason}: ${String(value)}`)
    this.name = 'CoordinateError'
    this.reason = reason
  }
}

export type AzimuthConvention = 'standard' | 'pole_meridian'

export interface Geographic {
  latitudeDeg: number
  longitudeDeg: number
  heightM: number
}

export function validateLatitudeDeg(latitudeDeg: number): number {
  if (!Number.isFinite(latitudeDeg))
    throw new CoordinateError('not_finite', latitudeDeg)
  if (latitudeDeg < -90 || latitudeDeg > 90) {
    throw new CoordinateError('latitude_out_of_range', latitudeDeg)
  }
  return latitudeDeg
}

/** Aduce orice longitudine finită în [-180, 180); pentru valori calculate. */
export function wrapLongitudeDeg(longitudeDeg: number): number {
  if (!Number.isFinite(longitudeDeg))
    throw new CoordinateError('not_finite', longitudeDeg)
  return ((longitudeDeg + 180) % 360) - 180
}

/** Acceptă [-180, 360) și întoarce valoarea echivalentă din [-180, 180). */
export function normalizeLongitudeDeg(longitudeDeg: number): number {
  if (!Number.isFinite(longitudeDeg))
    throw new CoordinateError('not_finite', longitudeDeg)
  if (longitudeDeg < -180 || longitudeDeg >= 360) {
    throw new CoordinateError('longitude_out_of_range', longitudeDeg)
  }
  // `+ 0` transformă un eventual -0 în 0, ca în Python.
  return wrapLongitudeDeg(longitudeDeg) + 0
}

export const azimuthConvention = (latitudeDeg: number): AzimuthConvention =>
  Math.abs(latitudeDeg) === 90 ? 'pole_meridian' : 'standard'

export function unitVector(latitudeDeg: number, longitudeDeg: number): Vec3 {
  const lat = degToRad(latitudeDeg)
  const lon = degToRad(longitudeDeg)
  return [
    Math.cos(lat) * Math.cos(lon),
    Math.cos(lat) * Math.sin(lon),
    Math.sin(lat),
  ]
}

export function geographicToMe(
  latitudeDeg: number,
  longitudeDeg: number,
  heightM: number,
  radiusM: number,
): Vec3 {
  const [ux, uy, uz] = unitVector(latitudeDeg, longitudeDeg)
  const r = radiusM + heightM
  return [r * ux, r * uy, r * uz]
}

/** Exact pe axa polară, longitudinea este 0. */
export function meToGeographic(pointM: Vec3, radiusM: number): Geographic {
  const [x, y, z] = pointM
  return {
    latitudeDeg: radToDeg(Math.atan2(z, Math.hypot(x, y))),
    longitudeDeg: wrapLongitudeDeg(radToDeg(Math.atan2(y, x))),
    heightM: Math.hypot(x, y, z) - radiusM,
  }
}

export interface EnuBasis {
  east: Vec3
  north: Vec3
  up: Vec3
}

export function enuBasis(latitudeDeg: number, longitudeDeg: number): EnuBasis {
  const lat = degToRad(latitudeDeg)
  const lon = degToRad(longitudeDeg)
  const [sinLat, cosLat] = [Math.sin(lat), Math.cos(lat)]
  const [sinLon, cosLon] = [Math.sin(lon), Math.cos(lon)]
  return {
    east: [-sinLon, cosLon, 0],
    north: [-sinLat * cosLon, -sinLat * sinLon, cosLat],
    up: [cosLat * cosLon, cosLat * sinLon, sinLat],
  }
}

export function meToEnu(
  vectorMe: Vec3,
  latitudeDeg: number,
  longitudeDeg: number,
): Vec3 {
  const { east, north, up } = enuBasis(latitudeDeg, longitudeDeg)
  return [dot(vectorMe, east), dot(vectorMe, north), dot(vectorMe, up)]
}

export function enuToMe(
  vectorEnu: Vec3,
  latitudeDeg: number,
  longitudeDeg: number,
): Vec3 {
  const { east, north, up } = enuBasis(latitudeDeg, longitudeDeg)
  const [e, n, u] = vectorEnu
  return [
    e * east[0] + n * north[0] + u * up[0],
    e * east[1] + n * north[1] + u * up[1],
    e * east[2] + n * north[2] + u * up[2],
  ]
}

export interface AzEl {
  azimuthDeg: number
  elevationDeg: number
}

export function azElFromEnu(vectorEnu: Vec3): AzEl {
  const [e, n, u] = vectorEnu
  const length = Math.hypot(e, n, u)
  if (length === 0) throw new CoordinateError('zero_vector', vectorEnu)
  let azimuthDeg = radToDeg(Math.atan2(e, n))
  if (azimuthDeg < 0) azimuthDeg += 360
  if (azimuthDeg >= 360) azimuthDeg = 0
  const elevationDeg = radToDeg(
    Math.asin(Math.max(-1, Math.min(1, u / length))),
  )
  return { azimuthDeg: azimuthDeg + 0, elevationDeg }
}

/** Versorul direcției: d = sin(az)cos(el)·E + cos(az)cos(el)·N + sin(el)·U. */
export function enuFromAzEl(azimuthDeg: number, elevationDeg: number): Vec3 {
  const az = degToRad(azimuthDeg)
  const el = degToRad(elevationDeg)
  return [
    Math.sin(az) * Math.cos(el),
    Math.cos(az) * Math.cos(el),
    Math.sin(el),
  ]
}

/** Poziția unui punct față de o origine locală, în metri, pe baza E, N, U din origine. */
export function meToLocalEnu(
  pointMe: Vec3,
  originLatitudeDeg: number,
  originLongitudeDeg: number,
  originMe: Vec3,
): Vec3 {
  const offset: Vec3 = [
    pointMe[0] - originMe[0],
    pointMe[1] - originMe[1],
    pointMe[2] - originMe[2],
  ]
  return meToEnu(offset, originLatitudeDeg, originLongitudeDeg)
}

export function localEnuToMe(
  pointEnu: Vec3,
  originLatitudeDeg: number,
  originLongitudeDeg: number,
  originMe: Vec3,
): Vec3 {
  const [dx, dy, dz] = enuToMe(pointEnu, originLatitudeDeg, originLongitudeDeg)
  return [originMe[0] + dx, originMe[1] + dy, originMe[2] + dz]
}
