// Left zone: the real catalog from GET /api/sites (search), a point by coordinates and the DEM
// coverage from GET /api/coverage. A planned target or representative point is labelled as such.

import { useMemo, useState, type FormEvent } from 'react'
import type { Catalog, Coverage } from '../contracts/generated.ts'
import { parseCoordinates } from '../geo/globe.ts'
import { en } from '../i18n/en.ts'
import type { Loadable } from '../state/types.ts'

interface Props {
  catalog: Loadable<Catalog>
  coverage: Loadable<Coverage>
  selectedSiteId: string | null
  onSelectSite: (siteId: string) => void
  onSelectPoint: (
    latitudeDeg: number,
    longitudeDeg: number,
    label: string,
  ) => void
  onShowCoverage: (latitudeDeg: number, longitudeDeg: number) => void
  onUseRepresentative: (latitudeDeg: number, longitudeDeg: number) => void
  onRetry: () => void
}

export function CatalogPanel({
  catalog,
  coverage,
  selectedSiteId,
  onSelectSite,
  onSelectPoint,
  onShowCoverage,
  onUseRepresentative,
  onRetry,
}: Props) {
  const [query, setQuery] = useState('')
  const sites = useMemo(
    () => (catalog.status === 'ready' ? catalog.data.sites : []),
    [catalog],
  )
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase()
    if (!needle) return sites
    return sites.filter((site) =>
      [site.name, site.mission, site.agency, site.operator, site.country]
        .filter(Boolean)
        .some((text) => String(text).toLowerCase().includes(needle)),
    )
  }, [sites, query])

  return (
    <>
      <section className="panel" aria-labelledby="catalog-heading">
        <h2 id="catalog-heading">{en.catalog.heading}</h2>
        <label className="field">
          <span>{en.catalog.search}</span>
          <input
            type="search"
            name="site-search"
            value={query}
            placeholder={en.catalog.searchPlaceholder}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        {catalog.status === 'loading' && (
          <p role="status">{en.catalog.loading}</p>
        )}
        {catalog.status === 'error' && (
          <div className="notice notice--error" role="alert">
            <p>{en.catalog.error}</p>
            <p>{catalog.error.message}</p>
            <button type="button" onClick={onRetry}>
              {en.common.retry}
            </button>
          </div>
        )}
        {catalog.status === 'ready' && (
          <>
            <p className="muted">
              {en.catalog.count(filtered.length, sites.length)}
            </p>
            {filtered.length === 0 ? (
              <p>{en.catalog.empty}</p>
            ) : (
              <ul className="site-list">
                {filtered.map((site) => (
                  <li key={site.id}>
                    <button
                      type="button"
                      className="site-item"
                      aria-pressed={site.id === selectedSiteId}
                      onClick={() => onSelectSite(site.id)}
                    >
                      <span className="site-name">{site.name}</span>
                      <span className="site-meta">
                        <span className={`badge badge--${site.position_kind}`}>
                          {en.catalog.positionKind[site.position_kind] ??
                            site.position_kind}
                        </span>
                        <span>
                          {en.catalog.mission(
                            en.catalog.missionStatus[site.mission_status] ??
                              site.mission_status,
                          )}
                        </span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </section>

      <CoordinatesForm onSubmit={onSelectPoint} />

      <section className="panel" aria-labelledby="coverage-heading">
        <h2 id="coverage-heading">{en.coverage.heading}</h2>
        {coverage.status === 'loading' && (
          <p role="status">{en.coverage.loading}</p>
        )}
        {coverage.status === 'error' && (
          <div className="notice notice--error" role="alert">
            <p>{en.coverage.error}</p>
            <p>{coverage.error.message}</p>
          </div>
        )}
        {coverage.status === 'ready' && (
          <>
            <p className="muted">
              {en.coverage.temporal(
                coverage.data.temporal.start_utc,
                coverage.data.temporal.end_utc,
                coverage.data.temporal.kernel_profile,
              )}
            </p>
            {coverage.data.terrain.length === 0 ? (
              <p>{en.coverage.noTerrain}</p>
            ) : (
              <ul className="plain-list">
                {coverage.data.terrain.map((product) => {
                  const ring = product.footprint?.coordinates[0] ?? []
                  const center = ring.length
                    ? {
                        latitude:
                          (product.min_latitude_deg +
                            product.max_latitude_deg) /
                          2,
                        longitude:
                          ring.reduce((sum, p) => sum + p[0], 0) / ring.length,
                      }
                    : null
                  return (
                    <li key={product.product_id}>
                      <span>
                        {en.coverage.product(
                          product.product_id,
                          product.role,
                          product.resolution_m,
                        )}
                      </span>
                      {center && (
                        <button
                          type="button"
                          className="link-button"
                          onClick={() =>
                            onShowCoverage(center.latitude, center.longitude)
                          }
                        >
                          {en.coverage.show}
                        </button>
                      )}
                      {center && (
                        <button
                          type="button"
                          className="link-button"
                          onClick={() =>
                            onUseRepresentative(
                              center.latitude,
                              center.longitude,
                            )
                          }
                        >
                          {en.coverage.useRepresentative}
                        </button>
                      )}
                    </li>
                  )
                })}
              </ul>
            )}
            <p className="muted small">{en.coverage.extentNote}</p>
          </>
        )}
      </section>
    </>
  )
}

function CoordinatesForm({
  onSubmit,
}: {
  onSubmit: (latitudeDeg: number, longitudeDeg: number, label: string) => void
}) {
  const [latitude, setLatitude] = useState('')
  const [longitude, setLongitude] = useState('')
  const [label, setLabel] = useState<string>(en.point.defaultLabel)
  const [touched, setTouched] = useState(false)
  const parsed = parseCoordinates(latitude, longitude)
  const labelOk = label.trim().length > 0

  const submit = (event: FormEvent) => {
    event.preventDefault()
    setTouched(true)
    if (parsed.value && labelOk) {
      onSubmit(
        parsed.value.latitudeDeg,
        parsed.value.longitudeDeg,
        label.trim(),
      )
    }
  }

  return (
    <section className="panel" aria-labelledby="point-heading">
      <h2 id="point-heading">{en.point.heading}</h2>
      <p className="muted small">{en.point.hint}</p>
      <form className="grid-form" onSubmit={submit} noValidate>
        <label className="field">
          <span>{en.point.latitude}</span>
          <input
            name="latitude"
            inputMode="decimal"
            value={latitude}
            aria-invalid={touched && !parsed.latitudeOk}
            aria-describedby={
              touched && !parsed.latitudeOk ? 'lat-error' : undefined
            }
            onChange={(event) => setLatitude(event.target.value)}
          />
        </label>
        <label className="field">
          <span>{en.point.longitude}</span>
          <input
            name="longitude"
            inputMode="decimal"
            value={longitude}
            aria-invalid={touched && !parsed.longitudeOk}
            aria-describedby={
              touched && !parsed.longitudeOk ? 'lon-error' : undefined
            }
            onChange={(event) => setLongitude(event.target.value)}
          />
        </label>
        <label className="field field--wide">
          <span>{en.point.label}</span>
          <input
            name="label"
            value={label}
            aria-invalid={touched && !labelOk}
            onChange={(event) => setLabel(event.target.value)}
          />
        </label>
        {touched && !parsed.latitudeOk && (
          <p id="lat-error" className="field-error field--wide">
            {en.point.latitudeError}
          </p>
        )}
        {touched && !parsed.longitudeOk && (
          <p id="lon-error" className="field-error field--wide">
            {en.point.longitudeError}
          </p>
        )}
        {touched && !labelOk && (
          <p className="field-error field--wide">{en.point.labelError}</p>
        )}
        <button type="submit" className="field--wide">
          {en.point.use}
        </button>
      </form>
    </section>
  )
}
