// Visual mapping only. No scene coordinates are fed back to physical calculations.
export type SystemBody = 'sun' | 'earth' | 'moon'
export type Point3 = [number, number, number]
export const KM_PER_SCENE_UNIT = 2_000_000
export const MOON_OFFSET_FACTOR = 80

export function systemScenePoint(
  body: SystemBody,
  earthKm: number[],
  moonKm: number[],
): Point3 {
  const position =
    body === 'sun'
      ? [0, 0, 0]
      : body === 'earth'
        ? earthKm
        : earthKm.map((v, i) => v + (moonKm[i] - v) * MOON_OFFSET_FACTOR)
  // Rigid, right-handed axis permutation: J2000 X → X, Z → Y, Y → -Z.
  return [
    position[0] / KM_PER_SCENE_UNIT,
    position[2] / KM_PER_SCENE_UNIT,
    -position[1] / KM_PER_SCENE_UNIT,
  ]
}
