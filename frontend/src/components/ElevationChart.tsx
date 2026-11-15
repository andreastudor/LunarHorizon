// Elevation of the Sun and Earth over time, with the horizon at each body's azimuth (E10). Drawn from
// the display series only; events and durations come from the refined backend calculation, never
// from these lines. Unknown horizon values are gaps.

import type { SiteSeries } from '../contracts/generated.ts'
import { en } from '../i18n/en.ts'

interface Props {
  series: SiteSeries
  index: number
}

const WIDTH = 360
const HEIGHT = 150
const LEFT = 34
const RIGHT = 6
const TOP = 8
const BOTTOM = 18

function path(
  values: (number | null)[],
  x: (i: number) => number,
  y: (v: number) => number,
): string {
  let d = ''
  let pen = false
  values.forEach((value, i) => {
    if (value === null) {
      pen = false
      return
    }
    d += `${pen ? 'L' : 'M'}${x(i).toFixed(1)},${y(value).toFixed(1)} `
    pen = true
  })
  return d.trim()
}

export function ElevationChart({ series, index }: Props) {
  const lines = [
    series.sun.elevation_deg,
    series.earth.elevation_deg,
    series.sun.horizon_elevation_deg,
    series.earth.horizon_elevation_deg,
  ]
  const known = lines.flat().filter((v): v is number => v !== null)
  const low = Math.floor(Math.min(-1, ...known))
  const high = Math.ceil(Math.max(1, ...known))
  const count = series.time_utc.length
  const plotW = WIDTH - LEFT - RIGHT
  const plotH = HEIGHT - TOP - BOTTOM
  const x = (i: number) => LEFT + (count > 1 ? (i / (count - 1)) * plotW : 0)
  const y = (v: number) => TOP + ((high - v) / (high - low || 1)) * plotH
  const cursor = x(Math.min(index, count - 1))
  return (
    <figure className="elevation-chart">
      <figcaption className="small">{en.chart.heading}</figcaption>
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label={en.chart.label}
        data-points={count}
      >
        <line
          className="chart-zero"
          x1={LEFT}
          x2={WIDTH - RIGHT}
          y1={y(0)}
          y2={y(0)}
        />
        <text
          className="chart-tick"
          x={LEFT - 4}
          y={y(high) + 4}
          textAnchor="end"
        >
          {high}°
        </text>
        <text className="chart-tick" x={LEFT - 4} y={y(low)} textAnchor="end">
          {low}°
        </text>
        <path
          className="chart-line chart-line--sun-horizon"
          d={path(series.sun.horizon_elevation_deg, x, y)}
        />
        <path
          className="chart-line chart-line--earth-horizon"
          d={path(series.earth.horizon_elevation_deg, x, y)}
        />
        <path
          className="chart-line chart-line--sun"
          d={path(series.sun.elevation_deg, x, y)}
        />
        <path
          className="chart-line chart-line--earth"
          d={path(series.earth.elevation_deg, x, y)}
        />
        <line
          className="chart-cursor"
          x1={cursor}
          x2={cursor}
          y1={TOP}
          y2={TOP + plotH}
        />
      </svg>
      <p className="small muted">
        <span className="chart-key chart-key--sun" /> {en.chart.sun}{' '}
        <span className="chart-key chart-key--sun-horizon" />{' '}
        {en.chart.sunHorizon} <span className="chart-key chart-key--earth" />{' '}
        {en.chart.earth} <span className="chart-key chart-key--earth-horizon" />{' '}
        {en.chart.earthHorizon}
      </p>
      <p className="small muted">{en.chart.note}</p>
    </figure>
  )
}
