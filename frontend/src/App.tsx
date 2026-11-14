// Main screen (docs/SPECIFICATIE.md §3.1): four zones — left catalog and parameters, centre 3D globe
// (default view), right active site and results, bottom time control. All numbers come from the API;
// the globe is visual only.

import { useCallback, useEffect, useMemo, useState } from 'react'
import { createApiDataSource, type DataSource } from './api/dataSource.ts'
import { describeError } from './api/errors.ts'
import { useSimulation } from './api/useSimulation.ts'
import { CatalogPanel } from './components/CatalogPanel.tsx'
import { GlobeView } from './components/GlobeView.tsx'
import { ParamsForm } from './components/ParamsForm.tsx'
import { ResultsPanel } from './components/ResultsPanel.tsx'
import { SiteSummary } from './components/SiteSummary.tsx'
import { TimeBar } from './components/TimeBar.tsx'
import type { Catalog, Coverage } from './contracts/generated.ts'
import { bodyDirectionScene } from './geo/globe.ts'
import type { GlobeFactory, GlobeState } from './globe/types.ts'
import { en } from './i18n/en.ts'
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
  now?: Date
  pollMs?: number
}

function App({ dataSource, globeFactory, now, pollMs }: AppProps) {
  const source = useMemo(
    () => dataSource ?? createApiDataSource(),
    [dataSource],
  )
  const [catalog, setCatalog] = useState<Loadable<Catalog>>({
    status: 'loading',
  })
  const [coverage, setCoverage] = useState<Loadable<Coverage>>({
    status: 'loading',
  })
  const [reloadToken, setReloadToken] = useState(0)
  const [selection, setSelection] = useState<Selection>(null)
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
      kind: 'catalog',
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
        <p className="mode-badge">{en.results.mode}</p>
      </header>

      <aside className="zone zone--left" aria-label={en.zones.catalog}>
        <CatalogPanel
          catalog={catalog}
          coverage={coverage}
          selectedSiteId={
            selection?.kind === 'catalog' ? selection.siteId : null
          }
          onSelectSite={selectSite}
          onSelectPoint={enterPoint}
          onShowCoverage={focusOn}
          onRetry={() => {
            setCatalog({ status: 'loading' })
            setCoverage({ status: 'loading' })
            setReloadToken((n) => n + 1)
          }}
        />
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
        <GlobeView
          state={globeState}
          textureUrl={source.globeTextureUrl}
          onPick={pickPoint}
          focusTarget={focusTarget}
          focusRequest={focusRequest}
          factory={globeFactory}
        />
      </main>

      <aside className="zone zone--right" aria-label={en.zones.summary}>
        <SiteSummary
          selection={selection}
          site={selectedSite}
          frameId={params.frameId}
        />
        <ResultsPanel
          view={view}
          result={result}
          index={safeIndex}
          stale={stale}
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
