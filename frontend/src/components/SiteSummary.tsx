// Right zone, top: what is selected and where its position comes from. Original source titles are
// shown unchanged; internal notes written for the team are not shown.

import type { Site } from '../contracts/generated.ts'
import { en } from '../i18n/en.ts'
import { fmtLatitude, fmtLongitude } from '../ui/format.ts'
import type { Selection } from '../state/types.ts'

interface Props {
  selection: Selection
  site: Site | null
  frameId: string
  /** Status of the local DEM terrain for this selection (useLocalTerrain). */
  terrainStatus: string
}

export function SiteSummary({
  selection,
  site,
  frameId,
  terrainStatus,
}: Props) {
  if (!selection) {
    return (
      <section className="panel" aria-labelledby="summary-heading">
        <h2 id="summary-heading">{en.selection.heading}</h2>
        <p className="muted">{en.selection.none}</p>
      </section>
    )
  }
  if (selection.kind === 'custom') {
    return (
      <section className="panel" aria-labelledby="summary-heading">
        <h2 id="summary-heading">{selection.label}</h2>
        <p className="muted">{en.selection.custom}</p>
        <dl className="facts">
          <dt>{en.selection.coordinates}</dt>
          <dd>
            {fmtLatitude(selection.latitudeDeg)},{' '}
            {fmtLongitude(selection.longitudeDeg)}
          </dd>
          <dt>{en.selection.frame}</dt>
          <dd>
            <code>{frameId}</code>
          </dd>
          <dt>{en.selection.localTerrain}</dt>
          <dd>
            {en.selection.localTerrainStatus[terrainStatus] ?? terrainStatus}
          </dd>
        </dl>
      </section>
    )
  }
  if (!site) return null
  const notLanding = site.position_kind !== 'actual'
  return (
    <section className="panel" aria-labelledby="summary-heading">
      <h2 id="summary-heading">{site.name}</h2>
      {notLanding && (
        <p className="notice notice--info">{en.selection.planNote}</p>
      )}
      <dl className="facts">
        <dt>{en.selection.coordinates}</dt>
        <dd>
          {fmtLatitude(site.latitude_deg)}, {fmtLongitude(site.longitude_deg)}
        </dd>
        <dt>{en.selection.frame}</dt>
        <dd>
          <code>{site.frame_id}</code>
        </dd>
        {site.mission && (
          <>
            <dt>{en.selection.mission}</dt>
            <dd>{site.mission}</dd>
          </>
        )}
        {(site.agency || site.operator) && (
          <>
            <dt>{en.selection.agency}</dt>
            <dd>
              {[site.agency, site.operator]
                .filter(Boolean)
                .filter((v, i, all) => all.indexOf(v) === i)
                .join(' / ')}
            </dd>
          </>
        )}
        {site.country && (
          <>
            <dt>{en.selection.country}</dt>
            <dd>{site.country}</dd>
          </>
        )}
        <dt>{en.selection.positionKind}</dt>
        <dd>
          {en.catalog.positionKind[site.position_kind] ?? site.position_kind}
        </dd>
        <dt>{en.selection.missionStatus}</dt>
        <dd>
          {en.catalog.missionStatus[site.mission_status] ?? site.mission_status}
        </dd>
        <dt>{en.selection.uncertainty}</dt>
        <dd>
          {site.horizontal_uncertainty_m === null
            ? en.common.unknown
            : `${site.horizontal_uncertainty_m} m`}
        </dd>
        <dt>{en.selection.elevation}</dt>
        <dd>
          {site.elevation_m === null || site.elevation_m === undefined
            ? en.common.unknown
            : `${site.elevation_m.toFixed(1)} m`}
        </dd>
        <dt>{en.selection.verification}</dt>
        <dd>
          {en.selection.verificationStatus[site.position_verification] ??
            site.position_verification}
        </dd>
        <dt>{en.selection.localTerrain}</dt>
        <dd>
          {en.selection.localTerrainStatus[terrainStatus] ?? terrainStatus}
        </dd>
      </dl>
      <h3>{en.selection.sources}</h3>
      <ul className="plain-list sources">
        {site.position_sources.map((source, index) => (
          <li key={`${source.url}-${index}`}>
            <a href={source.url} target="_blank" rel="noreferrer">
              {source.title}
            </a>
            <span className="muted small">
              {' '}
              — {source.institution}
              {source.accessed_at
                ? `, ${en.selection.accessed(source.accessed_at)}`
                : ''}
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}
