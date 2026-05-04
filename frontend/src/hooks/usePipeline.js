import { useState, useCallback } from 'react'

export function usePipeline() {
  const [steps, setSteps] = useState([])
  const [report, setReport] = useState(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState(null)

  const addStep = (event) => {
    setSteps(prev => {
      // Merge stream events into their parent step
      const existing = prev.findIndex(s => s.step === event.step)
      if (existing >= 0 && event.status === 'stream') {
        const updated = [...prev]
        updated[existing] = {
          ...updated[existing],
          messages: [...(updated[existing].messages || []), event.payload.message],
        }
        return updated
      }
      if (existing >= 0 && event.status === 'done') {
        const updated = [...prev]
        updated[existing] = { ...updated[existing], ...event, done: true }
        return updated
      }
      return [...prev, { ...event, messages: [], done: false }]
    })
  }

  const analyse = useCallback(async (githubUrl) => {
    setSteps([])
    setReport(null)
    setError(null)
    setRunning(true)

    try {
      const API_BASE = import.meta.env.VITE_API_URL || ''
      const res = await fetch(`${API_BASE}/api/analyse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ github_url: githubUrl }),
      })

      if (!res.ok) throw new Error(`Server error: ${res.status}`)

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() // keep incomplete line

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6).trim()
          if (raw === '[DONE]') { setRunning(false); return }

          try {
            const event = JSON.parse(raw)
            if (event.step === 'error') {
              setError(event.payload.message)
              setRunning(false)
              return
            }
            if (event.step === 'report' && event.status === 'done') {
              setReport(event.payload)
            }
            addStep(event)
          } catch {
            // malformed event — skip
          }
        }
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setRunning(false)
    }
  }, [])

  return { steps, report, running, error, analyse }
}
