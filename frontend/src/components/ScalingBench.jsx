import { useState } from 'react'
import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { BUDGET_MS, LANES, LANE_ORDER, streamSSE } from '../api'

const SIZES = [8, 32, 64, 128, 250]

export default function ScalingBench() {
  const [rows, setRows] = useState([])
  const [errors, setErrors] = useState({})
  const [running, setRunning] = useState(false)
  const [reps, setReps] = useState(3)

  async function run() {
    setRows([]); setErrors({}); setRunning(true)
    try {
      await streamSSE('/api/bench', { sizes: SIZES, reps }, (ev) => {
        if (ev.row) setRows((r) => [...r, ev.row])
        if (ev.errors && Object.keys(ev.errors).length) setErrors((e) => ({ ...e, ...ev.errors }))
      })
    } catch (e) {
      setErrors({ bench: String(e) })
    } finally {
      setRunning(false)
    }
  }

  const last = rows[rows.length - 1]
  const speedup = (a) => (last?.[a] && last?.clm ? (last[a] / last.clm).toFixed(1) : null)

  return (
    <section className="card">
      <div className="section-head">
        <div>
          <h2>What happens as the agent gets more tools?</h2>
          <p className="muted">
            Real requests with the same caller line, routed across {SIZES.join(' → ')} tools. CLM embeds each tool once and
            caches it, so each turn only encodes the conversation. Median of {reps} runs per point.
          </p>
        </div>
        <div className="bench-ctl">
          <label>runs <select value={reps} onChange={(e) => setReps(+e.target.value)} disabled={running}>
            {[1, 3, 5].map((n) => <option key={n}>{n}</option>)}
          </select></label>
          <button className="primary" onClick={run} disabled={running}>{running ? 'Running…' : 'Run live benchmark'}</button>
        </div>
      </div>

      <div className="chart">
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={rows} margin={{ top: 10, right: 20, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="var(--grid)" strokeDasharray="3 3" />
            <XAxis dataKey="n_tools" stroke="var(--muted)" label={{ value: 'tools in the Choice', position: 'insideBottom', offset: -2, fill: 'var(--muted)' }} />
            <YAxis stroke="var(--muted)" unit=" ms" width={80} />
            <Tooltip contentStyle={{ background: 'var(--panel)', border: '1px solid var(--line)' }} formatter={(v) => (v == null ? '—' : `${Math.round(v)} ms`)} />
            <Legend />
            <ReferenceLine y={BUDGET_MS} stroke="#ef4444" strokeDasharray="4 4" label={{ value: '300 ms voice budget', fill: '#ef4444', position: 'insideTopRight' }} />
            {LANE_ORDER.map((l) => (
              <Line key={l} type="monotone" dataKey={l} name={LANES[l].name} stroke={LANES[l].color} strokeWidth={3} dot={{ r: 4 }} connectNulls />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {last && (
        <div className="kpis">
          {speedup('jev') && <div className="kpi"><b>{speedup('jev')}×</b><span>CLM faster than Jev at {last.n_tools} tools</span></div>}
          {speedup('llm') && <div className="kpi"><b>{speedup('llm')}×</b><span>CLM faster than the LLM at {last.n_tools} tools</span></div>}
        </div>
      )}
      {Object.entries(errors).map(([k, v]) => <div key={k} className="err">{k}: {v}</div>)}
    </section>
  )
}
