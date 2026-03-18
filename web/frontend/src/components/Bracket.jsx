/**
 * Bracket.jsx  —  ESPN-style NCAA bracket
 *
 * Layout:
 *   [East  R1→R4] [CenterCol FF+Champ] [West  R4→R1]
 *   [South R1→R4] [Spacer]             [Midwest R4→R1]
 *
 * Spacing: mathematically exact so connector lines align.
 *   H = matchup height (58px), G1 = R64 gap (4px)
 *   R32 gap = H + 2G1 = 66px   pad = (H+G1)/2 = 31px
 *   S16 gap = 3H + 4G1 = 190px  pad = 93px
 *   E8  gap = N/A (1 game)       pad = 217px
 */

const CONF_COLOR = { high: '#3fb950', medium: '#d29922', low: '#f85149' }
const REGION_COLOR = { East: '#00539b', West: '#c8102e', South: '#007a33', Midwest: '#f5821f' }
const ROUND_LABEL = { 1: 'R64', 2: 'R32', 3: 'Sweet 16', 4: 'Elite 8', 5: 'Final Four', 6: 'Championship' }

// ─── Picks-mode bracket derivation ────────────────────────────────────────────

function derivePicksBracket(bracketData, userPicks) {
  const teamSeeds = {}
  bracketData.teams?.forEach(t => { teamSeeds[t.Team] = t.Seed })

  const modelLookup = {}
  Object.values(bracketData.rounds).forEach(round =>
    round.games.forEach(g => {
      modelLookup[`${g.team_a}|${g.team_b}`] = g
      modelLookup[`${g.team_b}|${g.team_a}`] = g
    })
  )

  const derived = []

  for (const region of ['East', 'West', 'South', 'Midwest']) {
    const r64   = (bracketData.rounds['1']?.games || []).filter(g => g.region === region)
    let slots   = r64.flatMap(g => [g.team_a, g.team_b])

    for (let rn = 1; rn <= 4; rn++) {
      const numGames = Math.floor(slots.length / 2)
      const next = []
      for (let gi = 0; gi < numGames; gi++) {
        const teamA  = slots[gi * 2]      || null
        const teamB  = slots[gi * 2 + 1] || null
        const gameId = `${region}-${rn}-${gi}`
        const model  = (teamA && teamB) ? (modelLookup[`${teamA}|${teamB}`] ?? null) : null
        const pick   = userPicks[gameId]
        const valid  = (pick === teamA || pick === teamB) ? pick : null
        derived.push({
          gameId, region, round_num: rn,
          team_a: teamA, team_b: teamB,
          seed_a: teamA ? teamSeeds[teamA] : null,
          seed_b: teamB ? teamSeeds[teamB] : null,
          winner: model?.winner ?? null,
          userWinner: valid, modelWinner: model?.winner ?? null,
          win_prob: model?.win_prob ?? 0.5, confidence: model?.confidence ?? 'low',
          factors: model?.factors ?? null,
        })
        next.push(valid)
      }
      slots = next
    }
  }

  // Regional champions
  const champs = {}
  for (const r of ['East', 'West', 'South', 'Midwest'])
    champs[r] = derived.find(g => g.region === r && g.round_num === 4)?.userWinner ?? null

  // Final Four
  const ffWinners = []
  ;[['East', 'West'], ['South', 'Midwest']].forEach(([r1, r2], fi) => {
    const teamA = champs[r1], teamB = champs[r2]
    const gameId = `FF-${fi}`
    const model  = bracketData.rounds['5']?.games?.[fi]
    const pick   = userPicks[gameId]
    const valid  = (pick === teamA || pick === teamB) ? pick : null
    derived.push({
      gameId, region: '', round_num: 5,
      team_a: teamA, team_b: teamB,
      seed_a: teamA ? teamSeeds[teamA] : null, seed_b: teamB ? teamSeeds[teamB] : null,
      winner: model?.winner ?? null, userWinner: valid, modelWinner: model?.winner ?? null,
      win_prob: model?.win_prob ?? 0.5, confidence: model?.confidence ?? 'low',
      factors: model?.factors ?? null,
    })
    ffWinners.push(valid)
  })

  // Championship
  const [w0, w1] = ffWinners
  const cpick    = userPicks['CHAMP']
  const cvalid   = (cpick === w0 || cpick === w1) ? cpick : null
  const model    = bracketData.rounds['6']?.games?.[0]
  derived.push({
    gameId: 'CHAMP', region: '', round_num: 6,
    team_a: w0 ?? null, team_b: w1 ?? null,
    seed_a: w0 ? teamSeeds[w0] : null, seed_b: w1 ? teamSeeds[w1] : null,
    winner: model?.winner ?? null, userWinner: cvalid, modelWinner: model?.winner ?? null,
    win_prob: model?.win_prob ?? 0.5, confidence: model?.confidence ?? 'low',
    factors: model?.factors ?? null,
  })

  return derived
}

// ─── Path-mode bracket derivation (selected team always wins) ─────────────────

function derivePathBracket(bracketData, pathTeam) {
  const teamSeeds = {}
  bracketData.teams?.forEach(t => { teamSeeds[t.Team] = t.Seed })

  const modelLookup = {}
  Object.values(bracketData.rounds).forEach(round =>
    round.games.forEach(g => {
      modelLookup[`${g.team_a}|${g.team_b}`] = g
      modelLookup[`${g.team_b}|${g.team_a}`] = g
    })
  )

  const derived = []

  for (const region of ['East', 'West', 'South', 'Midwest']) {
    const r64 = (bracketData.rounds['1']?.games || []).filter(g => g.region === region)
    let slots = r64.flatMap(g => [g.team_a, g.team_b])

    for (let rn = 1; rn <= 4; rn++) {
      const numGames = Math.floor(slots.length / 2)
      const next = []
      for (let gi = 0; gi < numGames; gi++) {
        const teamA  = slots[gi * 2]      || null
        const teamB  = slots[gi * 2 + 1] || null
        const gameId = `${region}-${rn}-${gi}`
        const model  = (teamA && teamB) ? (modelLookup[`${teamA}|${teamB}`] ?? null) : null
        // pathTeam always wins; other games use AI prediction
        const userWinner = (teamA === pathTeam || teamB === pathTeam)
          ? pathTeam
          : (model?.winner ?? teamA)
        derived.push({
          gameId, region, round_num: rn,
          team_a: teamA, team_b: teamB,
          seed_a: teamA ? teamSeeds[teamA] : null,
          seed_b: teamB ? teamSeeds[teamB] : null,
          winner: model?.winner ?? null, userWinner,
          modelWinner: model?.winner ?? null,
          win_prob: model?.win_prob ?? 0.5, confidence: model?.confidence ?? 'low',
          factors: model?.factors ?? null,
        })
        next.push(userWinner)
      }
      slots = next
    }
  }

  // Regional champions
  const champs = {}
  for (const r of ['East', 'West', 'South', 'Midwest'])
    champs[r] = derived.find(g => g.region === r && g.round_num === 4)?.userWinner ?? null

  // Final Four
  const ffWinners = []
  ;[['East', 'West'], ['South', 'Midwest']].forEach(([r1, r2], fi) => {
    const teamA = champs[r1], teamB = champs[r2]
    const model = bracketData.rounds['5']?.games?.[fi]
    const userWinner = (teamA === pathTeam || teamB === pathTeam)
      ? pathTeam
      : (model?.winner ?? teamA)
    derived.push({
      gameId: `FF-${fi}`, region: '', round_num: 5,
      team_a: teamA, team_b: teamB,
      seed_a: teamA ? teamSeeds[teamA] : null, seed_b: teamB ? teamSeeds[teamB] : null,
      winner: model?.winner ?? null, userWinner,
      modelWinner: model?.winner ?? null,
      win_prob: model?.win_prob ?? 0.5, confidence: model?.confidence ?? 'low',
      factors: model?.factors ?? null,
    })
    ffWinners.push(userWinner)
  })

  // Championship
  const [w0, w1] = ffWinners
  const model = bracketData.rounds['6']?.games?.[0]
  const userWinner = (w0 === pathTeam || w1 === pathTeam)
    ? pathTeam
    : (model?.winner ?? w0)
  derived.push({
    gameId: 'CHAMP', region: '', round_num: 6,
    team_a: w0 ?? null, team_b: w1 ?? null,
    seed_a: w0 ? teamSeeds[w0] : null, seed_b: w1 ? teamSeeds[w1] : null,
    winner: model?.winner ?? null, userWinner,
    modelWinner: model?.winner ?? null,
    win_prob: model?.win_prob ?? 0.5, confidence: model?.confidence ?? 'low',
    factors: model?.factors ?? null,
  })

  return derived
}

// ─── Team Slot ─────────────────────────────────────────────────────────────────

function TeamSlot({ name, seed, isWinner, isPicked, isSelected, onClick, probability, confidence, mode, champOdds }) {
  return (
    <div
      className={[
        'team-slot',
        mode === 'ai' && isWinner && name  ? 'won'      : '',
        mode === 'ai' && !isWinner && name ? 'lost'     : '',
        isPicked   ? 'picked'   : '',
        isSelected ? 'selected' : '',
        !name      ? 'tbd'      : '',
      ].filter(Boolean).join(' ')}
      onClick={() => name && onClick(name)}
    >
      <div className="team-logo">{name ? name.charAt(0) : '?'}</div>
      <span className="team-seed">{seed ?? ''}</span>
      <span className="team-name">{name || 'TBD'}</span>

      {mode === 'ai' && isWinner && probability != null && (
        <span className="team-prob" style={{ color: CONF_COLOR[confidence] }}>
          {(probability * 100).toFixed(0)}%
        </span>
      )}
      {mode === 'picks' && champOdds != null && champOdds >= 0.02 && (
        <span className="team-mc-odds">{(champOdds * 100).toFixed(0)}%</span>
      )}
      {mode === 'picks' && isPicked && <span className="pick-check">✓</span>}
    </div>
  )
}

// ─── Matchup ───────────────────────────────────────────────────────────────────

function Matchup({ game, onTeamSelect, selectedTeam, reverse, roundNum, mode, onPick, mcOdds, pathTeam }) {
  if (!game) return <div className="matchup empty" />

  const picks  = mode === 'picks'
  const winner = (picks || pathTeam) ? game.userWinner : game.winner
  const { team_a, team_b, win_prob = 0.5, confidence = 'low', seed_a, seed_b, gameId } = game

  const raw   = [
    { name: team_a, seed: seed_a, prob: win_prob },
    { name: team_b, seed: seed_b, prob: 1 - win_prob },
  ]
  const slots = reverse ? [...raw].reverse() : raw

  const handleClick = (name) => {
    onTeamSelect(name, game)
    if (picks && onPick) onPick(gameId, name)
  }

  const onPath = pathTeam && (team_a === pathTeam || team_b === pathTeam)
  const dimmed = pathTeam && !onPath

  return (
    <div className={['matchup', `round-${roundNum}`, picks ? 'picks-mode' : '', onPath ? 'path-on' : '', dimmed ? 'path-dim' : ''].filter(Boolean).join(' ')}>
      {slots.map(({ name, seed, prob }) => (
        <TeamSlot
          key={name ?? `tbd-${seed}`}
          name={name} seed={seed}
          isWinner={!!name && name === winner}
          isPicked={picks && !!name && name === winner}
          isSelected={name === selectedTeam}
          onClick={handleClick}
          probability={name === winner ? prob : null}
          confidence={confidence}
          mode={mode}
          champOdds={name && mcOdds?.champion ? mcOdds.champion[name] : null}
        />
      ))}
    </div>
  )
}

// ─── Round Column ──────────────────────────────────────────────────────────────

function RoundColumn({ region, games, roundNum, onTeamSelect, selectedTeam, reverse, mode, onPick, mcOdds, pathTeam }) {
  const rGames = games.filter(g => g.round_num === roundNum && g.region === region)
  return (
    <div className={`round-col round-r${roundNum}${reverse ? ' reverse' : ''}`}>
      <div className="round-label">{ROUND_LABEL[roundNum]}</div>
      <div className="round-games">
        {rGames.map((game, i) => (
          <div key={i} className="matchup-wrapper">
            <Matchup
              game={game}
              onTeamSelect={onTeamSelect}
              selectedTeam={selectedTeam}
              reverse={reverse}
              roundNum={roundNum}
              mode={mode}
              onPick={onPick}
              mcOdds={mcOdds}
              pathTeam={pathTeam}
            />
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Region Bracket ────────────────────────────────────────────────────────────

function RegionBracket({ region, games, onTeamSelect, selectedTeam, reverse, mode, onPick, mcOdds, pathTeam }) {
  const rounds = [1, 2, 3, 4]
  return (
    <div className={`region-bracket${reverse ? ' reverse' : ''}`}>
      <div className="region-name" style={{ color: REGION_COLOR[region] }}>{region}</div>
      <div className="region-rounds">
        {rounds.map(rn => (
          <RoundColumn
            key={rn} region={region} games={games} roundNum={rn}
            onTeamSelect={onTeamSelect} selectedTeam={selectedTeam}
            reverse={reverse} mode={mode} onPick={onPick} mcOdds={mcOdds} pathTeam={pathTeam}
          />
        ))}
      </div>
    </div>
  )
}

// ─── Center Team Row ───────────────────────────────────────────────────────────

function CenterTeamRow({ name, seed, isWinner, isSelected, onClick }) {
  return (
    <div
      className={['cc-team-row', isWinner ? 'cc-winner' : '', isSelected ? 'cc-selected' : '', !name ? 'cc-tbd' : ''].filter(Boolean).join(' ')}
      onClick={() => name && onClick(name)}
    >
      <span className="cc-seed">{seed != null ? seed : '—'}</span>
      <span className="cc-name">{name || 'TBD'}</span>
      {isWinner && name && <span className="cc-check">✓</span>}
    </div>
  )
}

// ─── Center Column ─────────────────────────────────────────────────────────────

function CenterColumn({ bracketData, games, onTeamSelect, selectedTeam, mode, pathTeam }) {
  const picks  = mode === 'picks'
  const useUserWinner = picks || !!pathTeam
  const sel    = (name, game) => onTeamSelect(name, game)
  const eff    = (g) => useUserWinner ? g.userWinner : g.winner

  const e8Games   = games.filter(g => g.round_num === 4)
  const ffGames   = games.filter(g => g.round_num === 5)
  const champ     = games.find(g => g.round_num === 6)
  const champWinner = champ ? eff(champ) : null

  const teamsFrom = (gameList) =>
    gameList.flatMap(g => [
      { name: g.team_a, seed: g.seed_a, isWinner: eff(g) === g.team_a, game: g },
      { name: g.team_b, seed: g.seed_b, isWinner: eff(g) === g.team_b, game: g },
    ])

  const e8Teams   = teamsFrom(e8Games)
  const ffTeams   = teamsFrom(ffGames)
  const champTeams = champ ? teamsFrom([champ]) : []

  return (
    <div className="center-col">
      <div className="ncaa-header">
        <img src="/marchMadnessLogo.png" alt="March Madness" className="ncaa-logo" />
      </div>

      <div className="cc-section">
        <div className="cc-section-header cc-e8">
          <span className="cc-header-label">Elite Eight</span>
        </div>
        <div className="cc-team-grid">
          {e8Teams.map(({ name, seed, isWinner, game }) => (
            <CenterTeamRow key={name ?? `tbd-e8-${seed}`} name={name} seed={seed}
              isWinner={isWinner} isSelected={name === selectedTeam || name === pathTeam}
              onClick={(n) => sel(n, game)} />
          ))}
        </div>
      </div>

      <div className="cc-section">
        <div className="cc-section-header cc-ff">
          <span className="cc-header-label">Final Four</span>
          <span className="cc-header-venue">Indianapolis</span>
        </div>
        <div className="cc-team-list">
          {ffTeams.map(({ name, seed, isWinner, game }) => (
            <CenterTeamRow key={name ?? `tbd-ff-${seed}`} name={name} seed={seed}
              isWinner={isWinner} isSelected={name === selectedTeam || name === pathTeam}
              onClick={(n) => sel(n, game)} />
          ))}
        </div>
      </div>

      {champ && (
        <div className="cc-section">
          <div className="cc-section-header cc-champ">
            <span className="cc-header-label">Championship</span>
          </div>
          <div className="cc-team-list">
            {champTeams.map(({ name, seed, isWinner, game }) => (
              <CenterTeamRow key={name ?? `tbd-champ-${seed}`} name={name} seed={seed}
                isWinner={isWinner} isSelected={name === selectedTeam || name === pathTeam}
                onClick={(n) => sel(n, game)} />
            ))}
          </div>
          <div className={`champion-reveal${!champWinner ? ' pending' : ''}`}>
            <div className="champion-label">
              {pathTeam ? `${pathTeam} path` : picks ? 'Your Champion' : 'Predicted Champion'}
            </div>
            <div className="champion-name">{champWinner || 'TBD'}</div>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Main Bracket ──────────────────────────────────────────────────────────────

export default function Bracket({ bracketData, onTeamSelect, selectedTeam, selectedGame,
                                  mode, userPicks, onPick, mcOdds, pathTeam }) {
  if (!bracketData?.rounds) return <div className="loading">No bracket data</div>

  const allGames = mode === 'picks'
    ? derivePicksBracket(bracketData, userPicks || {})
    : pathTeam
      ? derivePathBracket(bracketData, pathTeam)
      : Object.entries(bracketData.rounds).flatMap(([rn, r]) =>
          r.games.map(g => ({ ...g, round_num: parseInt(rn) }))
        )

  const shared = { onTeamSelect, selectedTeam, mode, onPick, mcOdds, pathTeam }

  return (
    <div className="bracket">
      <div className="bracket-left">
        <RegionBracket region="East"    games={allGames} {...shared} />
        <RegionBracket region="South"   games={allGames} {...shared} />
      </div>
      <CenterColumn bracketData={bracketData} games={allGames} {...shared} />
      <div className="bracket-right">
        <RegionBracket region="West"    games={allGames} {...shared} reverse />
        <RegionBracket region="Midwest" games={allGames} {...shared} reverse />
      </div>
    </div>
  )
}
