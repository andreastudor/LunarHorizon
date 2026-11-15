// Bottom zone: interval, current time, slider and playback over the series already received.
// Moving the slider never starts a new simulation.

import { useEffect } from 'react'
import type { SiteSeries } from '../contracts/generated.ts'
import { parseUtc } from '../geo/utc.ts'
import { en } from '../i18n/en.ts'
import { fmtUtc } from '../ui/format.ts'

interface Props {
  series: Pick<SiteSeries, 'time_utc' | 'step_s'> | null
  index: number
  playing: boolean
  onIndex: (index: number) => void
  onPlaying: (playing: boolean) => void
}

const PLAY_TICK_MS = 120

export function TimeBar({ series, index, playing, onIndex, onPlaying }: Props) {
  const count = series?.time_utc.length ?? 0

  useEffect(() => {
    if (!playing || count === 0) return
    const timer = setInterval(() => {
      onIndex(index + 1 >= count ? count - 1 : index + 1)
      if (index + 1 >= count - 1) onPlaying(false)
    }, PLAY_TICK_MS)
    return () => clearInterval(timer)
  }, [playing, index, count, onIndex, onPlaying])

  if (!series || count === 0) {
    return <p className="muted">{en.time.noResult}</p>
  }
  const current = fmtUtc(parseUtc(series.time_utc[index]))
  return (
    <div className="timebar">
      <button
        type="button"
        className="play"
        aria-pressed={playing}
        onClick={() => {
          if (!playing && index >= count - 1) onIndex(0)
          onPlaying(!playing)
        }}
      >
        {playing ? en.time.pause : en.time.play}
      </button>
      <div className="timebar-track">
        <label htmlFor="time-slider" className="sr-only">
          {en.time.slider}
        </label>
        <input
          id="time-slider"
          name="time-index"
          type="range"
          min={0}
          max={count - 1}
          step={1}
          value={index}
          aria-valuetext={current}
          onChange={(event) => onIndex(Number(event.target.value))}
        />
        <div className="timebar-labels small muted">
          <span>{fmtUtc(parseUtc(series.time_utc[0]))}</span>
          <span>
            {en.time.position(index + 1, count)} · {en.time.step(series.step_s)}
          </span>
          <span>{fmtUtc(parseUtc(series.time_utc[count - 1]))}</span>
        </div>
      </div>
      <output className="timebar-now" htmlFor="time-slider">
        {current}
      </output>
    </div>
  )
}
