// Generează tipurile TypeScript ale contractelor din schema JSON comună.
//   npm run contracts:generate   scrie src/contracts/generated.ts
//   npm run contracts:check      ieșire 1 dacă fișierul nu corespunde schemei
// Schema însăși se generează din modelele Pydantic: scripts/generate_contracts.py (rădăcină).
import { readFile, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { compile } from 'json-schema-to-typescript'
import * as prettier from 'prettier'

const schemaUrl = new URL(
  '../../data/schemas/lunarhorizon.schema.json',
  import.meta.url,
)
const outputUrl = new URL('../src/contracts/generated.ts', import.meta.url)
const check = process.argv.includes('--check')

const schema = JSON.parse(await readFile(schemaUrl, 'utf8'))

// Pydantic pune `title` pe fiecare proprietate; json-schema-to-typescript ar crea câte un alias
// de tip pentru fiecare. Păstrăm titlurile numai pe definițiile din $defs (modelele).
function stripNestedTitles(node, isDefinition) {
  if (Array.isArray(node)) {
    node.forEach((item) => stripNestedTitles(item, false))
    return
  }
  if (node === null || typeof node !== 'object') return
  if (!isDefinition) delete node.title
  for (const [key, value] of Object.entries(node)) {
    if (key === '$defs') {
      Object.values(value).forEach((definition) =>
        stripNestedTitles(definition, true),
      )
    } else if (key === 'properties' || key === 'patternProperties') {
      // Hartă nume → schemă: cheile sunt nume de câmpuri (inclusiv un câmp numit „title”).
      Object.values(value).forEach((property) =>
        stripNestedTitles(property, false),
      )
    } else if (key !== 'enum' && key !== 'const' && key !== 'required') {
      stripNestedTitles(value, false)
    }
  }
}
stripNestedTitles(schema, true)

const banner = [
  '/**',
  ' * GENERAT AUTOMAT din data/schemas/lunarhorizon.schema.json — nu se editează manual.',
  ' * Regenerare: scripts/generate_contracts.py (rădăcină), apoi `npm run contracts:generate`.',
  ` * Versiunea schemei: ${schema['x-schema-version']}`,
  ' */',
].join('\n')

const raw = await compile(schema, 'LunarHorizonContracts', {
  bannerComment: banner,
  additionalProperties: false,
  unreachableDefinitions: true,
  ignoreMinAndMaxItems: true,
  format: false,
})
const outputPath = fileURLToPath(outputUrl)
const options = (await prettier.resolveConfig(outputPath)) ?? {}
const formatted = await prettier.format(raw, {
  ...options,
  filepath: outputPath,
})

if (check) {
  let current = ''
  try {
    current = (await readFile(outputUrl, 'utf8')).replace(/\r\n/g, '\n')
  } catch {
    current = ''
  }
  if (current !== formatted) {
    console.error(
      'src/contracts/generated.ts nu corespunde schemei; rulați npm run contracts:generate',
    )
    process.exit(1)
  }
  console.log('Tipurile contractelor sunt la zi.')
} else {
  await writeFile(outputUrl, formatted, 'utf8')
  console.log('scris: src/contracts/generated.ts')
}
