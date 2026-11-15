// Imperative Three.js controller of the local terrain scene (E08). Geometry comes from geo/terrain.ts
// in true metres; vertical exaggeration is a scale on the terrain group only (visual). Lighting and
// shadows follow the Sun direction of the API result and are visual only: visibility is never
// derived from them (CLAUDE.md: the calculation does not use the render geometry).

import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { isClick, type PointerSample } from '../geo/globe.ts'
import { truePoint, visualPoint } from '../geo/terrain.ts'
import type { TerrainMesh } from '../geo/terrain.ts'
import type { Vec3 } from '../geo/vec3.ts'
import {
  WebGLUnavailableError,
  type TerrainCameraMode,
  type TerrainFactory,
  type TerrainHandle,
  type TerrainOptions,
  type TerrainSceneState,
} from './types.ts'

const COLORS = {
  background: 0x05070b,
  terrain: 0x9a9a9a,
  noData: 0xef4444,
  outline: 0x22d3ee,
  observer: 0x4ade80,
  sun: 0xfacc15,
  earth: 0x60a5fa,
}

const toVector = ([x, y, z]: Vec3) => new THREE.Vector3(x, y, z)

function webglAvailable(): boolean {
  try {
    const canvas = document.createElement('canvas')
    return Boolean(canvas.getContext('webgl2') ?? canvas.getContext('webgl'))
  } catch {
    return false
  }
}

export const createThreeTerrain: TerrainFactory = (
  container: HTMLElement,
  options: TerrainOptions,
): TerrainHandle => {
  if (!webglAvailable()) throw new WebGLUnavailableError()
  let renderer: THREE.WebGLRenderer
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true })
  } catch {
    throw new WebGLUnavailableError()
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.outputColorSpace = THREE.SRGBColorSpace
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFShadowMap
  renderer.domElement.setAttribute('aria-hidden', 'true')
  container.appendChild(renderer.domElement)
  container.dataset.webgl = renderer.capabilities.isWebGL2 ? 'webgl2' : 'webgl1'

  const scene = new THREE.Scene()
  scene.background = new THREE.Color(COLORS.background)
  const camera = new THREE.PerspectiveCamera(50, 1, 0.5, 400_000)
  const controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.screenSpacePanning = true

  const ambient = new THREE.AmbientLight(0xffffff, 0.35)
  const sunLight = new THREE.DirectionalLight(0xffffff, 0)
  sunLight.castShadow = true
  sunLight.shadow.mapSize.set(2048, 2048)
  sunLight.shadow.bias = -0.0005
  scene.add(ambient, sunLight, sunLight.target)

  // Materials are created once and reused; only geometries change with the terrain.
  const terrainMaterial = new THREE.MeshStandardMaterial({
    color: COLORS.terrain,
    roughness: 1,
    metalness: 0,
  })
  const noDataMaterial = new THREE.MeshBasicMaterial({
    color: COLORS.noData,
    transparent: true,
    opacity: 0.55,
    side: THREE.DoubleSide,
  })
  const outlineMaterial = new THREE.LineBasicMaterial({ color: COLORS.outline })
  const observerMaterial = new THREE.MeshBasicMaterial({
    color: COLORS.observer,
  })

  const terrainGroup = new THREE.Group() // exaggerated as a whole (visual only)
  scene.add(terrainGroup)
  const overlay = new THREE.Group() // observer and arrows, positioned with visualPoint()
  scene.add(overlay)

  let terrainMesh: THREE.Mesh | null = null
  let currentMesh: TerrainMesh | null = null
  let state: TerrainSceneState | null = null
  let mode: TerrainCameraMode = 'oblique'
  let meshBuilds = 0
  let probed = false

  // Observer view: look around from the eye with drag (yaw/pitch), no orbiting.
  let yaw = 0
  let pitch = 0

  const disposeGroup = (group: THREE.Group) => {
    group.traverse((child) => {
      const object = child as THREE.Mesh
      if (object.geometry) object.geometry.dispose()
    })
    group.clear()
  }

  // Diagnostics for tests (frontend/e2e).
  const publishStats = () => {
    container.dataset.meshBuilds = String(meshBuilds)
    container.dataset.terrainVertices = String(currentMesh?.vertexCount ?? 0)
    container.dataset.terrainTriangles = String(
      (currentMesh?.indices.length ?? 0) / 3,
    )
    container.dataset.noDataVertices = String(currentMesh?.noDataVertices ?? 0)
  }

  const setTerrain = (mesh: TerrainMesh | null) => {
    disposeGroup(terrainGroup)
    terrainMesh = null
    currentMesh = mesh
    probed = false
    if (!mesh) {
      publishStats()
      return
    }
    // NoData vertices are never referenced by triangles; a finite placeholder keeps the bounding
    // volumes finite.
    const positions = Float32Array.from(mesh.positions, (value) =>
      Number.isFinite(value) ? value : 0,
    )
    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    geometry.setIndex(new THREE.BufferAttribute(mesh.indices, 1))
    geometry.computeVertexNormals()
    geometry.computeBoundingSphere()
    terrainMesh = new THREE.Mesh(geometry, terrainMaterial)
    terrainMesh.castShadow = true
    terrainMesh.receiveShadow = true
    terrainGroup.add(terrainMesh)
    if (mesh.noDataPositions.length > 0) {
      const noData = new THREE.BufferGeometry()
      noData.setAttribute(
        'position',
        new THREE.BufferAttribute(mesh.noDataPositions, 3),
      )
      terrainGroup.add(new THREE.Mesh(noData, noDataMaterial))
    }
    const outline = new THREE.BufferGeometry()
    outline.setAttribute('position', new THREE.BufferAttribute(mesh.outline, 3))
    terrainGroup.add(new THREE.LineLoop(outline, outlineMaterial))
    meshBuilds += 1
    const half = mesh.extentM * 0.75
    const shadowCamera = sunLight.shadow.camera
    shadowCamera.left = -half
    shadowCamera.right = half
    shadowCamera.top = half
    shadowCamera.bottom = -half
    shadowCamera.near = 1
    shadowCamera.far = mesh.extentM * 6
    shadowCamera.updateProjectionMatrix()
    publishStats()
  }

  const exaggeration = () => state?.exaggeration ?? 1
  const extent = () => currentMesh?.extentM ?? 16_000

  const siteCenter = (): THREE.Vector3 =>
    state?.observer
      ? toVector(visualPoint(state.observer.ground, exaggeration()))
      : new THREE.Vector3(0, 0, 0)

  const visualEye = (): THREE.Vector3 | null => {
    if (!state?.observer) return null
    const { ground, eye } = state.observer
    const lift = eye[1] - ground[1]
    const base = visualPoint(ground, exaggeration())
    return new THREE.Vector3(base[0], base[1] + lift, base[2])
  }

  const applyObserverLook = () => {
    const eye = visualEye()
    if (!eye) return
    const direction = new THREE.Vector3(
      Math.sin(yaw) * Math.cos(pitch),
      Math.sin(pitch),
      -Math.cos(yaw) * Math.cos(pitch),
    )
    camera.position.copy(eye)
    camera.lookAt(eye.clone().add(direction))
  }

  const setCamera = (next: TerrainCameraMode) => {
    mode = next
    const center = siteCenter()
    const size = extent()
    controls.enabled = mode !== 'observer'
    if (mode === 'top') {
      controls.target.copy(center)
      camera.position.set(center.x, center.y + size * 1.3, center.z + 1)
    } else if (mode === 'oblique') {
      controls.target.copy(center)
      camera.position.set(
        center.x + size * 0.45,
        center.y + size * 0.35,
        center.z + size * 0.55,
      )
    } else {
      // Face the Sun's azimuth when its direction is known, otherwise north (−z).
      const sun = state?.sun
      yaw = sun ? Math.atan2(sun[0], -sun[2]) : 0
      pitch = 0
      applyObserverLook()
    }
    if (mode !== 'observer') controls.update()
    container.dataset.camera = mode
  }

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
  const resizeObserver = new ResizeObserver(resize)
  resizeObserver.observe(container)

  // Picking (click, not drag) and observer look-around.
  const raycaster = new THREE.Raycaster()
  let down: PointerSample | null = null
  let dragging = false
  let last = { x: 0, y: 0 }
  const onPointerDown = (event: PointerEvent) => {
    down = { x: event.clientX, y: event.clientY, timeMs: event.timeStamp }
    dragging = true
    last = { x: event.clientX, y: event.clientY }
  }
  const onPointerMove = (event: PointerEvent) => {
    if (!dragging || mode !== 'observer') return
    yaw += (event.clientX - last.x) * 0.004
    pitch = Math.max(
      -1.4,
      Math.min(1.4, pitch + (event.clientY - last.y) * 0.004),
    )
    last = { x: event.clientX, y: event.clientY }
    applyObserverLook()
  }
  const onPointerUp = (event: PointerEvent) => {
    dragging = false
    const up = { x: event.clientX, y: event.clientY, timeMs: event.timeStamp }
    if (!down || event.button !== 0 || !isClick(down, up) || !terrainMesh)
      return
    const rect = renderer.domElement.getBoundingClientRect()
    const ndc = new THREE.Vector2(
      ((event.clientX - rect.left) / rect.width) * 2 - 1,
      -((event.clientY - rect.top) / rect.height) * 2 + 1,
    )
    raycaster.setFromCamera(ndc, camera)
    const hit = raycaster.intersectObject(terrainMesh, false)[0]
    if (!hit) return
    options.onPick(
      truePoint([hit.point.x, hit.point.y, hit.point.z], exaggeration()),
    )
  }
  renderer.domElement.addEventListener('pointerdown', onPointerDown)
  renderer.domElement.addEventListener('pointermove', onPointerMove)
  renderer.domElement.addEventListener('pointerup', onPointerUp)

  const probe = () => {
    const gl = renderer.getContext()
    const width = gl.drawingBufferWidth
    const height = gl.drawingBufferHeight
    const pixel = new Uint8Array(4)
    const samples: string[] = []
    for (const [fx, fy] of [
      [0.5, 0.5],
      [0.4, 0.45],
      [0.6, 0.45],
      [0.45, 0.6],
      [0.55, 0.6],
    ]) {
      gl.readPixels(
        Math.floor(width * fx),
        Math.floor(height * fy),
        1,
        1,
        gl.RGBA,
        gl.UNSIGNED_BYTE,
        pixel,
      )
      samples.push(`${pixel[0]},${pixel[1]},${pixel[2]}`)
    }
    container.dataset.samples = samples.join(';')
    container.dataset.terrainReady = 'true'
    publishStats()
  }

  let publishedGeometries = -1
  renderer.setAnimationLoop(() => {
    if (mode !== 'observer') controls.update()
    renderer.render(scene, camera)
    // GPU geometry count after this frame (published only when it changes).
    const geometries = renderer.info.memory.geometries
    if (geometries !== publishedGeometries) {
      publishedGeometries = geometries
      container.dataset.geometries = String(geometries)
    }
    if (!probed && terrainMesh) {
      probed = true
      probe()
    }
  })

  return {
    update(next: TerrainSceneState) {
      const meshChanged = next.mesh !== currentMesh
      const observerAppeared = !state?.observer && Boolean(next.observer)
      state = next
      if (meshChanged) {
        container.dataset.terrainReady = 'false'
        setTerrain(next.mesh)
      }
      terrainGroup.scale.set(1, next.exaggeration, 1)
      container.dataset.exaggeration = String(next.exaggeration)

      disposeGroup(overlay)
      const eye = visualEye()
      if (eye && next.observer) {
        const ground = toVector(
          visualPoint(next.observer.ground, next.exaggeration),
        )
        const size = extent()
        const marker = new THREE.Mesh(
          new THREE.SphereGeometry(size * 0.004, 16, 12),
          observerMaterial,
        )
        marker.position.copy(ground)
        overlay.add(marker)
        const length = size * 0.18
        for (const [vector, color] of [
          [next.sun, COLORS.sun],
          [next.earth, COLORS.earth],
        ] as const) {
          if (!vector) continue
          overlay.add(
            new THREE.ArrowHelper(
              toVector(vector).normalize(),
              eye,
              length,
              color,
              length * 0.12,
              length * 0.05,
            ),
          )
        }
      }

      // Visual lighting from the Sun direction of the result; none when it is below the horizon.
      // Without a Sun direction the scene uses neutral display lighting (labelled in the UI).
      if (next.sun) {
        const target = siteCenter()
        sunLight.target.position.copy(target)
        sunLight.position.copy(
          target.clone().add(toVector(next.sun).multiplyScalar(extent() * 2)),
        )
        sunLight.intensity = (next.sunElevationDeg ?? 0) >= 0 ? 2.8 : 0
        ambient.intensity = 0.25
        container.dataset.light = next.sun.map((v) => v.toFixed(4)).join(',')
      } else {
        sunLight.target.position.set(0, 0, 0)
        // Neutral display light: low and from the north-west, to reveal the relief (not the Sun).
        sunLight.position.set(-1, 0.45, -0.8).multiplyScalar(extent() * 2)
        sunLight.intensity = 1.6
        ambient.intensity = 0.55
        container.dataset.light = 'neutral'
      }
      if (meshChanged || observerAppeared) setCamera(mode)
      else if (mode === 'observer') applyObserverLook()
      publishStats()
    },
    setCamera,
    goToSite() {
      setCamera('oblique')
    },
    dispose() {
      renderer.setAnimationLoop(null)
      resizeObserver.disconnect()
      renderer.domElement.removeEventListener('pointerdown', onPointerDown)
      renderer.domElement.removeEventListener('pointermove', onPointerMove)
      renderer.domElement.removeEventListener('pointerup', onPointerUp)
      controls.dispose()
      disposeGroup(terrainGroup)
      disposeGroup(overlay)
      terrainMaterial.dispose()
      noDataMaterial.dispose()
      outlineMaterial.dispose()
      observerMaterial.dispose()
      sunLight.shadow.map?.dispose()
      renderer.dispose()
      renderer.domElement.remove()
    },
  }
}
