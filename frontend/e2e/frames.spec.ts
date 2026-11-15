// E08b review — frame policy and DEM representative point labels in a real browser: a user point in
// another frame is refused, then re-interpreted (never converted) only on an explicit action with an
// explanation; catalog DEM points keep their own frame and are labelled as DEM representative points.

import { expect, test } from '@playwright/test'
import { en } from '../src/i18n/en.ts'

test('a user point is re-interpreted in the DEM frame only explicitly; DEM points are labelled as such', async ({
  page,
}) => {
  await page.goto('/')
  await expect(
    page.getByText(en.catalog.terrainBadge.terrain_available).first(),
  ).toBeVisible({ timeout: 30_000 })

  // Labels: 13 DEM representative points, the legend separates them from catalog positions.
  await expect(
    page.locator('.site-item').filter({ hasText: /DEM representative point/ }),
  ).toHaveCount(13)
  await expect(page.locator('.globe-legend')).toContainText(
    en.globe.legend.demPoint,
  )
  await expect(page.locator('body')).not.toContainText(
    /Landing sites|Approved landing candidates/,
  )

  // A user point (inside the Haworth product) in a frame that no DEM product declares.
  const frame = page.getByLabel(en.params.frame)
  await frame.selectOption('MOON_ME_DE440_ME421')
  await page.getByLabel(en.point.latitude).fill('-86.76')
  await page.getByLabel(en.point.longitude).fill('-22.78')
  await page.getByText(en.point.use).click()
  await page.getByRole('tab', { name: /Local terrain/ }).click()
  await expect(
    page.getByText(en.terrain.unavailable.frame_mismatch),
  ).toBeVisible({ timeout: 30_000 })
  await expect(page.getByText(en.terrain.adoptFrameExplanation)).toBeVisible()
  const canvas = page.locator('.terrain-canvas')
  await expect
    .poll(() => canvas.getAttribute('data-terrain-vertices'))
    .toBe('0')

  // Explicit re-interpretation: same numbers, DEM frame, stated as no conversion.
  await page.getByText(en.terrain.adoptFrame('MOON_ME_DE421')).click()
  await expect(frame).toHaveValue('MOON_ME_DE421')
  await expect(
    page.getByText(en.coverage.frameNotes.reinterpreted('MOON_ME_DE421')),
  ).toBeVisible()
  await expect(canvas).toHaveAttribute('data-terrain-ready', 'true', {
    timeout: 60_000,
  })

  // The catalog DEM point keeps its declared frame and its provenance label.
  await frame.selectOption('MOON_ME_DE440_ME421')
  await page.getByLabel(en.catalog.search).fill('Haworth')
  await page
    .locator('.site-item')
    .filter({ hasText: /Haworth — DEM representative point/ })
    .first()
    .click()
  await expect(frame).toHaveValue('MOON_ME_DE421')
  await expect(
    page.getByText(en.terrain.adoptFrame('MOON_ME_DE421')),
  ).toHaveCount(0)
  await expect(canvas).toHaveAttribute('data-terrain-ready', 'true', {
    timeout: 60_000,
  })
})
