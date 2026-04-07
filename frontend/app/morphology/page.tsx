'use client'

import React, { useState } from 'react'
import { Sparkles, Loader2, BookOpen, Layers, Activity } from 'lucide-react'
import { useAuth } from '../../components/LoginGuard'
import api, { MorphAnalysis } from '../../services/api'

export default function MorphologyPage() {
  const { token } = useAuth()
  const [word, setWord] = useState('ishlamoqdamasanmi')
  const [text, setText] = useState('')
  const [result, setResult] = useState<MorphAnalysis | null>(null)
  const [textResult, setTextResult] = useState<{ analyses: MorphAnalysis[]; unknowns: string[] } | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [mode, setMode] = useState<'word' | 'text'>('word')

  const analyzeWord = async () => {
    if (!word.trim()) return
    setLoading(true); setError(null)
    try {
      const r = await api.morph.analyze(word.trim())
      setResult(r)
      setTextResult(null)
    } catch (e: any) {
      setError(e?.message || 'Хатолик')
    } finally { setLoading(false) }
  }

  const analyzeText = async () => {
    if (!text.trim()) return
    setLoading(true); setError(null)
    try {
      const r = await api.morph.analyzeText(text.trim())
      setTextResult({ analyses: r.analyses, unknowns: r.unknowns })
      setResult(null)
    } catch (e: any) {
      setError(e?.message || 'Хатолик')
    } finally { setLoading(false) }
  }

  const renderAnalysis = (a: MorphAnalysis) => (
    <div style={{
      background: 'var(--bg-card)',
      border: '1.5px solid var(--border)',
      borderRadius: 14,
      padding: 20,
      marginBottom: 16,
      boxShadow: '0 2px 8px rgba(120, 80, 40, 0.06)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14, flexWrap: 'wrap', gap: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)' }}>{a.word}</span>
          <span style={{
            fontSize: '0.65rem', padding: '3px 10px', borderRadius: 12,
            background: a.pos === 'verb' ? '#FEF3C7' : a.pos === 'noun' ? '#DBEAFE' : '#F3E8FF',
            color: a.pos === 'verb' ? '#D97706' : a.pos === 'noun' ? '#2563EB' : '#9333EA',
            fontWeight: 700, textTransform: 'uppercase'
          }}>{a.pos}</span>
          <span style={{ fontSize: '0.65rem', padding: '3px 8px', borderRadius: 8, background: '#F3F4F6', color: '#6B7280' }}>
            {a.source}
          </span>
        </div>
      </div>

      {/* Stem highlighted */}
      <div style={{ marginBottom: 12 }}>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Стем (asos)</span>
        <div style={{ marginTop: 4, padding: '8px 14px', background: '#FFF7ED', border: '1.5px solid #FB923C', borderRadius: 8, display: 'inline-block', fontSize: '1.1rem', fontWeight: 700, color: '#9A3412' }}>
          {a.stem}
        </div>
      </div>

      {/* Morphemes breakdown */}
      <div style={{ marginBottom: 12 }}>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Морфемалар</span>
        <div style={{ marginTop: 6, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {a.morphemes.map((m, i) => (
            <div key={i} style={{
              padding: '6px 12px',
              background: m.kind === 'stem' ? '#FFF7ED' : m.kind === 'prefix' ? '#F0F9FF' : '#F0FDF4',
              border: `1.5px solid ${m.kind === 'stem' ? '#FB923C' : m.kind === 'prefix' ? '#0EA5E9' : '#22C55E'}`,
              borderRadius: 8,
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2
            }}>
              <span style={{ fontWeight: 700, color: m.kind === 'stem' ? '#9A3412' : m.kind === 'prefix' ? '#075985' : '#166534' }}>
                {m.surface}
              </span>
              {m.gloss && <span style={{ fontSize: '0.6rem', color: '#6B7280' }}>{m.gloss}</span>}
            </div>
          ))}
        </div>
      </div>

      {/* Features */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 14 }}>
        {a.tense && <FeatureBadge label="Замон" value={a.tense} color="#16A34A" />}
        {a.person !== null && <FeatureBadge label="Шахс" value={String(a.person)} color="#2563EB" />}
        {a.number && <FeatureBadge label="Сон" value={a.number} color="#9333EA" />}
        {a.case && <FeatureBadge label="Келишик" value={a.case} color="#EA580C" />}
        {a.mood && <FeatureBadge label="Mayl" value={a.mood} color="#DB2777" />}
        {a.negation && <FeatureBadge label="Инкор" value="ҳа" color="#DC2626" />}
      </div>

      {/* Validation badges (Phase 2.5) */}
      {(a.valid_order !== undefined || (a.order_score !== undefined && a.order_score < 1)) && (
        <div style={{
          marginTop: 14, padding: '10px 14px',
          background: a.valid_order ? '#F0FDF4' : '#FEF2F2',
          border: `1.5px solid ${a.valid_order ? '#86EFAC' : '#FCA5A5'}`,
          borderRadius: 10, fontSize: '0.8rem',
          color: a.valid_order ? '#166534' : '#991B1B'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 700 }}>
            {a.valid_order ? '✅' : '⚠️'} Тартиб ҳолати:
            <span>{a.valid_order ? 'Канон тартиб' : 'Морфема тартиби бузилган'}</span>
            {a.order_score !== undefined && (
              <span style={{ marginLeft: 'auto', fontSize: '0.7rem', opacity: 0.8 }}>
                Score: {(a.order_score * 100).toFixed(0)}%
              </span>
            )}
          </div>
          {a.order_issues && a.order_issues.length > 0 && (
            <ul style={{ margin: '8px 0 0 18px', padding: 0 }}>
              {a.order_issues.map((iss, i) => (
                <li key={i} style={{ marginBottom: 4 }}>{iss}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Breakdown */}
      <div style={{ marginTop: 14, padding: 10, background: '#F9FAFB', borderRadius: 8, fontFamily: 'monospace', fontSize: '0.85rem', color: '#374151' }}>
        {a.breakdown}
      </div>
    </div>
  )

  return (
    <div style={{ maxWidth: 960, margin: '0 auto' }}>
      {/* Hero */}
      <div style={{
        background: 'linear-gradient(135deg, #FFF8F0 0%, #FFEFDC 100%)',
        borderRadius: 20, padding: '28px 32px', border: '1.5px solid #FDE3C5',
        marginBottom: 24, display: 'flex', alignItems: 'center', gap: 18
      }}>
        <div style={{
          width: 52, height: 52, borderRadius: 14,
          background: 'linear-gradient(135deg, #B48C64, #8B5E3C)',
          display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>
          <Layers size={26} color="white" />
        </div>
        <div>
          <h1 style={{ fontSize: '1.7rem', fontWeight: 800, marginBottom: 4 }}>Морфологик таҳлил</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 0 }}>
            Ўзбек сўзларининг стем + аффикс + грамматик хусусиятлар таҳлили (Hunspell + heuristic + BERT)
          </p>
        </div>
      </div>

      {/* Mode tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <button onClick={() => setMode('word')}
          style={{
            padding: '10px 20px',
            background: mode === 'word' ? 'var(--accent-primary)' : 'var(--bg-card)',
            color: mode === 'word' ? 'white' : 'var(--text-primary)',
            border: '1.5px solid var(--border)',
            borderRadius: 10, fontWeight: 700, cursor: 'pointer'
          }}>
          Битта сўз
        </button>
        <button onClick={() => setMode('text')}
          style={{
            padding: '10px 20px',
            background: mode === 'text' ? 'var(--accent-primary)' : 'var(--bg-card)',
            color: mode === 'text' ? 'white' : 'var(--text-primary)',
            border: '1.5px solid var(--border)',
            borderRadius: 10, fontWeight: 700, cursor: 'pointer'
          }}>
          Бутун матн
        </button>
      </div>

      {/* Input */}
      {mode === 'word' ? (
        <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
          <input
            value={word}
            onChange={e => setWord(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && analyzeWord()}
            placeholder="Сўзни киритинг (масалан: ишламоқдамасанми)"
            style={{
              flex: 1, padding: '14px 16px', borderRadius: 12,
              border: '1.5px solid var(--border)', fontSize: '1rem',
              background: 'var(--bg-card)', outline: 'none'
            }}
          />
          <button onClick={analyzeWord} disabled={loading || !word.trim()}
            style={{
              padding: '14px 24px',
              background: 'linear-gradient(135deg, #B48C64, #8B5E3C)',
              color: 'white', border: 'none', borderRadius: 12,
              fontWeight: 700, fontSize: '0.9rem', cursor: loading ? 'not-allowed' : 'pointer',
              display: 'flex', alignItems: 'center', gap: 8
            }}>
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
            Таҳлил қилиш
          </button>
        </div>
      ) : (
        <div style={{ marginBottom: 24 }}>
          <textarea
            value={text}
            onChange={e => setText(e.target.value)}
            placeholder="Матнни киритинг..."
            rows={4}
            style={{
              width: '100%', padding: '14px 16px', borderRadius: 12,
              border: '1.5px solid var(--border)', fontSize: '0.95rem',
              background: 'var(--bg-card)', outline: 'none', resize: 'vertical', fontFamily: 'inherit'
            }}
          />
          <button onClick={analyzeText} disabled={loading || !text.trim()}
            style={{
              marginTop: 8,
              padding: '12px 24px',
              background: 'linear-gradient(135deg, #B48C64, #8B5E3C)',
              color: 'white', border: 'none', borderRadius: 12,
              fontWeight: 700, fontSize: '0.9rem', cursor: loading ? 'not-allowed' : 'pointer',
              display: 'flex', alignItems: 'center', gap: 8
            }}>
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Activity size={16} />}
            Матнни таҳлил қилиш
          </button>
        </div>
      )}

      {error && (
        <div style={{ padding: 14, background: '#FEF2F2', color: '#DC2626', border: '1.5px solid #FCA5A5', borderRadius: 10, marginBottom: 16 }}>
          {error}
        </div>
      )}

      {/* Single word result */}
      {result && renderAnalysis(result)}

      {/* Multi-word result */}
      {textResult && (
        <div>
          <div style={{ marginBottom: 12, padding: 14, background: '#F0FDF4', border: '1.5px solid #86EFAC', borderRadius: 10, fontSize: '0.85rem', color: '#166534' }}>
            <strong>{textResult.analyses.length}</strong> та сўз тан олинди
            {textResult.unknowns.length > 0 && (
              <span style={{ marginLeft: 12 }}>
                • <strong>{textResult.unknowns.length}</strong> та номаълум: {textResult.unknowns.slice(0, 5).join(', ')}{textResult.unknowns.length > 5 ? '...' : ''}
              </span>
            )}
          </div>
          {textResult.analyses.map((a, i) => <div key={i}>{renderAnalysis(a)}</div>)}
        </div>
      )}
    </div>
  )
}

function FeatureBadge({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{
      padding: '6px 12px',
      background: `${color}15`,
      border: `1.5px solid ${color}40`,
      borderRadius: 8,
      display: 'flex', flexDirection: 'column', alignItems: 'center'
    }}>
      <span style={{ fontSize: '0.55rem', color: '#6B7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</span>
      <span style={{ fontSize: '0.85rem', fontWeight: 700, color }}>{value}</span>
    </div>
  )
}
