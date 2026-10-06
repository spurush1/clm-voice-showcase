import { useCallback, useEffect, useRef, useState } from 'react'

// Browser speech in/out: Web Speech API recognition (Chrome/Edge) + speechSynthesis.
export function useSpeech(onFinal) {
  const recRef = useRef(null)
  const cbRef = useRef(onFinal)
  const [listening, setListening] = useState(false)
  const [interim, setInterim] = useState('')
  const SR = typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition)

  useEffect(() => { cbRef.current = onFinal }, [onFinal])

  useEffect(() => {
    if (!SR) return
    const rec = new SR()
    rec.lang = 'en-US'
    rec.interimResults = true
    rec.continuous = false
    rec.onresult = (e) => {
      let text = ''
      let final = false
      for (const r of e.results) { text += r[0].transcript; final = final || r.isFinal }
      setInterim(final ? '' : text)
      if (final && text.trim()) cbRef.current(text.trim())
    }
    rec.onend = () => { setListening(false); setInterim('') }
    rec.onerror = () => setListening(false)
    recRef.current = rec
    return () => rec.abort()
  }, [SR])

  const listen = useCallback(() => {
    if (!recRef.current) return
    window.speechSynthesis?.cancel()
    try { recRef.current.start(); setListening(true) } catch { /* already started */ }
  }, [])
  const stop = useCallback(() => recRef.current?.stop(), [])

  const speak = useCallback((text) => {
    if (!window.speechSynthesis) return
    window.speechSynthesis.cancel()
    const u = new SpeechSynthesisUtterance(text)
    u.rate = 1.05
    window.speechSynthesis.speak(u)
  }, [])

  return { supported: !!SR, listening, interim, listen, stop, speak }
}
