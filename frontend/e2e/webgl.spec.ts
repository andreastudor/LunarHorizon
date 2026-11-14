// E07 — early check of WebGL rendering in the test environment (BACKLOG E07, ARCHITECTURE §12).
// Proves, in a real headless browser, that a WebGL context is created, the globe and its E05 texture
// load, a frame is rendered (pixels read back from that frame) and no JavaScript error occurs.
// A missing texture or WebGL makes this test fail; it is never skipped.

import { expect, test } from '@playwright/test'
import { en } from '../src/i18n/en.ts'

const BACKGROUND = [5, 7, 11] // 0x05070b, the scene background

const parse = (sample: string) => sample.split(',').map(Number)
const distance = (a: number[], b: number[]) =>
  Math.max(...a.map((value, i) => Math.abs(value - b[i])))

test('the 3D globe renders with WebGL and the E05 texture', async ({
  page,
}) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`))
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(`console: ${message.text()}`)
  })

  const textureResponse = page.waitForResponse((response) =>
    response.url().endsWith('/api/assets/globe.jpg'),
  )
  await page.goto('/')
  const texture = await textureResponse
  expect(texture.status()).toBe(200)
  expect(texture.headers()['content-type']).toBe('image/jpeg')

  const globe = page.locator('.globe-canvas')
  // Published by the controller only after a frame was rendered with the texture bound.
  await expect(globe).toHaveAttribute('data-textured', 'true', {
    timeout: 60_000,
  })
  const webgl = await globe.getAttribute('data-webgl')
  expect(webgl).toMatch(/^webgl[12]$/)
  expect(
    Number(await globe.getAttribute('data-rendered-frames')),
  ).toBeGreaterThan(0)

  const samples = ((await globe.getAttribute('data-samples')) ?? '')
    .split(';')
    .map(parse)
  expect(samples).toHaveLength(6)
  const surface = samples.slice(0, 5)
  const corner = samples[5]
  // The corner is empty space; the five central samples are lunar surface, clearly not background.
  expect(distance(corner, BACKGROUND)).toBeLessThanOrEqual(12)
  for (const pixel of surface) {
    expect(distance(pixel, BACKGROUND)).toBeGreaterThan(40)
  }
  // Imagery, not a flat colour: the surface samples are not all identical.
  expect(new Set(surface.map((pixel) => pixel.join(','))).size).toBeGreaterThan(
    2,
  )

  const canvas = page.locator('.globe-canvas canvas')
  await expect(canvas).toHaveCount(1)
  const box = await canvas.boundingBox()
  expect(box?.width ?? 0).toBeGreaterThan(200)
  expect(box?.height ?? 0).toBeGreaterThan(200)
  await expect(page.getByText(en.globe.webglUnavailable)).toHaveCount(0)
  await expect(page.getByText(en.globe.textureMissing)).toHaveCount(0)

  const renderer = await page.evaluate(() => {
    const gl = document.createElement('canvas').getContext('webgl2')
    const info = gl?.getExtension('WEBGL_debug_renderer_info')
    return info && gl
      ? String(gl.getParameter(info.UNMASKED_RENDERER_WEBGL))
      : 'unknown'
  })
  const sampleText = samples.map((pixel) => pixel.join(',')).join(' ')
  test
    .info()
    .annotations.push(
      { type: 'webgl', description: webgl ?? '' },
      { type: 'renderer', description: renderer },
      { type: 'samples', description: sampleText },
    )
  console.log(`WebGL: ${webgl}; renderer: ${renderer}; samples: ${sampleText}`)

  expect(errors).toEqual([])
})
