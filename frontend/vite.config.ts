/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  base: process.env.LUNAR_BASE_PATH ?? '/',
  plugins: [react()],
  // Three.js (≈ 570 kB) is a separate chunk loaded only when a 3D view opens.
  build: { chunkSizeWarningLimit: 700 },
  // The FastAPI backend (backend/: uvicorn on 127.0.0.1:8000) is reached through /api.
  server: {
    proxy: { '/api': process.env.LUNAR_API_URL ?? 'http://127.0.0.1:8000' },
  },
  preview: {
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
  test: {
    environment: 'jsdom',
    // Browser smoke tests in e2e/ run with Playwright (npm run test:e2e), not Vitest.
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
