// Constante de convenție, identice cu backend/lunarhorizon/core/conventions.py.
// Testul src/geo/vectors.test.ts verifică egalitatea cu tests/vectors/conventions.json.

export const SCHEMA_VERSION = '0.8.0'

export const FRAME_ME_DE440 = 'MOON_ME_DE440_ME421'
export const FRAME_ME_DE421 = 'MOON_ME_DE421'
export const SUPPORTED_FRAMES = [FRAME_ME_DE440, FRAME_ME_DE421] as const
export type FrameId = (typeof SUPPORTED_FRAMES)[number]
/** Provizoriu: decizia D-01 [ASTRO]. */
export const DEFAULT_FRAME: FrameId = FRAME_ME_DE440
export const REJECTED_FRAME_ALIASES = [
  'MOON_ME',
  'MOON_PA',
  'IAU_MOON',
] as const

/** Raza sferei de referință, în metri. Provizoriu: decizia D-05 [GEO]. */
export const REFERENCE_RADIUS_M = 1_737_400

export const UNIT_SUFFIXES = [
  '_deg',
  '_m',
  '_km',
  '_s',
  '_utc',
  '_fraction',
  '_factor',
  '_px',
  '_bytes',
  '_count',
] as const

export function isSupportedFrame(frameId: string): frameId is FrameId {
  return (SUPPORTED_FRAMES as readonly string[]).includes(frameId)
}
