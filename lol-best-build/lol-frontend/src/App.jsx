import { useState, useEffect, useRef } from 'react'
import ChampionSearch from './components/ChampionSearch.jsx'
import BuildResult from './components/BuildResult.jsx'
import './App.css'

export default function App() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [progress, setProgress] = useState(null)

  const handleSearch = async ({ champion, region, queue }) => {
    setLoading(true)
    setError(null)
    setResult(null)
    setProgress(null)

    const url = `/api/champion/${encodeURIComponent(champion)}/best-build?region=${region}&queue=${queue}`
    const es = new EventSource(url)

    es.onmessage = (e) => {
      const data = JSON.parse(e.data)

      if (data.type === 'progress') {
        setProgress(data)
      } else if (data.type === 'result') {
        setResult(data)
        setLoading(false)
        setProgress(null)
        es.close()
      } else if (data.type === 'error') {
        setError(data.message)
        setLoading(false)
        setProgress(null)
        es.close()
      }
    }

    es.onerror = () => {
      setError("Erreur de connexion au serveur.")
      setLoading(false)
      es.close()
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-inner">
          <span className="header-logo">⚔</span>
          <h1 className="header-title">LoL Best Build</h1>
          <span className="header-subtitle">Builds des 3 meilleurs joueurs du ladder</span>
        </div>
      </header>

      <main className="app-main">
        <ChampionSearch onSearch={handleSearch} loading={loading} />

        {loading && (
          <div className="loading-block">
            <div className="spinner" />
            <p>{progress?.message || 'Initialisation...'}</p>
            {progress?.total && (
              <div className="progress-bar-wrap">
                <div
                  className="progress-bar"
                  style={{ width: `${(progress.current / progress.total) * 100}%` }}
                />
                <span className="progress-label">
                  {progress.current}/{progress.total} joueurs — {progress.mains_found} mains trouvés
                </span>
              </div>
            )}
          </div>
        )}

        {error && (
          <div className="error-block">
            <span className="error-icon">✕</span> {error}
          </div>
        )}

        {result && !loading && <BuildResult data={result} />}
      </main>

      <footer className="app-footer">
        LoL Best Build n'est pas affilié à Riot Games · Données via Riot Games API
      </footer>
    </div>
  )
}
