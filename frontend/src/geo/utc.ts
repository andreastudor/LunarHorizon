// Momente UTC în ISO 8601, cu aceleași reguli ca backend/lunarhorizon/core/utc.py:
// format `YYYY-MM-DDTHH:MM:SS[.fff](Z|±HH:MM)`, zonă obligatorie, secunda `:60` respinsă,
// ani 0001–9999, forma canonică în UTC cu `Z` și fără zerouri finale în fracțiune.
// Valoarea internă este numărul de milisecunde de la epoca Unix (precizie de milisecundă).

export type UtcErrorReason =
  | 'invalid_format'
  | 'missing_timezone'
  | 'invalid_offset'
  | 'invalid_date'
  | 'leap_second_unsupported'

export class UtcParseError extends Error {
  readonly reason: UtcErrorReason
  readonly text: string

  constructor(reason: UtcErrorReason, text: string) {
    super(`${reason}: ${JSON.stringify(text)}`)
    this.name = 'UtcParseError'
    this.reason = reason
    this.text = text
  }
}

const PARSE =
  /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,3}))?(Z|[+-]\d{2}:\d{2})?$/
const MS_PER_MINUTE = 60_000

function daysInMonth(year: number, month: number): number {
  const leap = (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0
  return [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
}

function epochMs(
  year: number,
  month: number,
  day: number,
  hour: number,
  minute: number,
  second: number,
  millisecond: number,
): number {
  // setUTCFullYear evită conversia anilor 0–99 în 1900–1999 făcută de Date.UTC.
  const date = new Date(0)
  date.setUTCFullYear(year, month - 1, day)
  date.setUTCHours(hour, minute, second, millisecond)
  return date.getTime()
}

export function parseUtc(text: string): number {
  const match = PARSE.exec(text)
  if (match === null) throw new UtcParseError('invalid_format', text)
  const [, y, mo, d, h, mi, s, fraction, zone] = match
  if (zone === undefined) throw new UtcParseError('missing_timezone', text)
  if (s === '60') throw new UtcParseError('leap_second_unsupported', text)

  let offsetMinutes = 0
  if (zone !== 'Z') {
    const offsetHours = Number(zone.slice(1, 3))
    const offsetMins = Number(zone.slice(4, 6))
    if (offsetHours > 23 || offsetMins > 59)
      throw new UtcParseError('invalid_offset', text)
    offsetMinutes = (offsetHours * 60 + offsetMins) * (zone[0] === '-' ? -1 : 1)
  }

  const [year, month, day, hour, minute, second] = [y, mo, d, h, mi, s].map(
    Number,
  )
  const millisecond = Number((fraction ?? '0').padEnd(3, '0'))
  const validDate =
    year >= 1 &&
    month >= 1 &&
    month <= 12 &&
    day >= 1 &&
    day <= daysInMonth(year, month) &&
    hour <= 23 &&
    minute <= 59 &&
    second <= 59
  if (!validDate) throw new UtcParseError('invalid_date', text)

  const utc =
    epochMs(year, month, day, hour, minute, second, millisecond) -
    offsetMinutes * MS_PER_MINUTE
  const utcYear = new Date(utc).getUTCFullYear()
  if (utcYear < 1 || utcYear > 9999)
    throw new UtcParseError('invalid_date', text)
  return utc
}

const pad = (value: number, width: number): string =>
  String(value).padStart(width, '0')

export function formatUtc(epochMilliseconds: number): string {
  if (!Number.isFinite(epochMilliseconds))
    throw new RangeError('moment nefinit')
  const date = new Date(Math.round(epochMilliseconds))
  const base =
    `${pad(date.getUTCFullYear(), 4)}-${pad(date.getUTCMonth() + 1, 2)}-` +
    `${pad(date.getUTCDate(), 2)}T${pad(date.getUTCHours(), 2)}:` +
    `${pad(date.getUTCMinutes(), 2)}:${pad(date.getUTCSeconds(), 2)}`
  const millisecond = date.getUTCMilliseconds()
  if (millisecond === 0) return `${base}Z`
  return `${base}.${pad(millisecond, 3).replace(/0+$/, '')}Z`
}

export const canonicalUtc = (text: string): string => formatUtc(parseUtc(text))
