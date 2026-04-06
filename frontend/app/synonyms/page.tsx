'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { Repeat2, Search, Plus, Trash2, Loader2, CheckCircle2, AlertCircle, X, RefreshCw, Languages, Download } from 'lucide-react'
import { useAuth } from '../../components/LoginGuard'
import * as XLSX from 'xlsx'
import api from '../../services/api'

interface SynEntry { id: number; synonym: string; frequency: number; source: string }
interface SynGroup { word: string; lang: string; synonyms: SynEntry[]; total_freq: number; ids: number[] }

export default function SynonymsPage() {
  const { token, user } = useAuth()
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const [groups, setGroups] = useState<SynGroup[]>([])
  const [totalSynonyms, setTotalSynonyms] = useState(0)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [lang, setLang] = useState<string>('')
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null)
  const [showAdd, setShowAdd] = useState(false)
  const [newWord, setNewWord] = useState('')
  const [newSynonym, setNewSynonym] = useState('')
  const [newLang, setNewLang] = useState('uz')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editValue, setEditValue] = useState('')
  const [editingWord, setEditingWord] = useState<string | null>(null)
  const [editWordValue, setEditWordValue] = useState('')
  const [page, setPage] = useState(0)
  const [perPage, setPerPage] = useState(25)

  const showToast = (msg: string, type: 'success' | 'error' = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3000)
  }

  const fetchSynonyms = useCallback(async () => {
    setLoading(true)
    try {
      const d = await api.synonyms.listGrouped(search || undefined, lang || undefined)
      setGroups((d as any).groups || [])
      setTotalSynonyms((d as any).total_synonyms || 0)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }, [search, lang])

  useEffect(() => { fetchSynonyms() }, [fetchSynonyms])

  const handleAdd = async () => {
    if (!newWord.trim() || !newSynonym.trim()) return
    try {
      await api.synonyms.save(newWord, newSynonym, newLang)
      showToast('Синоним қўшилди ✓')
      setNewWord(''); setNewSynonym(''); setShowAdd(false)
      fetchSynonyms()
    } catch { showToast('Хатолик', 'error') }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Синонимни ўчиришни тасдиқлайсизми?')) return
    try {
      await api.synonyms.delete(id)
      showToast('Ўчирилди ✓')
      fetchSynonyms()
    } catch { showToast('Хатолик', 'error') }
  }

  const handleEdit = async (id: number, newSyn: string) => {
    if (!newSyn.trim()) return
    try {
      await api.synonyms.update(id, { synonym: newSyn.trim() })
      showToast('Таҳрирланди ✓')
      setEditingId(null)
      fetchSynonyms()
    } catch { showToast('Хатолик', 'error') }
  }

  const handleEditWord = async (oldWord: string, newWord: string, lang: string) => {
    if (!newWord.trim()) return
    try {
      const group = groups.find(g => g.word === oldWord && g.lang === lang)
      if (group) {
        for (const id of group.ids) {
          await api.synonyms.update(id, { word: newWord.trim() })
        }
      }
      showToast('Сўз таҳрирланди ✓')
      setEditingWord(null)
      fetchSynonyms()
    } catch { showToast('Хатолик', 'error') }
  }

  const filtered = groups
  const totalPages = Math.ceil(filtered.length / perPage)
  const pageData = filtered.slice(page * perPage, (page + 1) * perPage)

  const langLabel = (l: string) => l === 'uz' ? '🇺🇿 UZ' : l === 'ru' ? '🇷🇺 RU' : l === 'en' ? '🇬🇧 EN' : l
  const langColor = (l: string) => l === 'uz' ? '#16A34A' : l === 'ru' ? '#2563EB' : l === 'en' ? '#9333EA' : '#666'

  return (
    <div>
      {toast && (
        <div style={{
          position: 'fixed', bottom: 32, right: 32, zIndex: 2000,
          padding: '14px 24px', borderRadius: '12px', fontWeight: 700,
          background: toast.type === 'success' ? '#16A34A' : '#DC2626',
          color: 'white', display: 'flex', alignItems: 'center', gap: '10px',
          boxShadow: '0 8px 24px rgba(0,0,0,0.15)'
        }}>
          {toast.type === 'success' ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
          {toast.msg}
        </div>
      )}

      {/* Hero */}
      <div style={{
        background: 'linear-gradient(135deg, #F0FDF4 0%, #ECFDF5 100%)', borderRadius: '20px',
        padding: '32px 36px', border: '1.5px solid #BBF7D0', marginBottom: '28px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '20px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <div style={{
            width: 52, height: 52, borderRadius: '14px',
            background: 'linear-gradient(135deg, #16A34A 0%, #059669 100%)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 4px 16px rgba(22,163,74,0.3)'
          }}>
            <Repeat2 size={24} color="white" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.7rem', fontWeight: 800, marginBottom: '4px' }}>Синонимлар базаси</h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 0 }}>
              3 тилда (EN/RU/UZ) синонимлар • <strong>{filtered.length}</strong> сўз • <strong>{totalSynonyms}</strong> синоним
            </p>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button onClick={() => {
            const ws = XLSX.utils.json_to_sheet(filtered.map((g: SynGroup, i: number) => ({
              '№': i + 1, 'Сўз': g.word, 'Синонимлар': g.synonyms.map(s => s.synonym).join(', '),
              'Тил': g.lang, 'Сони': g.synonyms.length, 'Жами частота': g.total_freq
            })))
            const wb = XLSX.utils.book_new()
            XLSX.utils.book_append_sheet(wb, ws, 'Синонимлар')
            XLSX.writeFile(wb, `synonyms_${new Date().toISOString().slice(0,10)}.xlsx`)
          }} style={{
            padding: '8px 16px', borderRadius: '10px', border: '1.5px solid #93C5FD',
            background: 'white', color: '#2563EB', fontWeight: 700, fontSize: '0.8rem', cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: '6px'
          }}><Download size={14} /> XLSX</button>
          <button onClick={fetchSynonyms} style={{
            padding: '8px 16px', borderRadius: '10px', border: '1.5px solid #BBF7D0',
            background: 'white', color: '#16A34A', fontWeight: 700, fontSize: '0.8rem', cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: '6px'
          }}><RefreshCw size={14} /> Янгилаш</button>
          <button onClick={() => setShowAdd(true)} style={{
            padding: '10px 22px', borderRadius: '12px', border: 'none',
            background: 'linear-gradient(135deg, #16A34A, #059669)', color: 'white',
            fontWeight: 800, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px',
            fontSize: '0.85rem', boxShadow: '0 4px 16px rgba(22,163,74,0.4)'
          }}><Plus size={16} /> СИНОНИМ ҚЎШИШ</button>
        </div>
      </div>

      {/* Filters */}
      <div style={{ marginBottom: '20px', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: '200px' }}>
          <Search size={15} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input placeholder="Сўз бўйича қидириш..." value={search} onChange={e => { setSearch(e.target.value); setPage(0) }}
            style={{
              width: '100%', padding: '12px 14px 12px 40px', borderRadius: '12px',
              border: '1.5px solid var(--border)', background: 'var(--bg-card)',
              fontSize: '0.9rem', outline: 'none', boxSizing: 'border-box'
            }} />
        </div>
        {['', 'uz', 'ru', 'en'].map(l => (
          <button key={l} onClick={() => { setLang(l); setPage(0) }} style={{
            padding: '10px 18px', borderRadius: '10px',
            border: lang === l ? '2px solid #16A34A' : '1.5px solid var(--border)',
            background: lang === l ? '#F0FDF4' : 'var(--bg-card)',
            color: lang === l ? '#16A34A' : 'var(--text-primary)',
            fontWeight: 700, fontSize: '0.82rem', cursor: 'pointer'
          }}>{l === '' ? 'Барчаси' : langLabel(l)}</button>
        ))}
      </div>

      {/* Table */}
      <div style={{ background: 'var(--bg-card)', borderRadius: '16px', border: '1px solid var(--border)', overflow: 'hidden', boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
        {loading ? (
          <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <Loader2 size={28} style={{ animation: 'spin 1s linear infinite', marginBottom: 12 }} />
            <p>Юкланмоқда...</p>
          </div>
        ) : pageData.length === 0 ? (
          <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <Repeat2 size={40} style={{ opacity: 0.2, marginBottom: 12 }} />
            <p style={{ fontWeight: 700 }}>Синонимлар топилмади</p>
          </div>
        ) : (
          <>
            <div style={{
              display: 'grid', gridTemplateColumns: '50px 200px 1fr 80px 80px 60px',
              padding: '14px 20px', background: 'var(--bg-secondary)', borderBottom: '2px solid var(--border)', gap: '12px'
            }}>
              {['№', 'СЎЗ', 'СИНОНИМЛАР', 'ТИЛ', 'СОНИ', ''].map(h => (
                <span key={h} style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>{h}</span>
              ))}
            </div>
            {pageData.map((g: SynGroup, i: number) => (
              <div key={`${g.word}-${g.lang}`} style={{
                display: 'grid', gridTemplateColumns: '50px 200px 1fr 80px 80px 60px',
                padding: '14px 20px', borderBottom: '1px solid var(--border)', gap: '12px', alignItems: 'flex-start',
                transition: 'background 0.15s'
              }}
                onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = 'var(--bg-secondary)'}
                onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = ''}
              >
                <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)', paddingTop: '4px' }}>{page * perPage + i + 1}</span>
                {editingWord === `${g.word}:${g.lang}` ? (
                  <div style={{ display: 'flex', gap: '4px', paddingTop: '2px' }}>
                    <input value={editWordValue} onChange={e => setEditWordValue(e.target.value)}
                      style={{ padding: '4px 8px', borderRadius: '6px', border: '1.5px solid #B48C64', fontSize: '0.85rem', fontWeight: 700, width: '150px' }}
                      autoFocus onKeyDown={e => { if (e.key === 'Enter') handleEditWord(g.word, editWordValue, g.lang); if (e.key === 'Escape') setEditingWord(null) }}
                    />
                    <button onClick={() => handleEditWord(g.word, editWordValue, g.lang)} style={{ padding: '2px 8px', borderRadius: '6px', border: 'none', background: '#B48C64', color: 'white', fontSize: '0.7rem', cursor: 'pointer' }}>✓</button>
                    <button onClick={() => setEditingWord(null)} style={{ padding: '2px 6px', borderRadius: '6px', border: '1px solid #ccc', background: 'white', fontSize: '0.7rem', cursor: 'pointer' }}>✕</button>
                  </div>
                ) : (
                  <span style={{ fontWeight: 700, fontSize: '0.9rem', paddingTop: '4px', cursor: 'pointer' }}
                    onClick={() => { setEditingWord(`${g.word}:${g.lang}`); setEditWordValue(g.word) }}
                    title="Таҳрирлаш учун босинг"
                  >{g.word}</span>
                )}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {g.synonyms.sort((a,b) => b.frequency - a.frequency).map((s) => (
                    editingId === s.id ? (
                      <div key={s.id} style={{ display: 'flex', gap: '4px' }}>
                        <input value={editValue} onChange={e => setEditValue(e.target.value)}
                          style={{ padding: '4px 8px', borderRadius: '6px', border: '1.5px solid #16A34A', fontSize: '0.8rem', width: '120px' }}
                          autoFocus onKeyDown={e => { if (e.key === 'Enter') handleEdit(s.id, editValue); if (e.key === 'Escape') setEditingId(null) }}
                        />
                        <button onClick={() => handleEdit(s.id, editValue)} style={{ padding: '2px 8px', borderRadius: '6px', border: 'none', background: '#16A34A', color: 'white', fontSize: '0.7rem', cursor: 'pointer' }}>✓</button>
                        <button onClick={() => setEditingId(null)} style={{ padding: '2px 6px', borderRadius: '6px', border: '1px solid #ccc', background: 'white', fontSize: '0.7rem', cursor: 'pointer' }}>✕</button>
                      </div>
                    ) : (
                      <span key={s.id} style={{
                        padding: '4px 10px', borderRadius: '8px', fontSize: '0.8rem', fontWeight: 600,
                        background: s.frequency > 5 ? '#DCFCE7' : s.frequency > 0 ? '#FEF3C7' : '#F1F5F9',
                        color: s.frequency > 5 ? '#16A34A' : s.frequency > 0 ? '#D97706' : '#64748B',
                        cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '4px',
                        border: `1px solid ${s.frequency > 5 ? '#BBF7D0' : s.frequency > 0 ? '#FDE68A' : '#E2E8F0'}`,
                        transition: 'all 0.15s'
                      }}
                        onClick={() => { setEditingId(s.id); setEditValue(s.synonym) }}
                        title={`Частота: ${s.frequency} | Манба: ${s.source} | Таҳрирлаш учун босинг`}
                      >
                        {s.synonym}
                        {s.frequency > 0 && <span style={{ fontSize: '0.6rem', opacity: 0.7 }}>{s.frequency}×</span>}
                        <span onClick={e => { e.stopPropagation(); if (confirm(`"${s.synonym}" ни ўчирасизми?`)) handleDelete(s.id) }}
                          style={{ marginLeft: '2px', opacity: 0.4, cursor: 'pointer', fontSize: '0.7rem' }}
                          title="Ўчириш"
                        >✕</span>
                      </span>
                    )
                  ))}
                  <button onClick={() => { setNewWord(g.word); setNewLang(g.lang); setNewSynonym(''); setShowAdd(true) }}
                    style={{ padding: '4px 8px', borderRadius: '8px', border: '1px dashed #BBF7D0', background: 'transparent', color: '#16A34A', fontSize: '0.75rem', cursor: 'pointer', fontWeight: 700 }}
                    title="Янги синоним қўшиш"
                  >+ қўшиш</button>
                </div>
                <span style={{
                  fontSize: '0.72rem', fontWeight: 700, padding: '4px 8px', borderRadius: '6px',
                  background: `${langColor(g.lang)}15`, color: langColor(g.lang), display: 'inline-block'
                }}>{langLabel(g.lang)}</span>
                <span style={{ fontSize: '0.85rem', fontWeight: 800, color: '#16A34A', paddingTop: '4px' }}>{g.synonyms.length}</span>
                <button onClick={() => g.ids.forEach(id => handleDelete(id))} style={{
                  padding: '6px', borderRadius: '8px', border: '1px solid #FECACA',
                  background: '#FEF2F2', color: '#DC2626', cursor: 'pointer'
                }}><Trash2 size={14} /></button>
              </div>
            ))}
          </>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', marginTop: '20px', flexWrap: 'wrap' }}>
          <button disabled={page === 0} onClick={() => setPage(p => p - 1)} style={{
            padding: '8px 16px', borderRadius: '8px', border: '1px solid var(--border)',
            background: page === 0 ? '#F1F5F9' : 'white', cursor: page === 0 ? 'default' : 'pointer',
            fontWeight: 700, fontSize: '0.82rem', color: page === 0 ? '#94A3B8' : '#334155'
          }}>← Олдинги</button>
          <span style={{ padding: '8px 16px', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)' }}>
            {page + 1} / {totalPages} ({filtered.length} та)
          </span>
          <button disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)} style={{
            padding: '8px 16px', borderRadius: '8px', border: '1px solid var(--border)',
            background: page >= totalPages - 1 ? '#F1F5F9' : 'white', cursor: page >= totalPages - 1 ? 'default' : 'pointer',
            fontWeight: 700, fontSize: '0.82rem', color: page >= totalPages - 1 ? '#94A3B8' : '#334155'
          }}>Кейинги →</button>
          <select value={perPage} onChange={e => { setPerPage(Number(e.target.value)); setPage(0) }} style={{
            padding: '6px 12px', borderRadius: '8px', border: '1px solid var(--border)',
            fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-secondary)', cursor: 'pointer'
          }}>
            <option value={25}>25 / бет</option>
            <option value={50}>50 / бет</option>
            <option value={100}>100 / бет</option>
          </select>
        </div>
      )}

      {/* Add Modal */}
      {showAdd && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(4px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}>
          <div style={{
            background: 'var(--bg-card)', borderRadius: '20px', padding: '32px', width: '100%', maxWidth: '480px',
            boxShadow: '0 24px 64px rgba(0,0,0,0.25)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
              <h3 style={{ fontWeight: 800, fontSize: '1.1rem' }}>Синоним қўшиш</h3>
              <button onClick={() => setShowAdd(false)} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
                <X size={20} />
              </button>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <input placeholder="Сўз..." value={newWord} onChange={e => setNewWord(e.target.value)}
                style={{ padding: '12px', borderRadius: '10px', border: '1.5px solid var(--border)', fontSize: '0.9rem' }} />
              <input placeholder="Синоним..." value={newSynonym} onChange={e => setNewSynonym(e.target.value)} autoFocus
                style={{ padding: '12px', borderRadius: '10px', border: '1.5px solid var(--border)', fontSize: '0.9rem' }}
                onKeyDown={e => { if (e.key === 'Enter') handleAdd() }} />
              <select value={newLang} onChange={e => setNewLang(e.target.value)}
                style={{ padding: '12px', borderRadius: '10px', border: '1.5px solid var(--border)', fontSize: '0.9rem' }}>
                <option value="uz">🇺🇿 Ўзбекча</option>
                <option value="ru">🇷🇺 Русча</option>
                <option value="en">🇬🇧 Инглизча</option>
              </select>
              <button onClick={handleAdd} style={{
                padding: '14px', borderRadius: '12px', border: 'none',
                background: 'linear-gradient(135deg, #16A34A, #059669)', color: 'white',
                fontWeight: 800, fontSize: '0.9rem', cursor: 'pointer'
              }}>Сақлаш</button>
            </div>
          </div>
        </div>
      )}

      <style jsx global>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  )
}
