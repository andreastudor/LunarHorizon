import { expect, test } from '@playwright/test'
import { en } from '../src/i18n/en.ts'

test('WebGL failure automatically opens a working 2D map', async ({ page }) => {
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext
    HTMLCanvasElement.prototype.getContext = function (
      this: HTMLCanvasElement,
      kind: string,
      ...args: unknown[]
    ) {
      if (kind.includes('webgl')) return null
      return original.apply(this, [kind, ...args] as Parameters<
        typeof original
      >)
    } as typeof original
  })
  await page.goto('/')
  await expect(page.getByText(en.map.fallback)).toBeVisible()
  await expect(page.locator('.map-canvas canvas')).toBeVisible()
})

test('2D map switches projections and preserves catalog selection', async ({
  page,
}) => {
  await page.goto('/')
  await page.getByLabel(en.catalog.search).fill('Leibnitz')
  await page
    .locator('.site-item')
    .filter({ hasText: 'Leibnitz Beta' })
    .first()
    .click()
  await page.getByRole('tab', { name: en.map.title }).click()
  await expect(page.locator('.map-canvas canvas')).toBeVisible()
  await page.getByRole('button', { name: en.map.global, exact: true }).click()
  await expect(page.locator('.map-canvas canvas')).toBeVisible()
  await page.getByRole('tab', { name: en.views.globe, exact: true }).click()
  await expect(page.locator('.site-item[aria-pressed="true"]')).toContainText(
    'Leibnitz',
  )
})

test('two real polar DEM sites compare and follow one clock and active terrain', async ({
  page,
}) => {
  test.setTimeout(600000)
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  let requests = 0
  page.on('request', (r) => {
    if (r.method() === 'POST' && r.url().includes('/simulations')) requests++
  })
  await page.goto('/')
  for (const name of ['Leibnitz', 'Connecting Ridge —']) {
    await page.getByLabel(en.catalog.search).fill(name)
    await page.locator('.site-item').filter({ hasText: name }).first().click()
    await page.getByRole('button', { name: en.compare.add }).click()
  }
  await page.locator('select[name="terrain-mode"]').selectOption('dem')
  await page.getByLabel(en.params.duration).selectOption('1')
  await page.getByRole('button', { name: en.compare.run, exact: true }).click()
  const columns = page.locator('.comparison-column')
  await expect(columns).toHaveCount(2, { timeout: 480000 })
  await expect(columns.nth(0)).toContainText('Leibnitz')
  await expect(columns.nth(1)).toContainText('Connecting Ridge')
  await page.locator('#time-slider').fill('24')
  expect(await columns.nth(0).locator('time').textContent()).toBe(
    await columns.nth(1).locator('time').textContent(),
  )
  await columns.nth(1).getByRole('button').click()
  await page.getByRole('tab', { name: /Local terrain/ }).click()
  await expect(page.locator('.terrain-canvas')).toHaveAttribute(
    'data-terrain-vertices',
    /[1-9]/,
    { timeout: 60000 },
  )
  await expect(columns.nth(1).getByRole('button')).toHaveAttribute(
    'aria-pressed',
    'true',
  )
  expect(requests).toBe(1)
  expect(errors).toEqual([])
})
