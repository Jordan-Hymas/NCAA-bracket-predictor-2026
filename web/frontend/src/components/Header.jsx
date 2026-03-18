export default function Header({ bracketData }) {
  if (!bracketData) return null

  const champion = bracketData.rounds?.['6']?.games?.[0]?.winner
  const finalFour = bracketData.rounds?.['5']?.games?.flatMap(g => [g.team_a, g.team_b]) || []

  return (
    <header className="header">
      <div className="header-left">
        <span className="header-logo">🏀</span>
        <div>
          <h1 className="header-title">2026 NCAA Tournament Predictor</h1>
          <p className="header-sub">AI-powered bracket predictions using advanced analytics</p>
        </div>
      </div>
      <div className="header-picks">
        {champion && (
          <div className="pick-chip champion">
            <span className="chip-label">Predicted Champion</span>
            <span className="chip-team">{champion}</span>
          </div>
        )}
        {finalFour.length === 4 && (
          <div className="pick-chip ff">
            <span className="chip-label">Final Four</span>
            <span className="chip-team">{finalFour.join(' · ')}</span>
          </div>
        )}
      </div>
    </header>
  )
}
