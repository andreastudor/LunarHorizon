import { expect, test } from 'vitest'
import { toPolar, fromPolar, lunarGeographic } from './map.ts'

test('lunar polar round trips across the seam and pole without terrestrial projection', () => {
  for (const point of [
    [31.7, -85.4],
    [-179.99, -88],
    [179.99, -87],
    [0, -90],
  ]) {
    const roundtrip = fromPolar(toPolar(point))
    expect(roundtrip[0]).toBeCloseTo(point[0], 9)
    expect(roundtrip[1]).toBeCloseTo(point[1], 9)
  }
  expect(lunarGeographic.getMetersPerUnit()).toBeCloseTo(
    (Math.PI * 1737400) / 180,
  )
})
