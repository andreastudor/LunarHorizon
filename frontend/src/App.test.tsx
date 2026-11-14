import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import App from './App.tsx'
import { ro } from './i18n/ro.ts'

afterEach(cleanup)

// Test de fum (E01): componenta rădăcină se randează.
describe('App', () => {
  it('afișează titlul aplicației', () => {
    render(<App />)
    expect(
      screen.getByRole('heading', { level: 1, name: ro.appTitle }),
    ).toBeDefined()
  })

  it('declară explicit stadiul proiectului', () => {
    render(<App />)
    expect(screen.getByRole('status').textContent).toBe(ro.stageNotice)
  })
})
