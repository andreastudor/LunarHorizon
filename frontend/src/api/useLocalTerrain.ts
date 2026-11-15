// Loads the local terrain for the selected point: manifest → visual level of detail (once per
// terrain) → observer height from the calculation raster. Responses that arrive after the
// selection changed are ignored. A point outside every DEM raster is "unavailable", never an
// invented relief.

import { useEffect, useRef, useState } from 'react'
import type { TerrainManifest, TerrainSample } from '../contracts/generated.ts'
import { buildTerrainMesh, type TerrainMesh } from '../geo/terrain.ts'
import { ApiError, type DataSource } from './dataSource.ts'
import { describeError, type ErrorDescription } from './errors.ts'

/** Visual level used for the mesh: level 0 (40 m/pixel for the first site). */
export const TERRAIN_LOD_LEVEL = 0

export type LocalTerrain =
  | { status: 'none' }
  | { status: 'loading' }
  | { status: 'unavailable' }
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

export function useLocalTerrain(
  source: DataSource,
  point: TerrainPoint | null,
  reloadToken: number,
): LocalTerrain {
  const [state, setState] = useState<LocalTerrain>({ status: 'none' })
  const meshes = useRef(
    new Map<string, { mesh: TerrainMesh; resolutionM: number }>(),
  )
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
          signal,
        )
        let cached = meshes.current.get(manifest.terrain_id)
        if (!cached) {
          const lod = manifest.lods.find(
            (item) => item.level === TERRAIN_LOD_LEVEL,
          )
          if (!lod) throw new Error('missing level of detail')
          const data = await source.terrainLod(
            manifest.terrain_id,
            lod.level,
            signal,
          )
          cached = {
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
          meshes.current.set(manifest.terrain_id, cached)
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
        if (
          error instanceof ApiError &&
          error.problem?.code === 'OUT_OF_DEM_COVERAGE'
        ) {
          setState({ status: 'unavailable' })
          return
        }
        setState({ status: 'error', error: describeError(error) })
      }
    }
    void load()
    return () => controller.abort()
  }, [source, latitude, longitude, reloadToken])

  return latitude === null || longitude === null ? { status: 'none' } : state
}
