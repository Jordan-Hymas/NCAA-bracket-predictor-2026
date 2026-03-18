import { useState, useEffect, useCallback } from 'react'
import Bracket from './components/Bracket'
import Sidebar from './components/Sidebar'
import Header from './components/Header'
import './App.css'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function App() {
  const [bracketData, setBracketData] = useState(null)
  const [loading, setLoading]         = useState(true)
  const [error, setError]             = useState(null)
  const [selectedTeam, setSelectedTeam] = useState(null)
  const [selectedGame, setSelectedGame] = useState(null)
  const [mode, setMode]               = useState('ai')   // 'ai' | 'picks'
  const [userPicks, setUserPicks]     = useState({})
  const [mcOdds, setMcOdds]           = useState(null)
  const [mcLoading, setMcLoading]     = useState(false)

  useEffect(() => {
    fetch(`${API}/api/bracket`)
      .then(r => r.json())
      .then(data => { setBracketData(data); setLoading(false) })
      .catch(e  => { setError(e.message);   setLoading(false) })
  }, [])

  const fetchMcOdds = useCallback(async () => {
    if (mcOdds || mcLoading) return
    setMcLoading(true)
    try {
      const res  = await fetch(`${API}/api/monte-carlo?n=200`)
      const data = await res.json()
      setMcOdds(data)
    } catch (e) {
      console.warn('Monte Carlo unavailable:', e)
    } finally {
      setMcLoading(false)
    }
  }, [mcOdds, mcLoading])

  const handleModeChange = (m) => {
    setMode(m)
    if (m === 'picks') fetchMcOdds()
  }

  const handlePick = useCallback((gameId, teamName) => {
    setUserPicks(prev => {
      if (prev[gameId] === teamName) {
        const { [gameId]: _, ...rest } = prev
        return rest
      }
      return { ...prev, [gameId]: teamName }
    })
  }, [])

  const handleTeamSelect = useCallback((team, game) => {
    setSelectedTeam(t => t === team ? null : team)
    if (game !== undefined) setSelectedGame(game)
  }, [])

  if (loading) return <div className="loading">Loading 2026 NCAA Tournament Bracket…</div>
  if (error) return (
    <div className="error">
      <p>Error: {error}</p>
      <p>Make sure the API is running: <code>./start.sh</code></p>
    </div>
  )

  return (
    <div className="app">
      <Header
        bracketData={bracketData}
        mode={mode}
        onModeChange={handleModeChange}
        userPicks={userPicks}
        onReset={() => setUserPicks({})}
        mcLoading={mcLoading}
      />
      <div className="main-layout">
        <div className="bracket-scroll">
          <Bracket
            bracketData={bracketData}
            onTeamSelect={handleTeamSelect}
            selectedTeam={selectedTeam}
            selectedGame={selectedGame}
            mode={mode}
            userPicks={userPicks}
            onPick={handlePick}
            mcOdds={mcOdds}
          />
        </div>
        <Sidebar
          bracketData={bracketData}
          selectedTeam={selectedTeam}
          selectedGame={selectedGame}
          mcOdds={mcOdds}
          mcLoading={mcLoading}
          apiBase={API}
        />
      </div>
    </div>
  )
}
