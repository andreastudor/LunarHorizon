// Horizon profile H(a) of the selected point (E09), loaded only while the Horizon view is open.
// A newer request supersedes an older one (abort + ignore); nothing is preloaded. `idle` and
// `loading` are derived during render from the request key; the effect only stores results.

import { useEffect, useState } from 'react'
import type { HorizonProfile } from '../contracts/generated.ts'
import type { DataSource } from './dataSource.ts'
import { describeError } from './errors.ts'

export type HorizonState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ready'; profile: HorizonProfile }
  | { status: 'error'; message: string }

type Settled =
  | { status: 'ready'; profile: HorizonProfile }
  | { status: 'error'; message: string }

export function useHorizonProfile(
  source: DataSource,
  latitude: number | null,
  longitude: number | null,
  frameId: string | null,
  observerHeightM: number | null,
  enabled: boolean,
  reloadToken: number,
): HorizonState {
  const [settled, setSettled] = useState<{
    key: string
    value: Settled
  } | null>(null)
  const active =
    enabled &&
    latitude !== null &&
    longitude !== null &&
    frameId !== null &&
    observerHeightM !== null
  const key = active
    ? `${latitude}|${longitude}|${frameId}|${observerHeightM}|${reloadToken}`
    : null

  useEffect(() => {
    if (
      key === null ||
      latitude === null ||
      longitude === null ||
      frameId === null ||
      observerHeightM === null
    )
      return
    const controller = new AbortController()
    let current = true
    source
      .horizonProfile(
        latitude,
        longitude,
        frameId,
        observerHeightM,
        controller.signal,
      )
      .then((profile) => {
        if (current) setSettled({ key, value: { status: 'ready', profile } })
      })
      .catch((error: unknown) => {
        if (!current) return
        if (error instanceof DOMException && error.name === 'AbortError') return
        setSettled({
          key,
          value: { status: 'error', message: describeError(error).message },
        })
      })
    return () => {
      current = false
      controller.abort()
    }
  }, [source, key, latitude, longitude, frameId, observerHeightM])

  if (key === null) return { status: 'idle' }
  if (settled === null || settled.key !== key) return { status: 'loading' }
  return settled.value
}
