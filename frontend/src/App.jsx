import { useCallback, useEffect, useRef, useState } from 'react'
import { BUDGET_MS, LANES, LANE_ORDER, getHealth, streamSSE } from './api'
import { useSpeech } from './useSpeech'
import LaneCard from './components/LaneCard'
import ScalingBench from './components/ScalingBench'
import WhyCLM from './components/WhyCLM'

const PRESETS = [
  'Hi, I need to see a doctor sometime next week for a follow-up.',
  'Actually, can I move my Thursday appointment to Monday instead?',
  'I was charged twice for my last visit and nobody has called me back!',
  'Do you take Blue Cross PPO?',
  'My dad just collapsed and he is not responding.',
  "I'd like to refill my, um…",
]
const GREETING = { role: 'agent', text: 'Thanks for calling Maple Street Clinic, how can I help you today?', lane: null }

export default function App() {
  const [health, setHealth] = useState(null)
  const [healthErr, setHealthErr] = useState(null)
  const [transcript, setTranscript] = useState([GREETING])
  const [results, setResults] = useState({})
  const [pending, setPending] = useState({})
  const [samples, setSamples] = useState({ llm: [], jev: [], clm: [] })
  const [wins, setWins] = useState({ llm: 0, jev: 0, clm: 0 })
  const [nTools, setNTools] = useState(8)
  const [driving, setDriving] = useState('clm')
  const [text, setText] = useState('')
  const [elapsed, setElapsed] = useState(0)
  const [ranks, setRanks] = useState({})
  const t0 = useRef(0)
  const busy = Object.values(pending).some(Boolean)

  const refreshHealth = useCallback(() => {
    getHealth().then((h) => { setHealth(h); setHealthErr(null) }).catch((e) => setHealthErr(String(e)))
  }, [])
  useEffect(refreshHealth, [refreshHealth])

  useEffect(() => {
    if (!busy) return
    let raf
    const tick = () => { setElapsed(performance.now() - t0.current); raf = requestAnimationFrame(tick) }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [busy])

  const speech = useSpeech((utterance) => sendTurn(utterance))

  async function sendTurn(utterance) {
    if (!utterance.trim() || busy) return
    const next = [...transcript, { role: 'caller', text: utterance.trim() }]
    setTranscript(next)
    setText('')
    setResults({})
    setRanks({})
    setPending({ llm: true, jev: true, clm: true })
    t0.current = performance.now()
    let order = 0
    let spoke = false
    const got = {}
    try {
      await streamSSE('/api/turn', { transcript: next.map(({ role, text }) => ({ role, text })), n_tools: nTools }, (ev) => {
        if (ev.done) return
        got[ev.lane] = ev
        setResults((r) => ({ ...r, [ev.lane]: ev }))
        setPending((p) => ({ ...p, [ev.lane]: false }))
        if (!ev.ok) return
        order += 1
        const rank = order
        setRanks((r) => ({ ...r, [ev.lane]: rank }))
        if (rank === 1) setWins((w) => ({ ...w, [ev.lane]: w[ev.lane] + 1 }))
        setSamples((s) => ({ ...s, [ev.lane]: [...s[ev.lane], ev.latency_ms] }))
        if (ev.lane === driving && !spoke) {
          spoke = true
          setTranscript((t) => [...t, { role: 'agent', text: ev.reply, lane: ev.lane, ms: ev.latency_ms }])
          speech.speak(ev.reply)
        }
      })
    } catch (e) {
      setResults({ llm: { ok: false, error: String(e) }, jev: { ok: false, error: String(e) }, clm: { ok: false, error: String(e) } })
    } finally {
      setPending({})
      // driving lane failed: fall back to the fastest successful lane so the call continues
      if (!spoke) {
        const ok = Object.values(got).filter((r) => r.ok).sort((a, b) => a.latency_ms - b.latency_ms)[0]
        if (ok) {
          setTranscript((t) => [...t, { role: 'agent', text: ok.reply, lane: ok.lane, ms: ok.latency_ms }])
          speech.speak(ok.reply)
        }
      }
    }
  }

  const session = sessionKpis(samples, wins)

  return (
    <div className="page">
      <header className="hero">
        <div className="eyebrow">Live demo · voice agent decisions</div>
        <h1>Voice agents need answers in <span className="accent">milliseconds</span>, not seconds.</h1>
        <p className="lede">
          Each caller turn goes live to three models at once: a normal generative LLM, TypeSafe's <b>Jev</b>, and the
          open <b>Contrastive Language Model (CLM-8B)</b>. They all make the same four decisions. Every number below
          is a real, measured round trip.
        </p>
        <div className="status">
          {healthErr && <span className="pill bad">backend unreachable: start uvicorn on :8000</span>}
          {health && LANE_ORDER.map((l) => {
            const h = health[l]
            const ok = h.configured && (l !== 'clm' || (h.reachable && !h.mock))
            return (
              <span key={l} className={`pill ${ok ? 'good' : 'bad'}`} style={{ '--c': LANES[l].color }}>
                {LANES[l].name}: {!h.configured ? 'not configured' : l === 'clm' && !h.reachable ? 'GPU cold/unreachable' : h.mock ? 'MOCK encoder' : 'live'}
              </span>
            )
          })}
          <button className="ghost" onClick={refreshHealth}>re-check</button>
        </div>
      </header>

      <section className="card call">
        <div className="call-grid">
          <div className="convo">
            <div className="convo-head">
              <h2>The call</h2>
              <button className="ghost" onClick={() => { setTranscript([GREETING]); setResults({}); setRanks({}) }} disabled={busy}>new call</button>
            </div>
            <div className="bubbles">
              {transcript.map((t, i) => (
                <div key={i} className={`bubble ${t.role}`}>
                  {t.lane && <span className="by" style={{ color: LANES[t.lane].color }}>{LANES[t.lane].name} · {Math.round(t.ms)} ms</span>}
                  {t.text}
                </div>
              ))}
              {speech.interim && <div className="bubble caller interim">{speech.interim}…</div>}
            </div>
            <form className="composer" onSubmit={(e) => { e.preventDefault(); sendTurn(text) }}>
              <button type="button" className={`mic ${speech.listening ? 'on' : ''}`} disabled={!speech.supported || busy}
                onClick={speech.listening ? speech.stop : speech.listen} title={speech.supported ? 'Speak as the caller' : 'Use Chrome or Edge for speech input'}>
                {speech.listening ? '■' : '🎙'}
              </button>
              <input value={text} onChange={(e) => setText(e.target.value)} placeholder={speech.supported ? 'Speak, or type what the caller says…' : 'Type what the caller says…'} disabled={busy} />
              <button className="primary" disabled={busy || !text.trim()}>Send</button>
            </form>
            <div className="presets">
              {PRESETS.map((p) => <button key={p} className="chip" disabled={busy} onClick={() => sendTurn(p)}>{p}</button>)}
            </div>
            <div className="tools-ctl">
              <label>Tools available to the agent: <b>{nTools}</b></label>
              <input type="range" min={8} max={250} step={1} value={nTools} onChange={(e) => setNTools(+e.target.value)} disabled={busy} />
              <span className="muted small">8 clinic tools, plus up to 242 other hospital tools (Jev's cap is 255 options)</span>
            </div>
          </div>

          <div className="lanes">
            {LANE_ORDER.map((l) => (
              <LaneCard key={l} lane={l} health={health?.[l]} result={results[l]} pending={!!pending[l]} elapsed={elapsed}
                rank={ranks[l]} samples={samples[l]} driving={driving === l} onDrive={() => setDriving(l)} />
            ))}
          </div>
        </div>
      </section>

      <ScalingBench />
      <WhyCLM session={session} />

      <footer className="muted small">
        CLM: Kwok et al., “Contrastive Language Models: A System One Model for Fast and Generalizable Decision-Making” (2026) ·
        github.com/Contrastive-LM/CLM · Jev: docs.typesafe.ai
      </footer>
    </div>
  )
}

function median(xs) {
  if (!xs.length) return null
  const s = [...xs].sort((a, b) => a - b)
  return s[Math.floor(s.length / 2)]
}

function sessionKpis(samples, wins) {
  const m = { llm: median(samples.llm), jev: median(samples.jev), clm: median(samples.clm) }
  if (!m.clm) return null
  const out = [{ value: `${Math.round(m.clm)} ms`, label: 'CLM median decision latency this session' }]
  if (m.jev) out.push({ value: `${(m.jev / m.clm).toFixed(1)}×`, label: 'CLM vs Jev (session medians)' })
  if (m.llm) out.push({ value: `${(m.llm / m.clm).toFixed(1)}×`, label: 'CLM vs normal LLM (session medians)' })
  const inB = samples.clm.filter((x) => x <= BUDGET_MS).length
  out.push({ value: `${inB}/${samples.clm.length}`, label: 'CLM turns inside the 300 ms budget' })
  out.push({ value: `${wins.clm}`, label: 'turns where CLM answered first' })
  return out
}
