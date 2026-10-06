// POST JSON and consume a Server-Sent-Events response, one parsed event at a time.
export async function streamSSE(url, body, onEvent, signal) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
  if (!res.ok) throw new Error(`${url} → HTTP ${res.status}: ${await res.text()}`)
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    let i
    while ((i = buf.indexOf('\n\n')) >= 0) {
      const chunk = buf.slice(0, i)
      buf = buf.slice(i + 2)
      if (chunk.startsWith('data: ')) onEvent(JSON.parse(chunk.slice(6)))
    }
  }
}

export async function getHealth() {
  const r = await fetch('/api/health')
  if (!r.ok) throw new Error(`health → HTTP ${r.status}`)
  return r.json()
}

export const LANES = {
  llm: { name: 'Normal LLM', tag: 'Generative · JSON output', color: '#f59e0b' },
  jev: { name: 'Jev', tag: 'TypeSafe System One', color: '#a78bfa' },
  clm: { name: 'CLM-8B', tag: 'Contrastive LM · cached actions', color: '#34d399' },
}
export const LANE_ORDER = ['llm', 'jev', 'clm']
export const BUDGET_MS = 300
export const FRUSTRATION = ['Calm', 'Impatient', 'Frustrated', 'Angry']
