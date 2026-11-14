// Starts a simulation and polls its status. Every run has a sequence number; a response that arrives
// after a newer run started (or after the selection changed and the run was cancelled) is ignored, so
// a late result can never be shown for a different site.

import { useCallback, useEffect, useRef, useState } from 'react'
import type {
  Progress,
  SimulationRequest,
  SimulationResult,
} from '../contracts/generated.ts'
import { ApiError, type DataSource } from './dataSource.ts'
import { describeError, type ErrorDescription } from './errors.ts'

export type SimulationView =
  | { phase: 'idle' }
  | { phase: 'submitting'; key: string }
  | { phase: 'running'; key: string; id: string; progress: Progress | null }
  | { phase: 'done'; key: string; id: string; result: SimulationResult }
  | { phase: 'failed'; key: string; error: ErrorDescription }

const isAbort = (error: unknown): boolean =>
  error instanceof DOMException && error.name === 'AbortError'

function wait(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, ms)
    signal.addEventListener(
      'abort',
      () => {
        clearTimeout(timer)
        reject(new DOMException('Aborted', 'AbortError'))
      },
      { once: true },
    )
  })
}

export function useSimulation(source: DataSource, pollMs = 500) {
  const [view, setView] = useState<SimulationView>({ phase: 'idle' })
  const runRef = useRef(0)
  const abortRef = useRef<AbortController | null>(null)

  const cancel = useCallback(() => {
    runRef.current += 1
    abortRef.current?.abort()
    abortRef.current = null
    setView({ phase: 'idle' })
  }, [])

  const start = useCallback(
    async (request: SimulationRequest, key: string) => {
      runRef.current += 1
      const run = runRef.current
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller
      const current = () => runRef.current === run
      setView({ phase: 'submitting', key })
      try {
        const accepted = await source.startSimulation(
          request,
          controller.signal,
        )
        if (!current()) return
        for (;;) {
          const status = await source.simulation(accepted.id, controller.signal)
          if (!current()) return
          if (status.status === 'done' && status.result) {
            setView({
              phase: 'done',
              key,
              id: status.id,
              result: status.result,
            })
            return
          }
          if (status.status === 'failed') {
            const problem = status.error
            setView({
              phase: 'failed',
              key,
              error: describeError(
                new ApiError(problem?.status ?? 500, problem, 'failed'),
              ),
            })
            return
          }
          setView({
            phase: 'running',
            key,
            id: status.id,
            progress: status.progress,
          })
          await wait(pollMs, controller.signal)
          if (!current()) return
        }
      } catch (error) {
        if (!current() || isAbort(error)) return
        setView({ phase: 'failed', key, error: describeError(error) })
      }
    },
    [source, pollMs],
  )

  useEffect(
    () => () => {
      runRef.current += 1
      abortRef.current?.abort()
    },
    [],
  )

  return { view, start, cancel }
}
