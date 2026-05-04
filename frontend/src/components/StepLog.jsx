import React from 'react'

const STEP_META = {
  classify:    { label: '01 CLASSIFY',    icon: '◈' },
  obligations: { label: '02 OBLIGATIONS', icon: '◉' },
  evidence:    { label: '03 EVIDENCE',    icon: '◎' },
  report:      { label: '04 REPORT',      icon: '◆' },
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  step: (done) => ({
    background: done ? 'var(--bg3)' : 'var(--bg2)',
    border: `1px solid ${done ? 'var(--border2)' : 'var(--border)'}`,
    borderRadius: '6px',
    overflow: 'hidden',
    transition: 'all 0.3s ease',
  }),
  header: (done) => ({
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '10px 14px',
    fontFamily: 'var(--mono)',
    fontSize: '11px',
    letterSpacing: '0.1em',
    color: done ? 'var(--accent)' : 'var(--text3)',
    fontWeight: 500,
  }),
  dot: (done, active) => ({
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    background: done ? 'var(--green)' : active ? 'var(--accent)' : 'var(--text3)',
    boxShadow: active && !done ? '0 0 8px var(--accent)' : 'none',
    animation: active && !done ? 'pulse 1s infinite' : 'none',
    flexShrink: 0,
  }),
  messages: {
    padding: '0 14px 10px 30px',
    display: 'flex',
    flexDirection: 'column',
    gap: '3px',
  },
  msg: {
    fontFamily: 'var(--mono)',
    fontSize: '11px',
    color: 'var(--text2)',
  },
}

export function StepLog({ steps, running }) {
  const activeStep = steps.findLast(s => !s.done)?.step

  return (
    <div style={styles.container}>
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
      {steps.map((s) => {
        const meta = STEP_META[s.step] || { label: s.step.toUpperCase(), icon: '○' }
        const isActive = s.step === activeStep && !s.done
        return (
          <div key={s.step} style={styles.step(s.done)}>
            <div style={styles.header(s.done)}>
              <span style={styles.dot(s.done, isActive)} />
              <span style={{ color: s.done ? 'var(--green)' : isActive ? 'var(--accent)' : 'var(--text3)' }}>
                {meta.label}
              </span>
              {s.done && <span style={{ marginLeft: 'auto', color: 'var(--green)' }}>✓</span>}
              {isActive && <span style={{ marginLeft: 'auto', color: 'var(--accent)' }}>…</span>}
            </div>
            {(s.messages?.length > 0) && (
              <div style={styles.messages}>
                {s.messages.map((m, i) => (
                  <div key={i} style={styles.msg}>› {m}</div>
                ))}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
