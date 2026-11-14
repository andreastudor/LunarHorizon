// Imperative Three.js controller for the global lunar map. All geometry comes from geo/globe.ts, so
// the texture, the markers and the click → latitude/longitude conversion share one convention.
// Rendering is visual only: nothing here feeds a calculation (CLAUDE.md).

import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import {
  MOON_RADIUS_KM,
  buildSphere,
  geoToScene,
  graticule,
  isClick,
  ringToScene,
  sceneToGeo,
  type PointerSample,
} from '../geo/globe.ts'
import type { Vec3 } from '../geo/vec3.ts'
import {
  WebGLUnavailableError,
  type GlobeFactory,
  type GlobeHandle,
  type GlobeOptions,
  type GlobeState,
} from './types.ts'

const COLORS = {
  background: 0x05070b,
  graticule: 0x9aa4b2,
  catalog: 0xe5e7eb,
  selected: 0xff8a3d,
  custom: 0x4ade80,
  coverage: 0x22d3ee,
  sun: 0xfacc15,
  earth: 0x60a5fa,
}
const MARKER_RADIUS_KM = 16
const ARROW_LENGTH_KM = 800
/** Initial view: from above 65°S on the 0° meridian, so the south pole is in view. */
const INITIAL_VIEW: [number, number] = [-65, 0]
const INITIAL_DISTANCE_KM = MOON_RADIUS_KM * 3.4

const toVector = ([x, y, z]: Vec3) => new THREE.Vector3(x, y, z)

function webglAvailable(): boolean {
  try {
    const canvas = document.createElement('canvas')
    return Boolean(canvas.getContext('webgl2') ?? canvas.getContext('webgl'))
  } catch {
    return false
  }
}

function disposeObject(object: THREE.Object3D): void {
  object.traverse((child) => {
    const mesh = child as THREE.Mesh
    mesh.geometry?.dispose()
    const material = mesh.material as
      THREE.Material | THREE.Material[] | undefined
    if (Array.isArray(material)) material.forEach((m) => m.dispose())
    else material?.dispose()
  })
}

export const createThreeGlobe: GlobeFactory = (
  container: HTMLElement,
  options: GlobeOptions,
): GlobeHandle => {
  if (!webglAvailable()) throw new WebGLUnavailableError()
  let renderer: THREE.WebGLRenderer
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true })
  } catch {
    throw new WebGLUnavailableError()
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.outputColorSpace = THREE.SRGBColorSpace
  renderer.domElement.setAttribute('aria-hidden', 'true')
  container.appendChild(renderer.domElement)

  const scene = new THREE.Scene()
  scene.background = new THREE.Color(COLORS.background)
  const camera = new THREE.PerspectiveCamera(40, 1, 10, 100_000)
  const controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.08
  controls.minDistance = MOON_RADIUS_KM * 1.02
  controls.maxDistance = MOON_RADIUS_KM * 10
  controls.screenSpacePanning = true

  const ambient = new THREE.AmbientLight(0xffffff, 1.4)
  const sunLight = new THREE.DirectionalLight(0xffffff, 0)
  scene.add(ambient, sunLight)

  // Moon sphere with the E05 texture (equirectangular, centred on 0°).
  const mesh = buildSphere(128, 256)
  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute(
    'position',
    new THREE.BufferAttribute(mesh.positions, 3),
  )
  geometry.setAttribute('normal', new THREE.BufferAttribute(mesh.normals, 3))
  geometry.setAttribute('uv', new THREE.BufferAttribute(mesh.uvs, 2))
  geometry.setIndex(new THREE.BufferAttribute(mesh.indices, 1))
  const material = new THREE.MeshLambertMaterial({ color: 0x8a8f98 })
  const moon = new THREE.Mesh(geometry, material)
  scene.add(moon)
  new THREE.TextureLoader().load(
    options.textureUrl,
    (texture) => {
      texture.colorSpace = THREE.SRGBColorSpace
      texture.anisotropy = renderer.capabilities.getMaxAnisotropy()
      material.map = texture
      material.color.set(0xffffff)
      material.needsUpdate = true
    },
    undefined,
    () => options.onTextureError(),
  )

  // Graticule every 15° of latitude and 30° of longitude; equator and prime meridian brighter.
  const grid = new THREE.Group()
  for (const line of graticule(15, 30)) {
    // Equator: every point has y = 0; prime meridian: every point has x = 0 and z ≥ 0.
    const isMain =
      line.every((p) => Math.abs(p[1]) < 1e-6) ||
      line.every((p) => Math.abs(p[0]) < 1e-6 && p[2] >= -1e-6)
    const lineGeometry = new THREE.BufferGeometry().setFromPoints(
      line.map(toVector),
    )
    grid.add(
      new THREE.Line(
        lineGeometry,
        new THREE.LineBasicMaterial({
          color: COLORS.graticule,
          transparent: true,
          opacity: isMain ? 0.55 : 0.22,
        }),
      ),
    )
  }
  scene.add(grid)

  const dynamic = new THREE.Group()
  scene.add(dynamic)

  const resetCamera = () => {
    const direction = toVector(geoToScene(...INITIAL_VIEW)).normalize()
    camera.position.copy(direction.multiplyScalar(INITIAL_DISTANCE_KM))
    controls.target.set(0, 0, 0)
    controls.update()
  }
  resetCamera()

  const resize = () => {
    const width = Math.max(container.clientWidth, 1)
    const height = Math.max(container.clientHeight, 1)
    renderer.setSize(width, height, false)
    renderer.domElement.style.width = '100%'
    renderer.domElement.style.height = '100%'
    camera.aspect = width / height
    camera.updateProjectionMatrix()
  }
  resize()
  const observer = new ResizeObserver(resize)
  observer.observe(container)

  // Picking: a click (not a drag) on the sphere gives latitude/longitude on the reference sphere.
  const raycaster = new THREE.Raycaster()
  let down: PointerSample | null = null
  const onPointerDown = (event: PointerEvent) => {
    down = { x: event.clientX, y: event.clientY, timeMs: event.timeStamp }
  }
  const onPointerUp = (event: PointerEvent) => {
    const up = { x: event.clientX, y: event.clientY, timeMs: event.timeStamp }
    if (!down || event.button !== 0 || !isClick(down, up)) return
    const rect = renderer.domElement.getBoundingClientRect()
    const ndc = new THREE.Vector2(
      ((event.clientX - rect.left) / rect.width) * 2 - 1,
      -((event.clientY - rect.top) / rect.height) * 2 + 1,
    )
    raycaster.setFromCamera(ndc, camera)
    const hit = raycaster.intersectObject(moon, false)[0]
    if (!hit) return
    const { latitudeDeg, longitudeDeg } = sceneToGeo([
      hit.point.x,
      hit.point.y,
      hit.point.z,
    ])
    options.onPick(latitudeDeg, longitudeDeg)
  }
  renderer.domElement.addEventListener('pointerdown', onPointerDown)
  renderer.domElement.addEventListener('pointerup', onPointerUp)

  renderer.setAnimationLoop(() => {
    controls.update()
    renderer.render(scene, camera)
  })

  return {
    update(state: GlobeState) {
      disposeObject(dynamic)
      dynamic.clear()
      const markerGeometry = new THREE.SphereGeometry(MARKER_RADIUS_KM, 16, 12)
      for (const marker of state.markers) {
        const color =
          marker.kind === 'custom'
            ? COLORS.custom
            : marker.selected
              ? COLORS.selected
              : COLORS.catalog
        const dot = new THREE.Mesh(
          markerGeometry.clone(),
          new THREE.MeshBasicMaterial({ color }),
        )
        dot.position.copy(
          toVector(geoToScene(marker.latitudeDeg, marker.longitudeDeg, 4)),
        )
        if (marker.selected) dot.scale.setScalar(1.8)
        dynamic.add(dot)
      }
      markerGeometry.dispose()
      for (const area of state.coverage) {
        const points = ringToScene(area.ring).map(toVector)
        dynamic.add(
          new THREE.LineLoop(
            new THREE.BufferGeometry().setFromPoints(points),
            new THREE.LineBasicMaterial({ color: COLORS.coverage }),
          ),
        )
      }
      const directions = state.directions
      if (directions) {
        const origin = toVector(
          geoToScene(directions.latitudeDeg, directions.longitudeDeg, 4),
        )
        for (const [vector, color] of [
          [directions.sun, COLORS.sun],
          [directions.earth, COLORS.earth],
        ] as const) {
          if (!vector) continue
          dynamic.add(
            new THREE.ArrowHelper(
              toVector(vector).normalize(),
              origin,
              ARROW_LENGTH_KM,
              color,
              ARROW_LENGTH_KM * 0.18,
              ARROW_LENGTH_KM * 0.09,
            ),
          )
        }
      }
      // Lighting follows the API Sun direction at the selected time (visual only); without it the
      // globe is evenly lit, so no illumination is implied.
      if (directions?.sun) {
        sunLight.position.copy(toVector(directions.sun).multiplyScalar(10_000))
        sunLight.intensity = 2.6
        ambient.intensity = 0.22
      } else {
        sunLight.intensity = 0
        ambient.intensity = 1.4
      }
    },
    resetCamera,
    focus(latitudeDeg: number, longitudeDeg: number) {
      const distance = Math.max(camera.position.length(), MOON_RADIUS_KM * 1.6)
      const direction = toVector(
        geoToScene(latitudeDeg, longitudeDeg),
      ).normalize()
      camera.position.copy(direction.multiplyScalar(distance))
      controls.target.set(0, 0, 0)
      controls.update()
    },
    dispose() {
      renderer.setAnimationLoop(null)
      observer.disconnect()
      renderer.domElement.removeEventListener('pointerdown', onPointerDown)
      renderer.domElement.removeEventListener('pointerup', onPointerUp)
      controls.dispose()
      disposeObject(scene)
      material.map?.dispose()
      renderer.dispose()
      renderer.domElement.remove()
    },
  }
}
