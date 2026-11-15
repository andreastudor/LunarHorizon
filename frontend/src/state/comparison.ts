import type { SimulationResult } from '../contracts/generated.ts'
import type { Selection, SimulationParams } from './types.ts'
import { buildRequest, selectionKey } from './model.ts'

export interface ComparisonEntry {
  selection: NonNullable<Selection>
  frameId: string
  label: string
}
export const comparisonKey = (entries: ComparisonEntry[]) =>
  JSON.stringify(entries)
export function comparisonRequest(
  entries: ComparisonEntry[],
  params: SimulationParams,
) {
  if (
    entries.length < 2 ||
    entries.length > 4 ||
    entries.some((e) => e.frameId !== params.frameId)
  )
    return null
  if (
    new Set(entries.map((e) => selectionKey(e.selection))).size !==
    entries.length
  )
    return null
  const requests = entries.map((e) => buildRequest(e.selection, params).request)
  if (requests.some((r) => !r)) return null
  return { ...requests[0]!, sites: requests.flatMap((r) => r!.sites) }
}
/** Preserve provenance/quality while selecting the corresponding records, never array-index joins. */
export function resultForSite(
  result: SimulationResult,
  index: number,
): SimulationResult {
  const site = result.sites[index] ?? result.sites[0]
  return {
    ...result,
    sites: [site],
    series: result.series.filter((s) => s.site_ref === site.site_ref),
    events: result.events.filter((s) => s.site_ref === site.site_ref),
    summary: result.summary.filter((s) => s.site_ref === site.site_ref),
  }
}
