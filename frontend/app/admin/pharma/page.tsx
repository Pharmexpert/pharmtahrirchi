'use client'

import React, { useState, useEffect, useMemo } from 'react'
import { Pill, BookOpen, Palette, Search, Loader2, RefreshCw, Filter, Download } from 'lucide-react'
import api from '../../../services/api'

type Tab = 'toc' | 'registry' | 'colors'

/* ── CSS color name → hex mapping for common pharmacopoeia colors ── */
const COLOR_MAP: Record<string, string> = {
  'scarlet': '#FF2400', 'garnet-red': '#733635', 'stable red-orange': '#E25822',
  'violet': '#8B00FF', 'purple-blue': '#4B0082', 'violet-bronze': '#7B5EA7',
  'violet-brown': '#6B3A6B', 'indigo-blue': '#3F51B5', 'violet-blue': '#7366BD',
  'blue': '#0000FF', 'dark blue': '#00008B', 'light blue': '#ADD8E6',
  'sky blue': '#87CEEB', 'azure': '#007FFF', 'cobalt blue': '#0047AB',
  'green': '#008000', 'dark green': '#006400', 'light green': '#90EE90',
  'olive green': '#6B8E23', 'yellow-green': '#9ACD32', 'emerald green': '#50C878',
  'bluish-green': '#009B8D', 'greenish-yellow': '#ADFF2F', 'green-yellow': '#ADFF2F',
  'yellow': '#FFD700', 'dark yellow': '#DAA520', 'light yellow': '#FFFFE0',
  'golden yellow': '#FFD700', 'lemon yellow': '#FFF44F', 'amber': '#FFBF00',
  'pale yellow': '#FFFF99', 'brownish-yellow': '#CC9900', 'brownish yellow': '#CC9900',
  'orange': '#FFA500', 'dark orange': '#FF8C00', 'light orange': '#FFD580',
  'reddish-orange': '#FF5349', 'red-orange': '#FF4500', 'yellowish-orange': '#FFAE42',
  'red': '#FF0000', 'dark red': '#8B0000', 'light red': '#FF6961',
  'cherry red': '#DE3163', 'brick red': '#CB4154', 'brownish-red': '#8B2500',
  'brownish red': '#8B2500', 'reddish-brown': '#A52A2A', 'reddish brown': '#A52A2A',
  'brown': '#8B4513', 'dark brown': '#5C4033', 'light brown': '#C4A484',
  'yellowish-brown': '#996515', 'yellowish brown': '#996515',
  'pink': '#FFC0CB', 'light pink': '#FFB6C1', 'rose': '#FF007F',
  'pale pink': '#FADADD', 'deep pink': '#FF1493', 'rose-pink': '#FF66CC',
  'white': '#F5F5F5', 'off-white': '#FAF9F6', 'cream': '#FFFDD0',
  'gray': '#808080', 'grey': '#808080', 'light gray': '#D3D3D3', 'dark gray': '#A9A9A9',
  'black': '#000000', 'colorless': '#F8F8F8', 'colourless': '#F8F8F8',
  'transparent': '#F0F0F0', 'turbid': '#C8C8C8',
  'purple': '#800080', 'magenta': '#FF00FF', 'fuchsia': '#FF00FF',
  'cyan': '#00FFFF', 'teal': '#008080', 'turquoise': '#40E0D0',
  'coral': '#FF7F50', 'salmon': '#FA8072', 'peach': '#FFCBA4',
  'lavender': '#E6E6FA', 'mauve': '#E0B0FF', 'lilac': '#C8A2C8',
  'maroon': '#800000', 'burgundy': '#800020', 'crimson': '#DC143C',
  'gold': '#FFD700', 'silver': '#C0C0C0', 'bronze': '#CD7F32',
  'tan': '#D2B48C', 'khaki': '#C3B091', 'beige': '#F5F5DC',
  'ivory': '#FFFFF0', 'charcoal': '#36454F', 'slate': '#708090',
  'olive': '#808000', 'lime': '#00FF00', 'aqua': '#00FFFF',
  'navy': '#000080', 'rust': '#B7410E', 'copper': '#B87333',
  'wine': '#722F37', 'plum': '#DDA0DD', 'mint': '#98FF98',
  'moss': '#8A9A5B', 'pine': '#01796F', 'forest': '#228B22',
  'chocolate': '#7B3F00', 'coffee': '#6F4E37', 'caramel': '#FFD59A',
  'honey': '#EB9605', 'sand': '#C2B280', 'wheat': '#F5DEB3',
  'straw': '#E4D96F', 'lemon': '#FFF44F', 'canary': '#FFEF00',
  'apricot': '#FBCEB1', 'tangerine': '#FF9966', 'pumpkin': '#FF7518',
  'cherry': '#DE3163', 'ruby': '#E0115F', 'garnet': '#733635',
  'claret': '#7F1734', 'raspberry': '#E30B5C', 'strawberry': '#FC5A8D',
  'tomato': '#FF6347', 'flame': '#E25822', 'vermilion': '#E34234',
  'cinnabar': '#E44D2E', 'carmine': '#960018',
  'pale': '#FAFAD2', 'faint': '#F5F5F5', 'weak': '#F0F0F0',
  'intense': '#FF4500', 'bright': '#FFFF00', 'deep': '#8B0000',
  'dark': '#2F4F4F', 'light': '#FAFAFA', 'vivid': '#FF6347',
  'stable red': '#CC3333', 'pure blue': '#0000FF', 'pure red': '#FF0000',
  'pure yellow': '#FFFF00', 'pure green': '#00FF00',
  'pale greenish-yellow': '#CCFF99', 'pale greenish yellow': '#CCFF99',
  'brownish-green': '#6B6B3E', 'brownish green': '#6B6B3E',
}

function resolveColor(enName: string): string | null {
  if (!enName) return null
  const lower = enName.toLowerCase().trim()
  if (COLOR_MAP[lower]) return COLOR_MAP[lower]
  // Try partial match — find the longest matching key
  let best: string | null = null
  let bestLen = 0
  for (const [key, hex] of Object.entries(COLOR_MAP)) {
    if (lower.includes(key) && key.length > bestLen) {
      best = hex
      bestLen = key.length
    }
  }
  return best
}

function colorHexCode(enName: string): string {
  const hex = resolveColor(enName)
  return hex || '—'
}

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
        exportUrl={api.admin.pharmaTocExportUrl()}
        exportName="df_mundarijasi.xlsx"
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
      <Toolbar q={q} setQ={setQ} color="#8B5E3C" total={rows.length} visible={visible.length} onRefresh={load}
        exportUrl={api.admin.pharmaRegistryExportUrl()}
        exportName="davlat_reestri.xlsx"
      />
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
                    <td style={{ padding: '10px 12px', color: '#475569', fontSize: '.72rem' }}>{(r.dosage_form || '').slice(0, 80)}{(r.dosage_form || '').length > 80 ? '...' : ''}</td>
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
      <Toolbar q={q} setQ={setQ} color="#DB2777" total={rows.length} visible={visible.length} onRefresh={load}
        exportUrl={api.admin.pharmaColorsExportUrl()}
        exportName="ranglar_jadvali.xlsx"
      />
      <div style={{ background: 'white', borderRadius: 14, border: '1px solid #E2E8F0', overflow: 'hidden', boxShadow: '0 2px 10px rgba(0,0,0,.03)' }}>
        {loading ? <Loader /> : visible.length === 0 ? <Empty /> : (
          <div style={{ maxHeight: '70vh', overflowY: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '.88rem' }}>
              <thead style={{ position: 'sticky', top: 0, background: '#FDF2F8', borderBottom: '2px solid #FBCFE8', zIndex: 1 }}>
                <tr>
                  <Th label="№" w={50} />
                  <Th label="Ранг" w={44} />
                  <Th label="Ранг коди" w={90} />
                  <Th label="🇺🇿 Ўзбекча" />
                  <Th label="🇷🇺 Русский" />
                  <Th label="🇬🇧 English" />
                </tr>
                <tr style={{ background: '#FAFBFC' }}>
                  <th></th>
                  <th></th>
                  <th></th>
                  <th style={{ padding: '5px 12px' }}><FilterInput value={fUz} onChange={setFUz} placeholder="🔍 uz" /></th>
                  <th style={{ padding: '5px 12px' }}><FilterInput value={fRu} onChange={setFRu} placeholder="🔍 ru" /></th>
                  <th style={{ padding: '5px 12px' }}><FilterInput value={fEn} onChange={setFEn} placeholder="🔍 en" /></th>
                </tr>
              </thead>
              <tbody>
                {visible.map((r, i) => {
                  const hex = resolveColor(r.en)
                  const code = colorHexCode(r.en)
                  return (
                    <tr key={r.id} style={{ borderBottom: '1px solid #F1F5F9' }}
                      onMouseEnter={e => e.currentTarget.style.background = '#FDF2F8'}
                      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                      <td style={{ padding: '8px 14px', color: '#94A3B8', fontWeight: 700 }}>{r.seq_no || i + 1}</td>
                      <td style={{ padding: '8px 6px' }}>
                        {hex ? (
                          <div style={{
                            width: 32, height: 22, borderRadius: 4,
                            background: hex,
                            border: '1px solid rgba(0,0,0,.12)',
                          }} title={r.en} />
                        ) : (
                          <div style={{
                            width: 32, height: 22, borderRadius: 4,
                            background: '#F1F5F9',
                            border: '1px dashed #CBD5E1',
                          }} />
                        )}
                      </td>
                      <td style={{ padding: '8px 10px', fontFamily: 'monospace', fontSize: '.72rem', color: hex ? '#475569' : '#CBD5E1', fontWeight: 600 }}>
                        {code}
                      </td>
                      <td style={{ padding: '8px 14px', fontWeight: 700, color: '#BE185D' }}>{r.uz}</td>
                      <td style={{ padding: '8px 14px', color: '#475569' }}>{r.ru || '—'}</td>
                      <td style={{ padding: '8px 14px', color: '#475569', fontStyle: 'italic' }}>{r.en || '—'}</td>
                    </tr>
                  )
                })}
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
function downloadXlsx(url: string, filename: string) {
  const token = typeof window !== 'undefined' ? localStorage.getItem('pharma_token') : null
  fetch(url, { headers: token ? { 'Authorization': `Bearer ${token}` } : {} })
    .then(r => { if (!r.ok) throw new Error('Download failed'); return r.blob() })
    .then(blob => {
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = filename
      a.click()
      URL.revokeObjectURL(a.href)
    })
    .catch(e => alert(`Юклаб олишда хатолик: ${e.message}`))
}

function Toolbar({ q, setQ, color, total, visible, extra, onRefresh, exportUrl, exportName }: any) {
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
      {exportUrl && (
        <button onClick={() => downloadXlsx(exportUrl, exportName || 'export.xlsx')}
          title="XLSX юклаб олиш"
          style={{ padding: '11px 16px', borderRadius: 10, border: `1.5px solid ${color}44`, background: `${color}08`, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, fontSize: '.82rem', color, fontWeight: 700, transition: 'all .15s' }}>
          <Download size={14} /> XLSX
        </button>
      )}
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
