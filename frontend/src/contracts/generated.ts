/**
 * GENERAT AUTOMAT din data/schemas/lunarhorizon.schema.json — nu se editează manual.
 * Regenerare: scripts/generate_contracts.py (rădăcină), apoi `npm run contracts:generate`.
 * Versiunea schemei: 0.4.0
 */

/**
 * Contractele de date LunarHorizon. Generat din backend/lunarhorizon/contracts; nu se editează manual (scripts/generate_contracts.py).
 */
export type LunarHorizonContracts =
  | Catalog
  | KernelManifest
  | DemProductManifest
  | TerrainManifest
  | SimulationRequest
  | SimulationAccepted
  | SimulationStatus
  | SimulationResult
  | ScenarioIndex
  | Health
  | Coverage
  | Problem
export type ErrorCode =
  | 'VALIDATION_ERROR'
  | 'TOO_MANY_SITES'
  | 'INTERVAL_TOO_LONG'
  | 'UNSUPPORTED_FRAME'
  | 'OUT_OF_EPHEMERIS_COVERAGE'
  | 'OUT_OF_DEM_COVERAGE'
  | 'SIMULATION_NOT_FOUND'
  | 'KERNEL_MISSING'
  | 'TERRAIN_DATA_MISSING'
  | 'PRECOMPUTED_NOT_AVAILABLE'
  | 'INTERNAL_ERROR'

export interface Catalog {
  schema_version: '0.4.0'
  catalog_version: string
  sites: Site[]
  demo_site_selection: DemoSiteSelection
}
export interface Site {
  id: string
  name: string
  mission: string | null
  agency: string | null
  operator: string | null
  country: string | null
  status: 'landed' | 'planned' | 'candidate' | 'impact' | 'custom'
  mission_status: 'landed' | 'impacted' | 'not_landed' | 'planned' | 'unknown'
  geometry_type: 'point' | 'region'
  position_kind: 'actual' | 'planned_target' | 'representative_point'
  latitude_deg: number
  longitude_deg: number
  frame_id: 'MOON_ME_DE440_ME421' | 'MOON_ME_DE421'
  original_coordinates: OriginalCoordinates | null
  horizontal_uncertainty_m: number | null
  elevation_m?: number | null
  elevation_reference?: string | null
  region?: GeoJsonPolygon | null
  landing_date_utc?: string | null
  related_site_id: string | null
  planned_target_note: string | null
  source_url: string
  accessed_at: string
  position_sources: SourceRecord[]
  position_verification: 'verified_at_original' | 'incomplete' | 'conflict_open'
  adoption_note: string
  description_ro: string | null
  description_en: string | null
  terrain_available: boolean
}
/**
 * Coordonatele exact cum apar în sursă, cu descrierea cadrului sau a convenției lor.
 */
export interface OriginalCoordinates {
  latitude_deg: number
  longitude_deg: number
  frame_description: string
  note?: string | null
}
/**
 * Poligon GeoJSON în coordonate lunare: poziții [longitudine_deg, latitudine_deg].
 */
export interface GeoJsonPolygon {
  type: 'Polygon'
  /**
   * @minItems 1
   */
  coordinates: number[][][]
}
/**
 * Un document sau produs consultat pentru o poziție; citarea completă este în SOURCES.
 */
export interface SourceRecord {
  used_for: 'position' | 'planned_target' | 'corroboration' | 'mission_context'
  institution: string
  title: string
  url: string
  identifier: string | null
  version_or_update: string | null
  published: string | null
  accessed_at: string
  locator: string
  access: 'opened_original' | 'not_accessible'
  coordinates: OriginalCoordinates | null
  declared_frame: string | null
  frame_realization_stated: boolean
  published_uncertainty_m: number | null
  uncertainty_definition: string | null
  quote: string | null
  file_sha256: string | null
}
/**
 * Starea deciziei D-07. Un candidat documentat NU este un sit demonstrativ aprobat.
 */
export interface DemoSiteSelection {
  decision_id: 'D-07'
  status: 'unconfirmed' | 'confirmed'
  confirmed_site_ids: string[]
  candidates: DemoCandidate[]
  excluded: ExcludedCandidate[]
  criteria: string[]
}
export interface DemoCandidate {
  site_id: string
  advantages: string[]
  limits: string[]
}
export interface ExcludedCandidate {
  label: string
  reason: string
}
export interface KernelManifest {
  schema_version: '0.4.0'
  default_profile: 'de440_me421' | 'de421'
  /**
   * @minItems 1
   */
  profiles: KernelProfile[]
}
export interface KernelProfile {
  profile_id: 'de440_me421' | 'de421'
  frame_id: 'MOON_ME_DE440_ME421' | 'MOON_ME_DE421'
  pa_frame_id: 'MOON_PA_DE440' | 'MOON_PA_DE421'
  status: 'provisional' | 'confirmed'
  /**
   * @minItems 1
   */
  files: KernelFile[]
  coverage_start_utc?: string | null
  coverage_end_utc?: string | null
}
export interface KernelFile {
  role: 'spk' | 'binary_pck' | 'text_pck' | 'fk' | 'lsk'
  filename: string
  url: string
  sha256: string | null
  md5: string | null
  size_bytes: number | null
  retrieved_at_utc: string | null
  expected_checksums: ChecksumReference[]
  coverage_start_utc?: string | null
  coverage_end_utc?: string | null
}
/**
 * O sumă de control așteptată, cu originea ei. Nu este suma calculată de proiect.
 */
export interface ChecksumReference {
  algorithm: 'md5' | 'sha256'
  value: string
  kind: 'published_by_source' | 'prior_independent_download'
  source: string
  source_url: string | null
}
export interface DemProductManifest {
  schema_version: '0.4.0'
  products: DemProduct[]
}
export interface DemProduct {
  product_id: string
  title: string
  institution: string
  landing_page_url: string
  citation: string
  accessed_at: string
  role: 'near' | 'far'
  resolution_m: number
  frame_id: 'MOON_ME_DE440_ME421' | 'MOON_ME_DE421'
  metadata_origin: 'declared_by_source' | 'read_from_file'
  crs_wkt: string | null
  reference_radius_m: number | null
  vertical_units: 'm'
  vertical_reference: string | null
  nodata_value: number | null
  gap_handling: string
  min_latitude_deg: number | null
  max_latitude_deg: number | null
  /**
   * @minItems 1
   */
  files: ProductFile[]
}
export interface ProductFile {
  kind:
    | 'height'
    | 'count'
    | 'uncertainty'
    | 'slope'
    | 'hillshade'
    | 'label'
    | 'other'
  filename: string
  url: string
  sha256: string | null
  size_bytes: number | null
}
export interface TerrainManifest {
  schema_version: '0.4.0'
  terrain_id: string
  source: TerrainSource
  frame_id: 'MOON_ME_DE440_ME421' | 'MOON_ME_DE421'
  crs: CrsDefinition
  reference_radius_m: number
  vertical: VerticalInfo
  calc_resolution_m: number
  local_origin: LocalOrigin
  bounds: ProjectedBounds
  nodata: NoDataInfo
  interpolated_pixels: InterpolatedPixelsInfo
  /**
   * @minItems 1
   */
  lods: TerrainLod[]
}
export interface TerrainSource {
  product_id: string
  url: string
  sha256: string | null
  citation: string
}
export interface CrsDefinition {
  proj4: string | null
  wkt: string | null
}
export interface VerticalInfo {
  units: 'm'
  reference: string
  exaggeration_default_factor: 1
}
export interface LocalOrigin {
  latitude_deg: number
  longitude_deg: number
  elevation_m: number
}
export interface ProjectedBounds {
  x_min_m: number
  x_max_m: number
  y_min_m: number
  y_max_m: number
}
export interface NoDataInfo {
  present: boolean
  encoding: string
  area_fraction: number | null
}
export interface InterpolatedPixelsInfo {
  flagged: boolean
  note: string
}
export interface TerrainLod {
  level: number
  visual_resolution_m: number
  width_px: number
  height_px: number
  heights_path: string
  encoding: string
  sha256: string
}
export interface SimulationRequest {
  /**
   * @minItems 1
   * @maxItems 4
   */
  sites: (CatalogSiteSelection | CustomSiteSelection)[]
  frame_id: 'MOON_ME_DE440_ME421' | 'MOON_ME_DE421'
  start_utc: string
  end_utc: string
  observer_height_m: number
  solar_criterion: 'disc_center'
  earth_criterion: EarthCriterion
  terrain_mode: 'dem' | 'idealized_local_plane'
  series_step_s?: number | null
  panel?: null
}
export interface CatalogSiteSelection {
  site_id: string
}
export interface CustomSiteSelection {
  custom: CustomPoint
}
export interface CustomPoint {
  label: string
  latitude_deg: number
  longitude_deg: number
}
export interface EarthCriterion {
  kind: 'center_above_horizon'
  min_elevation_deg: number
}
export interface SimulationAccepted {
  id: string
  status: 'queued' | 'running' | 'done' | 'failed'
  cache_hit: boolean
}
export interface SimulationStatus {
  id: string
  status: 'queued' | 'running' | 'done' | 'failed'
  progress: Progress | null
  error: Problem | null
  result: SimulationResult | null
}
export interface Progress {
  stage: string
  completed_fraction: number
}
/**
 * Eroare în formatul `application/problem+json` (RFC 9457), cu un `code` stabil.
 */
export interface Problem {
  type: string
  title: string
  status: number | null
  detail: string
  code: ErrorCode
  field_errors?: FieldError[] | null
  coverage_start_utc?: string | null
  coverage_end_utc?: string | null
}
export interface FieldError {
  loc: (string | number)[]
  message: string
}
export interface SimulationResult {
  schema_version: '0.4.0'
  request: SimulationRequest
  /**
   * @minItems 1
   * @maxItems 4
   */
  sites: ResultSite[]
  series: SiteSeries[]
  events: SiteEvents[]
  summary: SiteSummary[]
  horizon: SiteHorizon[]
  terrain: SiteTerrain[]
  provenance: Provenance
  quality: Quality
}
export interface ResultSite {
  site_ref: string
  label: string
  kind: 'catalog' | 'custom'
  catalog_id: string | null
  latitude_deg: number
  longitude_deg: number
  frame_id: 'MOON_ME_DE440_ME421' | 'MOON_ME_DE421'
  terrain_elevation_m: number | null
  observer_height_m: number
  on_reference_surface: boolean
  azimuth_convention: 'standard' | 'pole_meridian'
  coordinates_rounded: boolean
}
export interface SiteSeries {
  site_ref: string
  step_s: number
  /**
   * @minItems 1
   */
  time_utc: string[]
  sun: BodySeries
  earth: BodySeries
}
export interface BodySeries {
  azimuth_deg: (number | null)[]
  elevation_deg: number[]
  distance_km: number[]
  angular_radius_deg: number[]
  horizon_elevation_deg: (number | null)[]
  visible: (boolean | null)[]
}
export interface SiteEvents {
  site_ref: string
  sun: BodyEvents
  earth: BodyEvents
}
export interface BodyEvents {
  status: 'found' | 'none_in_interval' | 'unavailable'
  reason: string | null
  events: Event[]
}
export interface Event {
  body: 'sun' | 'earth'
  type: 'appearance' | 'disappearance'
  cause: 'terrain' | 'idealized_horizon'
  time_utc: string
  azimuth_deg: number | null
  elevation_deg: number
  obstacle_distance_m: number | null
  refinement_tolerance_s: number
}
export interface SiteSummary {
  site_ref: string
  sun_visible_duration_s: number | null
  sun_visible_fraction: number | null
  earth_visible_duration_s: number | null
  both_visible_duration_s: number | null
  sun_intervals: TimeInterval[]
  earth_windows: TimeInterval[]
}
export interface TimeInterval {
  start_utc: string
  end_utc: string
  truncated_start: boolean
  truncated_end: boolean
}
export interface SiteHorizon {
  site_ref: string
  mode: 'dem' | 'idealized_local_plane'
  azimuth_step_deg: number
  elevation_deg: (number | null)[]
  obstacle_distance_m: (number | null)[]
  quality: ('complete' | 'partial' | 'no_data')[]
  max_search_distance_m: number | null
  coverage_fraction: number
  dem_products: DemProductUse[]
}
export interface DemProductUse {
  product_id: string
  role: 'near' | 'far'
}
export interface SiteTerrain {
  site_ref: string
  available: boolean
  reason: string | null
  terrain_id: string | null
  product_id: string | null
  calc_resolution_m: number | null
  visual_resolutions_m: number[]
  frame_id: ('MOON_ME_DE440_ME421' | 'MOON_ME_DE421') | null
}
export interface Provenance {
  app_version: string
  computed_at_utc: string
  source_mode: 'live' | 'precomputed'
  kernel_profile: KernelProfileUse
  frame_id: 'MOON_ME_DE440_ME421' | 'MOON_ME_DE421'
  aberration_correction: string
  body_radii_km: {
    [k: string]: number
  }
  dem_products: DemProductUse[]
  horizon_parameters: {
    [k: string]: number | string | boolean
  }
  event_parameters: {
    [k: string]: number | string | boolean
  }
  criteria: {
    [k: string]: number | string | boolean
  }
}
export interface KernelProfileUse {
  profile_id: string
  files: KernelFileUse[]
}
export interface KernelFileUse {
  filename: string
  sha256: string | null
}
export interface Quality {
  issues: QualityIssue[]
  not_computed: NotComputed[]
  approximations: string[]
  limits: string[]
}
export interface QualityIssue {
  code: string
  severity: 'info' | 'warning' | 'error'
  site_ref: string | null
  field: string | null
  message_key: string
}
export interface NotComputed {
  group: 'series' | 'events' | 'summary' | 'horizon' | 'terrain'
  site_ref: string
  reason: string
}
export interface ScenarioIndex {
  schema_version: '0.4.0'
  scenarios: Scenario[]
}
export interface Scenario {
  scenario_id: string
  title_ro: string
  title_en: string
  /**
   * @minItems 1
   * @maxItems 4
   */
  site_ids: string[]
  request: SimulationRequest
  result_path: string
  terrain_manifest_paths: string[]
  result_sha256: string
}
export interface Health {
  status: 'ok' | 'degraded'
  app_version: string
  kernel_profile: string | null
  kernels_loaded: boolean
  dem_products: string[]
  time_utc: string
  issues: string[]
}
export interface Coverage {
  schema_version: '0.4.0'
  temporal: TemporalCoverage
  terrain: TerrainCoverage[]
}
export interface TemporalCoverage {
  start_utc: string
  end_utc: string
  kernel_profile: string
}
export interface TerrainCoverage {
  product_id: string
  role: 'near' | 'far'
  resolution_m: number
  footprint: GeoJsonPolygon | null
  min_latitude_deg: number
  max_latitude_deg: number
}
