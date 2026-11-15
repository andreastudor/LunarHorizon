import { expect, test } from 'vitest'
import { comparisonRequest, type ComparisonEntry } from './comparison.ts'
import { defaultParams } from './model.ts'

test('2–4 sites share one request and incompatible frames are refused', () => {
  const params = defaultParams(new Date('2026-11-15T00:00:00Z'))
  const entries: ComparisonEntry[] = Array.from({ length: 4 }, (_, i) => ({
    selection: {
      kind: 'custom',
      label: `synthetic_${i}`,
      latitudeDeg: -85,
      longitudeDeg: i,
    },
    label: `synthetic_${i}`,
    frameId: params.frameId,
  }))
  for (const n of [2, 3, 4])
    expect(comparisonRequest(entries.slice(0, n), params)?.sites).toHaveLength(
      n,
    )
  expect(comparisonRequest(entries.slice(0, 1), params)).toBeNull()
  expect(comparisonRequest([entries[0], entries[0]], params)).toBeNull()
  expect(
    comparisonRequest(
      [{ ...entries[0], frameId: 'MOON_ME_DE421' }, entries[1]],
      params,
    ),
  ).toBeNull()
})
