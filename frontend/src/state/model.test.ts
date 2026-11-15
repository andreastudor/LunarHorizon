import { describe, expect, it } from 'vitest'
import type { SimulationRequest } from '../contracts/generated.ts'
import { requestDiffers } from './model.ts'

const base = (longitude: number, height = 2): SimulationRequest => ({
  sites: [
    {
      custom: {
        label: 'synthetic_point',
        latitude_deg: -85.42660397429984,
        longitude_deg: longitude,
      },
    },
  ],
  frame_id: 'MOON_ME_DE421',
  start_utc: '2026-11-15T00:00:00Z',
  end_utc: '2026-12-15T00:00:00Z',
  observer_height_m: height,
  solar_criterion: 'disc_center',
  earth_criterion: { kind: 'center_above_horizon', min_elevation_deg: 0 },
  terrain_mode: 'idealized_local_plane',
  panel: null,
})

describe('requestDiffers', () => {
  it('ignores float noise from the server normalizing the longitude', () => {
    // The server's longitude normalization can change the last digits (float noise ≈ 1e-14°).
    expect(
      requestDiffers(base(31.74418217323797), base(31.74418217323797 + 1e-14)),
    ).toBe(false)
  })

  it('detects a real change of point or parameters', () => {
    expect(requestDiffers(base(31.7), base(31.8))).toBe(true)
    expect(requestDiffers(base(31.7, 3), base(31.7, 2))).toBe(true)
    expect(requestDiffers(null, base(31.7))).toBe(false)
  })
})
