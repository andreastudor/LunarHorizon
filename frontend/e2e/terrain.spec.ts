// E08 — real local terrain in a real headless browser, against the real backend and DEM products.
// Checks the mesh built from the visual raster (vertex and triangle counts of the 400 × 400 level),
// pixels read back from the rendered terrain, Sun lighting following the slider, exaggeration and
// cameras without mesh rebuilds, the no-DEM state, and GPU geometries released on selection change.

import { expect, test, type Locator, type Page } from '@playwright/test'
import { en } from '../src/i18n/en.ts'

const BACKGROUND = [5, 7, 11]
const distance = (a: number[], b: number[]) =>
  Math.max(...a.map((value, i) => Math.abs(value - b[i])))

async function data(locator: Locator, name: string): Promise<string> {
  return (await locator.getAttribute(`data-${name}`)) ?? ''
}

async function setSlider(page: Page, value: number) {
  await page.locator('#time-slider').evaluate((element, next) => {
    const input = element as HTMLInputElement
    Object.getOwnPropertyDescriptor(
      HTMLInputElement.prototype,
      'value',
    )!.set!.call(input, String(next))
    input.dispatchEvent(new Event('input', { bubbles: true }))
  }, value)
}

test('real local terrain loads, renders and follows the slider', async ({
  page,
}) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`))
  page.on('console', (message) => {
    if (message.type() !== 'error') return
    // Expected: the browser logs the contractual 404 OUT_OF_DEM_COVERAGE of the terrain manifest
    // for a selection without DEM (docs/API.md §2.4). Every other error fails the test.
    const expectedNoDem =
      message.text().includes('404') &&
      message.location().url.includes('/api/terrain/manifest')
    if (!expectedNoDem) errors.push(`console: ${message.text()}`)
  })

  await page.goto('/')
  await page
    .locator('li', { hasText: 'pgda104_leibnitz_beta' })
    .getByText(en.coverage.useRepresentative)
    .click()
  const canvas = page.locator('.terrain-canvas')
  await expect(canvas).toHaveAttribute('data-terrain-ready', 'true', {
    timeout: 60_000,
  })

  // Mesh from the 40 m visual raster: 400 × 400 vertices, 2 triangles per cell, no NoData here.
  expect(await data(canvas, 'terrain-vertices')).toBe('160000')
  expect(await data(canvas, 'terrain-triangles')).toBe(String(399 * 399 * 2))
  expect(await data(canvas, 'no-data-vertices')).toBe('0')
  expect(await data(canvas, 'mesh-builds')).toBe('1')
  expect(await data(canvas, 'webgl')).toMatch(/^webgl[12]$/)
  const samples = (await data(canvas, 'samples'))
    .split(';')
    .map((s) => s.split(',').map(Number))
  for (const pixel of samples) {
    expect(distance(pixel, BACKGROUND)).toBeGreaterThan(20)
  }
  expect(new Set(samples.map((p) => p.join(','))).size).toBeGreaterThan(1)

  await expect(page.getByText(en.terrain.banner)).toBeVisible()
  await expect(page.getByText(en.terrain.representativeNote)).toBeVisible()
  await expect(page.getByText(en.terrain.exaggeration(1))).toBeVisible()
  await expect(
    page.getByText(/Observer: terrain 6398\.\d m \+ equipment 2 m/),
  ).toBeVisible()
  await expect(page.getByLabel(en.params.frame)).toHaveValue('MOON_ME_DE421')
  expect(await data(canvas, 'light')).toBe('neutral')
  // GPU geometries with the terrain and the observer, before any result (no arrows yet).
  await page.waitForTimeout(500)
  const geometriesWithTerrain = Number(await data(canvas, 'geometries'))
  expect(geometriesWithTerrain).toBeGreaterThan(0)

  // A real simulation in the DEM frame drives the Sun direction and the light.
  await page.getByLabel(en.params.duration).selectOption('1')
  await page.getByText(en.params.run).click()
  await expect(page.getByText(/At the selected time/)).toBeVisible({
    timeout: 60_000,
  })
  const lightStart = await data(canvas, 'light')
  expect(lightStart).toMatch(/^-?\d/)
  await setSlider(page, 1000)
  await expect.poll(() => data(canvas, 'light')).not.toBe(lightStart)
  expect(await data(canvas, 'mesh-builds')).toBe('1')

  // Exaggeration changes the display only.
  const sunElevation = await page.locator('.card--sun .big').textContent()
  await page.getByLabel(en.terrain.exaggerationControl).selectOption('5')
  await expect(page.getByText(en.terrain.exaggeration(5))).toBeVisible()
  expect(await data(canvas, 'exaggeration')).toBe('5')
  expect(await data(canvas, 'mesh-builds')).toBe('1')
  await expect(page.locator('.card--sun .big')).toHaveText(sunElevation ?? '')

  for (const mode of ['top', 'observer', 'oblique'] as const) {
    await page.getByRole('button', { name: en.terrain.camera[mode] }).click()
    expect(await data(canvas, 'camera')).toBe(mode)
  }
  await page.getByRole('button', { name: en.terrain.goToSite }).click()
  expect(await data(canvas, 'camera')).toBe('oblique')

  // A site without DEM: no relief, terrain geometries released; back again: the same count as
  // the first load without a result (no leak).
  await page.getByText('Apollo 11 — Lunar Module “Eagle”').click()
  await expect(
    page.getByText(en.terrain.unavailable.no_dem_coverage),
  ).toBeVisible()
  await expect.poll(() => data(canvas, 'terrain-vertices')).toBe('0')
  await expect
    .poll(async () => Number(await data(canvas, 'geometries')))
    .toBeLessThan(geometriesWithTerrain)
  await page
    .locator('li', { hasText: 'pgda104_leibnitz_beta' })
    .getByText(en.coverage.useRepresentative)
    .click()
  await expect(canvas).toHaveAttribute('data-terrain-ready', 'true', {
    timeout: 60_000,
  })
  await expect
    .poll(async () => Number(await data(canvas, 'geometries')))
    .toBe(geometriesWithTerrain)

  expect(errors).toEqual([])
})
