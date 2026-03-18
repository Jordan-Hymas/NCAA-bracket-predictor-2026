import { useState } from 'react'

const CONF_COLORS = {
  ACC: '#003087', B10: '#0088ce', B12: '#002F6C', SEC: '#fcd116',
  BE: '#003087', WCC: '#c8102e', MVC: '#552583', A10: '#c41e3a',
  Amer: '#00843d', MWC: '#003087', MAC: '#003087', default: '#555',
}

// ─── Team Card ─────────────────────────────────────────────────────────────────

function Stat({ label, value }) {
  return (
    <div className="stat-item">
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value ?? '—'}</span>
    </div>
  )
}

function TeamCard({ team }) {
  if (!team) return null
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
      <div className="tc-record">{team.Region} · {team.Wins ?? '?'}-{team.Losses ?? '?'} · Rk #{team.Rk}</div>
      <div className="tc-stats">
        <Stat label="Net Rtg"  value={team.NetRtg?.toFixed(1)} />
        <Stat label="Off Rtg"  value={team.ORtg?.toFixed(1)} />
        <Stat label="Def Rtg"  value={team.DRtg?.toFixed(1)} />
        <Stat label="SOS"      value={team.SOS_NetRtg?.toFixed(2)} />
        <Stat label="Tempo"    value={team.AdjT?.toFixed(1)} />
        <Stat label="Luck"     value={team.Luck?.toFixed(3)} />
      </div>
    </div>
  )
}

// ─── Win Probability Gauge ────────────────────────────────────────────────────

function WinProbGauge({ teamA, teamB, probA }) {
  const pA = (probA * 100).toFixed(1)
  const pB = (100 - probA * 100).toFixed(1)
  return (
    <div className="prob-gauge">
      <div className="prob-labels">
        <span className="prob-name">{teamA}</span>
        <span className="prob-name right">{teamB}</span>
      </div>
      <div className="prob-bar-outer">
        <div className="prob-bar-a" style={{ width: `${pA}%` }}>
          {parseFloat(pA) > 15 && <span>{pA}%</span>}
        </div>
        <div className="prob-bar-b" style={{ width: `${pB}%` }}>
          {parseFloat(pB) > 15 && <span>{pB}%</span>}
        </div>
      </div>
    </div>
  )
}

// ─── Signal Bar Chart ─────────────────────────────────────────────────────────

const SIGNALS = [
  { key: 'h2h',       label: 'Head-to-Head',    weight: '32%', scale: 1.0 },
  { key: 'common',    label: 'Common Opp',       weight: '22%', scale: 30  },
  { key: 'net_rtg',   label: 'Net Rating',        weight: '18%', scale: 25  },
  { key: 'sos',       label: 'Strength of Sched', weight: '9%',  scale: 15  },
  { key: 'celebrity', label: 'Expert Consensus',  weight: '5%',  scale: 0.5 },
  { key: 'seed',      label: 'Seed Prior',        weight: '2%',  scale: 0.5 },
]

function SignalChart({ factors, teamA }) {
  if (!factors) return <p className="hint" style={{ marginTop: 8 }}>No factor data for this game.</p>

  const values = {
    h2h:       factors.h2h_score,
    common:    factors.common_opp_pts / 30,
    net_rtg:   factors.net_rtg_diff   / 25,
    sos:       factors.sos_diff       / 15,
    celebrity: factors.celebrity_pick === teamA
                 ? (factors.celebrity_agree - 0.5)
                 : -(factors.celebrity_agree - 0.5),
    seed:      (factors.seed_prior ?? 0.5) - 0.5,
  }

  return (
    <div className="signal-chart">
      <div className="sc-legend">
        <span className="sc-team-a">{teamA} ←</span>
        <span className="sc-center">0</span>
        <span className="sc-team-b">→ Opponent</span>
      </div>
      {SIGNALS.map(({ key, label, weight }) => {
        const raw   = values[key] ?? 0
        const clamped = Math.max(-1, Math.min(1, raw))
        const pct   = Math.abs(clamped) * 100
        const left  = clamped > 0

        return (
          <div key={key} className="sc-row">
            <div className="sc-label">
              <span>{label}</span>
              <span className="sc-weight">{weight}</span>
            </div>
            <div className="sc-bars">
              <div className="sc-bar-half left">
                {left && <div className="sc-fill fill-a" style={{ width: `${pct}%` }} />}
              </div>
              <div className="sc-divider" />
              <div className="sc-bar-half right">
                {!left && <div className="sc-fill fill-b" style={{ width: `${pct}%` }} />}
              </div>
            </div>
          </div>
        )
      })}

      {factors.h2h_games > 0 && (
        <div className="h2h-note">
          ⚔ {factors.h2h_games} direct H2H game{factors.h2h_games > 1 ? 's' : ''} ·
          score {factors.h2h_score > 0 ? '+' : ''}{factors.h2h_score?.toFixed(3)}
        </div>
      )}
      {factors.celebrity_pick && (
        <div className="h2h-note">
          🎤 Experts pick <strong>{factors.celebrity_pick}</strong> ({(factors.celebrity_agree * 100).toFixed(0)}% agreement)
        </div>
      )}
    </div>
  )
}

// ─── Stats Comparison Table ───────────────────────────────────────────────────

const COMPARE_STATS = [
  { key: 'NetRtg',      label: 'Net Rating',  higherBetter: true  },
  { key: 'ORtg',        label: 'Off Rating',  higherBetter: true  },
  { key: 'DRtg',        label: 'Def Rating',  higherBetter: false },
  { key: 'SOS_NetRtg',  label: 'SOS',         higherBetter: true  },
  { key: 'AdjT',        label: 'Tempo',       higherBetter: null  },
  { key: 'Luck',        label: 'Luck',        higherBetter: false },
]

function StatsComparison({ teamA, teamB }) {
  if (!teamA || !teamB) return null
  return (
    <table className="stats-table">
      <thead>
        <tr>
          <th className="st-team">{teamA.Team}</th>
          <th className="st-label">Stat</th>
          <th className="st-team right">{teamB.Team}</th>
        </tr>
      </thead>
      <tbody>
        {COMPARE_STATS.map(({ key, label, higherBetter }) => {
          const vA = teamA[key]
          const vB = teamB[key]
          const aWins = higherBetter === null ? false
            : higherBetter ? vA > vB : vA < vB
          const bWins = higherBetter === null ? false
            : higherBetter ? vB > vA : vB < vA
          return (
            <tr key={key}>
              <td className={`st-val${aWins ? ' better' : ''}`}>{vA?.toFixed(1) ?? '—'}</td>
              <td className="st-label-cell">{label}</td>
              <td className={`st-val right${bWins ? ' better' : ''}`}>{vB?.toFixed(1) ?? '—'}</td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

// ─── MC Odds Row ──────────────────────────────────────────────────────────────

function MCOddsRow({ teamA, teamB, mcOdds }) {
  if (!mcOdds) return null
  const champA = ((mcOdds.champion?.[teamA] || 0) * 100).toFixed(1)
  const ffA    = ((mcOdds.final_four?.[teamA] || 0) * 100).toFixed(0)
  const champB = ((mcOdds.champion?.[teamB] || 0) * 100).toFixed(1)
  const ffB    = ((mcOdds.final_four?.[teamB] || 0) * 100).toFixed(0)
  return (
    <div className="mc-odds-block">
      <div className="mc-row">
        <div className="mc-team-col">
          <div className="mc-name">{teamA}</div>
          <div className="mc-stat">🏆 {champA}%  · FF {ffA}%</div>
        </div>
        <div className="mc-vs">200 sims</div>
        <div className="mc-team-col right">
          <div className="mc-name">{teamB}</div>
          <div className="mc-stat">{champB}% 🏆  · {ffB}% FF</div>
        </div>
      </div>
    </div>
  )
}

// ─── Matchup Analysis Panel ───────────────────────────────────────────────────

function MatchupAnalysis({ game, bracketData, mcOdds }) {
  if (!game)
    return <p className="hint">Click any matchup in the bracket to see detailed analytics</p>
  if (!game.team_a || !game.team_b)
    return <p className="hint">This game's participants aren't determined yet — keep filling in your bracket!</p>

  const { team_a, team_b, winner, win_prob = 0.5, confidence, factors } = game
  const teamA = bracketData?.teams?.find(t => t.Team === team_a)
  const teamB = bracketData?.teams?.find(t => t.Team === team_b)

  return (
    <div className="matchup-analysis">
      <div className="ma-header">
        <span className="ma-teams">{team_a} vs {team_b}</span>
        <span className={`conf-badge ${confidence}`}>{confidence} confidence</span>
      </div>

      {winner && (
        <div className="ma-winner">
          Predicted winner: <strong>{winner}</strong>
        </div>
      )}

      <WinProbGauge teamA={team_a} teamB={team_b} probA={win_prob} />

      <h4 className="ma-section-title">Signal Breakdown</h4>
      <p className="ma-section-sub">Bars show each factor's direction and magnitude</p>
      <SignalChart factors={factors} teamA={team_a} />

      <h4 className="ma-section-title">Stats Comparison</h4>
      <StatsComparison teamA={teamA} teamB={teamB} />

      {mcOdds && (
        <>
          <h4 className="ma-section-title">Monte Carlo Odds</h4>
          <p className="ma-section-sub">200 simulations with model noise</p>
          <MCOddsRow teamA={team_a} teamB={team_b} mcOdds={mcOdds} />
        </>
      )}
    </div>
  )
}

// ─── Main Sidebar ─────────────────────────────────────────────────────────────

export default function Sidebar({ bracketData, selectedTeam, selectedGame, mcOdds, mcLoading, apiBase }) {
  const [tab, setTab] = useState('analysis')

  const teamObj  = bracketData?.teams?.find(t => t.Team === selectedTeam)
  const champion = bracketData?.rounds?.['6']?.games?.[0]?.winner
  const ff = bracketData?.rounds?.['5']?.games?.flatMap(g => [
    { team: g.team_a, won: g.winner === g.team_a },
    { team: g.team_b, won: g.winner === g.team_b },
  ]) || []
  const e8 = bracketData?.rounds?.['4']?.games?.flatMap(g => [
    { team: g.team_a, won: g.winner === g.team_a },
    { team: g.team_b, won: g.winner === g.team_b },
  ]) || []

  const TABS = [
    { id: 'analysis', label: 'Analysis' },
    { id: 'team',     label: 'Team Stats' },
    { id: 'picks',    label: 'AI Picks' },
  ]

  return (
    <aside className="sidebar">
      <div className="tabs">
        {TABS.map(t => (
          <button key={t.id} className={`tab${tab === t.id ? ' active' : ''}`} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'analysis' && (
        <div className="tab-content">
          {mcLoading && !selectedGame && (
            <p className="hint">⏳ Computing Monte Carlo odds (200 simulations)…</p>
          )}
          <MatchupAnalysis game={selectedGame} bracketData={bracketData} mcOdds={mcOdds} />
        </div>
      )}

      {tab === 'team' && (
        <div className="tab-content">
          {teamObj
            ? <TeamCard team={teamObj} />
            : <p className="hint">Click any team in the bracket to see their stats</p>
          }
        </div>
      )}

      {tab === 'picks' && (
        <div className="tab-content">
          <h3 className="section-title">🏆 AI Champion</h3>
          <div className="champion-box">{champion}</div>

          <h3 className="section-title">Final Four</h3>
          {ff.map(({ team, won }) => (
            <div key={team} className={`round-pick ${won ? 'winner' : 'loser'}`}>{team}</div>
          ))}

          <h3 className="section-title">Elite Eight</h3>
          {e8.map(({ team, won }) => (
            <div key={team} className={`round-pick ${won ? 'winner' : 'loser'}`}>{team}</div>
          ))}

          {mcOdds && (
            <>
              <h3 className="section-title">Championship Odds (200 sims)</h3>
              {Object.entries(mcOdds.champion)
                .filter(([, p]) => p > 0.01)
                .sort(([, a], [, b]) => b - a)
                .map(([team, prob]) => (
                  <div key={team} className="mc-list-row">
                    <span className="mc-list-name">{team}</span>
                    <div className="mc-list-bar">
                      <div className="mc-list-fill" style={{ width: `${(prob * 100).toFixed(0)}%` }} />
                    </div>
                    <span className="mc-list-pct">{(prob * 100).toFixed(1)}%</span>
                  </div>
                ))
              }
            </>
          )}
        </div>
      )}
    </aside>
  )
}
