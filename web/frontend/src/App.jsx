import { useState, useEffect } from 'react'
import Bracket from './components/Bracket'
import Sidebar from './components/Sidebar'
import Header from './components/Header'
import './App.css'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function App() {
  const [bracketData, setBracketData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedTeam, setSelectedTeam] = useState(null)

  useEffect(() => {
    fetch(`${API}/api/bracket`)
      .then(r => r.json())
      .then(data => { setBracketData(data); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [])

  if (loading) return <div className="loading">Loading 2026 NCAA Tournament Bracket...</div>
  if (error) return (
    <div className="error">
      <p>Error: {error}</p>
      <p>Make sure the API is running: <code>python -m uvicorn web.backend.app:app --reload</code></p>
    </div>
  )

  return (
    <div className="app">
      <Header bracketData={bracketData} />
      <div className="main-layout">
        <div className="bracket-scroll">
          <Bracket
            bracketData={bracketData}
            onTeamSelect={setSelectedTeam}
            selectedTeam={selectedTeam}
          />
        </div>
        <Sidebar
          bracketData={bracketData}
          selectedTeam={selectedTeam}
          apiBase={API}
        />
      </div>
    </div>
  )
}
