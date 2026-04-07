'use client'

import React, { useState, useEffect } from 'react'
import { Sparkles, Loader2, BookOpen, Check, X, RefreshCw, BarChart3, Award, Globe } from 'lucide-react'
import { useAuth } from '../../components/LoginGuard'
import api, { TilshunosCheckResult, LinguisticIssue } from '../../services/api'

type Lang = 'en' | 'ru' | 'uz-cyr' | 'uz-lat'

interface PanelState {
  text: string
  result: TilshunosCheckResult | null
  loading: boolean
}

const LANG_LABELS: Record<Lang, string> = {
  'en': 'English',
  'ru': 'Русский',
  'uz-cyr': 'Ўзбек (Кирилл)',
  'uz-lat': 'O\'zbek (Lotin)',
}

const LANG_FLAGS: Record<Lang, string> = {
  'en': '🇬🇧',
  'ru': '🇷🇺',
  'uz-cyr': '🇺🇿',
  'uz-lat': '🇺🇿',
}

const SEVERITY_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  high: { bg: '#FEF2F2', border: '#FCA5A5', text: '#991B1B' },
  medium: { bg: '#FFFBEB', border: '#FCD34D', text: '#92400E' },
  low: { bg: '#F0FDF4', border: '#86EFAC', text: '#166534' },
}

const CATEGORY_LABELS: Record<string, string> = {
  orthography: 'Имло',
  punctuation: 'Тиниш белгилари',
  syntax: 'Синтаксис',
  morphology: 'Морфология',
  grammar: 'Грамматика',
}

const CATEGORY_COLORS: Record<string, string> = {
  orthography: '#D97706',
  punctuation: '#0EA5E9',
  syntax: '#9333EA',
  morphology: '#16A34A',
  grammar: '#DC2626',
}

export default function TilshunosPage() {
  const { token } = useAuth()
  const [stats, setStats] = useState<any>(null)
  const [panels, setPanels] = useState<Record<Lang, PanelState>>({
    'en':     { text: '', result: null, loading: false },
    'ru':     { text: '', result: null, loading: false },
    'uz-cyr': { text: '', result: null, loading: false },
    'uz-lat': { text: '', result: null, loading: false },
  })

  // Load rules statistics on mount
  useEffect(() => {
    api.tilshunos.rulesStats()
      .then(setStats)
      .catch(() => {})
  }, [])

  const runCheck = async (lang: Lang) => {
    const text = panels[lang].text
    if (!text.trim()) return

    setPanels(p => ({ ...p, [lang]: { ...p[lang], loading: true } }))

    // Map UI lang to backend lang
    const backendLang = lang.startsWith('uz') ? 'uz' : lang
    try {
      const result = await api.tilshunos.check(text, backendLang)
      setPanels(p => ({ ...p, [lang]: { ...p[lang], result, loading: false } }))
    } catch (e) {
      console.error('Check failed:', e)
      setPanels(p => ({ ...p, [lang]: { ...p[lang], loading: false } }))
    }
  }

  const checkAll = async () => {
    for (const lang of Object.keys(panels) as Lang[]) {
      if (panels[lang].text.trim()) {
        await runCheck(lang)
      }
    }
  }

  const applyFix = async (lang: Lang, issue: LinguisticIssue) => {
    const text = panels[lang].text
    const newText = text.substring(0, issue.from_index) + issue.suggestion + text.substring(issue.to_index)
    setPanels(p => ({ ...p, [lang]: { ...p[lang], text: newText } }))

    // Confirm to backend → triggers self-learning
    try {
      const backendLang = lang.startsWith('uz') ? 'uz' : lang
      await api.tilshunos.confirm({
        wrong: issue.matched_text,
        correct: issue.suggestion,
        context: text,
        category: issue.error_type,
        lang: backendLang,
      })
    } catch (_) {}
  }

  const renderIssue = (lang: Lang, issue: LinguisticIssue, idx: number) => {
    const colors = SEVERITY_COLORS[issue.severity] || SEVERITY_COLORS.medium
    return (
      <div key={idx} style={{
        padding: 10,
        background: colors.bg,
        border: `1.5px solid ${colors.border}`,
        borderRadius: 8,
        marginBottom: 6,
        fontSize: '0.78rem',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4, flexWrap: 'wrap' }}>
          <span style={{
            fontSize: '0.55rem', padding: '2px 6px', borderRadius: 4,
            background: CATEGORY_COLORS[issue.category] || '#6B7280', color: 'white',
            fontWeight: 700, textTransform: 'uppercase'
          }}>
            {CATEGORY_LABELS[issue.category] || issue.category}
          </span>
          <span style={{ fontSize: '0.55rem', color: colors.text, fontWeight: 700 }}>
            {issue.error_type}
          </span>
          <span style={{ fontSize: '0.55rem', color: '#6B7280', marginLeft: 'auto' }}>
            {issue.source}
          </span>
        </div>
        <div style={{ color: colors.text, marginBottom: 4 }}>
          {issue.message}
        </div>
        {issue.matched_text && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontFamily: 'monospace', fontSize: '0.7rem' }}>
            <span style={{ background: '#FEE2E2', color: '#991B1B', padding: '1px 6px', borderRadius: 4, textDecoration: 'line-through' }}>
              {issue.matched_text}
            </span>
            {issue.suggestion && (
              <>
                <span>→</span>
                <span style={{ background: '#D1FAE5', color: '#065F46', padding: '1px 6px', borderRadius: 4, fontWeight: 700 }}>
                  {issue.suggestion}
                </span>
                <button onClick={() => applyFix(lang, issue)}
                  style={{
                    marginLeft: 'auto', padding: '2px 8px', background: '#10B981',
                    color: 'white', border: 'none', borderRadius: 4, fontSize: '0.65rem',
                    fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 3
                  }}>
                  <Check size={10} /> Қабул
                </button>
              </>
            )}
          </div>
        )}
      </div>
    )
  }

  const renderPanel = (lang: Lang) => {
    const state = panels[lang]
    return (
      <div style={{
        background: 'var(--bg-card)',
        border: '1.5px solid var(--border)',
        borderRadius: 14,
        padding: 16,
        display: 'flex',
        flexDirection: 'column',
        minHeight: 360,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
          <span style={{ fontSize: '1.3rem' }}>{LANG_FLAGS[lang]}</span>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 700, margin: 0 }}>{LANG_LABELS[lang]}</h3>
          {state.result && (
            <span style={{
              marginLeft: 'auto',
              fontSize: '0.7rem',
              padding: '3px 8px',
              borderRadius: 6,
              background: state.result.score >= 0.9 ? '#D1FAE5' : state.result.score >= 0.6 ? '#FEF3C7' : '#FEE2E2',
              color: state.result.score >= 0.9 ? '#065F46' : state.result.score >= 0.6 ? '#92400E' : '#991B1B',
              fontWeight: 700
            }}>
              Сифат: {Math.round(state.result.score * 100)}%
            </span>
          )}
        </div>

        <textarea
          value={state.text}
          onChange={e => setPanels(p => ({ ...p, [lang]: { ...p[lang], text: e.target.value } }))}
          placeholder={`${LANG_LABELS[lang]} матнни киритинг...`}
          style={{
            width: '100%',
            minHeight: 110,
            padding: 10,
            border: '1.5px solid var(--border)',
            borderRadius: 8,
            fontSize: '0.85rem',
            fontFamily: 'inherit',
            resize: 'vertical',
            outline: 'none',
            background: 'var(--bg-secondary)',
          }}
        />

        <button onClick={() => runCheck(lang)} disabled={state.loading || !state.text.trim()}
          style={{
            marginTop: 8,
            padding: '8px 12px',
            background: 'linear-gradient(135deg, #B48C64, #8B5E3C)',
            color: 'white',
            border: 'none',
            borderRadius: 8,
            fontWeight: 700,
            fontSize: '0.8rem',
            cursor: state.loading ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 6,
          }}>
          {state.loading ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
          Текшириш ва таҳрирлаш
        </button>

        {state.result && (
          <div style={{ marginTop: 10, flex: 1, overflow: 'auto', maxHeight: 250 }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 6, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <span>Жами хато: <strong>{state.result.total}</strong></span>
              {Object.entries(state.result.by_severity).map(([sev, count]) => count > 0 && (
                <span key={sev}>{sev}: <strong>{count}</strong></span>
              ))}
            </div>
            {state.result.issues.length === 0 ? (
              <div style={{ padding: 10, background: '#F0FDF4', borderRadius: 6, color: '#166534', fontSize: '0.8rem', textAlign: 'center' }}>
                ✅ Хато топилмади — матн тоза
              </div>
            ) : (
              state.result.issues.slice(0, 20).map((issue, i) => renderIssue(lang, issue, i))
            )}
          </div>
        )}
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 1600, margin: '0 auto', padding: '0 4px' }}>
      {/* Hero */}
      <div style={{
        background: 'linear-gradient(135deg, #FFF8F0 0%, #FFEFDC 100%)',
        borderRadius: 20,
        padding: '24px 32px',
        border: '1.5px solid #FDE3C5',
        marginBottom: 20,
        display: 'flex',
        alignItems: 'center',
        gap: 18,
        flexWrap: 'wrap',
      }}>
        <div style={{
          width: 52, height: 52, borderRadius: 14,
          background: 'linear-gradient(135deg, #B48C64, #8B5E3C)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Award size={26} color="white" />
        </div>
        <div style={{ flex: 1 }}>
          <h1 style={{ fontSize: '1.6rem', fontWeight: 800, marginBottom: 4 }}>Тилшунос</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: 0 }}>
            4 та тилда матн таржима, илмий таҳрир, имло, синтаксис, пунктуация, морфология, грамматика текшируви
          </p>
        </div>
        <button onClick={checkAll}
          style={{
            padding: '10px 20px',
            background: 'linear-gradient(135deg, #10B981, #059669)',
            color: 'white',
            border: 'none',
            borderRadius: 10,
            fontWeight: 700,
            fontSize: '0.85rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}>
          <RefreshCw size={14} /> Барча панелларни текшириш
        </button>
      </div>

      {/* Stats overview */}
      {stats && (
        <div style={{
          background: 'var(--bg-card)',
          border: '1.5px solid var(--border)',
          borderRadius: 12,
          padding: 14,
          marginBottom: 16,
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: 10,
        }}>
          <StatCard label="Hunspell" value={(stats.hunspell?.lat_words || 0) + (stats.hunspell?.cyr_words || 0)} suffix="сўз" color="#D97706" />
          <StatCard label="Tahrirchi" value={stats.tahrirchi_lexicon_words || 0} suffix="сўз" color="#0EA5E9" />
          <StatCard label="Sayqallash" value={stats.sayqallash_total || 0} suffix="қоида" color="#9333EA" />
          <StatCard label="Канон қоидалар" value={stats.canonical_rules?.total || 0} suffix="rules" color="#16A34A" />
          <StatCard label="Синонимлар" value={stats.platform_databases?.synonyms || 0} suffix="" color="#DB2777" />
          <StatCard label="Аббревиатуралар" value={stats.platform_databases?.abbreviations || 0} suffix="" color="#EA580C" />
        </div>
      )}

      {/* 4 panels grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
        gap: 14,
      }}>
        {(['en', 'ru', 'uz-cyr', 'uz-lat'] as Lang[]).map(lang => (
          <div key={lang}>{renderPanel(lang)}</div>
        ))}
      </div>
    </div>
  )
}

function StatCard({ label, value, suffix, color }: { label: string; value: number; suffix: string; color: string }) {
  return (
    <div style={{
      padding: 10,
      background: `${color}10`,
      border: `1.5px solid ${color}30`,
      borderRadius: 10,
    }}>
      <div style={{ fontSize: '0.6rem', color: '#6B7280', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
        {label}
      </div>
      <div style={{ fontSize: '1.3rem', fontWeight: 800, color }}>
        {value.toLocaleString()}
      </div>
      <div style={{ fontSize: '0.6rem', color: '#9CA3AF' }}>{suffix}</div>
    </div>
  )
}
