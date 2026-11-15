// Visibility bands over the simulated interval (E10), drawn from the backend timelines: each body's
// visible / hidden / undetermined intervals partition the interval. The "both" row is the
// intersection (hidden as soon as one body is hidden; undetermined otherwise unless both are visible).
// The cursor follows the slider; refined event times are marked, never derived from the series.

import type { SimulationResult, StateInterval } from '../contracts/generated.ts'
import { parseUtc } from '../geo/utc.ts'
import { en } from '../i18n/en.ts'
import { fmtUtc } from '../ui/format.ts'

interface Props {
  result: SimulationResult
  index: number
}

type BandState = 'visible' | 'hidden' | 'unknown'
interface Span {
  start: number
  end: number
  state: BandState
}

function spans(timeline: StateInterval[]): Span[] {
  return timeline.map((interval) => ({
    start: parseUtc(interval.start_utc),
    end: parseUtc(interval.end_utc),
    state: interval.state,
  }))
}

function stateAt(list: Span[], t: number): BandState {
  const found = list.find((span) => span.start <= t && t < span.end)
  return (found ?? list[list.length - 1]).state
}

/** Both criteria: hidden if one body is hidden; visible if both are; otherwise undetermined. */
function combine(sun: Span[], earth: Span[]): Span[] {
  const cuts = [
    ...new Set([...sun, ...earth].flatMap((span) => [span.start, span.end])),
  ].sort((a, b) => a - b)
  const out: Span[] = []
  for (let k = 0; k + 1 < cuts.length; k++) {
    const t = cuts[k]
    const a = stateAt(sun, t)
    const b = stateAt(earth, t)
    const state: BandState =
      a === 'hidden' || b === 'hidden'
        ? 'hidden'
        : a === 'visible' && b === 'visible'
          ? 'visible'
          : 'unknown'
    const last = out[out.length - 1]
    if (last && last.state === state) last.end = cuts[k + 1]
    else out.push({ start: t, end: cuts[k + 1], state })
  }
  return out
}

export function TimeBands({ result, index }: Props) {
  const summary = result.summary[0]
  const series = result.series[0]
  const events = result.events[0]
  if (!summary || !series) return null
  const start = parseUtc(result.request.start_utc)
  const end = parseUtc(result.request.end_utc)
  const width = end - start
  const at = (t: number) => `${(((t - start) / width) * 100).toFixed(4)}%`
  const span = (a: number, b: number) =>
    `${(((b - a) / width) * 100).toFixed(4)}%`
  const sun = spans(summary.sun_timeline)
  const earth = spans(summary.earth_timeline)
  const rows: {
    key: 'sun' | 'earth' | 'both'
    label: string
    list: Span[]
  }[] = [
    { key: 'sun', label: en.bands.sun, list: sun },
    { key: 'earth', label: en.bands.earth, list: earth },
    { key: 'both', label: en.bands.both, list: combine(sun, earth) },
  ]
  const cursor = parseUtc(
    series.time_utc[Math.min(index, series.time_utc.length - 1)],
  )
  return (
    <div className="bands" aria-label={en.bands.heading}>
      {rows.map((row) => (
        <div key={row.key} className="bands-row">
          <span className="bands-label">{row.label}</span>
          <div
            className="bands-track"
            role="img"
            aria-label={en.bands.description(
              row.label,
              row.list.filter((s) => s.state === 'visible').length,
              row.list.filter((s) => s.state === 'unknown').length,
            )}
            data-band={row.key}
          >
            {row.list.map((item) => (
              <span
                key={`${row.key}-${item.start}`}
                className={`band band--${item.state} band--${row.key}`}
                style={{
                  left: at(item.start),
                  width: span(item.start, item.end),
                }}
                data-state={item.state}
                title={`${en.bands.states[item.state]}: ${fmtUtc(item.start)} – ${fmtUtc(item.end)}`}
              />
            ))}
            {row.key !== 'both' &&
              events?.[row.key].events.map((event) => (
                <span
                  key={`${row.key}-ev-${event.time_utc}`}
                  className={`band-event band-event--${event.type}`}
                  style={{ left: at(parseUtc(event.time_utc)) }}
                  title={`${en.results.eventTypes[event.type]} · ${fmtUtc(parseUtc(event.time_utc))}`}
                />
              ))}
            <span
              className="bands-cursor"
              style={{ left: at(cursor) }}
              aria-hidden="true"
            />
          </div>
        </div>
      ))}
      <p className="bands-legend small muted">
        <span className="band-key band--visible" /> {en.bands.states.visible}{' '}
        <span className="band-key band--hidden" /> {en.bands.states.hidden}{' '}
        <span className="band-key band--unknown" /> {en.bands.states.unknown} ·{' '}
        {en.results.reliefOnly}
      </p>
    </div>
  )
}
