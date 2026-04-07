'use client'

import React, { useEffect, useState } from 'react'
import { Pill, Search, Plus, Database, BookOpen, Loader2 } from 'lucide-react'
import api from '../../../services/api'
import { useAuth } from '../../../components/LoginGuard'

export default function PharmaAdminPage() {
  const { token } = useAuth()
  const [tab, setTab] = useState<'drugs' | 'terms'>('drugs')
  const [drugs, setDrugs] = useState<any[]>([])
  const [terms, setTerms] = useState<any[]>([])
  const [drugTotal, setDrugTotal] = useState(0)
  const [termTotal, setTermTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)
  const [seeding, setSeeding] = useState(false)
  const [showAdd, setShowAdd] = useState(false)
  const [newDrug, setNewDrug] = useState({ inn: '', brand_name: '', atc_code: '', form: '', dose: '', manufacturer: '', country: '', category: '', description: '' })
  const [newTerm, setNewTerm] = useState({ term_uz: '', term_ru: '', term_en: '', definition: '', category: '', synonyms: '' })

  const load = async () => {
    if (!token) return
    setLoading(true)
    try {
      if (tab === 'drugs') {
        const r = await api.admin.drugs(search, 200)
        setDrugs(r.drugs || [])
        setDrugTotal(r.total || 0)
      } else {
        const r = await api.admin.medicalTerms(search, 200)
        setTerms(r.terms || [])
        setTermTotal(r.total || 0)
      }
    } catch (_) {}
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [token, tab])

  const handleSeed = async () => {
    if (!confirm('85+ стандарт фарма дориларни базага қўшишни тасдиқлайсизми?')) return
    setSeeding(true)
    try {
      const r = await api.admin.seedDrugs()
      if (r.success) {
        alert(`✓ ${r.inserted || 0} дори қўшилди`)
        await load()
      }
    } catch (e: any) { alert('Хатолик: ' + (e?.message || e)) }
    finally { setSeeding(false) }
  }

  const handleAddDrug = async () => {
    if (!newDrug.inn) return alert('INN мажбурий')
    try {
      const r = await api.admin.addDrug(newDrug)
      if (r.success) {
        setNewDrug({ inn: '', brand_name: '', atc_code: '', form: '', dose: '', manufacturer: '', country: '', category: '', description: '' })
        setShowAdd(false)
        await load()
      }
    } catch (e: any) { alert(e?.message || e) }
  }

  const handleAddTerm = async () => {
    if (!newTerm.term_uz && !newTerm.term_ru && !newTerm.term_en) return alert('Камida бir til termini киритинг')
    try {
      const r = await api.admin.addMedicalTerm(newTerm)
      if (r.success) {
        setNewTerm({ term_uz: '', term_ru: '', term_en: '', definition: '', category: '', synonyms: '' })
        setShowAdd(false)
        await load()
      }
    } catch (e: any) { alert(e?.message || e) }
  }

  return (
    <div style={{ maxWidth: 1400, margin: '0 auto', padding: '0 4px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 20 }}>
        <Pill size={32} color="var(--accent-primary)" />
        <div>
          <h1 style={{ margin: 0, fontSize: '1.6rem', fontWeight: 800 }}>Фарма базаси</h1>
          <p style={{ margin: 0, color: 'var(--text-muted)' }}>Дорилар (INN/ATC) ва тиббий терминлар</p>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 16, borderBottom: '1px solid var(--border)' }}>
        {[{ k: 'drugs', label: `Дорилар (${drugTotal})`, icon: Pill }, { k: 'terms', label: `Терминлар (${termTotal})`, icon: BookOpen }].map(({ k, label, icon: Icon }) => (
          <button key={k} onClick={() => { setTab(k as any); setSearch('') }} style={{
            padding: '10px 18px',
            background: tab === k ? 'var(--accent-bg)' : 'transparent',
            border: 'none',
            borderBottom: tab === k ? '3px solid var(--accent-primary)' : '3px solid transparent',
            color: tab === k ? 'var(--accent-primary)' : 'var(--text-secondary)',
            fontWeight: 700, fontSize: '0.9rem', cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <Icon size={16} /> {label}
          </button>
        ))}
      </div>

      {/* Toolbar */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 14, flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: 280 }}>
          <Search size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && load()}
            placeholder={tab === 'drugs' ? 'INN, бренд ёки ATC код бўйича қидириш...' : 'Узбек/русча/инглизча термин...'}
            style={{ width: '100%', padding: '10px 14px 10px 38px', borderRadius: 10, border: '1.5px solid var(--border)', fontSize: '0.9rem', outline: 'none' }}
          />
        </div>
        <button onClick={load} disabled={loading} style={{ padding: '10px 18px', borderRadius: 10, border: '1.5px solid var(--border)', background: 'white', cursor: 'pointer', fontWeight: 600 }}>
          {loading ? <Loader2 size={14} className="animate-spin" /> : 'Қидириш'}
        </button>
        <button onClick={() => setShowAdd(true)} style={{ padding: '10px 18px', borderRadius: 10, border: 'none', background: 'linear-gradient(135deg, #16A34A, #059669)', color: 'white', cursor: 'pointer', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 6 }}>
          <Plus size={14} /> Янги қўшиш
        </button>
        {tab === 'drugs' && (
          <button onClick={handleSeed} disabled={seeding} style={{ padding: '10px 18px', borderRadius: 10, border: '1.5px solid #D97706', background: '#FFF7ED', color: '#D97706', cursor: 'pointer', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 6 }}>
            {seeding ? <Loader2 size={14} className="animate-spin" /> : <Database size={14} />} 85 та стандарт дори импорт
          </button>
        )}
      </div>

      {/* Add modal */}
      {showAdd && (
        <div onClick={() => setShowAdd(false)} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div onClick={e => e.stopPropagation()} style={{ background: 'white', borderRadius: 16, padding: 24, width: 'min(560px, 92vw)', maxHeight: '85vh', overflow: 'auto' }}>
            <h3 style={{ margin: '0 0 16px', fontSize: '1.2rem', fontWeight: 800 }}>{tab === 'drugs' ? 'Янги дори' : 'Янги тиббий термин'}</h3>
            {tab === 'drugs' ? (
              <div style={{ display: 'grid', gap: 10 }}>
                {(['inn', 'brand_name', 'atc_code', 'form', 'dose', 'manufacturer', 'country', 'category', 'description'] as const).map(k => (
                  <input key={k} placeholder={k.replace('_', ' ').toUpperCase()} value={(newDrug as any)[k]} onChange={e => setNewDrug({ ...newDrug, [k]: e.target.value })} style={{ padding: 10, border: '1.5px solid #E5E7EB', borderRadius: 8, fontSize: '0.9rem' }} />
                ))}
                <button onClick={handleAddDrug} style={{ padding: '12px', borderRadius: 8, border: 'none', background: '#16A34A', color: 'white', fontWeight: 700, cursor: 'pointer' }}>Қўшиш</button>
              </div>
            ) : (
              <div style={{ display: 'grid', gap: 10 }}>
                {(['term_uz', 'term_ru', 'term_en', 'definition', 'category', 'synonyms'] as const).map(k => (
                  k === 'definition' ? (
                    <textarea key={k} placeholder={k.toUpperCase()} value={(newTerm as any)[k]} onChange={e => setNewTerm({ ...newTerm, [k]: e.target.value })} rows={3} style={{ padding: 10, border: '1.5px solid #E5E7EB', borderRadius: 8, fontSize: '0.9rem', resize: 'vertical' }} />
                  ) : (
                    <input key={k} placeholder={k.replace('_', ' ').toUpperCase()} value={(newTerm as any)[k]} onChange={e => setNewTerm({ ...newTerm, [k]: e.target.value })} style={{ padding: 10, border: '1.5px solid #E5E7EB', borderRadius: 8, fontSize: '0.9rem' }} />
                  )
                ))}
                <button onClick={handleAddTerm} style={{ padding: '12px', borderRadius: 8, border: 'none', background: '#16A34A', color: 'white', fontWeight: 700, cursor: 'pointer' }}>Қўшиш</button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Table */}
      <div style={{ background: 'white', border: '1.5px solid var(--border)', borderRadius: 14, overflow: 'hidden' }}>
        {tab === 'drugs' ? (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ background: '#F8FAFC', borderBottom: '2px solid var(--border)', textAlign: 'left' }}>
                <th style={{ padding: 12 }}>INN</th>
                <th style={{ padding: 12 }}>Бренд</th>
                <th style={{ padding: 12 }}>ATC</th>
                <th style={{ padding: 12 }}>Шакл</th>
                <th style={{ padding: 12 }}>Доза</th>
                <th style={{ padding: 12 }}>Категория</th>
              </tr>
            </thead>
            <tbody>
              {drugs.map(d => (
                <tr key={d.id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                  <td style={{ padding: 12, fontWeight: 700, color: '#7C3AED' }}>{d.inn}</td>
                  <td style={{ padding: 12 }}>{d.brand_name}</td>
                  <td style={{ padding: 12, fontFamily: 'monospace', fontSize: '0.8rem', color: 'var(--text-muted)' }}>{d.atc_code}</td>
                  <td style={{ padding: 12 }}>{d.form}</td>
                  <td style={{ padding: 12 }}>{d.dose}</td>
                  <td style={{ padding: 12, fontSize: '0.78rem', color: 'var(--text-muted)' }}>{d.category}</td>
                </tr>
              ))}
              {drugs.length === 0 && !loading && (
                <tr><td colSpan={6} style={{ padding: 60, textAlign: 'center', color: 'var(--text-muted)' }}>Дорилар топилмади. «85 та стандарт дори импорт» тугмасини босинг.</td></tr>
              )}
            </tbody>
          </table>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ background: '#F8FAFC', borderBottom: '2px solid var(--border)', textAlign: 'left' }}>
                <th style={{ padding: 12 }}>UZ</th>
                <th style={{ padding: 12 }}>RU</th>
                <th style={{ padding: 12 }}>EN</th>
                <th style={{ padding: 12 }}>Изоҳ</th>
              </tr>
            </thead>
            <tbody>
              {terms.map(t => (
                <tr key={t.id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                  <td style={{ padding: 12, fontWeight: 700 }}>{t.term_uz}</td>
                  <td style={{ padding: 12 }}>{t.term_ru}</td>
                  <td style={{ padding: 12 }}>{t.term_en}</td>
                  <td style={{ padding: 12, fontSize: '0.78rem', color: 'var(--text-muted)' }}>{t.definition}</td>
                </tr>
              ))}
              {terms.length === 0 && !loading && (
                <tr><td colSpan={4} style={{ padding: 60, textAlign: 'center', color: 'var(--text-muted)' }}>Терминлар топилмади. «Янги қўшиш» тугмасини босинг.</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
