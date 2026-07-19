import { useState } from 'react'
import Hero from './components/Hero'
import Dashboard from './components/Dashboard'
import UploadForm from './components/UploadForm'

function App() {
  const [view, setView] = useState('hero') // hero | dashboard | upload
  const [refreshKey, setRefreshKey] = useState(0)

  return (
    <div className="min-h-screen bg-ink-950">
      {/* Floating pill nav, matching the ReactBits reference layout */}
      <div className="sticky top-4 z-50 px-6">
        <nav className="max-w-4xl mx-auto bg-ink-900/90 backdrop-blur border border-ink-700 rounded-full px-5 h-14 flex items-center gap-6 shadow-lg">
          <button onClick={() => setView('hero')} className="font-display font-semibold text-paper">
            Smart Budget Analyzer
          </button>
          <div className="flex gap-1 ml-auto items-center">
            <button
              onClick={() => setView('dashboard')}
              className={`px-3 py-1.5 rounded-full text-sm transition-colors ${view === 'dashboard' ? 'bg-ink-800 text-paper' : 'text-paper-dim hover:text-paper'}`}
            >
              Dashboard
            </button>
            <button
              onClick={() => setView('upload')}
              className="bg-brass text-ink-950 font-medium px-4 py-1.5 rounded-full text-sm hover:bg-brass-bright transition-colors ml-2"
            >
              Upload
            </button>
          </div>
        </nav>
      </div>

      {view === 'hero' && (
        <Hero onLearnMore={() => setView('upload')} />
      )}
      {view === 'dashboard' && <Dashboard key={refreshKey} />}
      {view === 'upload' && (
        <UploadForm
          onUploaded={() => {
            setRefreshKey((k) => k + 1)
            setView('dashboard')
          }}
        />
      )}
    </div>
  )
}

export default App
