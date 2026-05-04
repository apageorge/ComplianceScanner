import React, { useState } from 'react'
import { usePipeline } from './hooks/usePipeline'
import { StepLog } from './components/StepLog'
import { ComplianceReport } from './components/ComplianceReport'

const TEST_REPOS = [
  { label: '🟢 High scorer', url: 'https://github.com/microsoft/responsible-ai-toolbox' },
  { label: '🔴 Low scorer',  url: '' },
]

export default function App() {
  const [url, setUrl] = useState('')
  const { steps, report, running, error, analyse } = usePipeline()

  const handleSubmit = () => {
    const trimmed = url.trim()
    if (!trimmed || running) return
    analyse(trimmed)
  }

  const hasActivity = steps.length > 0 || report || error

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>

      {/* Header */}
      <header style={{
        borderBottom: '1px solid var(--border)',
        padding: '16px 24px',
        display: 'flex',
        alignItems: 'center',
        gap: '16px',
        position: 'sticky',
        top: 0,
        background: 'var(--bg)',
        zIndex: 10,
      }}>
        <div>
          <div style={{ fontFamily: 'var(--mono)', fontSize: '10px', color: 'var(--text3)', letterSpacing: '0.12em' }}>
            EU AI ACT
          </div>
          <div style={{ fontSize: '16px', fontWeight: 800, letterSpacing: '-0.02em' }}>
            COMPLIANCE SCANNER
          </div>
        </div>
        <div style={{
          marginLeft: 'auto',
          fontFamily: 'var(--mono)',
          fontSize: '10px',
          color: 'var(--text3)',
          border: '1px solid var(--border)',
          padding: '3px 8px',
          borderRadius: '4px',
        }}>
          v0.1 · agentic
        </div>
      </header>

      <main style={{ maxWidth: '860px', margin: '0 auto', padding: '32px 24px' }}>

        {/* Input section */}
        <div style={{ marginBottom: '32px' }}>
          <div style={{
            fontFamily: 'var(--mono)',
            fontSize: '10px',
            color: 'var(--text3)',
            letterSpacing: '0.1em',
            marginBottom: '10px',
          }}>
            GITHUB REPOSITORY URL
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <input
              type="text"
              value={url}
              onChange={e => setUrl(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSubmit()}
              placeholder="https://github.com/owner/repo"
              disabled={running}
              style={{
                flex: 1,
                background: 'var(--bg2)',
                border: '1px solid var(--border2)',
                borderRadius: '6px',
                padding: '10px 14px',
                fontFamily: 'var(--mono)',
                fontSize: '13px',
                color: 'var(--text)',
                outline: 'none',
                transition: 'border-color 0.2s',
              }}
              onFocus={e => e.target.style.borderColor = 'var(--accent)'}
              onBlur={e => e.target.style.borderColor = 'var(--border2)'}
            />
            <button
              onClick={handleSubmit}
              disabled={running || !url.trim()}
              style={{
                background: running ? 'var(--bg3)' : 'var(--accent)',
                color: running ? 'var(--text3)' : 'white',
                border: 'none',
                borderRadius: '6px',
                padding: '10px 20px',
                fontFamily: 'var(--mono)',
                fontSize: '12px',
                fontWeight: 600,
                letterSpacing: '0.08em',
                cursor: running ? 'not-allowed' : 'pointer',
                transition: 'all 0.2s',
                whiteSpace: 'nowrap',
              }}
            >
              {running ? 'SCANNING…' : 'SCAN →'}
            </button>
          </div>

          {/* Quick-fill test repos */}
          <div style={{ display: 'flex', gap: '8px', marginTop: '10px', flexWrap: 'wrap' }}>
            {TEST_REPOS.map(r => (
              <button
                key={r.url}
                onClick={() => setUrl(r.url)}
                disabled={running}
                style={{
                  background: 'none',
                  border: '1px solid var(--border)',
                  borderRadius: '4px',
                  padding: '4px 10px',
                  fontFamily: 'var(--mono)',
                  fontSize: '10px',
                  color: 'var(--text3)',
                  cursor: 'pointer',
                  transition: 'border-color 0.2s',
                }}
                onMouseOver={e => e.target.style.borderColor = 'var(--border2)'}
                onMouseOut={e => e.target.style.borderColor = 'var(--border)'}
              >
                {r.label}
              </button>
            ))}
            <span style={{ fontFamily: 'var(--mono)', fontSize: '10px', color: 'var(--text3)', alignSelf: 'center' }}>
              ← test repos
            </span>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div style={{
            background: 'rgba(239,68,68,0.08)',
            border: '1px solid var(--red)',
            borderRadius: '6px',
            padding: '12px 16px',
            fontFamily: 'var(--mono)',
            fontSize: '12px',
            color: 'var(--red)',
            marginBottom: '24px',
          }}>
            ERROR › {error}
          </div>
        )}

        {/* Two-column layout when active */}
        {hasActivity && (
          <div style={{
            display: 'grid',
            gridTemplateColumns: report ? '280px 1fr' : '1fr',
            gap: '20px',
            alignItems: 'start',
          }}>
            {/* Agent log */}
            <div>
              <div style={{
                fontFamily: 'var(--mono)', fontSize: '10px',
                color: 'var(--text3)', letterSpacing: '0.1em', marginBottom: '10px',
              }}>
                AGENT LOG
              </div>
              <StepLog steps={steps} running={running} />
            </div>

            {/* Report */}
            {report && (
              <div>
                <div style={{
                  fontFamily: 'var(--mono)', fontSize: '10px',
                  color: 'var(--text3)', letterSpacing: '0.1em', marginBottom: '10px',
                }}>
                  COMPLIANCE REPORT
                </div>
                <ComplianceReport report={report} />
              </div>
            )}
          </div>
        )}

        {/* Empty state */}
        {!hasActivity && (
          <div style={{
            textAlign: 'center',
            padding: '60px 20px',
            color: 'var(--text3)',
            fontFamily: 'var(--mono)',
            fontSize: '12px',
            lineHeight: 2,
          }}>
            <div style={{ fontSize: '32px', marginBottom: '12px', opacity: 0.3 }}>◈</div>
            Enter a GitHub URL to begin analysis<br />
            The agent will classify the system, select obligations,<br />
            gather evidence, and produce a confidence-aware report.
          </div>
        )}
      </main>
    </div>
  )
}
