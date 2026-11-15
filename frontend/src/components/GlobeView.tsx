// Thin React wrapper around the imperative globe controller. The Three.js module is loaded lazily, so
// the first paint and the tests do not depend on it; a factory can be injected for tests.

import { useEffect, useRef, useState } from 'react'
import { en } from '../i18n/en.ts'
import {
  WebGLUnavailableError,
  type GlobeFactory,
  type GlobeHandle,
  type GlobeState,
} from '../globe/types.ts'

type Phase = 'loading' | 'ready' | 'unavailable'

const loadDefaultFactory = async (): Promise<GlobeFactory> =>
  (await import('../globe/threeGlobe.ts')).createThreeGlobe

interface Props {
  state: GlobeState
  textureUrl: string
  onPick: (latitudeDeg: number, longitudeDeg: number) => void
  focusTarget: { latitudeDeg: number; longitudeDeg: number } | null
  /** Moves the camera when the nonce changes (catalog selection, "Show on globe"). */
  focusRequest: {
    latitudeDeg: number
    longitudeDeg: number
    nonce: number
  } | null
  factory?: GlobeFactory
  onUnavailable?: () => void
}

export function GlobeView({
  state,
  textureUrl,
  onPick,
  focusTarget,
  focusRequest,
  factory,
  onUnavailable,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const handleRef = useRef<GlobeHandle | null>(null)
  const pickRef = useRef(onPick)
  const stateRef = useRef(state)
  const [phase, setPhase] = useState<Phase>('loading')
  const [textureMissing, setTextureMissing] = useState(false)

  useEffect(() => {
    pickRef.current = onPick
  }, [onPick])

  useEffect(() => {
    stateRef.current = state
    handleRef.current?.update(state)
  }, [state])

  useEffect(() => {
    if (focusRequest && phase === 'ready') {
      handleRef.current?.focus(
        focusRequest.latitudeDeg,
        focusRequest.longitudeDeg,
      )
    }
  }, [focusRequest, phase])

  useEffect(() => {
    let disposed = false
    const container = containerRef.current
    if (!container) return
    const create = async () => {
      try {
        const make = factory ?? (await loadDefaultFactory())
        if (disposed) return
        const handle = make(container, {
          textureUrl,
          onPick: (lat, lon) => pickRef.current(lat, lon),
          onTextureError: () => setTextureMissing(true),
        })
        handleRef.current = handle
        handle.update(stateRef.current)
        setPhase('ready')
      } catch (error) {
        if (disposed) return
        if (!(error instanceof WebGLUnavailableError)) console.error(error)
        setPhase('unavailable')
        onUnavailable?.()
      }
    }
    void create()
    return () => {
      disposed = true
      handleRef.current?.dispose()
      handleRef.current = null
    }
  }, [factory, textureUrl, onUnavailable])

  return (
    <div className="globe">
      <div
        ref={containerRef}
        className="globe-canvas"
        role="img"
        aria-label={en.globe.label}
      />
      {phase === 'loading' && (
        <p className="globe-overlay" role="status">
          {en.globe.loading}
        </p>
      )}
      {phase === 'unavailable' && (
        <p className="globe-overlay globe-overlay--alert" role="alert">
          {en.globe.webglUnavailable}
        </p>
      )}
      {phase === 'ready' && (
        <>
          <div className="globe-toolbar">
            <button
              type="button"
              onClick={() => handleRef.current?.resetCamera()}
            >
              {en.globe.resetCamera}
            </button>
            <button
              type="button"
              disabled={!focusTarget}
              onClick={() =>
                focusTarget &&
                handleRef.current?.focus(
                  focusTarget.latitudeDeg,
                  focusTarget.longitudeDeg,
                )
              }
            >
              {en.globe.focusSelection}
            </button>
          </div>
          <ul className="globe-legend small" aria-label="Legend">
            <li>
              <span className="swatch swatch--catalog" />
              {en.globe.legend.catalog}
            </li>
            <li>
              <span className="swatch swatch--dem-point" />
              {en.globe.legend.demPoint}
            </li>
            <li>
              <span className="swatch swatch--observer" />
              {en.globe.legend.custom}
            </li>
            <li>
              <span className="swatch swatch--selected" />
              {en.globe.legend.selected}
            </li>
          </ul>
          <p className="globe-lod">{en.globe.lod}</p>
          {textureMissing && (
            <p className="globe-overlay globe-overlay--warning" role="status">
              {en.globe.textureMissing}
            </p>
          )}
        </>
      )}
    </div>
  )
}
