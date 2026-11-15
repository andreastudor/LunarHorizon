import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import type { SystemSeries } from '../contracts/generated.ts'
import { systemScenePoint, type SystemBody } from '../geo/system.ts'
import { en } from '../i18n/en.ts'

export interface SystemHandle {
  update(index: number): void
  focus(body: SystemBody | null): void
  dispose(): void
}
const BODIES: SystemBody[] = ['sun', 'earth', 'moon']
const COLOURS = { sun: 0xfbbf24, earth: 0x38bdf8, moon: 0xd6d3d1 }
const RADII = { sun: 6, earth: 2.5, moon: 1.1 }

export function createThreeSystem(
  container: HTMLElement,
  data: SystemSeries,
): SystemHandle {
  const renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.outputColorSpace = THREE.SRGBColorSpace
  renderer.domElement.setAttribute('aria-label', en.system.title)
  container.appendChild(renderer.domElement)
  const scene = new THREE.Scene()
  scene.background = new THREE.Color(0x05070b)
  const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 3000)
  const controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.minDistance = 4
  controls.maxDistance = 500
  scene.add(new THREE.AmbientLight(0xffffff, 2.2))
  const light = new THREE.DirectionalLight(0xffffff, 2)
  light.position.set(15, 25, 10)
  scene.add(light)
  const meshes = {} as Record<SystemBody, THREE.Mesh>
  const labels = {} as Record<SystemBody, THREE.Sprite>
  const textures: THREE.Texture[] = []
  for (const body of BODIES) {
    const material =
      body === 'sun'
        ? new THREE.MeshBasicMaterial({ color: COLOURS[body] })
        : new THREE.MeshStandardMaterial({
            color: COLOURS[body],
            roughness: 0.85,
          })
    const mesh = new THREE.Mesh(
      new THREE.SphereGeometry(RADII[body], 40, 24),
      material,
    )
    meshes[body] = mesh
    scene.add(mesh)
    const canvas = document.createElement('canvas')
    canvas.width = 256
    canvas.height = 64
    const ctx = canvas.getContext('2d')!
    ctx.font = 'bold 28px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillStyle = '#f8fafc'
    ctx.fillText(en.system[body], 128, 42)
    const texture = new THREE.CanvasTexture(canvas)
    textures.push(texture)
    const sprite = new THREE.Sprite(
      new THREE.SpriteMaterial({ map: texture, depthTest: false }),
    )
    sprite.scale.set(12, 3, 1)
    labels[body] = sprite
    scene.add(sprite)
    if (body !== 'sun') {
      const points = data.time_utc.map(
        (_, i) =>
          new THREE.Vector3(
            ...systemScenePoint(
              body,
              data.position_km.earth[i],
              data.position_km.moon[i],
            ),
          ),
      )
      const path = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(points),
        new THREE.LineBasicMaterial({
          color: COLOURS[body],
          transparent: true,
          opacity: 0.45,
        }),
      )
      scene.add(path) // Open line: never artificially close a partial interval.
    }
  }
  const links = [
    ['sun', 'earth'],
    ['earth', 'moon'],
    ['sun', 'moon'],
  ] as const
  const lines = links.map(() => {
    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute(
      'position',
      new THREE.BufferAttribute(new Float32Array(6), 3),
    )
    const line = new THREE.Line(
      geometry,
      new THREE.LineBasicMaterial({
        color: 0x64748b,
        transparent: true,
        opacity: 0.6,
      }),
    )
    line.frustumCulled = false
    scene.add(line)
    return line
  })
  let selected: SystemBody | null = null
  let index = 0
  const update = (next: number) => {
    index = Math.min(next, data.time_utc.length - 1)
    const previous = selected ? meshes[selected].position.clone() : null
    for (const body of BODIES) {
      meshes[body].position.set(
        ...systemScenePoint(
          body,
          data.position_km.earth[index],
          data.position_km.moon[index],
        ),
      )
      labels[body].position
        .copy(meshes[body].position)
        .add(new THREE.Vector3(0, RADII[body] + 3, 0))
    }
    if (selected && previous) {
      const delta = meshes[selected].position.clone().sub(previous)
      camera.position.add(delta)
      controls.target.add(delta)
    }
    links.forEach(([a, b], i) => {
      const attr = lines[i].geometry.getAttribute(
        'position',
      ) as THREE.BufferAttribute
      attr.setXYZ(0, ...meshes[a].position.toArray())
      attr.setXYZ(1, ...meshes[b].position.toArray())
      attr.needsUpdate = true
    })
    container.dataset.timeUtc = data.time_utc[index]
  }
  const focus = (body: SystemBody | null) => {
    selected = body
    if (body) {
      controls.target.copy(meshes[body].position)
      camera.position
        .copy(controls.target)
        .add(new THREE.Vector3(0, RADII[body] * 4 + 4, RADII[body] * 7 + 8))
    } else {
      const bounds = new THREE.Box3()
      for (const bodyName of BODIES)
        bounds.expandByPoint(meshes[bodyName].position)
      const middle = bounds.getCenter(new THREE.Vector3())
      controls.target.copy(middle)
      const span = Math.max(65, bounds.getSize(new THREE.Vector3()).length())
      camera.position
        .copy(middle)
        .add(new THREE.Vector3(0, span * 1.25, span * 1.35))
    }
    controls.update()
  }
  update(0)
  focus(null)
  const resize = () => {
    const width = Math.max(1, container.clientWidth),
      height = Math.max(1, container.clientHeight)
    renderer.setSize(width, height)
    camera.aspect = width / height
    camera.updateProjectionMatrix()
  }
  const observer = new ResizeObserver(resize)
  observer.observe(container)
  resize()
  let frame = 0,
    count = 0,
    disposed = false
  const animate = () => {
    if (disposed) return
    controls.update()
    renderer.render(scene, camera)
    count++
    container.dataset.renderedFrames = String(count)
    container.dataset.geometries = String(renderer.info.memory.geometries)
    // Read the rendered body centres for the real-browser regression test.
    if (count % 15 === 1) {
      const gl = renderer.getContext(),
        size = renderer.getDrawingBufferSize(new THREE.Vector2())
      container.dataset.samples = BODIES.map((body) => {
        const p = meshes[body].position.clone().project(camera)
        const x = Math.floor(((p.x + 1) * size.x) / 2),
          y = Math.floor(((p.y + 1) * size.y) / 2)
        if (x < 0 || y < 0 || x >= size.x || y >= size.y || Math.abs(p.z) > 1)
          return 'offscreen'
        const pixel = new Uint8Array(4)
        gl.readPixels(x, y, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, pixel)
        return Array.from(pixel.slice(0, 3)).join(',')
      }).join(';')
    }
    frame = requestAnimationFrame(animate)
  }
  animate()
  return {
    update,
    focus,
    dispose() {
      disposed = true
      cancelAnimationFrame(frame)
      observer.disconnect()
      controls.dispose()
      scene.traverse((object) => {
        const drawable = object as THREE.Mesh
        drawable.geometry?.dispose()
        const materials = drawable.material
          ? Array.isArray(drawable.material)
            ? drawable.material
            : [drawable.material]
          : []
        materials.forEach((material) => material.dispose())
      })
      textures.forEach((texture) => texture.dispose())
      renderer.dispose()
      renderer.forceContextLoss()
      renderer.domElement.remove()
    },
  }
}
