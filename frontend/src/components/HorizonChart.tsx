// Horizon profile chart (E09): H(a) computed by the backend from the DEM calculation rasters.
// Unknown azimuths stay gaps (never drawn as a flat or free horizon); partial azimuths are marked.
// The Sun and Earth are drawn only when the simulation used the same frame as the DEM profile.

import type { HorizonState } from '../api/useHorizonProfile.ts'
import type { HorizonProfile } from '../contracts/generated.ts'
import { en } from '../i18n/en.ts'

export interface SkyBody {
  azimuthDeg: number | null
  elevationDeg: number
}

interface Props {
  state: HorizonState
  hasPoint: boolean
  hasHeight: boolean
  bodies: { sun: SkyBody; earth: SkyBody } | null
  simulationFrame: string | null
  onRetry: () => void
}

const WIDTH = 720
const HEIGHT = 300
const LEFT = 48
const RIGHT = 12
const TOP = 12
const BOTTOM = 40
const COMPASS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW', 'N']

const fmt = (value: number, digits = 2) => value.toFixed(digits)

export function HorizonChart(props: Props) {
  return (
    <section className="horizon-view" aria-labelledby="horizon-heading">
      <h2 id="horizon-heading">{en.horizon.heading}</h2>
      <p className="small muted">{en.horizon.intro}</p>
      <Body {...props} />
    </section>
  )
}

function Body({
  state,
  hasPoint,
  hasHeight,
  bodies,
  simulationFrame,
  onRetry,
}: Props) {
  if (!hasPoint) return <p className="muted">{en.horizon.needPoint}</p>
  if (!hasHeight) return <p className="muted">{en.horizon.needHeight}</p>
  if (state.status === 'idle' || state.status === 'loading')
    return <p aria-live="polite">{en.horizon.loading}</p>
  if (state.status === 'error')
    return (
      <div className="notice notice--error" role="alert">
        <p>{en.horizon.error}</p>
        <p className="small">{state.message}</p>
        <button type="button" onClick={onRetry}>
          {en.common.retry}
        </button>
      </div>
    )
  const profile = state.profile
  if (profile.status === 'unavailable') {
    return (
      <div className="notice notice--warning" data-horizon-status="unavailable">
        <p>
          <strong>{en.horizon.status.unavailable}</strong>
          {': '}
          {profile.reason_code && profile.reason_code !== 'missing_samples'
            ? en.horizon.unavailable[profile.reason_code]
            : profile.reason}
        </p>
        <p className="small">{en.horizon.unknownNotFlat}</p>
      </div>
    )
  }
  const drawBodies = bodies !== null && simulationFrame === profile.frame_id
  return (
    <>
      <p
        className={`notice ${profile.status === 'complete' ? 'notice--info' : 'notice--warning'}`}
        data-horizon-status={profile.status}
      >
        <strong>{en.horizon.status[profile.status]}</strong>
        {': '}
        {profile.status === 'complete'
          ? en.horizon.completeNote(
              fmt(profile.max_search_distance_m / 1000, 0),
            )
          : en.horizon.partialNote}
      </p>
      <Chart profile={profile} bodies={drawBodies ? bodies : null} />
      {bodies !== null && simulationFrame !== null && !drawBodies && (
        <p className="small muted">{en.horizon.bodiesFrame}</p>
      )}
      {drawBodies && <p className="small muted">{en.horizon.bodiesHint}</p>}
      <Facts profile={profile} />
      <p className="small">{en.horizon.provisional}</p>
      <p className="small muted">{en.horizon.visibilityPending}</p>
    </>
  )
}

function Chart({
  profile,
  bodies,
}: {
  profile: HorizonProfile
  bodies: { sun: SkyBody; earth: SkyBody } | null
}) {
  const step = profile.azimuth_step_deg
  const values = profile.elevation_deg
  const known = values.filter((v): v is number => v !== null)
  const bodyValues = bodies
    ? [bodies.sun, bodies.earth]
        .filter((b) => b.azimuthDeg !== null)
        .map((b) => b.elevationDeg)
    : []
  const low = Math.floor(Math.min(-2, ...known, ...bodyValues) - 0.5)
  const high = Math.ceil(Math.max(2, ...known, ...bodyValues) + 0.5)
  const plotW = WIDTH - LEFT - RIGHT
  const plotH = HEIGHT - TOP - BOTTOM
  const x = (az: number) => LEFT + (az / 360) * plotW
  const y = (el: number) => TOP + ((high - el) / (high - low)) * plotH

  // Segments of known values; the profile is continuous at 0°/360°.
  const segments: string[] = []
  let current: string[] = []
  for (let i = 0; i <= values.length; i++) {
    const value = values[i % values.length]
    if (value === null) {
      if (current.length > 1) segments.push(current.join(' '))
      current = []
      continue
    }
    current.push(`${fmt(x(i * step))},${fmt(y(value))}`)
  }
  if (current.length > 1) segments.push(current.join(' '))

  const yTicks: number[] = []
  const tickStep = high - low > 12 ? 4 : high - low > 6 ? 2 : 1
  for (let t = Math.ceil(low / tickStep) * tickStep; t <= high; t += tickStep)
    yTicks.push(t)
  const bandWidth = Math.max((step / 360) * plotW, 1)

  return (
    <svg
      className="horizon-chart"
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      role="img"
      aria-label={en.horizon.chartLabel(
        en.horizon.status[profile.status],
        known.length,
        values.length,
      )}
      data-azimuths={values.length}
      data-known={known.length}
    >
      {values.map((value, i) =>
        value === null ? (
          <rect
            key={`nd-${i}`}
            className="horizon-nodata"
            x={x(i * step) - bandWidth / 2}
            y={TOP}
            width={bandWidth}
            height={plotH}
          />
        ) : null,
      )}
      {yTicks.map((t) => (
        <g key={`y-${t}`}>
          <line
            className={t === 0 ? 'horizon-zero' : 'horizon-grid'}
            x1={LEFT}
            x2={WIDTH - RIGHT}
            y1={y(t)}
            y2={y(t)}
          />
          <text
            className="horizon-tick"
            x={LEFT - 6}
            y={y(t) + 4}
            textAnchor="end"
          >
            {t}°
          </text>
        </g>
      ))}
      {COMPASS.map((label, k) => (
        <g key={`x-${k}`}>
          <line
            className="horizon-grid"
            x1={x(k * 45)}
            x2={x(k * 45)}
            y1={TOP}
            y2={TOP + plotH}
          />
          <text
            className="horizon-tick"
            x={x(k * 45)}
            y={HEIGHT - BOTTOM + 16}
            textAnchor="middle"
          >
            {k * 45}° {label}
          </text>
        </g>
      ))}
      {segments.map((points, k) => (
        <polyline key={`s-${k}`} className="horizon-line" points={points} />
      ))}
      {profile.quality.map((quality, i) =>
        quality === 'partial' ? (
          <rect
            key={`p-${i}`}
            className="horizon-partial"
            x={x(i * step) - bandWidth / 2}
            y={TOP + plotH - 6}
            width={bandWidth}
            height={6}
          />
        ) : null,
      )}
      {bodies &&
        (['sun', 'earth'] as const).map((name) => {
          const body = bodies[name]
          if (body.azimuthDeg === null) return null
          return (
            <g key={name} className={`horizon-body horizon-body--${name}`}>
              <circle cx={x(body.azimuthDeg)} cy={y(body.elevationDeg)} r={6} />
              <text x={x(body.azimuthDeg) + 9} y={y(body.elevationDeg) - 7}>
                {name === 'sun' ? en.results.sun : en.results.earth}
              </text>
            </g>
          )
        })}
      <text
        className="horizon-axis"
        x={LEFT + plotW / 2}
        y={HEIGHT - 4}
        textAnchor="middle"
      >
        {en.horizon.axisAzimuth}
      </text>
    </svg>
  )
}

function Facts({ profile }: { profile: HorizonProfile }) {
  return (
    <dl className="facts small">
      <dt>{en.horizon.facts.observer}</dt>
      <dd>
        {profile.observer_terrain_elevation_m === null
          ? en.common.unknown
          : `${fmt(profile.observer_terrain_elevation_m, 1)} m`}
      </dd>
      <dt>{en.horizon.facts.equipment}</dt>
      <dd>{fmt(profile.observer_height_m, 1)} m</dd>
      <dt>{en.horizon.facts.frame}</dt>
      <dd>
        <code>{profile.frame_id}</code>
      </dd>
      <dt>{en.horizon.facts.dMax}</dt>
      <dd>{fmt(profile.max_search_distance_m / 1000, 0)} km</dd>
      <dt>{en.horizon.facts.step}</dt>
      <dd>{profile.azimuth_step_deg}°</dd>
      <dt>{en.horizon.facts.coverage}</dt>
      <dd>{fmt(profile.coverage_fraction * 100, 1)} %</dd>
      <dt>{en.horizon.facts.products}</dt>
      <dd>
        {profile.dem_products.map((product) => (
          <span key={product.product_id} className="horizon-product">
            <code>{product.product_id}</code> ({en.horizon.role[product.role]},{' '}
            {product.resolution_m} m)
          </span>
        ))}
      </dd>
      {profile.compute_time_s !== null && (
        <>
          <dt>{en.horizon.facts.time}</dt>
          <dd>{fmt(profile.compute_time_s, 2)} s</dd>
        </>
      )}
    </dl>
  )
}
