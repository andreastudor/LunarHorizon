// E08b — real terrain for several PGDA 104 regions in a real headless browser: each region loads its
// own product (different vertex counts), GPU geometries do not accumulate when switching, and sites
// without DEM show the right state (no relief generated).

import { expect, test, type Locator, type Page } from '@playwright/test'
import { en } from '../src/i18n/en.ts'

async function data(locator: Locator, name: string): Promise<string> {
  return (await locator.getAttribute(`data-${name}`)) ?? ''
}

async function selectSite(page: Page, query: string, name: RegExp) {
  await page.getByLabel(en.catalog.search).fill(query)
  await page.locator('.site-item').filter({ hasText: name }).first().click()
}

test('several real DEM regions load their own terrain without accumulating GPU resources', async ({
  page,
}) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`))
  page.on('console', (message) => {
    if (message.type() !== 'error') return
    const expected =
      message.text().includes('404') &&
      message.location().url.includes('/api/terrain/manifest')
    if (!expected) errors.push(`console: ${message.text()}`)
  })

  await page.goto('/')
  await expect(
    page.getByText(en.catalog.terrainBadge.terrain_available).first(),
  ).toBeVisible({ timeout: 30_000 })

  await selectSite(page, 'Haworth', /Haworth — PGDA 104/)
  await page.getByRole('tab', { name: /Local terrain/ }).click()
  const canvas = page.locator('.terrain-canvas')
  await expect(canvas).toHaveAttribute('data-terrain-ready', 'true', {
    timeout: 60_000,
  })
  // Haworth: 5960 px at 5 m; the 40 m level (745²) exceeds the budget, the 100 m level is used.
  expect(await data(canvas, 'terrain-vertices')).toBe(String(298 * 298))
  await expect(page.getByText(/mesh 100 m\/pixel/)).toBeVisible()
  await page.waitForTimeout(500)
  const geometriesHaworth = Number(await data(canvas, 'geometries'))

  await selectSite(page, 'Malapert', /Malapert Massif — PGDA 104/)
  await expect
    .poll(() => data(canvas, 'terrain-vertices'), { timeout: 60_000 })
    .toBe(String(525 * 525))
  await expect(canvas).toHaveAttribute('data-terrain-ready', 'true', {
    timeout: 60_000,
  })
  await expect(page.getByText(/^DEM pgda104_malapert_massif/)).toBeVisible()

  await selectSite(page, 'Haworth', /Haworth — PGDA 104/)
  await expect
    .poll(() => data(canvas, 'terrain-vertices'), { timeout: 60_000 })
    .toBe(String(298 * 298))
  await expect(canvas).toHaveAttribute('data-terrain-ready', 'true', {
    timeout: 60_000,
  })
  await expect
    .poll(async () => Number(await data(canvas, 'geometries')))
    .toBe(geometriesHaworth)

  await selectSite(page, 'Chandrayaan', /Vikram lander/)
  await expect(
    page.getByText(en.terrain.unavailable.coverage_unverified),
  ).toBeVisible()
  await expect.poll(() => data(canvas, 'terrain-vertices')).toBe('0')

  await selectSite(page, 'Apollo 11', /Apollo 11/)
  await expect(
    page.getByText(en.terrain.unavailable.no_dem_coverage),
  ).toBeVisible()

  expect(errors).toEqual([])
})
