// E09 — horizon profile from the DEM in a real browser: the Leibnitz Beta DEM representative point
// gets a complete two-tier profile (near PGDA 104 + far LOLA GDR), and a simulation in `dem` mode
// shows the terrain horizon per body and the computed visibility (E10).

import { expect, test } from '@playwright/test'
import { en } from '../src/i18n/en.ts'

test('the horizon profile is computed from the DEM and used by a dem-mode simulation', async ({
  page,
}) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`))
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(`console: ${message.text()}`)
  })

  await page.goto('/')
  await expect(
    page.getByText(en.catalog.terrainBadge.terrain_available).first(),
  ).toBeVisible({ timeout: 30_000 })
  await page.getByLabel(en.catalog.search).fill('Leibnitz')
  await page
    .locator('.site-item')
    .filter({ hasText: /Leibnitz Beta Plateau — DEM representative point/ })
    .first()
    .click()

  await page.getByRole('tab', { name: en.views.horizon }).click()
  const chart = page.getByRole('img', { name: /Horizon profile/ })
  await expect(chart).toBeVisible({ timeout: 60_000 })
  await expect(chart).toHaveAttribute('data-azimuths', '720')
  await expect(chart).toHaveAttribute('data-known', '720')
  await expect(page.locator('[data-horizon-status="complete"]')).toBeVisible()
  await expect(page.getByText('lola_gdr_ldem_75s_120m')).toBeVisible()
  await expect(page.getByText(en.horizon.provisional)).toBeVisible()

  await page.locator('select[name="terrain-mode"]').selectOption('dem')
  await page.getByRole('button', { name: en.params.run }).click()
  await expect(page.getByText(en.results.terrainHorizon).first()).toBeVisible({
    timeout: 120_000,
  })
  // E10: visibility, events and indicators are computed (no group left uncomputed).
  await expect(page.getByText(en.results.notComputedHeading)).toHaveCount(0)
  await expect(page.locator('[data-combination]')).toBeVisible()
  // Both mode badges (header, results) name the DEM mode, never the idealized one.
  await expect(page.locator('.mode-badge')).toHaveText([
    en.results.modeDem,
    en.results.modeDem,
  ])
  // Same frame (MOON_ME_DE421) for the result and the DEM: Sun and Earth are drawn on the chart.
  await expect(page.locator('.horizon-body--sun')).toBeVisible()
  await expect(page.getByText(en.horizon.bodiesHint)).toBeVisible()

  expect(errors).toEqual([])
})
