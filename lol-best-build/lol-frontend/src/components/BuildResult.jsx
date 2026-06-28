import './BuildResult.css'

const SPELL_ICONS = {
  4:  'SummonerFlash',
  14: 'SummonerDot',
  12: 'SummonerTeleport',
  11: 'SummonerSmite',
  7:  'SummonerHeal',
  3:  'SummonerExhaust',
  6:  'SummonerHaste',
  1:  'SummonerBoost',
  21: 'SummonerBarrier',
}

const DDR = 'https://ddragon.leagueoflegends.com/cdn/14.24.1'

function spellIcon(id) {
  const name = SPELL_ICONS[id] || `Summoner${id}`
  return `${DDR}/img/spell/${name}.png`
}

export default function BuildResult({ data }) {
  const { champion, region, queue, topPlayers, totalMatchesAnalyzed, bestBuild } = data
  const { winRate, sampleSize, items, summonerSpells, runes, averageStats } = bestBuild

  return (
    <div className="result">
      {/* Champion header */}
      <div className="result-hero">
        <img className="champ-splash" src={champion.imageUrl} alt={champion.name} />
        <div className="champ-info">
          <h2 className="champ-name">{champion.name}</h2>
          <div className="champ-meta">
            <Tag>{region.toUpperCase()}</Tag>
            <Tag>{queue === 'ranked_solo' ? 'Solo/Duo' : 'Flex'}</Tag>
            <Tag gold>{sampleSize} parties analysées</Tag>
          </div>
          <div className="winrate-row">
            <span className="winrate-label">Win rate global</span>
            <span className="winrate-value" style={{ color: winRate >= 50 ? 'var(--green)' : 'var(--red)' }}>
              {winRate}%
            </span>
          </div>
        </div>
      </div>

      <div className="result-grid">
        {/* Items */}
        <Section title="Items recommandés">
          <div className="items-row">
            {items.map((item, i) => (
              <div key={item.itemId} className="item-cell">
                <div className="item-rank">{i + 1}</div>
                <img
                  className="item-img"
                  src={`${DDR}/img/item/${item.itemId}.png`}
                  alt={`Item ${item.itemId}`}
                  onError={e => e.target.style.opacity = '0.3'}
                />
                <div className="item-stats">
                  <span className="item-wr" style={{ color: item.winRate >= 50 ? 'var(--green)' : 'var(--red)' }}>
                    {item.winRate}% WR
                  </span>
                  <span className="item-pr">{item.pickRate}% pick</span>
                </div>
              </div>
            ))}
          </div>
        </Section>

        {/* Sorts + Runes */}
        <div className="side-panels">
          {/* Summoner Spells */}
          {summonerSpells?.spell1 && (
            <Section title="Sorts d'invocateur">
              <div className="spells-row">
                <SpellCard id={summonerSpells.spell1.id} name={summonerSpells.spell1.name} />
                <SpellCard id={summonerSpells.spell2.id} name={summonerSpells.spell2.name} />
              </div>
              <p className="sub-stat">Joués dans {summonerSpells.pickRate}% des parties</p>
            </Section>
          )}

          {/* Runes */}
          {runes?.primaryStyle?.name && (
            <Section title="Runes">
              <div className="runes-row">
                <RuneCard label="Principal" name={runes.primaryStyle.name} rate={runes.primaryStyle.pickRate} />
                <RuneCard label="Secondaire" name={runes.secondaryStyle.name} rate={runes.secondaryStyle.pickRate} />
              </div>
            </Section>
          )}
        </div>

        {/* KDA */}
        {averageStats && (
          <Section title="Stats moyennes">
            <div className="kda-row">
              <KdaStat label="Kills" value={averageStats.kills} color="var(--gold-light)" />
              <KdaStat label="Morts" value={averageStats.deaths} color="var(--red)" />
              <KdaStat label="Assists" value={averageStats.assists} color="var(--green)" />
              <KdaStat label="KDA" value={averageStats.kda} color="var(--gold)" large />
            </div>
          </Section>
        )}

        {/* Top players */}
        <Section title="Meilleurs joueurs analysés">
          <table className="players-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Joueur</th>
                <th>Rang</th>
                <th>LP</th>
                <th>Maîtrise</th>
                <th>Parties</th>
              </tr>
            </thead>
            <tbody>
              {topPlayers.map((p, i) => (
                <tr key={i}>
                  <td className="player-rank">#{i + 1}</td>
                  <td className="player-name">{p.summonerName || 'Inconnu'}</td>
                  <td>{p.rank || '—'}</td>
                  <td><span className="lp-badge">{p.lp} LP</span></td>
                  <td><span className="mastery-badge">
                    {p.masteryPoints ? `${(p.masteryPoints / 1000).toFixed(0)}k` : '—'}
                  </span></td>
                  <td>{p.matchesAnalyzed}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Section>
      </div>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div className="section">
      <h3 className="section-title">{title}</h3>
      {children}
    </div>
  )
}

function Tag({ children, gold }) {
  return <span className={`tag ${gold ? 'tag-gold' : ''}`}>{children}</span>
}

function SpellCard({ id, name }) {
  return (
    <div className="spell-card">
      <img className="spell-img" src={spellIcon(id)} alt={name}
        onError={e => { e.target.style.display = 'none' }} />
      <span className="spell-name">{name}</span>
    </div>
  )
}

function RuneCard({ label, name, rate }) {
  return (
    <div className="rune-card">
      <span className="rune-label">{label}</span>
      <span className="rune-name">{name}</span>
      <span className="rune-rate">{rate}%</span>
    </div>
  )
}

function KdaStat({ label, value, color, large }) {
  return (
    <div className="kda-stat">
      <span className="kda-value" style={{ color, fontSize: large ? '1.8rem' : '1.4rem' }}>{value}</span>
      <span className="kda-label">{label}</span>
    </div>
  )
}
