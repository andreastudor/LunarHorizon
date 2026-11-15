import type { SimulationResult } from '../contracts/generated.ts'
import { resultForSite } from '../state/comparison.ts'
import { ElevationChart } from './ElevationChart.tsx'
import { TimeBands } from './TimeBands.tsx'
import { en } from '../i18n/en.ts'
import { fmtDuration, fmtPercent, fmtDeg } from '../ui/format.ts'

const colours = ['#38bdf8', '#fb923c', '#a78bfa', '#34d399']
export function ComparisonPanel({
  result,
  index,
  active,
  onActive,
  stale,
}: {
  result: SimulationResult
  index: number
  active: number
  onActive: (i: number) => void
  stale: boolean
}) {
  const values = result.series
    .flatMap((s) => [
      s.sun.elevation_deg,
      s.earth.elevation_deg,
      s.sun.horizon_elevation_deg,
      s.earth.horizon_elevation_deg,
    ])
    .flat()
    .filter((v): v is number => v !== null)
  const domain: [number, number] = values.reduce(
    ([low, high], v) => [
      Math.min(low, Math.floor(v)),
      Math.max(high, Math.ceil(v)),
    ],
    [-1, 1],
  )
  const total =
    (Date.parse(result.request.end_utc) -
      Date.parse(result.request.start_utc)) /
    1000
  const duration = (s: number | null) =>
    s === null
      ? en.common.unknown
      : `${fmtDuration(s * 1000)} · ${fmtPercent(s / total)}`
  return (
    <section className="comparison-panel" aria-label={en.compare.title}>
      <h2>{en.compare.title}</h2>
      <p>
        {result.request.start_utc} — {result.request.end_utc} ·{' '}
        {result.request.frame_id} · {result.request.terrain_mode}
      </p>
      {stale && (
        <p role="status" className="notice">
          {en.params.stale}
        </p>
      )}
      <p className="small">{en.compare.note}</p>
      <div className="comparison-grid">
        {result.sites.map((site, n) => {
          const one = resultForSite(result, n),
            s = one.series[0],
            summary = one.summary[0]
          const i = s ? Math.min(index, s.time_utc.length - 1) : 0
          return (
            <article
              key={site.site_ref}
              className="comparison-column"
              data-site-ref={site.site_ref}
              style={{ borderTopColor: colours[n] }}
            >
              <button aria-pressed={active === n} onClick={() => onActive(n)}>
                {n + 1}. {site.label}
              </button>
              {s ? (
                <>
                  <p className="small">
                    <time>{s.time_utc[i]}</time>
                  </p>
                  <dl className="facts">
                    <dt>{en.results.sun}</dt>
                    <dd>
                      {en.results.sunStates[s.sun.state[i]]} ·{' '}
                      {fmtDeg(s.sun.elevation_deg[i])}
                    </dd>
                    <dt>{en.results.earth}</dt>
                    <dd>
                      {en.results.earthStates[s.earth.state[i]]} ·{' '}
                      {fmtDeg(s.earth.elevation_deg[i])}
                    </dd>
                  </dl>
                  <ElevationChart series={s} index={i} domain={domain} />
                </>
              ) : (
                <p>{en.common.notComputed}</p>
              )}
              {summary && (
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
              )}
              <TimeBands result={one} index={i} />
              {result.quality.issues
                .filter((q) => q.site_ref === site.site_ref)
                .map((q, k) => (
                  <p className="small" key={k}>
                    {en.quality.issueMessages[q.message_key] ?? q.code}
                  </p>
                ))}
            </article>
          )
        })}
      </div>
    </section>
  )
}
