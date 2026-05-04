import React, { useState } from 'react'

const TIER_COLORS = {
  unacceptable: 'var(--red)',
  high:         'var(--orange)',
  limited:      'var(--yellow)',
  minimal:      'var(--green)',
}

const VERDICT_COLORS = {
  compliant:       'var(--green)',
  partial:         'var(--yellow)',
  'non-compliant': 'var(--red)',
  'not-checkable': 'var(--text3)',
}

const VERDICT_LABELS = {
  compliant:       'COMPLIANT',
  partial:         'PARTIAL',
  'non-compliant': 'NON-COMPLIANT',
  'not-checkable': 'NOT CHECKABLE',
}

function ScoreBar({ value, ceiling, color }) {
  return (
    <div style={{ position: 'relative', height: '6px', background: 'var(--bg)', borderRadius: '3px', overflow: 'hidden' }}>
      {/* ceiling indicator */}
      <div style={{
        position: 'absolute', left: 0, top: 0, bottom: 0,
        width: `${ceiling * 100}%`,
        background: 'var(--border2)',
        borderRadius: '3px',
      }} />
      {/* actual score */}
      <div style={{
        position: 'absolute', left: 0, top: 0, bottom: 0,
        width: `${value * 100}%`,
        background: color,
        borderRadius: '3px',
        transition: 'width 0.8s cubic-bezier(0.4,0,0.2,1)',
      }} />
    </div>
  )
}

function FindingCard({ finding }) {
  const [open, setOpen] = useState(false)
  const color = VERDICT_COLORS[finding.verdict] || 'var(--text2)'

  return (
    <div style={{
      border: `1px solid var(--border)`,
      borderLeft: `3px solid ${color}`,
      borderRadius: '6px',
      overflow: 'hidden',
      background: 'var(--bg2)',
    }}>
      {/* Header */}
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%', textAlign: 'left', background: 'none', border: 'none',
          cursor: 'pointer', padding: '14px 16px', display: 'flex',
          alignItems: 'center', gap: '12px',
        }}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
            <span style={{ fontFamily: 'var(--mono)', fontSize: '10px', color: 'var(--text3)' }}>
              {finding.article}
            </span>
            <span style={{
              fontFamily: 'var(--mono)', fontSize: '10px', fontWeight: 600,
              color, padding: '1px 6px', border: `1px solid ${color}`,
              borderRadius: '3px', opacity: 0.9,
            }}>
              {VERDICT_LABELS[finding.verdict] || finding.verdict}
            </span>
          </div>
          <div style={{ fontWeight: 600, fontSize: '14px', color: 'var(--text)', marginBottom: '8px' }}>
            {finding.tenet}
          </div>
          <ScoreBar value={finding.score} ceiling={finding.confidence_ceiling} color={color} />
          <div style={{
            display: 'flex', justifyContent: 'space-between', marginTop: '4px',
            fontFamily: 'var(--mono)', fontSize: '10px', color: 'var(--text3)',
          }}>
            <span>score {Math.round(finding.score * 100)}%</span>
            <span>ceiling {Math.round(finding.confidence_ceiling * 100)}% · confidence {Math.round(finding.confidence * 100)}%</span>
          </div>
        </div>
        <span style={{ color: 'var(--text3)', fontSize: '12px', flexShrink: 0 }}>
          {open ? '▲' : '▼'}
        </span>
      </button>

      {/* Expanded detail */}
      {open && (
        <div style={{ padding: '0 16px 16px', borderTop: '1px solid var(--border)' }}>
          <p style={{ color: 'var(--text2)', fontSize: '13px', lineHeight: 1.7, marginTop: '12px' }}>
            {finding.summary}
          </p>

          {finding.evidence_highlights?.length > 0 && (
            <div style={{ marginTop: '12px' }}>
              <div style={{ fontFamily: 'var(--mono)', fontSize: '10px', color: 'var(--text3)', marginBottom: '6px', letterSpacing: '0.08em' }}>
                EVIDENCE FOUND
              </div>
              {finding.evidence_highlights.map((e, i) => (
                <div key={i} style={{
                  fontFamily: 'var(--mono)', fontSize: '11px', color: 'var(--green)',
                  padding: '3px 0', borderBottom: '1px solid var(--border)',
                }}>
                  ✓ {e}
                </div>
              ))}
            </div>
          )}

          {finding.not_checkable_notes?.length > 0 && (
            <div style={{ marginTop: '12px' }}>
              <div style={{ fontFamily: 'var(--mono)', fontSize: '10px', color: 'var(--text3)', marginBottom: '6px', letterSpacing: '0.08em' }}>
                REQUIRES EXTERNAL VERIFICATION
              </div>
              {finding.not_checkable_notes.map((n, i) => (
                <div key={i} style={{
                  fontFamily: 'var(--mono)', fontSize: '11px', color: 'var(--text3)',
                  padding: '3px 0', borderBottom: '1px solid var(--border)',
                }}>
                  ○ {n}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export function ComplianceReport({ report }) {
  const tierColor = TIER_COLORS[report.risk_tier] || 'var(--text2)'
  const scorePercent = Math.round(report.overall_score * 100)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* Overall header */}
      <div style={{
        background: 'var(--bg2)', border: '1px solid var(--border2)',
        borderRadius: '8px', padding: '20px',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <div style={{ fontFamily: 'var(--mono)', fontSize: '10px', color: 'var(--text3)', letterSpacing: '0.1em', marginBottom: '4px' }}>
              REPOSITORY
            </div>
            <div style={{ fontSize: '18px', fontWeight: 700 }}>{report.repo_name}</div>
            <a href={report.repo_url} target="_blank" rel="noreferrer"
              style={{ fontFamily: 'var(--mono)', fontSize: '11px', color: 'var(--text3)' }}>
              {report.repo_url}
            </a>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{
              fontFamily: 'var(--mono)', fontSize: '10px', letterSpacing: '0.1em',
              color: tierColor, border: `1px solid ${tierColor}`,
              padding: '3px 10px', borderRadius: '4px', marginBottom: '8px', display: 'inline-block',
            }}>
              {report.risk_tier.toUpperCase()} RISK
            </div>
            <div style={{ fontSize: '36px', fontWeight: 800, color: tierColor, lineHeight: 1 }}>
              {scorePercent}<span style={{ fontSize: '16px', fontWeight: 400, color: 'var(--text3)' }}>%</span>
            </div>
            <div style={{ fontFamily: 'var(--mono)', fontSize: '10px', color: 'var(--text3)' }}>
              overall · {Math.round(report.overall_confidence * 100)}% confidence
            </div>
          </div>
        </div>

        <div style={{
          marginTop: '14px', padding: '10px 14px',
          background: 'var(--bg3)', borderRadius: '5px',
          fontFamily: 'var(--mono)', fontSize: '11px', color: 'var(--text2)', lineHeight: 1.6,
        }}>
          <span style={{ color: 'var(--text3)' }}>CLASSIFICATION › </span>
          {report.risk_tier_reasoning}
        </div>
      </div>

      {/* Findings */}
      <div>
        <div style={{
          fontFamily: 'var(--mono)', fontSize: '10px', letterSpacing: '0.1em',
          color: 'var(--text3)', marginBottom: '10px',
        }}>
          OBLIGATION FINDINGS — {report.findings?.length || 0} ASSESSED
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {report.findings?.map(f => (
            <FindingCard key={f.obligation_id} finding={f} />
          ))}
        </div>
      </div>

      {/* Legend */}
      <div style={{
        fontFamily: 'var(--mono)', fontSize: '10px', color: 'var(--text3)',
        padding: '10px 14px', background: 'var(--bg2)', borderRadius: '6px',
        border: '1px solid var(--border)', lineHeight: 1.8,
      }}>
        <div style={{ marginBottom: '4px', letterSpacing: '0.08em' }}>NOTE ON CONFIDENCE CEILING</div>
        The grey bar shows the maximum achievable score from code inspection alone.
        Obligations requiring legal documentation, audits, or user studies cannot be
        fully verified from source code and are capped accordingly. External verification
        is always required for regulatory compliance.
      </div>
    </div>
  )
}
