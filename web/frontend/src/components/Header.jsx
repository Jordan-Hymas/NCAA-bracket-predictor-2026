export default function Header({ bracketData, mode, onModeChange, userPicks, onReset, mcLoading }) {
  const aiChampion   = bracketData?.rounds?.['6']?.games?.[0]?.winner
  const userChampion = userPicks?.['CHAMP'] ?? null
  const champion     = mode === 'picks' ? userChampion : aiChampion

  const aiFinalFour  = bracketData?.rounds?.['5']?.games?.flatMap(g => [g.team_a, g.team_b]) || []

  return (
    <header className="header">
      <div className="header-left">
        <span className="header-logo">🏀</span>
        <div>
          <h1 className="header-title">2026 NCAA Tournament Predictor</h1>
          <p className="header-sub">AI predictions · H2H analytics · Expert consensus</p>
        </div>
      </div>

      <div className="mode-tabs">
        <button
          className={`mode-tab${mode === 'ai' ? ' active' : ''}`}
          onClick={() => onModeChange('ai')}
        >
          AI Prediction
        </button>
        <button
          className={`mode-tab${mode === 'picks' ? ' active' : ''}`}
          onClick={() => onModeChange('picks')}
        >
          Your Picks
          {mcLoading && <span className="mode-tab-loading"> ⏳</span>}
        </button>
      </div>

      <div className="header-picks">
        {mode === 'ai' && (
          <>
            {aiChampion && (
              <div className="pick-chip champion">
                <span className="chip-label">AI Champion</span>
                <span className="chip-team">{aiChampion}</span>
              </div>
            )}
            {aiFinalFour.length === 4 && (
              <div className="pick-chip">
                <span className="chip-label">Final Four</span>
                <span className="chip-team">{aiFinalFour.join(' · ')}</span>
              </div>
            )}
          </>
        )}

        {mode === 'picks' && (
          <>
            <div className={`pick-chip${champion ? ' your-pick' : ''}`}>
              <span className="chip-label">Your Champion</span>
              <span className={`chip-team${!champion ? ' tbd-text' : ''}`}>
                {champion || 'TBD — fill in your bracket'}
              </span>
            </div>
            {Object.keys(userPicks).length > 0 && (
              <button className="reset-btn" onClick={onReset}>↺ Reset</button>
            )}
          </>
        )}
      </div>
    </header>
  )
}
