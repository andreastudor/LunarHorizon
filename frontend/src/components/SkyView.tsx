// Local sky dome seen from above (map view): zenith at the centre, idealized horizon (0°) on the rim,
// north up and east right. Bodies below the horizon or with an undefined azimuth are not plotted.

import { en } from '../i18n/en.ts'
import { fmtDeg } from '../ui/format.ts'

interface BodyPosition {
  azimuthDeg: number | null
  elevationDeg: number
}

const SIZE = 220
const CENTER = SIZE / 2
const RADIUS = SIZE / 2 - 22

function project({ azimuthDeg, elevationDeg }: BodyPosition) {
  if (azimuthDeg === null || elevationDeg < 0) return null
  const r = (RADIUS * (90 - elevationDeg)) / 90
  const a = (azimuthDeg * Math.PI) / 180
  return { x: CENTER + r * Math.sin(a), y: CENTER - r * Math.cos(a) }
}

function describe(position: BodyPosition): string {
  if (position.elevationDeg < 0) return en.sky.belowHorizon
  return `${en.results.elevation.toLowerCase()} ${fmtDeg(position.elevationDeg)}, azimuth ${fmtDeg(position.azimuthDeg)}`
}

export function SkyView({
  sun,
  earth,
}: {
  sun: BodyPosition
  earth: BodyPosition
}) {
  const sunPoint = project(sun)
  const earthPoint = project(earth)
  const label = en.sky.description(describe(sun), describe(earth))
  return (
    <figure className="sky">
      <figcaption>{en.sky.heading}</figcaption>
      <svg
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        width={SIZE}
        height={SIZE}
        role="img"
        aria-label={label}
      >
        <circle cx={CENTER} cy={CENTER} r={RADIUS} className="sky-dome" />
        {[30, 60].map((elevation) => (
          <circle
            key={elevation}
            cx={CENTER}
            cy={CENTER}
            r={(RADIUS * (90 - elevation)) / 90}
            className="sky-ring"
          />
        ))}
        <line
          x1={CENTER}
          y1={CENTER - RADIUS}
          x2={CENTER}
          y2={CENTER + RADIUS}
          className="sky-ring"
        />
        <line
          x1={CENTER - RADIUS}
          y1={CENTER}
          x2={CENTER + RADIUS}
          y2={CENTER}
          className="sky-ring"
        />
        <text x={CENTER} y={14} className="sky-label">
          {en.sky.north}
        </text>
        <text x={SIZE - 10} y={CENTER + 4} className="sky-label">
          {en.sky.east}
        </text>
        <text x={CENTER} y={SIZE - 4} className="sky-label">
          {en.sky.south}
        </text>
        <text x={10} y={CENTER + 4} className="sky-label">
          {en.sky.west}
        </text>
        {sunPoint && (
          <circle cx={sunPoint.x} cy={sunPoint.y} r={8} className="sky-sun" />
        )}
        {earthPoint && (
          <circle
            cx={earthPoint.x}
            cy={earthPoint.y}
            r={7}
            className="sky-earth"
          />
        )}
      </svg>
    </figure>
  )
}
