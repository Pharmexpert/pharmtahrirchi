'use client'

import React, { useEffect, useState } from 'react'
import { FileText, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react'
import api from '../../../services/api'
import { useAuth } from '../../../components/LoginGuard'

export default function StyleGuidePage() {
  const { token } = useAuth()
  const [rules, setRules] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [filter, setFilter] = useState<string>('')
  const [testText, setTestText] = useState('')
  const [violations, setViolations] = useState<any[]>([])
  const [checking, setChecking] = useState(false)

  const load = async () => {
    if (!token) return
    setLoading(true)
    try {
      const r = await api.tilshunos.styleRules(filter || undefined)
      setRules(r.rules || [])
    } catch (_) {}
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [token, filter])

  const handleCheck = async () => {
    if (!testText.trim()) return
    setChecking(true)
    try {
      const r = await api.tilshunos.checkStyle(testText)
      setViolations(r.violations || [])
    } catch (e: any) { alert(e?.message || e) }
    finally { setChecking(false) }
  }

  const SEV_COLORS: Record<string, string> = {
    must: '#DC2626',
    should: '#D97706',
    may: '#0EA5E9',
  }

  const categories = Array.from(new Set(rules.map(r => r.category))).sort()

  return (
    <div style={{ maxWidth: 1400, margin: '0 auto', padding: '0 4px', paddingBottom: 80 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 20 }}>
        <FileText size={32} color="var(--accent-primary)" />
        <div>
          <h1 style={{ margin: 0, fontSize: '1.6rem', fontWeight: 800 }}>Style Guide — Pharma стандартлар</h1>
          <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.85rem' }}>USP / Ph.Eur. / ICH асосида тиббий-фарма ҳужжатлар учун ёзув қоидалари</p>
        </div>
      </div>

      {/* Test box */}
      <div style={{ background: 'white', border: '1.5px solid var(--border)', borderRadius: 14, padding: 16, marginBottom: 20 }}>
        <h3 style={{ margin: '0 0 10px', fontSize: '0.9rem', fontWeight: 700 }}>📝 Матнни style қоидаларга текшириш</h3>
        <textarea
          value={testText}
          onChange={e => setTestText(e.target.value)}
          placeholder="Pharma матн жойланг (масалан: 'Bemorga 500mg paracetamol berildi')..."
          rows={3}
          style={{ width: '100%', padding: 10, border: '1.5px solid var(--border)', borderRadius: 8, fontSize: '0.88rem', fontFamily: 'inherit', resize: 'vertical' }}
        />
        <button onClick={handleCheck} disabled={checking || !testText.trim()} style={{ marginTop: 8, padding: '8px 16px', borderRadius: 8, border: 'none', background: 'linear-gradient(135deg,#7C3AED,#6D28D9)', color: 'white', fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
          {checking ? <Loader2 size={14} className="animate-spin" /> : <AlertCircle size={14} />} Текшириш
        </button>

        {violations.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#DC2626', marginBottom: 6 }}>⚠ {violations.length} та қоидабузарлик топилди:</div>
            {violations.map((v, i) => (
              <div key={i} style={{ padding: '6px 10px', marginBottom: 4, background: '#FEF2F2', border: '1px solid #FCA5A5', borderRadius: 6, fontSize: '0.78rem' }}>
                <strong style={{ color: SEV_COLORS[v.severity] || '#9CA3AF' }}>[{v.rule_id}]</strong> {v.description} — <code style={{ background: 'white', padding: '0 4px' }}>{v.matched}</code>
              </div>
            ))}
          </div>
        )}
        {violations.length === 0 && checking === false && testText && (
          <div style={{ marginTop: 8, fontSize: '0.78rem', color: '#16A34A', display: 'flex', alignItems: 'center', gap: 4 }}>
            <CheckCircle2 size={14} /> Қоидабузарлик топилмади
          </div>
        )}
      </div>

      {/* Filter */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 14, flexWrap: 'wrap' }}>
        <button onClick={() => setFilter('')} style={{
          padding: '6px 14px', borderRadius: 8,
          background: !filter ? 'linear-gradient(135deg,#7C3AED,#6D28D9)' : 'white',
          color: !filter ? 'white' : 'var(--text-secondary)',
          border: !filter ? 'none' : '1.5px solid var(--border)',
          fontWeight: 700, fontSize: '0.78rem', cursor: 'pointer',
        }}>Барчаси ({rules.length})</button>
        {categories.map(c => (
          <button key={c} onClick={() => setFilter(c)} style={{
            padding: '6px 14px', borderRadius: 8,
            background: filter === c ? 'linear-gradient(135deg,#7C3AED,#6D28D9)' : 'white',
            color: filter === c ? 'white' : 'var(--text-secondary)',
            border: filter === c ? 'none' : '1.5px solid var(--border)',
            fontWeight: 700, fontSize: '0.78rem', cursor: 'pointer',
          }}>{c}</button>
        ))}
      </div>

      {/* Rules table */}
      <div style={{ background: 'white', border: '1.5px solid var(--border)', borderRadius: 14, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
          <thead>
            <tr style={{ background: '#F8FAFC', borderBottom: '2px solid var(--border)', textAlign: 'left' }}>
              <th style={{ padding: 12 }}>ID</th>
              <th style={{ padding: 12 }}>Категория</th>
              <th style={{ padding: 12 }}>Тавсиф</th>
              <th style={{ padding: 12 }}>Мисол</th>
              <th style={{ padding: 12 }}>Даража</th>
              <th style={{ padding: 12 }}>Манба</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} style={{ padding: 30, textAlign: 'center' }}><Loader2 className="animate-spin" /></td></tr>
            ) : rules.length === 0 ? (
              <tr><td colSpan={6} style={{ padding: 30, textAlign: 'center', color: '#9CA3AF' }}>Қоидалар йўқ</td></tr>
            ) : rules.map(r => (
              <tr key={r.id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                <td style={{ padding: 12, fontFamily: 'monospace', fontSize: '0.78rem', color: '#7C3AED', fontWeight: 700 }}>{r.rule_id}</td>
                <td style={{ padding: 12 }}><span style={{ padding: '2px 8px', borderRadius: 4, background: '#F3E8FF', color: '#7C3AED', fontSize: '0.72rem', fontWeight: 700 }}>{r.category}</span></td>
                <td style={{ padding: 12 }}>{r.description}</td>
                <td style={{ padding: 12, fontFamily: 'monospace', fontSize: '0.75rem', color: '#475569' }}>{r.examples}</td>
                <td style={{ padding: 12 }}><span style={{ padding: '2px 8px', borderRadius: 4, background: `${SEV_COLORS[r.severity] || '#9CA3AF'}22`, color: SEV_COLORS[r.severity] || '#9CA3AF', fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase' }}>{r.severity}</span></td>
                <td style={{ padding: 12, fontSize: '0.75rem', color: 'var(--text-muted)' }}>{r.source}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
