// Local terrain view (E08): the real DEM mesh around the selected point, the observer at the terrain
// height plus the equipment height, and the Sun/Earth directions of the API result at the selected
// time. Exaggeration, camera and shadows are visual only; visibility does not use terrain yet.

import { useEffect, useMemo, useRef, useState } from 'react'
import type { LocalTerrain } from '../api/useLocalTerrain.ts'
import {
  EXAGGERATION_OPTIONS,
  bodyDirectionLocal,
  observerScene,
  terrainFrame,
} from '../geo/terrain.ts'
import type { Vec3 } from '../geo/vec3.ts'
import {
  WebGLUnavailableError,
  type TerrainCameraMode,
  type TerrainFactory,
  type TerrainHandle,
  type TerrainSceneState,
} from '../globe/types.ts'
import { en } from '../i18n/en.ts'
import { fmtDeg } from '../ui/format.ts'

export interface BodyAtTime {
  azimuthDeg: number | null
  elevationDeg: number
}

interface Props {
  terrain: LocalTerrain
  point: { latitudeDeg: number; longitudeDeg: number } | null
  equipmentHeightM: number | null
  /** Bodies at the selected time, from the result for this point; null without a result. */
  bodies: { sun: BodyAtTime; earth: BodyAtTime; timeLabel: string } | null
  /** Frame of the simulation that produced `bodies`. */
  simulationFrame: string | null
  onPick: (latitudeDeg: number, longitudeDeg: number) => void
  onRetry: () => void
  /** Offered for a frame mismatch on a user point: adopt the DEM frame (no conversion). */
  onAdoptFrame?: () => void
  /** The frame declared by the DEM products, when they all declare the same one. */
  demFrame?: string | null
  /** Terrain mode of the loaded result (selects the banner text). */
  resultMode?: 'dem' | 'idealized_local_plane' | null
  /** Computed states at the slider time, from the backend result (never from the shadows). */
  indicators?: {
    sun: string
    earth: string
    sunState: string
    earthState: string
  } | null
  factory?: TerrainFactory
}

const loadDefaultFactory = async (): Promise<TerrainFactory> =>
  (await import('../globe/threeTerrain.ts')).createThreeTerrain

const CAMERA_MODES: TerrainCameraMode[] = ['top', 'oblique', 'observer']

export function LocalTerrainView({
  terrain,
  point,
  equipmentHeightM,
  bodies,
  simulationFrame,
  onPick,
  onRetry,
  onAdoptFrame,
  demFrame,
  resultMode = null,
  indicators = null,
  factory,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const handleRef = useRef<TerrainHandle | null>(null)
  const pickRef = useRef(onPick)
  const terrainRef = useRef(terrain)
  const [phase, setPhase] = useState<'loading' | 'ready' | 'unavailable'>(
    'loading',
  )
  const [exaggeration, setExaggeration] = useState(1)
  const [mode, setMode] = useState<TerrainCameraMode>('oblique')

  useEffect(() => {
    pickRef.current = onPick
    terrainRef.current = terrain
  }, [onPick, terrain])

  const ready = terrain.status === 'ready' ? terrain : null
  const frameMatches =
    ready !== null &&
    simulationFrame !== null &&
    simulationFrame === ready.manifest.frame_id

  const sceneState = useMemo<TerrainSceneState>(() => {
    if (!ready || !point) {
      return {
        mesh: null,
        observer: null,
        sun: null,
        earth: null,
        sunElevationDeg: null,
        exaggeration,
      }
    }
    const elevation = ready.sample.elevation_m
    const observer =
      elevation !== null && equipmentHeightM !== null
        ? observerScene(
            ready.manifest,
            point.latitudeDeg,
            point.longitudeDeg,
            elevation,
            equipmentHeightM,
          )
        : null
    const direction = (body: BodyAtTime | undefined): Vec3 | null =>
      body && frameMatches
        ? bodyDirectionLocal(
            ready.manifest,
            body.azimuthDeg,
            body.elevationDeg,
            point.latitudeDeg,
            point.longitudeDeg,
          )
        : null
    return {
      mesh: ready.mesh,
      observer,
      sun: direction(bodies?.sun),
      earth: direction(bodies?.earth),
      sunElevationDeg: frameMatches ? (bodies?.sun.elevationDeg ?? null) : null,
      exaggeration,
    }
  }, [ready, point, equipmentHeightM, bodies, frameMatches, exaggeration])

  const stateRef = useRef(sceneState)
  useEffect(() => {
    stateRef.current = sceneState
    handleRef.current?.update(sceneState)
  }, [sceneState])

  useEffect(() => {
    let disposed = false
    const container = containerRef.current
    if (!container) return
    const create = async () => {
      try {
        const make = factory ?? (await loadDefaultFactory())
        if (disposed) return
        const handle = make(container, {
          onPick: (scenePoint) => {
            const current = terrainRef.current
            if (current.status !== 'ready') return
            const geo = terrainFrame(current.manifest).sceneToGeographic(
              scenePoint,
            )
            pickRef.current(geo.latitudeDeg, geo.longitudeDeg)
          },
        })
        handleRef.current = handle
        handle.update(stateRef.current)
        setPhase('ready')
      } catch (error) {
        if (disposed) return
        if (!(error instanceof WebGLUnavailableError)) console.error(error)
        setPhase('unavailable')
      }
    }
    void create()
    return () => {
      disposed = true
      handleRef.current?.dispose()
      handleRef.current = null
    }
  }, [factory])

  const chooseCamera = (next: TerrainCameraMode) => {
    setMode(next)
    handleRef.current?.setCamera(next)
  }

  const isRepresentative =
    ready !== null &&
    point !== null &&
    Math.abs(point.latitudeDeg - ready.manifest.local_origin.latitude_deg) <
      1e-9 &&
    Math.abs(point.longitudeDeg - ready.manifest.local_origin.longitude_deg) <
      1e-9

  const undefinedAzimuth =
    frameMatches &&
    bodies !== null &&
    (bodies.sun.azimuthDeg === null || bodies.earth.azimuthDeg === null)

  const lighting =
    !bodies || !frameMatches || bodies.sun.azimuthDeg === null
      ? en.terrain.lightingNeutral
      : bodies.sun.elevationDeg < 0
        ? en.terrain.lightingSunBelow
        : en.terrain.lightingSun(bodies.timeLabel)

  return (
    <div className="terrain">
      <div
        ref={containerRef}
        className="terrain-canvas"
        role="img"
        aria-label={en.terrain.label}
      />
      <p className="terrain-banner" role="note">
        {resultMode === 'dem' ? en.terrain.bannerDem : en.terrain.banner}
      </p>
      {indicators && (
        <ul className="terrain-indicators" aria-label={en.terrain.indicators}>
          <li data-body="sun" data-state={indicators.sunState}>
            ☀ {indicators.sun}
          </li>
          <li data-body="earth" data-state={indicators.earthState}>
            ⊕ {indicators.earth}
          </li>
        </ul>
      )}

      {phase === 'unavailable' && (
        <p className="globe-overlay globe-overlay--alert" role="alert">
          {en.globe.webglUnavailable}
        </p>
      )}
      {terrain.status === 'none' && (
        <p className="globe-overlay">{en.terrain.noSelection}</p>
      )}
      {terrain.status === 'loading' && (
        <p className="globe-overlay" role="status">
          {en.terrain.loading}
        </p>
      )}
      {terrain.status === 'unavailable' && (
        <div className="globe-overlay globe-overlay--warning" role="status">
          <p>{en.terrain.unavailable[terrain.gap]}</p>
          {terrain.gap === 'frame_mismatch' &&
            (onAdoptFrame && demFrame ? (
              <>
                <p className="small">{en.terrain.adoptFrameExplanation}</p>
                <button type="button" onClick={onAdoptFrame}>
                  {en.terrain.adoptFrame(demFrame)}
                </button>
              </>
            ) : (
              <p className="small">{en.terrain.catalogFrameRefusal}</p>
            ))}
        </div>
      )}
      {terrain.status === 'error' && (
        <div className="globe-overlay globe-overlay--alert" role="alert">
          <p>
            {en.terrain.error} {terrain.error.message}
          </p>
          <button type="button" onClick={onRetry}>
            {en.common.retry}
          </button>
        </div>
      )}

      {ready && phase === 'ready' && (
        <>
          <div className="terrain-toolbar" role="toolbar">
            {CAMERA_MODES.map((cameraMode) => (
              <button
                key={cameraMode}
                type="button"
                aria-pressed={mode === cameraMode}
                disabled={cameraMode === 'observer' && !sceneState.observer}
                onClick={() => chooseCamera(cameraMode)}
              >
                {en.terrain.camera[cameraMode]}
              </button>
            ))}
            <button
              type="button"
              onClick={() => {
                setMode('oblique')
                handleRef.current?.goToSite()
              }}
            >
              {en.terrain.goToSite}
            </button>
            <label className="terrain-exaggeration">
              <span>{en.terrain.exaggerationControl}</span>
              <select
                name="vertical-exaggeration"
                value={exaggeration}
                onChange={(event) =>
                  setExaggeration(Number(event.target.value))
                }
              >
                {EXAGGERATION_OPTIONS.map((value) => (
                  <option key={value} value={value}>
                    {value}×
                  </option>
                ))}
              </select>
            </label>
          </div>
          <p className="terrain-exaggeration-label" aria-live="polite">
            {en.terrain.exaggeration(exaggeration)}
          </p>

          <details className="terrain-info small" open>
            <summary>{en.terrain.details}</summary>
            {isRepresentative && (
              <p className="notice notice--warning">
                {en.terrain.representativeNote}
              </p>
            )}
            <p>
              {en.terrain.product(
                ready.manifest.source.product_id,
                ready.lodResolutionM,
                ready.manifest.calc_resolution_m,
              )}
            </p>
            <p>{en.terrain.frame(ready.manifest.frame_id)}</p>
            <p>
              {ready.sample.elevation_m === null
                ? en.terrain.observerUnknown
                : equipmentHeightM === null
                  ? en.terrain.observerNoHeight
                  : en.terrain.observer(
                      ready.sample.elevation_m,
                      equipmentHeightM,
                    )}
            </p>
            {bodies && !frameMatches && simulationFrame && (
              <p className="notice notice--warning">
                {en.terrain.frameMismatch(
                  simulationFrame,
                  ready.manifest.frame_id,
                )}
              </p>
            )}
            {undefinedAzimuth && (
              <p className="notice notice--info">
                {en.results.undefinedAzimuth}
              </p>
            )}
            {bodies && frameMatches && (
              <p>
                {en.terrain.bodies(
                  fmtDeg(bodies.sun.elevationDeg),
                  fmtDeg(bodies.earth.elevationDeg),
                )}
              </p>
            )}
            <p>{lighting}</p>
            <p>{en.terrain.shadows}</p>
            <ul className="legend">
              <li>
                <span className="swatch swatch--observer" />
                {en.terrain.legend.observer}
              </li>
              <li>
                <span className="swatch swatch--sun" />
                {en.terrain.legend.sun}
              </li>
              <li>
                <span className="swatch swatch--earth" />
                {en.terrain.legend.earth}
              </li>
              <li>
                <span className="swatch swatch--extent" />
                {en.terrain.legend.extent}
              </li>
              <li>
                <span className="swatch swatch--nodata" />
                {en.terrain.legend.noData(ready.mesh.noDataVertices)}
              </li>
            </ul>
          </details>
        </>
      )}
    </div>
  )
}
