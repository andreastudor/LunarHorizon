// Simulation parameters: UTC start, duration, observer height, Earth threshold, frame and horizon
// mode. "DEM terrain" can be chosen but the server refuses it explicitly; it is never replaced by the
// idealized mode behind the user's back.

import type { FormEvent } from 'react'
import { SUPPORTED_FRAMES, type FrameId } from '../geo/conventions.ts'
import { en } from '../i18n/en.ts'
import { DURATION_OPTIONS_DAYS, type ParamErrors } from '../state/model.ts'
import type { SimulationParams, TerrainModeChoice } from '../state/types.ts'

interface Props {
  params: SimulationParams
  errors: ParamErrors
  showErrors: boolean
  canRun: boolean
  running: boolean
  hasSelection: boolean
  onChange: (params: SimulationParams) => void
  onRun: () => void
}

export function ParamsForm({
  params,
  errors,
  showErrors,
  canRun,
  running,
  hasSelection,
  onChange,
  onRun,
}: Props) {
  const set = <K extends keyof SimulationParams>(
    key: K,
    value: SimulationParams[K],
  ) => onChange({ ...params, [key]: value })
  const submit = (event: FormEvent) => {
    event.preventDefault()
    onRun()
  }
  const anyError = Object.keys(errors).length > 0

  return (
    <section className="panel" aria-labelledby="params-heading">
      <h2 id="params-heading">{en.params.heading}</h2>
      <form className="grid-form" onSubmit={submit} noValidate>
        <label className="field">
          <span>{en.params.startDate}</span>
          <input
            type="date"
            name="start-date"
            value={params.startDate}
            aria-invalid={showErrors && Boolean(errors.date)}
            onChange={(event) => set('startDate', event.target.value)}
          />
        </label>
        <label className="field">
          <span>{en.params.startTime}</span>
          <input
            name="start-time"
            inputMode="numeric"
            placeholder="HH:MM"
            pattern="[0-2][0-9]:[0-5][0-9]"
            maxLength={5}
            value={params.startTime}
            aria-invalid={showErrors && Boolean(errors.date)}
            onChange={(event) => set('startTime', event.target.value)}
          />
        </label>
        <label className="field">
          <span>{en.params.duration}</span>
          <select
            name="duration"
            value={params.durationDays}
            onChange={(event) =>
              set('durationDays', Number(event.target.value))
            }
          >
            {DURATION_OPTIONS_DAYS.map((days) => (
              <option key={days} value={days}>
                {en.params.days(days)}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>{en.params.observerHeight}</span>
          <input
            name="observer-height"
            inputMode="decimal"
            value={params.observerHeightM}
            aria-invalid={showErrors && Boolean(errors.height)}
            onChange={(event) => set('observerHeightM', event.target.value)}
          />
        </label>
        <label className="field">
          <span>{en.params.earthMinElevation}</span>
          <input
            name="earth-min-elevation"
            inputMode="decimal"
            value={params.earthMinElevationDeg}
            aria-invalid={showErrors && Boolean(errors.elevation)}
            onChange={(event) =>
              set('earthMinElevationDeg', event.target.value)
            }
          />
        </label>
        <label className="field field--wide">
          <span>{en.params.frame}</span>
          <select
            name="frame"
            value={params.frameId}
            onChange={(event) => set('frameId', event.target.value as FrameId)}
          >
            {SUPPORTED_FRAMES.map((frame) => (
              <option key={frame} value={frame}>
                {frame}
              </option>
            ))}
          </select>
        </label>
        <label className="field field--wide">
          <span>{en.params.terrainMode}</span>
          <select
            name="terrain-mode"
            value={params.terrainMode}
            onChange={(event) =>
              set('terrainMode', event.target.value as TerrainModeChoice)
            }
          >
            <option value="idealized_local_plane">{en.params.idealized}</option>
            <option value="dem">{en.params.dem}</option>
          </select>
        </label>
        {showErrors && errors.date && (
          <p className="field-error field--wide">{en.params.dateError}</p>
        )}
        {showErrors && errors.height && (
          <p className="field-error field--wide">{en.params.heightError}</p>
        )}
        {showErrors && errors.elevation && (
          <p className="field-error field--wide">{en.params.elevationError}</p>
        )}
        {!hasSelection && (
          <p className="muted small field--wide">{en.params.needSelection}</p>
        )}
        <button
          type="submit"
          className="primary field--wide"
          disabled={!hasSelection || running || (showErrors && anyError)}
          aria-disabled={!canRun}
        >
          {running ? en.params.running : en.params.run}
        </button>
      </form>
    </section>
  )
}
