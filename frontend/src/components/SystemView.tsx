import { useEffect, useRef, useState } from 'react'
import type { SystemLoad } from '../api/useSystemSeries.ts'
import type { SystemSeries } from '../contracts/generated.ts'
import type { SystemBody } from '../geo/system.ts'
import type { SystemHandle } from '../globe/threeSystem.ts'
import { en } from '../i18n/en.ts'
import { fmtKm } from '../ui/format.ts'

function Scene({ data, index }: { data: SystemSeries; index: number }) {
  const container = useRef<HTMLDivElement>(null)
  const handle = useRef<SystemHandle | null>(null)
  const latestIndex = useRef(index)
  const [unavailable, setUnavailable] = useState(false)
  useEffect(() => {
    latestIndex.current = index
    handle.current?.update(index)
  }, [index])
  useEffect(() => {
    let disposed = false
    import('../globe/threeSystem.ts')
      .then(({ createThreeSystem }) => {
        if (disposed || !container.current) return
        try {
          handle.current = createThreeSystem(container.current, data)
          handle.current.update(latestIndex.current)
          setUnavailable(false)
        } catch {
          setUnavailable(true)
        }
      })
      .catch(() => {
        if (!disposed) setUnavailable(true)
      })
    return () => {
      disposed = true
      handle.current?.dispose()
      handle.current = null
    }
  }, [data])
  return (
    <>
      <div className="system-tools" aria-label={en.system.focus}>
        <button onClick={() => handle.current?.focus(null)}>
          {en.system.reset}
        </button>
        {(['sun', 'earth', 'moon'] as SystemBody[]).map((body) => (
          <button key={body} onClick={() => handle.current?.focus(body)}>
            {en.system.focus} {en.system[body]}
          </button>
        ))}
      </div>
      {unavailable && (
        <p role="alert" className="notice">
          {en.system.webgl}
        </p>
      )}
      <div ref={container} className="system-canvas" />
    </>
  )
}

export function SystemView({
  state,
  index,
  onRetry,
}: {
  state: SystemLoad
  index: number
  onRetry: () => void
}) {
  const data = state.status === 'ready' ? state.data : null
  const i = data ? Math.min(index, data.time_utc.length - 1) : 0
  const download = () => {
    if (!data) return
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }),
    )
    const link = document.createElement('a')
    link.href = url
    link.download = 'earth-moon-sun.json'
    link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
  return (
    <section className="system-view" aria-label={en.system.title}>
      <header className="system-heading">
        <div>
          <p className="eyebrow">{en.system.subtitle}</p>
          <h2>{en.system.heading}</h2>
        </div>
        <span className="mode-badge">{en.system.notToScale}</span>
      </header>
      {state.status === 'loading' && <p role="status">{en.system.loading}</p>}
      {state.status === 'idle' && <p>{en.system.invalidTime}</p>}
      {state.status === 'error' && (
        <div role="alert">
          <p>{state.message}</p>
          <button onClick={onRetry}>{en.common.retry}</button>
        </div>
      )}
      {data && (
        <>
          <p className="small system-epoch" role="status">
            {en.system.ready} · <time>{data.time_utc[i]}</time> · UTC
          </p>
          <Scene data={data} index={i} />
          <div className="system-distances" aria-label={en.system.distance}>
            {(
              [
                ['earth_moon', 'earthMoon'],
                ['sun_earth', 'sunEarth'],
                ['sun_moon', 'sunMoon'],
              ] as const
            ).map(([key, label]) => (
              <article key={key} className="card">
                <h3>{en.system[label]}</h3>
                <output data-testid={`distance-${key}`}>
                  {fmtKm(data.distance_km[key][i])}
                </output>
                <p className="small muted">{en.system.distance}</p>
              </article>
            ))}
          </div>
          <p className="small muted">{en.system.scale}</p>
          <p className="small muted">
            {en.system.trails}
            <br />
            {data.time_utc[0]} — {data.time_utc.at(-1)} (UTC)
          </p>
          <details className="system-provenance">
            <summary>{en.system.geometry}</summary>
            <p>{en.system.difference}</p>
            <p>
              {en.system.profile}: <code>{data.kernel_profile}</code>
            </p>
            <p>{en.system.source}</p>
            <p>SHA-256: {data.kernel_sha256.join(', ')}</p>
          </details>
          <button onClick={download}>{en.system.export}</button>
        </>
      )}
    </section>
  )
}
