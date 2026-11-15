// Main screen (docs/SPECIFICATIE.md §3.1): four zones — left catalog and parameters, centre 3D globe
// (default view), right active site and results, bottom time control. All numbers come from the API;
// the globe is visual only.

import { useCallback, useEffect, useMemo, useState } from 'react'
import { createApiDataSource, type DataSource } from './api/dataSource.ts'
import { describeError } from './api/errors.ts'
import { useLocalTerrain } from './api/useLocalTerrain.ts'
import { useHorizonProfile } from './api/useHorizonProfile.ts'
import { useSimulation } from './api/useSimulation.ts'
import { CatalogPanel } from './components/CatalogPanel.tsx'
import { GlobeView } from './components/GlobeView.tsx'
import { HorizonChart } from './components/HorizonChart.tsx'
import { LocalTerrainView } from './components/LocalTerrainView.tsx'
import { ParamsForm } from './components/ParamsForm.tsx'
import { ResultsPanel } from './components/ResultsPanel.tsx'
import { SiteSummary } from './components/SiteSummary.tsx'
import { TimeBands } from './components/TimeBands.tsx'
import { TimeBar } from './components/TimeBar.tsx'
import type { Catalog, Coverage } from './contracts/generated.ts'
import { bodyDirectionScene } from './geo/globe.ts'
import type { GlobeFactory, GlobeState, TerrainFactory } from './globe/types.ts'
import { en } from './i18n/en.ts'
import { fmtPercent, fmtUtc } from './ui/format.ts'
import { parseUtc } from './geo/utc.ts'
import {
  buildRequest,
  defaultParams,
  requestDiffers,
  selectionKey,
} from './state/model.ts'
import type { Loadable, Selection, SimulationParams } from './state/types.ts'

export interface AppProps {
  dataSource?: DataSource
  globeFactory?: GlobeFactory
  terrainFactory?: TerrainFactory
  now?: Date
  pollMs?: number
}

function App({
  dataSource,
  globeFactory,
  terrainFactory,
  now,
  pollMs,
}: AppProps) {
  const source = useMemo(
    () => dataSource ?? createApiDataSource(),
    [dataSource],
  )
  const [catalog, setCatalog] = useState<Loadable<Catalog>>({
    status: 'loading',
  })
  const [terrainStatuses, setTerrainStatuses] = useState<
    Record<string, string>
  >({})
  // The frame declared by the registered DEM products, when they all declare the same one.
  const [demFrame, setDemFrame] = useState<string | null>(null)
  const [coverage, setCoverage] = useState<Loadable<Coverage>>({
    status: 'loading',
  })
  const [reloadToken, setReloadToken] = useState(0)
  const [selection, setSelection] = useState<Selection>(null)
  const [centerView, setCenterView] = useState<'globe' | 'terrain' | 'horizon'>(
    'globe',
  )
  const [horizonReload, setHorizonReload] = useState(0)
  const [terrainReload, setTerrainReload] = useState(0)
  const [frameNote, setFrameNote] = useState<string | null>(null)
  const [params, setParams] = useState<SimulationParams>(() =>
    defaultParams(now ?? new Date()),
  )
  const [showErrors, setShowErrors] = useState(false)
  const [index, setIndex] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [focusRequest, setFocusRequest] = useState<{
    latitudeDeg: number
    longitudeDeg: number
    nonce: number
  } | null>(null)
  const simulation = useSimulation(source, pollMs)
  const { cancel, start } = simulation

  useEffect(() => {
    const controller = new AbortController()
    source
      .sites(controller.signal)
      .then((data) => setCatalog({ status: 'ready', data }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted)
          setCatalog({ status: 'error', error: describeError(error) })
      })
    source
      .terrainStatus(controller.signal)
      .then((report) => {
        setTerrainStatuses(
          Object.fromEntries(report.sites.map((s) => [s.site_id, s.status])),
        )
        const frames = new Set(report.products.map((p) => p.frame_id))
        setDemFrame(frames.size === 1 ? [...frames][0] : null)
      })
      .catch(() => {
        // Badges are omitted when the status report is unavailable; selection still works.
      })
    source
      .coverage(controller.signal)
      .then((data) => setCoverage({ status: 'ready', data }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted)
          setCoverage({ status: 'error', error: describeError(error) })
      })
    return () => controller.abort()
  }, [source, reloadToken])

  const sites = useMemo(
    () => (catalog.status === 'ready' ? catalog.data.sites : []),
    [catalog],
  )
  const selectedSite =
    selection?.kind === 'catalog'
      ? (sites.find((site) => site.id === selection.siteId) ?? null)
      : null
  const key = selectionKey(selection)
  const view = simulation.view
  const result = view.phase === 'done' && view.key === key ? view.result : null
  const built = buildRequest(selection, params)
  const stale = result ? requestDiffers(built.request, result.request) : false
  const series = result
    ? (result.series.find((s) => s.site_ref === result.sites[0].site_ref) ??
      null)
    : null
  const safeIndex = series ? Math.min(index, series.time_utc.length - 1) : 0

  const terrainPoint = useMemo(() => {
    if (selection?.kind === 'custom')
      return {
        latitudeDeg: selection.latitudeDeg,
        longitudeDeg: selection.longitudeDeg,
      }
    if (selection?.kind === 'catalog' && selectedSite)
      return {
        latitudeDeg: selectedSite.latitude_deg,
        longitudeDeg: selectedSite.longitude_deg,
      }
    return null
  }, [selection, selectedSite])
  // Catalog sites use the frame they are declared in; user points use the selected frame.
  const terrainFrameId =
    selection?.kind === 'catalog'
      ? (selectedSite?.frame_id ?? null)
      : selection?.kind === 'custom'
        ? params.frameId
        : null
  const localTerrain = useLocalTerrain(
    source,
    terrainPoint,
    terrainFrameId,
    terrainReload,
  )
  const bodies = useMemo(() => {
    if (!series) return null
    return {
      sun: {
        azimuthDeg: series.sun.azimuth_deg[safeIndex],
        elevationDeg: series.sun.elevation_deg[safeIndex],
      },
      earth: {
        azimuthDeg: series.earth.azimuth_deg[safeIndex],
        elevationDeg: series.earth.elevation_deg[safeIndex],
      },
      timeLabel: fmtUtc(parseUtc(series.time_utc[safeIndex])),
    }
  }, [series, safeIndex])
  // Computed states at the slider time (backend result), shown in the local 3D scene.
  const indicators = useMemo(() => {
    if (!series) return null
    const sunState = series.sun.state[safeIndex]
    const earthState = series.earth.state[safeIndex]
    const fraction = series.sun.visible_fraction[safeIndex]
    const sunText =
      (en.results.sunStates[sunState] ?? sunState) +
      (sunState === 'partially_visible' && fraction !== null
        ? ` (${fmtPercent(fraction)})`
        : '')
    return {
      sun: `${en.results.sun}: ${sunText}`,
      earth: `${en.results.earth}: ${en.results.earthStates[earthState] ?? earthState}`,
      sunState,
      earthState,
    }
  }, [series, safeIndex])
  const parsedHeight = Number(params.observerHeightM)
  const equipmentHeightM = result
    ? result.request.observer_height_m
    : params.observerHeightM.trim() !== '' &&
        Number.isFinite(parsedHeight) &&
        parsedHeight >= 0
      ? parsedHeight
      : null

  // Loaded only while the Horizon view is open (no preloading).
  const horizon = useHorizonProfile(
    source,
    terrainPoint?.latitudeDeg ?? null,
    terrainPoint?.longitudeDeg ?? null,
    terrainFrameId,
    equipmentHeightM,
    centerView === 'horizon',
    horizonReload,
  )

  const focusOn = useCallback((latitudeDeg: number, longitudeDeg: number) => {
    setFocusRequest((previous) => ({
      latitudeDeg,
      longitudeDeg,
      nonce: (previous?.nonce ?? 0) + 1,
    }))
  }, [])

  const select = useCallback(
    (next: Selection) => {
      // A different selection makes any running or finished simulation obsolete.
      cancel()
      setIndex(0)
      setPlaying(false)
      setSelection(next)
    },
    [cancel],
  )

  const selectSite = (siteId: string) => {
    const site = sites.find((s) => s.id === siteId)
    if (!site) return
    // The request uses the frame in which the catalog position is declared (no conversion).
    setParams((previous) => ({ ...previous, frameId: site.frame_id }))
    select({ kind: 'catalog', siteId })
    focusOn(site.latitude_deg, site.longitude_deg)
  }

  const pickPoint = useCallback(
    (latitudeDeg: number, longitudeDeg: number) =>
      select({
        kind: 'custom',
        label: en.point.defaultLabel,
        latitudeDeg,
        longitudeDeg,
      }),
    [select],
  )

  // A point chosen on the local terrain or the product's representative point: the request adopts
  // the frame declared by the DEM product (a working hypothesis, shown to the user), so the scene
  // and the Sun/Earth directions use the same frame. No coordinates are converted.
  const selectTerrainPoint = useCallback(
    (
      latitudeDeg: number,
      longitudeDeg: number,
      label: string,
      frameId: string,
    ) => {
      if (frameId === 'MOON_ME_DE440_ME421' || frameId === 'MOON_ME_DE421') {
        setParams((previous) =>
          previous.frameId === frameId ? previous : { ...previous, frameId },
        )
        setFrameNote(en.coverage.frameNotes.demPoint(frameId))
      }
      select({ kind: 'custom', label, latitudeDeg, longitudeDeg })
    },
    [select],
  )

  const adoptRepresentative = async (
    latitudeDeg: number,
    longitudeDeg: number,
  ) => {
    try {
      const manifest = await source.terrainManifest(
        latitudeDeg,
        longitudeDeg,
        null,
      )
      // Prefer the catalog entry of this DEM representative point: it keeps its provenance.
      const origin = manifest.local_origin
      const catalogPoint = sites.find(
        (site) =>
          site.position_kind === 'representative_point' &&
          Math.abs(site.latitude_deg - origin.latitude_deg) < 1e-9 &&
          Math.abs(site.longitude_deg - origin.longitude_deg) < 1e-9,
      )
      if (catalogPoint) {
        selectSite(catalogPoint.id)
      } else {
        selectTerrainPoint(
          origin.latitude_deg,
          origin.longitude_deg,
          en.terrain.representativeFallback(manifest.terrain_id),
          manifest.frame_id,
        )
      }
      setCenterView('terrain')
    } catch (error) {
      setFrameNote(describeError(error).message)
    }
  }

  const enterPoint = (
    latitudeDeg: number,
    longitudeDeg: number,
    label: string,
  ) => {
    select({ kind: 'custom', label, latitudeDeg, longitudeDeg })
    focusOn(latitudeDeg, longitudeDeg)
  }

  const run = () => {
    setShowErrors(true)
    if (!built.request) return
    setIndex(0)
    setPlaying(false)
    void start(built.request, key)
  }

  const globeState = useMemo<GlobeState>(() => {
    const markers: GlobeState['markers'] = sites.map((site) => ({
      id: site.id,
      latitudeDeg: site.latitude_deg,
      longitudeDeg: site.longitude_deg,
      kind:
        site.position_kind === 'representative_point' ? 'dem_point' : 'catalog',
      selected: selection?.kind === 'catalog' && selection.siteId === site.id,
    }))
    if (selection?.kind === 'custom') {
      markers.push({
        id: 'custom',
        latitudeDeg: selection.latitudeDeg,
        longitudeDeg: selection.longitudeDeg,
        kind: 'custom',
        selected: true,
      })
    }
    const coverageRings =
      coverage.status === 'ready'
        ? coverage.data.terrain
            .filter((product) => product.footprint)
            .map((product) => ({
              id: product.product_id,
              ring: product.footprint?.coordinates[0] ?? [],
            }))
        : []
    let directions: GlobeState['directions'] = null
    if (result && series) {
      const site = result.sites[0]
      directions = {
        latitudeDeg: site.latitude_deg,
        longitudeDeg: site.longitude_deg,
        sun: bodyDirectionScene(
          series.sun.azimuth_deg[safeIndex],
          series.sun.elevation_deg[safeIndex],
          site.latitude_deg,
          site.longitude_deg,
        ),
        earth: bodyDirectionScene(
          series.earth.azimuth_deg[safeIndex],
          series.earth.elevation_deg[safeIndex],
          site.latitude_deg,
          site.longitude_deg,
        ),
      }
    }
    return { markers, coverage: coverageRings, directions }
  }, [sites, selection, coverage, result, series, safeIndex])

  const focusTarget =
    selection?.kind === 'custom'
      ? selection
      : selectedSite
        ? {
            latitudeDeg: selectedSite.latitude_deg,
            longitudeDeg: selectedSite.longitude_deg,
          }
        : null
  const running = view.phase === 'submitting' || view.phase === 'running'

  return (
    <div className="layout">
      <header className="topbar">
        <div>
          <h1>{en.app.title}</h1>
          <p className="tagline">{en.app.tagline}</p>
        </div>
        <p className="mode-badge">
          {params.terrainMode === 'dem' ? en.results.modeDem : en.results.mode}
        </p>
      </header>

      <aside className="zone zone--left" aria-label={en.zones.catalog}>
        <CatalogPanel
          terrainStatuses={terrainStatuses}
          catalog={catalog}
          coverage={coverage}
          selectedSiteId={
            selection?.kind === 'catalog' ? selection.siteId : null
          }
          onSelectSite={selectSite}
          onSelectPoint={enterPoint}
          onShowCoverage={(latitudeDeg, longitudeDeg) => {
            setCenterView('globe')
            focusOn(latitudeDeg, longitudeDeg)
          }}
          onUseRepresentative={(latitudeDeg, longitudeDeg) =>
            void adoptRepresentative(latitudeDeg, longitudeDeg)
          }
          onRetry={() => {
            setCatalog({ status: 'loading' })
            setCoverage({ status: 'loading' })
            setReloadToken((n) => n + 1)
          }}
        />
        {frameNote && (
          <p className="notice notice--info small" role="status">
            {frameNote}
          </p>
        )}
        <ParamsForm
          params={params}
          errors={built.errors}
          showErrors={showErrors}
          canRun={Boolean(built.request) && !running}
          running={running}
          hasSelection={selection !== null}
          onChange={setParams}
          onRun={run}
        />
      </aside>

      <main className="zone zone--center" aria-label={en.zones.globe}>
        <div className="view-tabs" role="tablist" aria-label={en.views.label}>
          <button
            type="button"
            role="tab"
            aria-selected={centerView === 'globe'}
            onClick={() => setCenterView('globe')}
          >
            {en.views.globe}
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={centerView === 'terrain'}
            onClick={() => setCenterView('terrain')}
          >
            {localTerrain.status === 'unavailable'
              ? en.views.terrainUnavailable
              : en.views.terrain}
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={centerView === 'horizon'}
            onClick={() => setCenterView('horizon')}
          >
            {en.views.horizon}
          </button>
        </div>
        {/* One WebGL renderer at a time: the inactive view is unmounted and its GPU resources freed. */}
        <div className="view-panel" role="tabpanel">
          {centerView === 'horizon' ? (
            <HorizonChart
              state={horizon}
              hasPoint={terrainPoint !== null}
              hasHeight={equipmentHeightM !== null}
              bodies={bodies}
              simulationFrame={result ? result.request.frame_id : null}
              onRetry={() => setHorizonReload((n) => n + 1)}
            />
          ) : centerView === 'globe' ? (
            <GlobeView
              state={globeState}
              textureUrl={source.globeTextureUrl}
              onPick={pickPoint}
              focusTarget={focusTarget}
              focusRequest={focusRequest}
              factory={globeFactory}
            />
          ) : (
            <LocalTerrainView
              terrain={localTerrain}
              point={terrainPoint}
              equipmentHeightM={equipmentHeightM}
              bodies={bodies}
              simulationFrame={result ? result.request.frame_id : null}
              onPick={(latitudeDeg, longitudeDeg) =>
                selectTerrainPoint(
                  latitudeDeg,
                  longitudeDeg,
                  en.point.defaultLabel,
                  localTerrain.status === 'ready'
                    ? localTerrain.manifest.frame_id
                    : params.frameId,
                )
              }
              onRetry={() => setTerrainReload((n) => n + 1)}
              demFrame={demFrame}
              resultMode={result ? result.request.terrain_mode : null}
              indicators={indicators}
              onAdoptFrame={
                // Only a user point may be re-interpreted (never converted); catalog positions
                // keep the frame of their source and stay refused.
                selection?.kind === 'custom' && demFrame
                  ? () => {
                      setParams((previous) => ({
                        ...previous,
                        frameId: demFrame as SimulationParams['frameId'],
                      }))
                      setFrameNote(
                        en.coverage.frameNotes.reinterpreted(demFrame),
                      )
                    }
                  : undefined
              }
              factory={terrainFactory}
            />
          )}
        </div>
      </main>

      <aside className="zone zone--right" aria-label={en.zones.summary}>
        <SiteSummary
          selection={selection}
          site={selectedSite}
          frameId={params.frameId}
          terrainStatus={
            localTerrain.status === 'unavailable'
              ? localTerrain.gap
              : localTerrain.status
          }
        />
        <ResultsPanel
          view={view}
          result={result}
          index={safeIndex}
          stale={stale}
          terrainMode={
            result ? result.request.terrain_mode : params.terrainMode
          }
        />
      </aside>

      <section className="zone zone--bottom" aria-label={en.zones.time}>
        <TimeBar
          series={series}
          index={safeIndex}
          playing={playing}
          onIndex={setIndex}
          onPlaying={setPlaying}
        />
        {result && <TimeBands result={result} index={safeIndex} />}
      </section>

      <footer className="credits small">
        <span>{en.credits.texture}</span>
        <span>{en.credits.ephemerides}</span>
        <span>{en.credits.design}</span>
        <span>{en.app.independent}</span>
      </footer>
    </div>
  )
}

export default App
