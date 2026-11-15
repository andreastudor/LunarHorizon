// Right zone, bottom: Sun and Earth at the selected time, from the API result only. The card layout
// (text + glyph badges, never colour alone; "next event in …") is adapted from Nasa-moon
// (src/components/navigator/SunEarthCards.tsx, commit dcc3f0a5, MIT License, Kazi Ahammad Ullah).
// Undefined azimuth is shown as "Undefined"; unknown values are never shown as zero.

import type {
  BodyEvents,
  BodySeries,
  SimulationResult,
  SiteSummary,
} from '../contracts/generated.ts'
import type { SimulationView } from '../api/useSimulation.ts'
import { parseUtc } from '../geo/utc.ts'
import { en } from '../i18n/en.ts'
import { fmtDeg, fmtDuration, fmtKm, fmtPercent, fmtUtc } from '../ui/format.ts'
import { ElevationChart } from './ElevationChart.tsx'
import { SkyView } from './SkyView.tsx'

interface Props {
  view: SimulationView
  result: SimulationResult | null
  index: number
  stale: boolean
  /** The mode of the shown result, or the selected mode when there is no result yet. */
  terrainMode: 'dem' | 'idealized_local_plane'
}

export function ResultsPanel({
  view,
  result,
  index,
  stale,
  terrainMode,
}: Props) {
  return (
    <section
      className="panel"
      aria-labelledby="results-heading"
      aria-busy={view.phase === 'submitting' || view.phase === 'running'}
    >
      <h2 id="results-heading">{en.results.heading}</h2>
      <p className="mode-badge">
        {terrainMode === 'dem' ? en.results.modeDem : en.results.mode}
      </p>
      <p className="small muted">{en.results.reliefOnly}</p>
      <StatusLine view={view} hasResult={Boolean(result)} />
      {stale && result && (
        <p className="notice notice--warning" role="status">
          {en.params.stale}
        </p>
      )}
      {result && <ResultBody result={result} index={index} />}
    </section>
  )
}

function StatusLine({
  view,
  hasResult,
}: {
  view: SimulationView
  hasResult: boolean
}) {
  if (view.phase === 'failed') {
    return (
      <div className="notice notice--error" role="alert">
        <p>
          <strong>{en.errors.title}.</strong> {view.error.message}
        </p>
        {view.error.details.map((detail) => (
          <p key={detail} className="small">
            {detail}
          </p>
        ))}
        {view.error.code && (
          <p className="small muted">
            <code>{view.error.code}</code>
          </p>
        )}
      </div>
    )
  }
  if (view.phase === 'submitting') {
    return <p role="status">{en.results.queued}</p>
  }
  if (view.phase === 'running') {
    const percent = Math.round((view.progress?.completed_fraction ?? 0) * 100)
    return <p role="status">{en.results.running(percent)}</p>
  }
  if (!hasResult) return <p className="muted">{en.results.idle}</p>
  return null
}

function ResultBody({
  result,
  index,
}: {
  result: SimulationResult
  index: number
}) {
  const site = result.sites[0]
  const series = result.series.find((s) => s.site_ref === site.site_ref)
  const events = result.events.find((e) => e.site_ref === site.site_ref)
  const summary = result.summary.find((s) => s.site_ref === site.site_ref)
  const notComputed = result.quality.not_computed.filter(
    (entry) => entry.site_ref === site.site_ref,
  )
  if (!series) {
    return <p className="muted">{en.common.notComputed}</p>
  }
  const i = Math.min(Math.max(index, 0), series.time_utc.length - 1)
  const nowMs = parseUtc(series.time_utc[i])
  const sunAz = series.sun.azimuth_deg[i]
  const earthAz = series.earth.azimuth_deg[i]

  return (
    <>
      <p className="time-readout" aria-live="polite">
        {en.results.at(fmtUtc(nowMs))}
      </p>
      <Combination sun={series.sun.state[i]} earth={series.earth.state[i]} />
      <div className="cards">
        <BodyCard
          body="sun"
          series={series.sun}
          events={events?.sun ?? null}
          index={i}
          nowMs={nowMs}
          showTerrainHorizon={result.request.terrain_mode === 'dem'}
        />
        <BodyCard
          body="earth"
          series={series.earth}
          events={events?.earth ?? null}
          index={i}
          nowMs={nowMs}
          showTerrainHorizon={result.request.terrain_mode === 'dem'}
        />
      </div>
      {(sunAz === null || earthAz === null) && (
        <p className="notice notice--info">{en.results.undefinedAzimuth}</p>
      )}
      <SkyView
        sun={{ azimuthDeg: sunAz, elevationDeg: series.sun.elevation_deg[i] }}
        earth={{
          azimuthDeg: earthAz,
          elevationDeg: series.earth.elevation_deg[i],
        }}
      />
      <p className="muted small">{en.results.directions}</p>
      <ElevationChart series={series} index={i} />
      {notComputed.length > 0 && (
        <div className="notice notice--info">
          <p>{en.results.notComputedHeading}</p>
          <ul className="small">
            {notComputed.map((entry) => (
              <li key={entry.group}>
                <code>{entry.group}</code>: {entry.reason}
              </li>
            ))}
          </ul>
        </div>
      )}
      {summary && <Totals summary={summary} result={result} />}
      {events && <EventList sun={events.sun} earth={events.earth} />}
      <Provenance result={result} />
    </>
  )
}

function stateLabel(body: 'sun' | 'earth', state: string): string {
  return body === 'sun'
    ? (en.results.sunStates[state] ?? state)
    : (en.results.earthStates[state] ?? state)
}

/** The four combinations when both states are determined; a distinct state otherwise. */
function Combination({ sun, earth }: { sun: string; earth: string }) {
  const sunUp = sun === 'partially_visible' || sun === 'fully_visible'
  const earthUp = earth === 'visible'
  const known = sun !== 'undetermined' && earth !== 'undetermined'
  const text = known
    ? en.results.combination[
        `${sunUp ? 'v' : 'h'}${earthUp ? 'v' : 'h'}` as
          'vv' | 'vh' | 'hv' | 'hh'
      ]
    : en.results.combination.unknown(
        stateLabel('sun', sun),
        stateLabel('earth', earth),
      )
  return (
    <p
      className={`combination ${known ? '' : 'combination--unknown'}`}
      data-combination={
        known ? `${sunUp ? 'v' : 'h'}${earthUp ? 'v' : 'h'}` : 'unknown'
      }
      aria-live="polite"
    >
      <strong>{en.results.combination.heading}:</strong> {text}
    </p>
  )
}

/** Next event relative to the slider, from refined events only (never from the series). */
function nextEventText(
  body: 'sun' | 'earth',
  events: BodyEvents | null,
  state: string,
  nowMs: number,
): string {
  const name = body === 'sun' ? en.results.sun : en.results.earth
  const next = events?.events.find((event) => parseUtc(event.time_utc) > nowMs)
  const prefix =
    state === 'hidden' ? `${en.results.currentlyHidden(name)} ` : ''
  if (!next) {
    if (events?.status === 'unavailable' && events.reason)
      return prefix + en.results.eventUnavailable(events.reason)
    return prefix + en.results.noEventInInterval
  }
  const at = parseUtc(next.time_utc)
  const make =
    next.type === 'appearance'
      ? en.results.nextAppearance
      : next.type === 'disappearance'
        ? en.results.nextDisappearance
        : en.results.nextContact
  const window =
    next.quality === 'window'
      ? ` (${en.results.windowNote(
          fmtDuration(
            parseUtc(next.window_end_utc) - parseUtc(next.window_start_utc),
          ),
        )})`
      : ''
  return prefix + make(name, fmtDuration(at - nowMs), fmtUtc(at)) + window
}

function BodyCard({
  body,
  series,
  events,
  index,
  nowMs,
  showTerrainHorizon,
}: {
  body: 'sun' | 'earth'
  series: BodySeries
  events: BodyEvents | null
  index: number
  nowMs: number
  showTerrainHorizon: boolean
}) {
  const terrainHorizon = series.horizon_elevation_deg[index]
  const state = series.state[index]
  const reason = series.state_reason[index]
  const fraction = series.visible_fraction[index]
  const uncertainty = series.visible_uncertainty_fraction[index]
  const title = body === 'sun' ? en.results.sun : en.results.earth
  const tone =
    state === 'undetermined'
      ? 'status--unknown'
      : state === 'hidden'
        ? 'status--down'
        : 'status--up'
  const glyph =
    state === 'undetermined'
      ? '?'
      : state === 'hidden'
        ? '○'
        : state === 'partially_visible'
          ? '◐'
          : '●'
  return (
    <article className={`card card--${body}`} aria-label={title}>
      <header className="card-header">
        <h3>
          <span aria-hidden="true">{body === 'sun' ? '☀' : '⊕'}</span> {title}
        </h3>
        <span className={`status ${tone}`} data-state={state}>
          <span aria-hidden="true">{glyph}</span> {stateLabel(body, state)}
        </span>
      </header>
      {reason && (
        <p className="small">{en.results.reasons[reason] ?? reason}</p>
      )}
      {body === 'sun' && fraction !== null && state !== 'hidden' && (
        <p className="small" data-fraction={fraction}>
          {en.results.fraction(
            fmtPercent(fraction),
            fmtPercent(uncertainty ?? 0),
          )}
        </p>
      )}
      <dl className="readouts">
        <dt>{en.results.elevation}</dt>
        <dd className="big">{fmtDeg(series.elevation_deg[index], 2)}</dd>
        <dt>{en.results.azimuth}</dt>
        <dd>{fmtDeg(series.azimuth_deg[index], 2)}</dd>
        <dt>{en.results.distance}</dt>
        <dd>{fmtKm(series.distance_km[index])}</dd>
        {showTerrainHorizon && (
          <>
            <dt>{en.results.terrainHorizon}</dt>
            <dd>
              {terrainHorizon === null
                ? en.common.unknown
                : fmtDeg(terrainHorizon, 2)}
            </dd>
          </>
        )}
      </dl>
      <p className="small next-event">
        {nextEventText(body, events, state, nowMs)}
      </p>
      <p className="small muted">
        {body === 'sun' ? en.results.fractionNote : en.results.earthNote}
      </p>
    </article>
  )
}

function Totals({
  summary,
  result,
}: {
  summary: SiteSummary
  result: SimulationResult
}) {
  const totalS =
    (parseUtc(result.request.end_utc) - parseUtc(result.request.start_utc)) /
    1000
  const duration = (seconds: number | null) =>
    seconds === null
      ? en.common.unknown
      : `${fmtDuration(seconds * 1000)} · ${fmtPercent(totalS > 0 ? seconds / totalS : null)}`
  return (
    <>
      <h3>{en.results.summary}</h3>
      <dl className="facts">
        <dt>{en.results.sunTotal}</dt>
        <dd>{duration(summary.sun_visible_duration_s)}</dd>
        <dt>{en.results.earthTotal}</dt>
        <dd>{duration(summary.earth_visible_duration_s)}</dd>
        <dt>{en.results.bothTotal}</dt>
        <dd>{duration(summary.both_visible_duration_s)}</dd>
        <dt>{en.results.sunUnknown}</dt>
        <dd>{duration(summary.sun_unknown_duration_s)}</dd>
        <dt>{en.results.earthUnknown}</dt>
        <dd>{duration(summary.earth_unknown_duration_s)}</dd>
        <dt>{en.results.bothUnknown}</dt>
        <dd>{duration(summary.both_unknown_duration_s)}</dd>
      </dl>
    </>
  )
}

function EventList({ sun, earth }: { sun: BodyEvents; earth: BodyEvents }) {
  const all = [...sun.events, ...earth.events].sort(
    (a, b) => parseUtc(a.time_utc) - parseUtc(b.time_utc),
  )
  return (
    <details className="details">
      <summary>
        {en.results.events} ({all.length})
      </summary>
      {all.length === 0 ? (
        <p className="muted">{en.results.noEvents}</p>
      ) : (
        <ul className="plain-list small">
          {all.map((event) => (
            <li key={`${event.body}-${event.time_utc}`}>
              {fmtUtc(parseUtc(event.time_utc))} —{' '}
              {event.body === 'sun' ? en.results.sun : en.results.earth}{' '}
              {en.results.eventTypes[event.type]} (az{' '}
              {fmtDeg(event.azimuth_deg)})
              {event.quality === 'window' &&
                ` — ${en.results.windowNote(
                  fmtDuration(
                    parseUtc(event.window_end_utc) -
                      parseUtc(event.window_start_utc),
                  ),
                )}`}
            </li>
          ))}
        </ul>
      )}
    </details>
  )
}

function Provenance({ result }: { result: SimulationResult }) {
  const { provenance, quality } = result
  return (
    <details className="details">
      <summary>{en.quality.heading}</summary>
      <dl className="facts small">
        <dt>{en.quality.kernelProfile}</dt>
        <dd>
          <code>{provenance.kernel_profile.profile_id}</code> (
          {provenance.kernel_profile.files.map((f) => f.filename).join(', ')})
        </dd>
        <dt>{en.quality.frame}</dt>
        <dd>
          <code>{provenance.frame_id}</code>
        </dd>
        <dt>{en.quality.correction}</dt>
        <dd>
          <code>{provenance.aberration_correction}</code>
        </dd>
        <dt>{en.quality.computedAt}</dt>
        <dd>{fmtUtc(parseUtc(provenance.computed_at_utc))}</dd>
        <dt>{en.quality.appVersion}</dt>
        <dd>{provenance.app_version}</dd>
      </dl>
      <h4>{en.quality.approximations}</h4>
      <ul className="small">
        {quality.approximations.map((text) => (
          <li key={text}>{text}</li>
        ))}
      </ul>
      <h4>{en.quality.limits}</h4>
      <ul className="small">
        {quality.limits.map((text) => (
          <li key={text}>{text}</li>
        ))}
      </ul>
      {quality.issues.length > 0 && (
        <>
          <h4>{en.quality.issues}</h4>
          <ul className="small">
            {quality.issues.map((issue) => (
              <li key={`${issue.code}-${issue.site_ref}-${issue.field}`}>
                {en.quality.issueMessages[issue.message_key] ?? issue.code}
                {issue.field && (
                  <>
                    {' '}
                    (<code>{issue.field}</code>)
                  </>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </details>
  )
}
