// Display formatting. fmtDuration and the "always UTC, always labelled" convention are adapted from
// Nasa-moon (src/components/navigator/format.ts, commit dcc3f0a5ee693ed3fe2ab4cf0b0ed2134770176c,
// MIT License, Copyright (c) 2026 Kazi Ahammad Ullah). Null values are never shown as zero.

import { en } from '../i18n/en.ts'

const pad = (n: number): string => String(n).padStart(2, '0')

/** Degrees with the unit; `null` (undefined azimuth) is shown as “Undefined”. */
export function fmtDeg(value: number | null, digits = 1): string {
  return value === null ? en.common.undefined : `${value.toFixed(digits)}°`
}

/** Milliseconds as "2 d 4 h", "5 h 12 min", "42 min" or "30 s". */
export function fmtDuration(ms: number): string {
  const totalSeconds = Math.max(0, Math.round(ms / 1000))
  const days = Math.floor(totalSeconds / 86_400)
  const hours = Math.floor((totalSeconds % 86_400) / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  if (days > 0) return `${days} d ${hours} h`
  if (hours > 0) return `${hours} h ${minutes} min`
  if (minutes > 0) return `${minutes} min`
  return `${seconds} s`
}

/** "2026-11-15 01:55:29 UTC" — always UTC, always labelled. */
export function fmtUtc(epochMs: number): string {
  const d = new Date(epochMs)
  return (
    `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ` +
    `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())} UTC`
  )
}

/** Latitude with hemisphere, e.g. "85.4266° S". */
export function fmtLatitude(value: number, digits = 4): string {
  const hemisphere = value < 0 ? 'S' : 'N'
  return `${Math.abs(value).toFixed(digits)}° ${hemisphere}`
}

/** Longitude east-positive with hemisphere, e.g. "31.7442° E" or "148.0000° W". */
export function fmtLongitude(value: number, digits = 4): string {
  const hemisphere = value < 0 ? 'W' : 'E'
  return `${Math.abs(value).toFixed(digits)}° ${hemisphere}`
}

export function fmtPercent(fraction: number | null): string {
  return fraction === null
    ? en.common.unknown
    : `${(fraction * 100).toFixed(1)}%`
}

export function fmtKm(value: number): string {
  return `${Math.round(value).toLocaleString('en-US')} km`
}
