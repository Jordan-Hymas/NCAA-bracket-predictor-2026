import { useState } from 'react'

const CONF_COLORS = {
  ACC: '#003087', B10: '#0088ce', B12: '#002F6C', SEC: '#fcd116',
  BE: '#003087', WCC: '#c8102e', MVC: '#552583', A10: '#c41e3a',
  Amer: '#00843d', MWC: '#003087', MAC: '#003087', default: '#555'
}

function TeamCard({ team }) {
  if (!team) return null
  const wl = `${team.Wins ?? '?'}-${team.Losses ?? '?'}`
  const color = CONF_COLORS[team.Conf] || CONF_COLORS.default
  return (
    <div className="team-card">
      <div className="tc-header" style={{ borderLeftColor: color }}>
        <div>
          <span className="tc-seed">#{team.Seed}</span>
          <span className="tc-name">{team.Team}</span>
        </div>
        <span className="tc-conf" style={{ background: color }}>{team.Conf}</span>
      </div>
      <div className="tc-record">{team.Region} · {wl} · Rk #{team.Rk}</div>
      <div className="tc-stats">
        <Stat label="Net Rtg" value={team.NetRtg?.toFixed(1)} />
        <Stat label="Off Rtg" value={team.ORtg?.toFixed(1)} />
        <Stat label="Def Rtg" value={team.DRtg?.toFixed(1)} />
        <Stat label="SOS" value={team.SOS_NetRtg?.toFixed(2)} />
        <Stat label="Tempo" value={team.AdjT?.toFixed(1)} />
        <Stat label="Luck" value={team.Luck?.toFixed(3)} />
      </div>
    </div>
  )
}

function Stat({ label, value }) {
  return (
    <div className="stat-item">
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value ?? '—'}</span>
    </div>
  )
}

function CelebrityForm({ apiBase, onAdded }) {
  const [name, setName] = useState('')
  const [champion, setChampion] = useState('')
  const [ff, setFf] = useState(['', '', '', ''])
  const [status, setStatus] = useState('')

  const submit = async () => {
    try {
      const res = await fetch(`${apiBase}/api/celebrity`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name, champion, final_four: ff.filter(Boolean)
        })
      })
      const data = await res.json()
      setStatus(data.message)
      onAdded()
    } catch (e) {
      setStatus('Error: ' + e.message)
    }
  }

  return (
    <div className="celeb-form">
      <h4>Add Celebrity Bracket</h4>
      <input placeholder="Celebrity name" value={name} onChange={e => setName(e.target.value)} />
      <input placeholder="Predicted champion" value={champion} onChange={e => setChampion(e.target.value)} />
      <div className="ff-inputs">
        {ff.map((v, i) => (
          <input key={i} placeholder={`Final Four team ${i + 1}`} value={v}
            onChange={e => setFf(prev => prev.map((x, j) => j === i ? e.target.value : x))} />
        ))}
      </div>
      <button onClick={submit} disabled={!name || !champion}>Add Bracket</button>
      {status && <p className="status">{status}</p>}
    </div>
  )
}

export default function Sidebar({ bracketData, selectedTeam, apiBase }) {
  const [tab, setTab] = useState('team')

  const teamObj = bracketData?.teams?.find(t => t.Team === selectedTeam)
  const champion = bracketData?.rounds?.['6']?.games?.[0]?.winner

  // Build Final Four + Elite Eight lists
  const ff = bracketData?.rounds?.['5']?.games?.flatMap(g => [
    { team: g.team_a, won: g.winner === g.team_a },
    { team: g.team_b, won: g.winner === g.team_b },
  ]) || []
  const e8 = bracketData?.rounds?.['4']?.games?.flatMap(g => [
    { team: g.team_a, won: g.winner === g.team_a },
    { team: g.team_b, won: g.winner === g.team_b },
  ]) || []

  return (
    <aside className="sidebar">
      <div className="tabs">
        {['team', 'picks', 'celebrity'].map(t => (
          <button key={t} className={`tab ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
            {t === 'team' ? 'Team Stats' : t === 'picks' ? 'Predictions' : 'Celebrity'}
          </button>
        ))}
      </div>

      {tab === 'team' && (
        <div className="tab-content">
          {teamObj
            ? <TeamCard team={teamObj} />
            : <p className="hint">Click a team in the bracket to see their stats</p>
          }
        </div>
      )}

      {tab === 'picks' && (
        <div className="tab-content">
          <h3 className="section-title">🏆 Predicted Champion</h3>
          <div className="champion-box">{champion}</div>

          <h3 className="section-title">Final Four</h3>
          {ff.map(({ team, won }) => (
            <div key={team} className={`round-pick ${won ? 'winner' : 'loser'}`}>{team}</div>
          ))}

          <h3 className="section-title">Elite Eight</h3>
          {e8.map(({ team, won }) => (
            <div key={team} className={`round-pick ${won ? 'winner' : 'loser'}`}>{team}</div>
          ))}
        </div>
      )}

      {tab === 'celebrity' && (
        <div className="tab-content">
          <p className="hint">Add public celebrity bracket picks to influence predictions.</p>
          <CelebrityForm apiBase={apiBase} onAdded={() => window.location.reload()} />
        </div>
      )}
    </aside>
  )
}
