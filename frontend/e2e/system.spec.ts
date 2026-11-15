import { expect, test } from '@playwright/test'
import { en } from '../src/i18n/en.ts'

test('real system renders, follows time and caches tab switches', async ({
  page,
}) => {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  let requests = 0
  page.on('request', (r) => {
    if (r.url().includes('/system/series')) requests++
  })
  await page.goto('/')
  await page.getByRole('tab', { name: en.system.title }).click()
  const scene = page.locator('.system-canvas')
  await expect(scene).toHaveAttribute('data-rendered-frames', /[1-9]/, {
    timeout: 60000,
  })
  // All three projected centres must contain rendered pixels, not just a running render loop.
  await expect(scene).toHaveAttribute(
    'data-samples',
    /^\d+,\d+,\d+;\d+,\d+,\d+;\d+,\d+,\d+$/,
  )
  const pixels = (await scene.getAttribute('data-samples'))!.split(';')
  for (const pixel of pixels) {
    expect(Math.max(...pixel.split(',').map(Number))).toBeGreaterThan(35)
  }
  const geometries = await scene.getAttribute('data-geometries')
  await expect(page.getByTestId('distance-earth_moon')).toContainText('km')
  const before = await page.getByTestId('distance-earth_moon').textContent()
  await page.locator('#time-slider').fill('24')
  await expect(page.getByTestId('distance-earth_moon')).not.toHaveText(before!)
  const epoch = await scene.getAttribute('data-time-utc')
  await page
    .getByRole('button', {
      name: `${en.system.focus} ${en.system.moon}`,
      exact: true,
    })
    .click()
  await expect(scene).toHaveAttribute('data-time-utc', epoch!)
  await page.getByRole('tab', { name: en.views.globe, exact: true }).click()
  await page.getByRole('tab', { name: en.system.title }).click()
  await expect(scene).toHaveAttribute('data-time-utc', epoch!)
  await expect(scene).toHaveAttribute('data-geometries', geometries!)
  expect(requests).toBe(1)
  expect(errors).toEqual([])
  await page.screenshot({ path: test.info().outputPath('system.png') })
})
