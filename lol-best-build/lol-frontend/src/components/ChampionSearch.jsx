import { useState, useEffect, useRef } from 'react'
import './ChampionSearch.css'

const REGIONS = [
  { value: 'euw1', label: 'EUW' },
  { value: 'na1',  label: 'NA' },
  { value: 'kr',   label: 'KR' },
  { value: 'eun1', label: 'EUNE' },
  { value: 'br1',  label: 'BR' },
  { value: 'jp1',  label: 'JP' },
]

const QUEUES = [
  { value: 'ranked_solo', label: 'Solo/Duo' },
  { value: 'ranked_flex', label: 'Flex' },
]

export default function ChampionSearch({ onSearch, loading }) {
  const [input, setInput] = useState('')
  const [region, setRegion] = useState('euw1')
  const [queue, setQueue] = useState('ranked_solo')
  const [champions, setChampions] = useState([])
  const [suggestions, setSuggestions] = useState([])
  const [focused, setFocused] = useState(false)
  const inputRef = useRef(null)

  useEffect(() => {
    fetch('/api/champions')
      .then(r => r.json())
      .then(d => setChampions(d.champions || []))
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!input.trim() || input.length < 2) { setSuggestions([]); return }
    const q = input.toLowerCase()
    setSuggestions(
      champions
        .filter(c => c.name.toLowerCase().startsWith(q) || c.id.toLowerCase().startsWith(q))
        .slice(0, 8)
    )
  }, [input, champions])

  const handleSubmit = (name = input) => {
    if (!name.trim() || loading) return
    setSuggestions([])
    onSearch({ champion: name.trim(), region, queue })
  }

  const handleKey = (e) => {
    if (e.key === 'Enter') handleSubmit()
  }

  return (
    <div className="search-card">
      <div className="search-row">
        {/* Champion autocomplete */}
        <div className="search-input-wrap">
          <input
            ref={inputRef}
            className="search-input"
            placeholder="Champion…"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            onFocus={() => setFocused(true)}
            onBlur={() => setTimeout(() => setFocused(false), 150)}
            autoComplete="off"
            disabled={loading}
          />
          {focused && suggestions.length > 0 && (
            <ul className="suggestions">
              {suggestions.map(c => (
                <li
                  key={c.id}
                  className="suggestion-item"
                  onMouseDown={() => { setInput(c.name); handleSubmit(c.name) }}
                >
                  <img
                    className="suggestion-icon"
                    src={`https://ddragon.leagueoflegends.com/cdn/14.24.1/img/champion/${c.id}.png`}
                    alt={c.name}
                  />
                  {c.name}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Region */}
        <select
          className="search-select"
          value={region}
          onChange={e => setRegion(e.target.value)}
          disabled={loading}
        >
          {REGIONS.map(r => (
            <option key={r.value} value={r.value}>{r.label}</option>
          ))}
        </select>

        {/* Queue */}
        <select
          className="search-select"
          value={queue}
          onChange={e => setQueue(e.target.value)}
          disabled={loading}
        >
          {QUEUES.map(q => (
            <option key={q.value} value={q.value}>{q.label}</option>
          ))}
        </select>

        <button
          className="search-btn"
          onClick={() => handleSubmit()}
          disabled={loading || !input.trim()}
        >
          {loading ? '…' : 'Analyser'}
        </button>
      </div>
    </div>
  )
}
