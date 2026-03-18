/**
 * Bracket.jsx
 * -----------
 * Renders the full NCAA tournament bracket:
 *   [East R1–R4] [FF+Champ] [West R4–R1]
 *   [South R1–R4]           [Midwest R4–R1]
 *
 * Connector lines: each matchup box has CSS pseudo-elements that draw
 * horizontal connector arms and vertical spine lines joining pairs.
 */

const CONFIDENCE_COLOR = {
  high:   '#22c55e',
  medium: '#f59e0b',
  low:    '#f87171',
}

const REGION_COLOR = {
  East:    '#00539b',
  West:    '#c8102e',
  South:   '#007a33',
  Midwest: '#f5821f',
}

const ROUND_LABELS = {
  1: 'R64', 2: 'R32', 3: 'Sweet 16', 4: 'Elite 8',
  5: 'Final Four', 6: 'Championship',
}

// Round index → how many games per region (8, 4, 2, 1)
// Used to compute connector heights
const ROUND_GAME_COUNT = { 1: 8, 2: 4, 3: 2, 4: 1 }

function TeamSlot({ name, seed, isWinner, isSelected, onSelect, probability, confidence }) {
  return (
    <div
      className={`team-slot${isWinner ? ' won' : ' lost'}${isSelected ? ' selected' : ''}`}
      onClick={() => onSelect(name)}
      title={isWinner && probability ? `${(probability * 100).toFixed(0)}% win probability` : name}
    >
      <span className="team-seed">{seed ?? ''}</span>
      <span className="team-name">{name}</span>
      {isWinner && probability && (
        <span className="team-prob" style={{ color: CONFIDENCE_COLOR[confidence] }}>
          {(probability * 100).toFixed(0)}%
        </span>
      )}
    </div>
  )
}

function Matchup({ game, onSelect, selectedTeam, reverse = false, roundNum }) {
  if (!game) return <div className="matchup empty" />

  const { team_a, team_b, winner, win_prob, confidence, seed_a, seed_b } = game

  const probA = win_prob
  const probB = 1 - win_prob

  const slots = reverse
    ? [{ name: team_b, seed: seed_b, prob: probB }, { name: team_a, seed: seed_a, prob: probA }]
    : [{ name: team_a, seed: seed_a, prob: probA }, { name: team_b, seed: seed_b, prob: probB }]

  return (
    <div className={`matchup round-${roundNum}${reverse ? ' reverse' : ''}`}>
      {slots.map(({ name, seed, prob }) => (
        <TeamSlot
          key={name}
          name={name}
          seed={seed}
          isWinner={name === winner}
          isSelected={name === selectedTeam}
          onSelect={onSelect}
          probability={name === winner ? prob : null}
          confidence={confidence}
        />
      ))}
    </div>
  )
}

function RoundColumn({ region, games, roundNum, onSelect, selectedTeam, reverse }) {
  const roundGames = games.filter(g => g.round_num === roundNum && g.region === region)
  return (
    <div className={`round-col round-r${roundNum}${reverse ? ' reverse' : ''}`}>
      <div className="round-label">{ROUND_LABELS[roundNum]}</div>
      <div className="round-games">
        {roundGames.map((game, i) => (
          <div key={i} className="matchup-wrapper">
            <Matchup
              game={game}
              onSelect={onSelect}
              selectedTeam={selectedTeam}
              reverse={reverse}
              roundNum={roundNum}
            />
          </div>
        ))}
      </div>
    </div>
  )
}

function RegionBracket({ region, games, onSelect, selectedTeam, reverse }) {
  const rounds = reverse ? [4, 3, 2, 1] : [1, 2, 3, 4]
  return (
    <div className={`region-bracket${reverse ? ' reverse' : ''}`}>
      <div className="region-name" style={{ color: REGION_COLOR[region] }}>{region}</div>
      <div className="region-rounds">
        {rounds.map(rn => (
          <RoundColumn
            key={rn}
            region={region}
            games={games}
            roundNum={rn}
            onSelect={onSelect}
            selectedTeam={selectedTeam}
            reverse={reverse}
          />
        ))}
      </div>
    </div>
  )
}

function FirstFourSection({ games, onSelect, selectedTeam }) {
  return (
    <div className="ff-section">
      <div className="center-badge ff-badge">FIRST FOUR · Dayton, OH</div>
      {games.map((game, i) => (
        <div key={i} className="ff-game">
          <span className="ff-seed">#{game.seed_a}</span>
          <span
            className={`ff-team${game.winner === game.team_a ? ' won' : ' lost'}${game.team_a === selectedTeam ? ' selected' : ''}`}
            onClick={() => onSelect(game.team_a)}
          >{game.team_a}</span>
          <span className="ff-vs">vs</span>
          <span
            className={`ff-team${game.winner === game.team_b ? ' won' : ' lost'}${game.team_b === selectedTeam ? ' selected' : ''}`}
            onClick={() => onSelect(game.team_b)}
          >{game.team_b}</span>
          <span className="ff-arrow">→ <strong>{game.winner}</strong></span>
        </div>
      ))}
    </div>
  )
}

function CenterColumn({ bracketData, onSelect, selectedTeam }) {
  const ffGames   = (bracketData.rounds?.['0']?.games || []).map(g => ({ ...g, round_num: 0 }))
  const ffResults = (bracketData.rounds?.['5']?.games || []).map(g => ({ ...g, round_num: 5 }))
  const champ     = bracketData.rounds?.['6']?.games?.[0]

  return (
    <div className="center-col">
      <div className="ncaa-header">
        <div className="ncaa-emblem">🏀</div>
        <div className="ncaa-wordmark">2026 NCAA</div>
        <div className="ncaa-subtitle">MEN'S BASKETBALL CHAMPIONSHIP</div>
      </div>

      {ffGames.length > 0 && (
        <FirstFourSection games={ffGames} onSelect={onSelect} selectedTeam={selectedTeam} />
      )}

      <div className="ff-results-section">
        <div className="center-badge semifinal-badge">FINAL FOUR</div>
        {ffResults.map((game, i) => (
          <Matchup key={i} game={game} onSelect={onSelect} selectedTeam={selectedTeam} roundNum={5} />
        ))}
      </div>

      {champ && (
        <div className="championship-section">
          <div className="center-badge champ-badge">🏆 NATIONAL CHAMPIONSHIP</div>
          <Matchup game={champ} onSelect={onSelect} selectedTeam={selectedTeam} roundNum={6} />
          <div className="champion-reveal">
            <div className="champion-label">PREDICTED CHAMPION</div>
            <div className="champion-name">{champ.winner}</div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function Bracket({ bracketData, onTeamSelect, selectedTeam }) {
  if (!bracketData?.rounds) return <div className="loading">No bracket data</div>

  const allGames = Object.entries(bracketData.rounds).flatMap(([rn, r]) =>
    r.games.map(g => ({ ...g, round_num: parseInt(rn) }))
  )

  const select = (team) => onTeamSelect(team === selectedTeam ? null : team)

  return (
    <div className="bracket">
      <div className="bracket-row top-row">
        <RegionBracket region="East" games={allGames} onSelect={select} selectedTeam={selectedTeam} />
        <CenterColumn bracketData={bracketData} onSelect={select} selectedTeam={selectedTeam} />
        <RegionBracket region="West" games={allGames} onSelect={select} selectedTeam={selectedTeam} reverse />
      </div>
      <div className="bracket-row bottom-row">
        <RegionBracket region="South" games={allGames} onSelect={select} selectedTeam={selectedTeam} />
        <div className="center-spacer" />
        <RegionBracket region="Midwest" games={allGames} onSelect={select} selectedTeam={selectedTeam} reverse />
      </div>
    </div>
  )
}
