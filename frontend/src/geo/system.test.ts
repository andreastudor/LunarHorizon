import { expect, test } from 'vitest'
import { systemScenePoint } from './system.ts'

test('schematic transform preserves physical arrays and exaggerates only lunar displacement', () => {
  const earth = [150000000, 0, 0],
    moon = [150000000, 400000, 0]
  expect(systemScenePoint('sun', earth, moon)).toEqual([0, 0, -0])
  expect(systemScenePoint('earth', earth, moon)).toEqual([75, 0, -0])
  expect(systemScenePoint('moon', earth, moon)).toEqual([75, 0, -16])
  expect(moon).toEqual([150000000, 400000, 0])
})
