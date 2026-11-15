// E10 — end to end on real data (Leibnitz Beta DEM representative point, DEM mode, 30 days):
// terrain → horizon → astronomy → visibility → events → indicators → synchronised display. At several
// slider positions the Sun card, the band under the cursor and the 3D scene indicator must agree;
// the slider only reads the loaded result (no new simulation requests).

import { expect, test, type Page } from '@playwright/test'
import { en } from '../src/i18n/en.ts'

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

/** State of the band segment under the cursor, read from the DOM. */
async function bandAtCursor(page: Page, band: string): Promise<string | null> {
  return page.locator(`[data-band="${band}"]`).evaluate((track) => {
    const cursor = track.querySelector('.bands-cursor') as HTMLElement
    const x = parseFloat(cursor.style.left)
    for (const el of track.querySelectorAll<HTMLElement>('[data-state]')) {
      const left = parseFloat(el.style.left)
      const width = parseFloat(el.style.width)
      if (x >= left - 1e-6 && x < left + width + 1e-6)
        return el.dataset.state ?? null
    }
    return null
  })
}

const CARD_TO_BAND: Record<string, string[]> = {
  hidden: ['hidden'],
  partially_visible: ['visible'],
  fully_visible: ['visible'],
  visible: ['visible'],
  undetermined: ['unknown'],
}

test('a real DEM site works end to end and every view shows the same computed state', async ({
  page,
}) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`))
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(`console: ${message.text()}`)
  })
  let simulationRequests = 0
  page.on('request', (request) => {
    if (
      request.method() === 'POST' &&
      request.url().includes('/api/simulations')
    )
      simulationRequests += 1
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
  await page.locator('select[name="terrain-mode"]').selectOption('dem')
  await page.getByRole('button', { name: en.params.run }).click()
  await expect(page.locator('[data-combination]')).toBeVisible({
    timeout: 180_000,
  })
  await expect(page.locator('.mode-badge').first()).toHaveText(
    en.results.modeDem,
  )
  await expect(page.getByText(en.results.reliefOnly).first()).toBeVisible()
  await expect(page.getByRole('img', { name: en.chart.label })).toBeVisible()
  await expect(page.locator('[data-band]')).toHaveCount(3)
  const requestsAfterRun = simulationRequests

  await page.getByRole('tab', { name: /Local terrain/ }).click()
  const indicators = page.getByRole('list', { name: en.terrain.indicators })
  await expect(indicators).toBeVisible({ timeout: 60_000 })
  await expect(page.getByText(en.terrain.bannerDem)).toBeVisible()

  const max = Number(await page.locator('#time-slider').getAttribute('max'))
  const seen = new Set<string>()
  for (const value of [0, 200, 400, 600, 800, 1000, 1200, max]) {
    await setSlider(page, value)
    const sunCard = page.getByRole('article', { name: en.results.sun })
    const cardState =
      (await sunCard
        .locator('[data-state]')
        .first()
        .getAttribute('data-state')) ?? ''
    seen.add(cardState)
    expect(CARD_TO_BAND[cardState], `slider ${value}`).toContain(
      await bandAtCursor(page, 'sun'),
    )
    expect(
      await indicators.locator('[data-body="sun"]').getAttribute('data-state'),
      `slider ${value}`,
    ).toBe(cardState)
    const earthCard = page.getByRole('article', { name: en.results.earth })
    const earthState =
      (await earthCard
        .locator('[data-state]')
        .first()
        .getAttribute('data-state')) ?? ''
    expect(CARD_TO_BAND[earthState]).toContain(
      await bandAtCursor(page, 'earth'),
    )
    expect(
      await indicators
        .locator('[data-body="earth"]')
        .getAttribute('data-state'),
    ).toBe(earthState)
  }
  // The 30 days include both a hidden and a visible Sun here; the slider made no new requests.
  expect(seen.has('hidden')).toBe(true)
  expect(
    [...seen].some((s) => s === 'fully_visible' || s === 'partially_visible'),
  ).toBe(true)
  expect(simulationRequests).toBe(requestsAfterRun)
  expect(errors).toEqual([])
})
