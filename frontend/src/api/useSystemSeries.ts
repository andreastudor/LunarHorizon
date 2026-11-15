import { useEffect, useMemo, useState } from 'react'
import type { DataSource } from './dataSource.ts'
import { describeError } from './errors.ts'
import type { SystemSeries } from '../contracts/generated.ts'

export type SystemLoad =
  | { status: 'idle' | 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: SystemSeries }

export function useSystemSeries(
  source: DataSource,
  times: string[],
  enabled: boolean,
  retry: number,
): SystemLoad {
  const key = JSON.stringify(times)
  const [entry, setEntry] = useState<{
    source: DataSource
    key: string
    value: SystemLoad
  } | null>(null)
  const cache = useMemo(
    () => ({ source, values: new Map<string, SystemSeries>() }),
    [source],
  )
  useEffect(() => {
    if (!enabled || times.length === 0) return
    const stored = cache.values.get(key)
    const controller = new AbortController()
    Promise.resolve()
      .then(() => {
        if (controller.signal.aborted) return null
        if (stored) return stored
        setEntry({ source, key, value: { status: 'loading' } })
        return source.systemSeries({ time_utc: times }, controller.signal)
      })
      .then((data) => {
        if (controller.signal.aborted || !data) return
        cache.values.set(key, data)
        if (cache.values.size > 2)
          cache.values.delete(cache.values.keys().next().value!)
        setEntry({ source, key, value: { status: 'ready', data } })
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          const info = describeError(error)
          setEntry({
            source,
            key,
            value: {
              status: 'error',
              message: [info.message, ...info.details].join(' '),
            },
          })
        }
      })
    return () => controller.abort()
  }, [source, cache, key, times, enabled, retry])
  return entry?.key === key && entry.source === source
    ? entry.value
    : { status: enabled && times.length > 0 ? 'loading' : 'idle' }
}
