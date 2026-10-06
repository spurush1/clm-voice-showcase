const ROWS = [
  ['Output', 'Free text / JSON to parse', 'Typed answers + probabilities', 'Typed answers + probabilities'],
  ['Cost per turn as tools grow', 'Grows (all tools in the prompt)', 'Grows (options scored per request)', 'Flat: tool embeddings cached once'],
  ['Calibrated confidence', 'No', 'Yes', 'Yes'],
  ['Self-host / data stays in VPC', 'Depends on vendor', 'Hosted API', 'Yes: open weights (Apache-2.0)'],
  ['Fine-tune on your call logs', 'Expensive', 'No (shared weights)', 'Yes: train a 20M-param head in about an hour'],
  ['Long-horizon verifier', 'Slow', 'Below the random-pick (Pass@1) baseline (blog)', 'SOTA: DeepSWE 81.6%, Terminal-Bench 2.1 87.6%'],
  ['Migration from Jev', '—', '—', 'Same /v1/systemone request format'],
]

export default function WhyCLM({ session }) {
  return (
    <section className="card">
      <h2>Why go with CLM for voice</h2>
      <p className="muted">
        A voice agent makes several small decisions on every turn: has the caller finished speaking, which tool to call,
        how they feel, whether a human should take over. Those decisions sit between speech recognition and speech output,
        so their latency is heard directly as silence.
      </p>

      {session && (
        <div className="kpis">
          {session.map((k) => <div className="kpi" key={k.label}><b>{k.value}</b><span>{k.label}</span></div>)}
        </div>
      )}

      <div className="table-wrap">
        <table>
          <thead><tr><th /><th>Normal LLM</th><th>Jev</th><th className="win">CLM-8B</th></tr></thead>
          <tbody>
            {ROWS.map(([k, ...v]) => (
              <tr key={k}><td>{k}</td><td>{v[0]}</td><td>{v[1]}</td><td className="win">{v[2]}</td></tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="arch">
        <svg viewBox="0 0 760 170" role="img" aria-label="CLM action caching">
          <defs><marker id="ar" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="currentColor" /></marker></defs>
          <g className="box"><rect x="10" y="20" width="170" height="50" rx="10" /><text x="95" y="50">caller turn (state)</text></g>
          <g className="box hot"><rect x="230" y="20" width="160" height="50" rx="10" /><text x="310" y="42">state encoder</text><text x="310" y="60" className="s">1 pass / turn</text></g>
          <g className="box"><rect x="10" y="100" width="170" height="50" rx="10" /><text x="95" y="130">N tools (actions)</text></g>
          <g className="box cold"><rect x="230" y="100" width="160" height="50" rx="10" /><text x="310" y="122">action encoder</text><text x="310" y="140" className="s">once, then cached</text></g>
          <g className="box"><rect x="450" y="60" width="140" height="50" rx="10" /><text x="520" y="90">cosine scores</text></g>
          <g className="box hot"><rect x="630" y="60" width="120" height="50" rx="10" /><text x="690" y="90">best tool</text></g>
          <g className="edge"><path d="M180,45 H228" /><path d="M180,125 H228" /><path d="M390,45 C420,45 420,80 448,80" /><path d="M390,125 C420,125 420,90 448,90" /><path d="M590,85 H628" /></g>
        </svg>
        <p className="muted small">
          Jev reads the conversation together with every option on each request. CLM encodes the state and the actions
          separately, so tool embeddings are computed once and reused. The blog reports up to 9× lower latency at the same
          accuracy, and 13× at ~1k candidates.
        </p>
      </div>
    </section>
  )
}
