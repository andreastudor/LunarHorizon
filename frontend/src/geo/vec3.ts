// Vectori 3D și conversii de unghi, definite identic cu backend/lunarhorizon/core/units.py.

export type Vec3 = readonly [number, number, number]

export const DEG_TO_RAD = Math.PI / 180
export const RAD_TO_DEG = 180 / Math.PI

export const degToRad = (angleDeg: number): number => angleDeg * DEG_TO_RAD
export const radToDeg = (angleRad: number): number => angleRad * RAD_TO_DEG

export const dot = (a: Vec3, b: Vec3): number =>
  a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

export const cross = (a: Vec3, b: Vec3): Vec3 => [
  a[1] * b[2] - a[2] * b[1],
  a[2] * b[0] - a[0] * b[2],
  a[0] * b[1] - a[1] * b[0],
]

export const norm = (v: Vec3): number => Math.hypot(v[0], v[1], v[2])

export const sub = (a: Vec3, b: Vec3): Vec3 => [
  a[0] - b[0],
  a[1] - b[1],
  a[2] - b[2],
]

export const add = (a: Vec3, b: Vec3): Vec3 => [
  a[0] + b[0],
  a[1] + b[1],
  a[2] + b[2],
]
