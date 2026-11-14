// Transformările către scenele 3D (docs/SPEC_FIZICA.md §10.1). Three.js folosește un sistem drept,
// cu axa Y în sus.
//
// Scena globală — kilometri, centrul Lunii în origine:
//   (x_s, y_s, z_s) = (Y_ME, Z_ME, X_ME) / 1000
//   polul nord pe +y, meridianul 0° pe +z, 90°E pe +x.
// Scena locală — metri, origine pe teren în punctul de referință al sitului:
//   (x_s, y_s, z_s) = (e, u, -n)
//   est pe +x, zenit pe +y, nord pe -z.
// Ambele sunt permutări sau reflexii compuse care păstrează orientarea dreaptă (det = +1).
// Exagerarea verticală, dacă se aplică, este numai vizuală și nu face parte din aceste funcții.

import {
  enuFromAzEl,
  geographicToMe,
  localEnuToMe,
  meToGeographic,
  meToLocalEnu,
  type Geographic,
} from './coords.ts'
import type { Vec3 } from './vec3.ts'

const M_PER_KM = 1000

export const meToGlobalScene = ([x, y, z]: Vec3): Vec3 => [
  y / M_PER_KM,
  z / M_PER_KM,
  x / M_PER_KM,
]

export const globalSceneToMe = ([xs, ys, zs]: Vec3): Vec3 => [
  zs * M_PER_KM,
  xs * M_PER_KM,
  ys * M_PER_KM,
]

/** Punct ales pe glob → coordonate lunare (înălțimea față de sfera de referință). */
export const globalScenePointToGeographic = (
  pointScene: Vec3,
  radiusM: number,
): Geographic => meToGeographic(globalSceneToMe(pointScene), radiusM)

export const enuToLocalScene = ([e, n, u]: Vec3): Vec3 => [e, u, -n + 0]

export const localSceneToEnu = ([xs, ys, zs]: Vec3): Vec3 => [xs, -zs + 0, ys]

/** Direcția spre un corp, din azimut și elevație, ca versor în scena locală. */
export const directionToLocalScene = (
  azimuthDeg: number,
  elevationDeg: number,
): Vec3 => enuToLocalScene(enuFromAzEl(azimuthDeg, elevationDeg))

/** Cadrul scenei locale, legat de originea unui sit. */
export class LocalSceneFrame {
  readonly origin: Geographic
  readonly radiusM: number
  readonly originMe: Vec3

  constructor(origin: Geographic, radiusM: number) {
    this.origin = origin
    this.radiusM = radiusM
    this.originMe = geographicToMe(
      origin.latitudeDeg,
      origin.longitudeDeg,
      origin.heightM,
      radiusM,
    )
  }

  meToScene(pointMe: Vec3): Vec3 {
    return enuToLocalScene(
      meToLocalEnu(
        pointMe,
        this.origin.latitudeDeg,
        this.origin.longitudeDeg,
        this.originMe,
      ),
    )
  }

  sceneToMe(pointScene: Vec3): Vec3 {
    return localEnuToMe(
      localSceneToEnu(pointScene),
      this.origin.latitudeDeg,
      this.origin.longitudeDeg,
      this.originMe,
    )
  }

  geographicToScene({ latitudeDeg, longitudeDeg, heightM }: Geographic): Vec3 {
    return this.meToScene(
      geographicToMe(latitudeDeg, longitudeDeg, heightM, this.radiusM),
    )
  }

  sceneToGeographic(pointScene: Vec3): Geographic {
    return meToGeographic(this.sceneToMe(pointScene), this.radiusM)
  }
}
