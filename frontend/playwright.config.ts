// Browser smoke tests (docs/ARCHITECTURE.md §12: interface level, Playwright). They run in a real
// headless Chromium against the real backend and the Vite dev server (both reused when already
// running). WebGL is forced onto the SwiftShader software renderer so the check does not depend on a
// GPU: this is the "rendering in the test environment" check required by BACKLOG E07.
// Run: npm run test:e2e (needs the SPICE-free endpoints and data/_cache/e05_auxiliary/globe.jpg).

import { defineConfig, devices } from '@playwright/test'

const python =
  process.platform === 'win32' ? '.venv\\Scripts\\python' : '.venv/bin/python'

export default defineConfig({
  testDir: 'e2e',
  timeout: 90_000,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:5174',
    trace: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium-swiftshader',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1440, height: 900 },
        launchOptions: {
          args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
        },
      },
    },
  ],
  webServer: [
    {
      command: `${python} -m uvicorn lunarhorizon.api.app:app --host 127.0.0.1 --port 8001`,
      cwd: '../backend',
      url: 'http://127.0.0.1:8001/api/health',
      env: { PYTHONUTF8: '1' },
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 5174 --strictPort',
      url: 'http://127.0.0.1:5174',
      env: { LUNAR_API_URL: 'http://127.0.0.1:8001' },
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
})
