'use client'

import React, { useState, useEffect, useMemo } from 'react'
import { Pill, BookOpen, Palette, Search, Loader2, RefreshCw, Filter } from 'lucide-react'
import api from '../../../services/api'

type Tab = 'toc' | 'registry' | 'colors'

export default function PharmaDbPage() {
  const [tab, setTab] = useState<Tab>('toc')

  return (
    <div style={{ maxWidth: 1400, margin: '0 auto', padding: '0 4px 60px' }}>
      {/* Hero */}
      <div style={{
        background: 'linear-gradient(135deg, #FFF8F0 0%, #FFEFDC 100%)',
        borderRadius: 20, padding: '26px 32px', marginBottom: 22,
        border: '1.5px solid #FDE3C5', display: 'flex', alignItems: 'center', gap: 18
      }}>
        <div style={{
          width: 56, height: 56, borderRadius: 14,
          background: 'linear-gradient(135deg, #B48C64, #8B5E3C)',
          display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>
          <Pill size={28} color="white" />
        </div>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.6rem', fontWeight: 800 }}>Фарма базаси 💊</h1>
          <p style={{ margin: 0, color: '#64748B', fontSize: '.9rem' }}>
            Давлат фармакопеяси мундарижаси, Давлат реестри, ранглар жадвали
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
        {[
          { id: 'toc', label: 'ДФ мундарижаси', icon: BookOpen, color: '#0EA5E9' },
          { id: 'registry', label: 'Давлат реестри', icon: Pill, color: '#8B5E3C' },
          { id: 'colors', label: 'Ранглар жадвали', icon: Palette, color: '#DB2777' },
        ].map(t => {
          const Icon = t.icon
          const active = tab === t.id
          return (
            <button key={t.id} onClick={() => setTab(t.id as Tab)} style={{
              padding: '12px 22px', borderRadius: 14,
              border: active ? `2px solid ${t.color}` : '1.5px solid #E2E8F0',
              background: active ? `${t.color}10` : 'white',
              color: active ? t.color : '#64748B',
              fontWeight: 800, fontSize: '.88rem', cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 8,
              boxShadow: active ? `0 4px 16px ${t.color}22` : 'none',
              transition: 'all 0.2s',
            }}>
              <Icon size={16} /> {t.label}
            </button>
          )
        })}
      </div>

      {tab === 'toc' && <TocTable />}
      {tab === 'registry' && <RegistryTable />}
      {tab === 'colors' && <ColorsTable />}
    </div>
  )
}

// ═══════════════════════════════════════════════════
// ДФ мундарижаси
// ═══════════════════════════════════════════════════
function TocTable() {
  const [rows, setRows] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')
  const [edition, setEdition] = useState('')
  const [fUz, setFUz] = useState('')
  const [fEn, setFEn] = useState('')
  const [fRu, setFRu] = useState('')
  const [fText, setFText] = useState('')

  const load = async () => {
    setLoading(true)
    try { const r: any = await api.admin.pharmaToc(q, edition); setRows(r.rows || []) }
    finally { setLoading(false) }
  }
  useEffect(() => { load() /* eslint-disable-next-line */ }, [q, edition])

  const visible = useMemo(() => rows.filter(r => {
    if (fUz && !(r.name_uz || '').toLowerCase().includes(fUz.toLowerCase())) return false
    if (fEn && !(r.name_en || '').toLowerCase().includes(fEn.toLowerCase())) return false
    if (fRu && !(r.name_ru || '').toLowerCase().includes(fRu.toLowerCase())) return false
    if (fText && !(r.text_no || '').toLowerCase().includes(fText.toLowerCase())) return false
    return true
  }), [rows, fUz, fEn, fRu, fText])

  const editions = Array.from(new Set(rows.map(r => r.edition).filter(Boolean)))

  return (
    <div>
      <Toolbar
        q={q} setQ={setQ} color="#0EA5E9" total={rows.length} visible={visible.length}
        extra={
          <select value={edition} onChange={e => setEdition(e.target.value)}
            style={{ padding: '9px 14px', borderRadius: 10, border: '1.5px solid #E0F2FE', background: 'white', fontSize: '.82rem', cursor: 'pointer', fontWeight: 600 }}>
            <option value="">Барча нашрлар</option>
            {editions.map(e => <option key={e} value={e}>{e}</option>)}
          </select>
        }
        onRefresh={load}
      />
      <div style={{ background: 'white', borderRadius: 14, border: '1px solid #E2E8F0', overflow: 'hidden', boxShadow: '0 2px 10px rgba(0,0,0,.03)' }}>
        {loading ? <Loader /> : visible.length === 0 ? <Empty /> : (
          <div style={{ maxHeight: '70vh', overflowY: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '.83rem' }}>
              <thead style={{ position: 'sticky', top: 0, background: '#F0F9FF', borderBottom: '2px solid #BAE6FD', zIndex: 1 }}>
                <tr>
                  <Th label="№" w={60} />
                  <Th label="Нашр" w={130} />
                  <Th label="Ўзбекча" />
                  <Th label="English" />
                  <Th label="Русский" />
                  <Th label="Матн №" w={90} />
                </tr>
                <tr style={{ background: '#FAFBFC' }}>
                  <th></th>
                  <th></th>
                  <th style={{ padding: '5px 12px' }}><FilterInput value={fUz} onChange={setFUz} placeholder="🔍 uz" /></th>
                  <th style={{ padding: '5px 12px' }}><FilterInput value={fEn} onChange={setFEn} placeholder="🔍 en" /></th>
                  <th style={{ padding: '5px 12px' }}><FilterInput value={fRu} onChange={setFRu} placeholder="🔍 ru" /></th>
                  <th style={{ padding: '5px 12px' }}><FilterInput value={fText} onChange={setFText} placeholder="🔍" /></th>
                </tr>
              </thead>
              <tbody>
                {visible.map((r, i) => (
                  <tr key={r.id} style={{ borderBottom: '1px solid #F1F5F9', transition: 'background .15s' }}
                    onMouseEnter={e => e.currentTarget.style.background = '#F0F9FF'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                    <td style={{ padding: '11px 14px', color: '#94A3B8', fontWeight: 700 }}>{r.seq_no || i + 1}</td>
                    <td style={{ padding: '11px 14px' }}>
                      <span style={{ padding: '2px 8px', borderRadius: 10, background: '#E0F2FE', color: '#0369A1', fontSize: '.7rem', fontWeight: 700 }}>{r.edition}</span>
                    </td>
                    <td style={{ padding: '11px 14px', fontWeight: 600, color: '#1E293B' }}>{r.name_uz}</td>
                    <td style={{ padding: '11px 14px', color: '#475569', fontStyle: 'italic' }}>{r.name_en || '—'}</td>
                    <td style={{ padding: '11px 14px', color: '#475569' }}>{r.name_ru || '—'}</td>
                    <td style={{ padding: '11px 14px', textAlign: 'center', fontFamily: 'monospace', fontSize: '.75rem', color: '#0EA5E9', fontWeight: 700 }}>{r.text_no}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════
// Давлат реестри
// ═══════════════════════════════════════════════════
function RegistryTable() {
  const [rows, setRows] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')
  const [fTrade, setFTrade] = useState('')
  const [fInn, setFInn] = useState('')
  const [fCountry, setFCountry] = useState('')
  const [fAtc, setFAtc] = useState('')
  const [fManuf, setFManuf] = useState('')
  const [fDisp, setFDisp] = useState('')

  const load = async () => {
    setLoading(true)
    try { const r: any = await api.admin.pharmaRegistry(q); setRows(r.rows || []) }
    finally { setLoading(false) }
  }
  useEffect(() => { load() /* eslint-disable-next-line */ }, [q])

  const visible = useMemo(() => rows.filter(r => {
    if (fTrade && !(r.trade_name || '').toLowerCase().includes(fTrade.toLowerCase())) return false
    if (fInn && !(r.inn || '').toLowerCase().includes(fInn.toLowerCase())) return false
    if (fCountry && !(r.country || '').toLowerCase().includes(fCountry.toLowerCase())) return false
    if (fAtc && !(r.atc_code || '').toLowerCase().includes(fAtc.toLowerCase())) return false
    if (fManuf && !(r.manufacturer || '').toLowerCase().includes(fManuf.toLowerCase())) return false
    if (fDisp && !(r.dispense_type || '').toLowerCase().includes(fDisp.toLowerCase())) return false
    return true
  }), [rows, fTrade, fInn, fCountry, fAtc, fManuf, fDisp])

  return (
    <div>
      <Toolbar q={q} setQ={setQ} color="#8B5E3C" total={rows.length} visible={visible.length} onRefresh={load} />
      <div style={{ background: 'white', borderRadius: 14, border: '1px solid #E2E8F0', overflow: 'hidden', boxShadow: '0 2px 10px rgba(0,0,0,.03)' }}>
        {loading ? <Loader /> : visible.length === 0 ? <Empty /> : (
          <div style={{ maxHeight: '75vh', overflowY: 'auto', overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '.78rem', minWidth: 1200 }}>
              <thead style={{ position: 'sticky', top: 0, background: '#FDF6F0', borderBottom: '2px solid #FDE3C5', zIndex: 1 }}>
                <tr>
                  <Th label="№" w={50} />
                  <Th label="Савдо номи" />
                  <Th label="INN" />
                  <Th label="Шакл" w={220} />
                  <Th label="Мамлакат" w={120} />
                  <Th label="Ишлаб чиқарувчи" w={180} />
                  <Th label="ATC" w={90} />
                  <Th label="Рег. №" w={130} />
                  <Th label="Сана" w={90} />
                  <Th label="Сотув" w={100} />
                </tr>
                <tr style={{ background: '#FAFBFC' }}>
                  <th></th>
                  <th style={{ padding: '5px 10px' }}><FilterInput value={fTrade} onChange={setFTrade} placeholder="🔍 savdo" /></th>
                  <th style={{ padding: '5px 10px' }}><FilterInput value={fInn} onChange={setFInn} placeholder="🔍 INN" /></th>
                  <th></th>
                  <th style={{ padding: '5px 10px' }}><FilterInput value={fCountry} onChange={setFCountry} placeholder="🔍 mam." /></th>
                  <th style={{ padding: '5px 10px' }}><FilterInput value={fManuf} onChange={setFManuf} placeholder="🔍 firma" /></th>
                  <th style={{ padding: '5px 10px' }}><FilterInput value={fAtc} onChange={setFAtc} placeholder="🔍 ATC" /></th>
                  <th></th>
                  <th></th>
                  <th style={{ padding: '5px 10px' }}><FilterInput value={fDisp} onChange={setFDisp} placeholder="🔍" /></th>
                </tr>
              </thead>
              <tbody>
                {visible.map((r, i) => (
                  <tr key={r.id} style={{ borderBottom: '1px solid #F1F5F9' }}
                    onMouseEnter={e => e.currentTarget.style.background = '#FFFBEB'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                    <td style={{ padding: '10px 12px', color: '#94A3B8', fontWeight: 700 }}>{r.seq_no || i + 1}</td>
                    <td style={{ padding: '10px 12px', fontWeight: 700, color: '#8B5E3C', whiteSpace: 'pre-line' }}>{r.trade_name}</td>
                    <td style={{ padding: '10px 12px', color: '#1D4ED8', fontWeight: 600 }}>{r.inn}</td>
                    <td style={{ padding: '10px 12px', color: '#475569', fontSize: '.72rem' }}>{(r.dosage_form || '').slice(0, 80)}{(r.dosage_form || '').length > 80 ? '…' : ''}</td>
                    <td style={{ padding: '10px 12px', color: '#0369A1' }}>{r.country}</td>
                    <td style={{ padding: '10px 12px', color: '#475569', fontSize: '.72rem' }}>{(r.manufacturer || '').slice(0, 60)}</td>
                    <td style={{ padding: '10px 12px' }}>
                      {r.atc_code && <span style={{ padding: '2px 8px', borderRadius: 10, background: '#F3E8FF', color: '#7C3AED', fontSize: '.7rem', fontWeight: 700, fontFamily: 'monospace' }}>{r.atc_code}</span>}
                    </td>
                    <td style={{ padding: '10px 12px', fontFamily: 'monospace', fontSize: '.7rem', color: '#64748B' }}>{r.registration_no}</td>
                    <td style={{ padding: '10px 12px', fontSize: '.7rem', color: '#94A3B8' }}>{r.registration_date}</td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{
                        padding: '2px 8px', borderRadius: 10, fontSize: '.68rem', fontWeight: 700,
                        background: (r.dispense_type || '').includes('рецепту') ? '#FEE2E2' : '#DCFCE7',
                        color: (r.dispense_type || '').includes('рецепту') ? '#991B1B' : '#15803D',
                      }}>
                        {r.dispense_type || '—'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════
// Ранглар жадвали
// ═══════════════════════════════════════════════════
function ColorsTable() {
  const [rows, setRows] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')
  const [fUz, setFUz] = useState('')
  const [fRu, setFRu] = useState('')
  const [fEn, setFEn] = useState('')

  const load = async () => {
    setLoading(true)
    try { const r: any = await api.admin.pharmaColors(q); setRows(r.rows || []) }
    finally { setLoading(false) }
  }
  useEffect(() => { load() /* eslint-disable-next-line */ }, [q])

  const visible = useMemo(() => rows.filter(r => {
    if (fUz && !(r.uz || '').toLowerCase().includes(fUz.toLowerCase())) return false
    if (fRu && !(r.ru || '').toLowerCase().includes(fRu.toLowerCase())) return false
    if (fEn && !(r.en || '').toLowerCase().includes(fEn.toLowerCase())) return false
    return true
  }), [rows, fUz, fRu, fEn])

  return (
    <div>
      <Toolbar q={q} setQ={setQ} color="#DB2777" total={rows.length} visible={visible.length} onRefresh={load} />
      <div style={{ background: 'white', borderRadius: 14, border: '1px solid #E2E8F0', overflow: 'hidden', boxShadow: '0 2px 10px rgba(0,0,0,.03)' }}>
        {loading ? <Loader /> : visible.length === 0 ? <Empty /> : (
          <div style={{ maxHeight: '70vh', overflowY: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '.88rem' }}>
              <thead style={{ position: 'sticky', top: 0, background: '#FDF2F8', borderBottom: '2px solid #FBCFE8', zIndex: 1 }}>
                <tr>
                  <Th label="№" w={60} />
                  <Th label="🇺🇿 Ўзбекча" />
                  <Th label="🇷🇺 Русский" />
                  <Th label="🇬🇧 English" />
                </tr>
                <tr style={{ background: '#FAFBFC' }}>
                  <th></th>
                  <th style={{ padding: '5px 12px' }}><FilterInput value={fUz} onChange={setFUz} placeholder="🔍 uz" /></th>
                  <th style={{ padding: '5px 12px' }}><FilterInput value={fRu} onChange={setFRu} placeholder="🔍 ru" /></th>
                  <th style={{ padding: '5px 12px' }}><FilterInput value={fEn} onChange={setFEn} placeholder="🔍 en" /></th>
                </tr>
              </thead>
              <tbody>
                {visible.map((r, i) => (
                  <tr key={r.id} style={{ borderBottom: '1px solid #F1F5F9' }}
                    onMouseEnter={e => e.currentTarget.style.background = '#FDF2F8'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                    <td style={{ padding: '11px 14px', color: '#94A3B8', fontWeight: 700 }}>{r.seq_no || i + 1}</td>
                    <td style={{ padding: '11px 14px', fontWeight: 700, color: '#BE185D' }}>{r.uz}</td>
                    <td style={{ padding: '11px 14px', color: '#475569' }}>{r.ru || '—'}</td>
                    <td style={{ padding: '11px 14px', color: '#475569', fontStyle: 'italic' }}>{r.en || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════
// Shared helpers
// ═══════════════════════════════════════════════════
function Toolbar({ q, setQ, color, total, visible, extra, onRefresh }: any) {
  return (
    <div style={{
      background: 'white', borderRadius: 12, padding: 14, marginBottom: 14,
      border: '1px solid #E2E8F0', display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center'
    }}>
      <div style={{ position: 'relative', flex: 1, minWidth: 260 }}>
        <Search size={15} style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: '#94A3B8' }} />
        <input value={q} onChange={e => setQ(e.target.value)} placeholder="Қидирув..."
          style={{ width: '100%', padding: '11px 14px 11px 40px', borderRadius: 10, border: `1.5px solid ${color}33`, background: '#FAFBFC', fontSize: '.88rem', outline: 'none', boxSizing: 'border-box' }} />
      </div>
      {extra}
      <button onClick={onRefresh} style={{ padding: '11px 16px', borderRadius: 10, border: '1px solid #E2E8F0', background: 'white', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, fontSize: '.82rem' }}>
        <RefreshCw size={14} />
      </button>
      <div style={{ fontSize: '.75rem', color: '#64748B', fontWeight: 700, padding: '0 10px' }}>
        {visible < total ? `${visible} / ${total}` : total} та
      </div>
    </div>
  )
}

const Th = ({ label, w }: { label: string; w?: number }) => (
  <th style={{
    padding: '14px 14px', textAlign: 'left', fontWeight: 700, fontSize: '.7rem',
    color: '#64748B', textTransform: 'uppercase', letterSpacing: '.04em',
    ...(w ? { width: w } : {}),
  }}>{label}</th>
)

const FilterInput = ({ value, onChange, placeholder }: any) => (
  <input value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
    style={{ width: '100%', padding: '5px 8px', borderRadius: 6, border: '1px solid #E2E8F0', fontSize: '.72rem', background: 'white', outline: 'none' }} />
)

const Loader = () => (
  <div style={{ padding: 60, textAlign: 'center', color: '#94A3B8' }}>
    <Loader2 className="animate-spin" size={32} style={{ margin: '0 auto 10px' }} />
    <div style={{ fontSize: '.8rem' }}>Юкланмоқда...</div>
  </div>
)

const Empty = () => (
  <div style={{ padding: 60, textAlign: 'center', color: '#94A3B8' }}>
    <Filter size={40} style={{ opacity: 0.2, marginBottom: 10 }} />
    <div style={{ fontSize: '.85rem', fontWeight: 700 }}>Маълумот топилмади</div>
  </div>
)
