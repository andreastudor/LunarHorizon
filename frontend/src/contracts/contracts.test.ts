// Tipurile generate acoperă schema comună: fiecare definiție și fiecare proprietate.
// (Faptul că fișierul este la zi cu schema îl verifică `npm run contracts:check`.)
import { describe, expect, it } from 'vitest'
import schema from '../../../data/schemas/lunarhorizon.schema.json'
import generated from './generated.ts?raw'
import { SCHEMA_VERSION } from '../geo/conventions.ts'

interface Definition {
  properties?: Record<string, unknown>
  enum?: string[]
}
const definitions = schema.$defs as Record<string, Definition>

function interfaceBody(name: string): string | undefined {
  const start = generated.indexOf(`export interface ${name} {`)
  if (start < 0) return undefined
  return generated.slice(start, generated.indexOf('\n}', start))
}

describe('tipurile contractelor', () => {
  it('au aceeași versiune de schemă ca modulul geo', () => {
    expect(schema['x-schema-version']).toBe(SCHEMA_VERSION)
  })

  const objectDefinitions = Object.entries(definitions).filter(
    ([, d]) => d.properties,
  )
  it.each(objectDefinitions)(
    'interfața %s are toate proprietățile',
    (name, definition) => {
      const body = interfaceBody(name)
      expect(body, `lipsește interfața ${name}`).toBeDefined()
      for (const property of Object.keys(definition.properties ?? {})) {
        expect(body).toMatch(new RegExp(`\\n  ${property}\\??:`))
      }
    },
  )

  it('declară toate codurile de eroare', () => {
    for (const code of definitions.ErrorCode.enum ?? []) {
      expect(generated).toContain(`'${code}'`)
    }
  })
})
