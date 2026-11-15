import { afterEach, expect, test, vi } from 'vitest'
import { createApiDataSource } from './dataSource.ts'

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

test('public API base applies to requests and imagery', async () => {
  vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.test/api/')
  const fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ sites: [] }),
  })
  vi.stubGlobal('fetch', fetch)
  const source = createApiDataSource()
  await source.sites()
  expect(fetch).toHaveBeenCalledWith('https://api.example.test/api/sites', {
    signal: undefined,
  })
  expect(source.globeTextureUrl).toBe(
    'https://api.example.test/api/assets/globe.jpg',
  )
})

test('same-origin installation keeps local API and asset paths', () => {
  vi.stubEnv('VITE_API_BASE_URL', '')
  expect(createApiDataSource().globeTextureUrl).toBe('/api/assets/globe.jpg')
})
