// Proiecția stereografică polară sudică pe sferă; oglinda lui
// backend/lunarhorizon/core/projection.py. Parametrii impliciți sunt provizorii (D-05, D-06).
//   rho = 2·R·k0·tan(45° + lat/2),  x = rho·sin(lon - lon0),  y = rho·cos(lon - lon0)
//   k   = 2·k0 / (1 - sin(lat))

import { REFERENCE_RADIUS_M } from './conventions.ts'
import {
  CoordinateError,
  validateLatitudeDeg,
  wrapLongitudeDeg,
} from './coords.ts'
import { degToRad, radToDeg } from './vec3.ts'

export interface SouthPolarStereographicParams {
  radiusM: number
  centralMeridianDeg: number
  scaleFactor: number
  status: 'provisional' | 'confirmed'
}

export const DEFAULT_SOUTH_POLAR_STEREOGRAPHIC: SouthPolarStereographicParams =
  {
    radiusM: REFERENCE_RADIUS_M,
    centralMeridianDeg: 0,
    scaleFactor: 1,
    status: 'provisional',
  }

export class SouthPolarStereographic {
  readonly params: SouthPolarStereographicParams

  constructor(
    params: SouthPolarStereographicParams = DEFAULT_SOUTH_POLAR_STEREOGRAPHIC,
  ) {
    this.params = params
  }

  /** (lat, lon) → [x_m, y_m]. Polul nord nu este reprezentabil. */
  forward(latitudeDeg: number, longitudeDeg: number): [number, number] {
    validateLatitudeDeg(latitudeDeg)
    if (latitudeDeg === 90)
      throw new CoordinateError('latitude_out_of_range', latitudeDeg)
    const { radiusM, scaleFactor, centralMeridianDeg } = this.params
    const rho =
      2 *
      radiusM *
      scaleFactor *
      Math.tan(Math.PI / 4 + degToRad(latitudeDeg) / 2)
    const delta = degToRad(longitudeDeg - centralMeridianDeg)
    return [rho * Math.sin(delta), rho * Math.cos(delta)]
  }

  /** [x_m, y_m] → (lat, lon). În origine, longitudinea este meridianul central. */
  inverse(
    xM: number,
    yM: number,
  ): { latitudeDeg: number; longitudeDeg: number } {
    if (!Number.isFinite(xM) || !Number.isFinite(yM)) {
      throw new CoordinateError('not_finite', [xM, yM])
    }
    const { radiusM, scaleFactor, centralMeridianDeg } = this.params
    const rho = Math.hypot(xM, yM)
    const latitudeDeg =
      -90 + 2 * radToDeg(Math.atan(rho / (2 * radiusM * scaleFactor)))
    const longitudeDeg = wrapLongitudeDeg(
      centralMeridianDeg + radToDeg(Math.atan2(xM, yM)),
    )
    return { latitudeDeg, longitudeDeg }
  }

  /** Factorul de scară local: distanța în plan / distanța pe sferă. */
  scale(latitudeDeg: number): number {
    return (2 * this.params.scaleFactor) / (1 - Math.sin(degToRad(latitudeDeg)))
  }

  toProj4(): string {
    const { radiusM, scaleFactor, centralMeridianDeg } = this.params
    return (
      `+proj=stere +lat_0=-90 +lon_0=${centralMeridianDeg} +k=${scaleFactor} ` +
      `+x_0=0 +y_0=0 +R=${radiusM} +units=m +no_defs`
    )
  }
}
