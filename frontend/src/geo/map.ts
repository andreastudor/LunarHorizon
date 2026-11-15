import Projection from 'ol/proj/Projection.js'
import { addProjection, addCoordinateTransforms } from 'ol/proj.js'
import { SouthPolarStereographic } from './projection.ts'
import { REFERENCE_RADIUS_M } from './conventions.ts'

const polar = new SouthPolarStereographic()
export const lunarGeographic = new Projection({
  code: 'LUNAR:GEOGRAPHIC',
  units: 'degrees',
  extent: [-180, -90, 180, 90],
  global: true,
  metersPerUnit: (Math.PI * REFERENCE_RADIUS_M) / 180,
})
export const lunarPolar = new Projection({
  code: 'LUNAR:SOUTH',
  units: 'm',
  extent: [-1000000, -1000000, 1000000, 1000000],
  worldExtent: [-180, -90, 180, -60],
})
addProjection(lunarGeographic)
addProjection(lunarPolar)
export const toPolar = (p: number[]) =>
  polar.forward(Math.min(p[1], 89.999999), p[0])
export const fromPolar = (p: number[]) => {
  const v = polar.inverse(p[0], p[1])
  return [v.longitudeDeg, v.latitudeDeg]
}
addCoordinateTransforms(lunarGeographic, lunarPolar, toPolar, fromPolar)
