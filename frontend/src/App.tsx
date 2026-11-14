import { ro } from './i18n/ro.ts'

// Componenta rădăcină. Cele patru zone ale ecranului și harta 3D implicită se construiesc de la E07.
function App() {
  return (
    <main className="app">
      <h1>{ro.appTitle}</h1>
      <p>{ro.appTagline}</p>
      <p role="status">{ro.stageNotice}</p>
    </main>
  )
}

export default App
