// Loads the local terrain for the selected point: manifest → visual level of detail (once per
// terrain) → observer height from the calculation raster. Responses that arrive after the
// selection changed are ignored. A point outside every DEM raster is "unavailable", never an
// invented relief.

import { useEffect, useRef, useState } from 'react'
import type { TerrainManifest, TerrainSample } from '../contracts/generated.ts'
import { buildTerrainMesh, type TerrainMesh } from '../geo/terrain.ts'
import { ApiError, type DataSource } from './dataSource.ts'
import { describeError, type ErrorDescription } from './errors.ts'

/** The finest visual level with at most this many vertices is used for the mesh. */
export const VERTEX_BUDGET = 300_000

/** Why no terrain is shown (each state is displayed distinctly; no relief is generated). */
export type TerrainGap =
  | 'no_dem_coverage'
  | 'coverage_unverified'
  | 'terrain_not_downloaded'
  | 'frame_mismatch'

export type LocalTerrain =
  | { status: 'none' }
  | { status: 'loading' }
  | { status: 'unavailable'; gap: TerrainGap }
  | { status: 'error'; error: ErrorDescription }
  | {
      status: 'ready'
      manifest: TerrainManifest
      mesh: TerrainMesh
      lodResolutionM: number
      sample: TerrainSample
    }

export interface TerrainPoint {
  latitudeDeg: number
  longitudeDeg: number
}

const isAbort = (error: unknown) =>
  error instanceof DOMException && error.name === 'AbortError'

function gapOf(error: unknown): TerrainGap | null {
  if (!(error instanceof ApiError) || !error.problem) return null
  const { code, detail } = error.problem
  if (code === 'TERRAIN_DATA_MISSING') return 'terrain_not_downloaded'
  if (code === 'UNSUPPORTED_FRAME') return 'frame_mismatch'
  if (code === 'OUT_OF_DEM_COVERAGE')
    // The server prefixes the detail with the selection status (an identifier).
    return detail.startsWith('coverage_unverified')
      ? 'coverage_unverified'
      : 'no_dem_coverage'
  return null
}

export function useLocalTerrain(
  source: DataSource,
  point: TerrainPoint | null,
  frameId: string | null,
  reloadToken: number,
): LocalTerrain {
  const [state, setState] = useState<LocalTerrain>({ status: 'none' })
  // Only the current terrain is kept (no preloading, released when another region is selected).
  const current = useRef<{
    terrainId: string
    mesh: TerrainMesh
    resolutionM: number
  } | null>(null)
  const latitude = point?.latitudeDeg ?? null
  const longitude = point?.longitudeDeg ?? null

  useEffect(() => {
    if (latitude === null || longitude === null) return
    const controller = new AbortController()
    const { signal } = controller
    const load = async () => {
      setState({ status: 'loading' })
      try {
        const manifest = await source.terrainManifest(
          latitude,
          longitude,
          frameId,
          signal,
        )
        let cached =
          current.current?.terrainId === manifest.terrain_id
            ? current.current
            : null
        if (!cached) {
          const lod = [...manifest.lods]
            .sort((a, b) => a.visual_resolution_m - b.visual_resolution_m)
            .find((item) => item.width_px * item.height_px <= VERTEX_BUDGET)
          if (!lod)
            throw new Error('no level of detail within the vertex budget')
          const data = await source.terrainLod(
            manifest.terrain_id,
            lod.level,
            signal,
          )
          cached = {
            terrainId: manifest.terrain_id,
            mesh: buildTerrainMesh(
              {
                width: data.width,
                height: data.height,
                heights: data.heights,
                resolutionM: lod.visual_resolution_m,
                xMinM: manifest.bounds.x_min_m,
                yMaxM: manifest.bounds.y_max_m,
              },
              manifest,
            ),
            resolutionM: lod.visual_resolution_m,
          }
          current.current = cached
        }
        const sample = await source.terrainElevation(
          manifest.terrain_id,
          latitude,
          longitude,
          signal,
        )
        if (signal.aborted) return
        setState({
          status: 'ready',
          manifest,
          mesh: cached.mesh,
          lodResolutionM: cached.resolutionM,
          sample,
        })
      } catch (error) {
        if (signal.aborted || isAbort(error)) return
        const gap = gapOf(error)
        if (gap) {
          setState({ status: 'unavailable', gap })
          return
        }
        setState({ status: 'error', error: describeError(error) })
      }
    }
    void load()
    return () => controller.abort()
  }, [source, latitude, longitude, frameId, reloadToken])

  return latitude === null || longitude === null ? { status: 'none' } : state
}
