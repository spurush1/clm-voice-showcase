import { BUDGET_MS, FRUSTRATION, LANES } from '../api'

const fmt = (ms) => (ms == null ? '—' : ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(2)} s`)
const pct = (p) => (p == null ? '' : `${Math.round(p * 100)}%`)

function stats(samples) {
  if (!samples.length) return null
  const s = [...samples].sort((a, b) => a - b)
  const q = (f) => s[Math.min(s.length - 1, Math.floor(f * s.length))]
  return { n: s.length, p50: q(0.5), p95: q(0.95), inBudget: s.filter((x) => x <= BUDGET_MS).length }
}

export default function LaneCard({ lane, health, result, pending, elapsed, rank, samples, driving, onDrive }) {
  const meta = LANES[lane]
  const ms = pending ? elapsed : result?.latency_ms
  const scaleMax = Math.max(1500, ms || 0)
  const over = ms != null && ms > BUDGET_MS
  const st = stats(samples)
  const offline = health && !health.configured

  return (
    <div className={`lane ${driving ? 'driving' : ''}`} style={{ '--c': meta.color }}>
      <div className="lane-head">
        <div>
          <div className="lane-name">{meta.name}</div>
          <div className="lane-tag">{meta.tag}{health?.model ? ` · ${health.model}` : ''}</div>
        </div>
        {rank != null && !pending && result?.ok && <div className={`rank r${rank}`}>#{rank}</div>}
      </div>

      <div className={`ms ${over ? 'over' : 'under'} ${pending ? 'ticking' : ''}`}>{fmt(ms)}</div>
      <div className="bar">
        <div className="fill" style={{ width: `${Math.min(100, ((ms || 0) / scaleMax) * 100)}%` }} />
        <div className="budget" style={{ left: `${(BUDGET_MS / scaleMax) * 100}%` }} title="300 ms voice budget" />
      </div>
      <div className="bar-legend">
        <span>{pending ? 'thinking… caller hears silence' : over ? 'dead air: over the 300 ms budget' : ms != null ? 'inside the voice budget' : ''}</span>
        {result?.server_ms != null && <span>server {fmt(result.server_ms)}</span>}
      </div>

      {offline && <div className="err">Not configured. Add the key/URL to backend/.env</div>}
      {result && !result.ok && !offline && <div className="err">{result.error}</div>}

      {result?.ok && (
        <div className="decisions">
          <Row k="Tool" v={<><code>{result.tool}</code> <b>{pct(result.tool_prob)}</b></>} />
          <Row k="Turn ended" v={<Meter p={result.end_of_turn} />} />
          <Row k="Escalate" v={<Meter p={result.escalate} danger />} />
          <Row k="Frustration" v={`${FRUSTRATION[Math.round(result.frustration)] ?? '?'} (${result.frustration.toFixed(2)}/3)`} />
          {result.tool_top3?.length > 1 && (
            <div className="top3">
              {result.tool_top3.map(([t, p]) => <span key={t}>{t} {pct(p)}</span>)}
            </div>
          )}
          <div className="reply">“{result.reply}”</div>
        </div>
      )}

      <div className="lane-foot">
        {st ? (
          <span>p50 {fmt(st.p50)} · p95 {fmt(st.p95)} · {st.inBudget}/{st.n} in budget</span>
        ) : <span>no turns yet</span>}
        <button className={`drive ${driving ? 'on' : ''}`} onClick={onDrive} title="This lane's decision drives the agent's voice">
          {driving ? '🔊 voice' : 'use voice'}
        </button>
      </div>
    </div>
  )
}

function Row({ k, v }) {
  return <div className="row"><span className="k">{k}</span><span className="v">{v}</span></div>
}

function Meter({ p, danger }) {
  return (
    <span className="meter">
      <span className="track"><span className={`dot ${danger && p >= 0.5 ? 'hot' : ''}`} style={{ width: `${p * 100}%` }} /></span>
      <b>{pct(p)}</b>
    </span>
  )
}
