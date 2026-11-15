// Pure helpers for the shared state: the selection key and the SimulationRequest built from the form.
// UTC only; the request always names the frame explicitly and never converts coordinates.

import type { SimulationRequest } from '../contracts/generated.ts'
import { DEFAULT_FRAME } from '../geo/conventions.ts'
import { formatUtc, parseUtc } from '../geo/utc.ts'
import type { Selection, SimulationParams } from './types.ts'

export const DURATION_OPTIONS_DAYS = [1, 3, 7, 14, 30, 60, 90] as const

export function selectionKey(selection: Selection): string {
  if (!selection) return 'none'
  if (selection.kind === 'catalog') return `catalog:${selection.siteId}`
  return `custom:${selection.latitudeDeg}:${selection.longitudeDeg}:${selection.label}`
}

const pad = (n: number) => String(n).padStart(2, '0')

/** Default start: the current UTC day at 00:00, a 30-day interval, observer 2 m above the surface. */
export function defaultParams(now: Date): SimulationParams {
  return {
    startDate: `${now.getUTCFullYear()}-${pad(now.getUTCMonth() + 1)}-${pad(now.getUTCDate())}`,
    startTime: '00:00',
    durationDays: 30,
    observerHeightM: '2',
    earthMinElevationDeg: '0',
    frameId: DEFAULT_FRAME,
    terrainMode: 'idealized_local_plane',
  }
}

export interface ParamErrors {
  date?: boolean
  height?: boolean
  elevation?: boolean
}

export interface BuiltRequest {
  request: SimulationRequest | null
  errors: ParamErrors
}

export function buildRequest(
  selection: Selection,
  params: SimulationParams,
): BuiltRequest {
  const errors: ParamErrors = {}
  let startMs = NaN
  try {
    startMs = parseUtc(`${params.startDate}T${params.startTime}:00Z`)
  } catch {
    errors.date = true
  }
  const height = Number(params.observerHeightM)
  if (
    params.observerHeightM.trim() === '' ||
    !Number.isFinite(height) ||
    height < 0
  ) {
    errors.height = true
  }
  const elevation = Number(params.earthMinElevationDeg)
  if (
    params.earthMinElevationDeg.trim() === '' ||
    !Number.isFinite(elevation) ||
    elevation < -90 ||
    elevation > 90
  ) {
    errors.elevation = true
  }
  if (!selection || Object.keys(errors).length > 0) {
    return { request: null, errors }
  }
  const site =
    selection.kind === 'catalog'
      ? { site_id: selection.siteId }
      : {
          custom: {
            label: selection.label,
            latitude_deg: selection.latitudeDeg,
            longitude_deg: selection.longitudeDeg,
          },
        }
  return {
    errors,
    request: {
      sites: [site],
      frame_id: params.frameId,
      start_utc: formatUtc(startMs),
      end_utc: formatUtc(startMs + params.durationDays * 86_400_000),
      observer_height_m: height,
      solar_criterion: 'disc_positive_area',
      earth_criterion: {
        kind: 'center_above_horizon',
        min_elevation_deg: elevation,
      },
      terrain_mode: params.terrainMode,
      panel: null,
    },
  }
}

/** True when the form now describes a different request than the one behind the shown result. */
export function requestDiffers(
  a: SimulationRequest | null,
  b: SimulationRequest,
): boolean {
  if (!a) return false
  // The server normalizes coordinates (e.g. longitude), which can change the last float digits:
  // sites are compared with a 1e-9° tolerance, everything else exactly.
  const sameSites =
    a.sites.length === b.sites.length &&
    a.sites.every((site, i) => {
      const other = b.sites[i]
      if ('site_id' in site || 'site_id' in other)
        return (
          'site_id' in site &&
          'site_id' in other &&
          site.site_id === other.site_id
        )
      return (
        site.custom.label === other.custom.label &&
        Math.abs(site.custom.latitude_deg - other.custom.latitude_deg) < 1e-9 &&
        Math.abs(site.custom.longitude_deg - other.custom.longitude_deg) < 1e-9
      )
    })
  if (!sameSites) return true
  const pick = (r: SimulationRequest) =>
    JSON.stringify([
      r.frame_id,
      r.start_utc,
      r.end_utc,
      r.observer_height_m,
      r.earth_criterion,
      r.terrain_mode,
    ])
  return pick(a) !== pick(b)
}
