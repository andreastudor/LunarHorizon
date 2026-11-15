import { useEffect, useRef, useState } from 'react'
import Map from 'ol/Map.js'
import View from 'ol/View.js'
import Feature from 'ol/Feature.js'
import Point from 'ol/geom/Point.js'
import LineString from 'ol/geom/LineString.js'
import VectorSource from 'ol/source/Vector.js'
import VectorLayer from 'ol/layer/Vector.js'
import ImageLayer from 'ol/layer/Image.js'
import ImageStatic from 'ol/source/ImageStatic.js'
import { Circle, Fill, Stroke, Style } from 'ol/style.js'
import 'ol/ol.css'
import { lunarGeographic, lunarPolar, toPolar, fromPolar } from '../geo/map.ts'
import type { GlobeState } from '../globe/types.ts'
import { en } from '../i18n/en.ts'

export function MapView({
  state,
  textureUrl,
  onPick,
  onSite,
  focusTarget,
}: {
  state: GlobeState
  textureUrl: string
  onPick: (lat: number, lon: number) => void
  onSite: (id: string) => void
  focusTarget: { latitudeDeg: number; longitudeDeg: number } | null
}) {
  const container = useRef<HTMLDivElement>(null)
  const handle = useRef<Map | null>(null)
  const vector = useRef(new VectorSource())
  const callbacks = useRef({ onPick, onSite })
  useEffect(() => {
    callbacks.current = { onPick, onSite }
  }, [onPick, onSite])
  const [requestedMode, setMode] = useState<'polar' | 'global'>('polar')
  const mode =
    focusTarget && focusTarget.latitudeDeg > -60 ? 'global' : requestedMode
  const [imageError, setImageError] = useState(false)
  useEffect(() => {
    if (!container.current) return
    const image = new ImageStatic({
      url: textureUrl,
      crossOrigin: 'anonymous',
      projection: lunarGeographic,
      imageExtent: [-180, -90, 180, 90],
    })
    image.on('imageloaderror', () => setImageError(true))
    image.on('imageloadend', () => setImageError(false))
    const map = new Map({
      target: container.current,
      layers: [
        new ImageLayer({ source: image }),
        new VectorLayer({ source: vector.current }),
      ],
      view: new View({
        projection: mode === 'polar' ? lunarPolar : lunarGeographic,
        center: mode === 'polar' ? [0, 0] : [0, -30],
        resolution: mode === 'polar' ? 1800 : 0.5,
        minResolution: mode === 'polar' ? 2 : 0.0001,
      }),
    })
    handle.current = map
    map.on('singleclick', (event) => {
      const hit = map.forEachFeatureAtPixel(
        event.pixel,
        (f) => f.get('siteId') as string | undefined,
        { hitTolerance: 8 },
      )
      if (hit && hit !== 'custom') {
        callbacks.current.onSite(hit)
        return
      }
      const [lon, lat] =
        mode === 'polar' ? fromPolar(event.coordinate) : event.coordinate
      if (lat >= -90 && lat <= 90)
        callbacks.current.onPick(lat, ((((lon + 180) % 360) + 360) % 360) - 180)
    })
    const resize = new ResizeObserver(() => map.updateSize())
    resize.observe(container.current)
    return () => {
      resize.disconnect()
      map.setTarget(undefined)
      map.dispose()
      handle.current = null
    }
  }, [mode, textureUrl])
  useEffect(() => {
    const xy = (lon: number, lat: number) =>
      mode === 'polar' ? toPolar([lon, lat]) : [lon, lat]
    vector.current.clear()
    for (const marker of state.markers) {
      if (mode === 'polar' && marker.latitudeDeg > -60) continue
      const feature = new Feature({
        geometry: new Point(xy(marker.longitudeDeg, marker.latitudeDeg)),
        siteId: marker.id,
      })
      feature.setStyle(
        new Style({
          image: new Circle({
            radius: marker.selected ? 8 : 5,
            fill: new Fill({
              color: marker.selected
                ? '#fb923c'
                : marker.kind === 'dem_point'
                  ? '#a78bfa'
                  : '#38bdf8',
            }),
            stroke: new Stroke({ color: '#fff', width: 1 }),
          }),
        }),
      )
      vector.current.addFeature(feature)
    }
    for (const coverage of state.coverage) {
      // Split at the antimeridian in geographic view; never draw a world-spanning chord.
      let part: number[][] = []
      const flush = () => {
        if (part.length > 1) {
          const f = new Feature(new LineString(part))
          f.setStyle(
            new Style({ stroke: new Stroke({ color: '#34d399', width: 2 }) }),
          )
          vector.current.addFeature(f)
        }
        part = []
      }
      for (const p of coverage.ring) {
        if (
          mode === 'global' &&
          part.length &&
          Math.abs(p[0] - part[part.length - 1][0]) > 180
        )
          flush()
        part.push(xy(p[0], p[1]))
      }
      flush()
    }
  }, [state, mode])
  useEffect(() => {
    if (!focusTarget) return
    if (mode === 'polar' && focusTarget.latitudeDeg > -60) {
      return
    }
    handle.current
      ?.getView()
      .setCenter(
        mode === 'polar'
          ? toPolar([focusTarget.longitudeDeg, focusTarget.latitudeDeg])
          : [focusTarget.longitudeDeg, focusTarget.latitudeDeg],
      )
  }, [focusTarget, mode])
  return (
    <section className="map-view">
      <div className="system-tools">
        <button
          aria-pressed={mode === 'polar'}
          onClick={() => setMode('polar')}
        >
          {en.map.polar}
        </button>
        <button
          aria-pressed={mode === 'global'}
          onClick={() => setMode('global')}
        >
          {en.map.global}
        </button>
      </div>
      <p className="small">{en.map.convention}</p>
      {imageError && <p role="status">{en.globe.textureMissing}</p>}
      <div
        ref={container}
        className="map-canvas"
        role="region"
        aria-label={en.map.title}
      />
      <p className="small">
        {en.map.legend} · {en.credits.texture}
      </p>
    </section>
  )
}
