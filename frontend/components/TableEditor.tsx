'use client'

import React from 'react'
import { Save, Sparkles, Loader2, Plus, Trash2, Search } from 'lucide-react'
import type { RowData } from '../types/api'
import SynonymPopup from './editor/SynonymPopup'
import TermHighlighter from './editor/TermHighlighter'
import RichContent from './editor/RichContent'
import LangCell from './editor/LangCell'
import TableToolbar from './editor/TableToolbar'
import { useTableEditor } from './editor/useTableEditor'

export type { RowData }

interface Props {
  initialData: RowData[]
  filename: string
  textId?: string
}

export default function TableEditor({ initialData, filename, textId = '' }: Props) {
  const editor = useTableEditor({ initialData, filename, textId })
  const {
    token, API_BASE, authHeaders,
    data, setData,
    savingRow, improvingRow,
    dragIdx, dropIdx, popup, setPopup,
    isLinguisticLoading, linguisticProgress,
    showSourceLangModal, setShowSourceLangModal,
    linguisticPreview, setLinguisticPreview,
    linguisticSearchQuery, setLinguisticSearchQuery,
    isBatchPolishing, batchSummary, setBatchSummary,
    terms, colWidths,
    notify, update, insertRowAfter,
    handleDragStart, handleDragOver, handleDragLeave, handleDrop, handleDragEnd,
    deleteRow, handleWordClick, applyVariant, handleBlockDrop,
    improveRow, saveSingleRow, startLinguisticAnalysis,
    confirmSaveLinguisticItems, searchLinguisticDatabase,
    onMagicSplit, startResizing,
  } = editor

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', fontFamily: "'Inter','Segoe UI',sans-serif", background: '#f1f5f9' }}>

      <TableToolbar
        textId={textId}
        filename={filename}
        API_BASE={API_BASE}
        showSourceLangModal={editor.showSourceLangModal}
        saveStatus={editor.saveStatus}
        isBatchPolishing={editor.isBatchPolishing}
        isAiAligning={editor.isAiAligning}
        savingAll={editor.savingAll}
        isFinishing={editor.isFinishing}
        handleLinguisticBtnClick={editor.handleLinguisticBtnClick}
        batchTransliterate={editor.batchTransliterate}
        runBatchSayqallash={editor.runBatchSayqallash}
        aiAlign={editor.aiAlign}
        handleSaveAll={editor.handleSaveAll}
        finishWork={editor.finishWork}
        handleExport={editor.handleExport}
      />

      {/* Progress Modal (Batch Polishing / AI Analysis) */}
      {(isLinguisticLoading || isBatchPolishing) && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(15, 23, 42, 0.7)', backdropFilter: 'blur(4px)', zIndex: 10000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ background: 'white', padding: '30px', borderRadius: 20, width: '400px', textAlign: 'center', boxShadow: '0 20px 50px rgba(0,0,0,0.3)' }}>
            <h3 style={{ margin: '0 0 15px 0', fontSize: '1.1rem', color: '#1e293b' }}>
              {isBatchPolishing ? 'Ҳужжат сайқалланмоқда...' : 'Мантиқий таҳлил олиб борилмоқда...'}
            </h3>
            <div style={{ height: '10px', background: '#e2e8f0', borderRadius: 10, overflow: 'hidden', marginBottom: '10px', position: 'relative' }}>
              <div style={{ height: '100%', width: `${linguisticProgress}%`, background: 'linear-gradient(90deg, #059669, #10b981)', transition: 'width 0.3s ease' }} />
            </div>
            <span style={{ fontSize: '0.9rem', fontWeight: 800, color: '#059669' }}>{Math.round(linguisticProgress)}%</span>
            <p style={{ margin: '15px 0 0 0', fontSize: '0.75rem', color: '#64748b' }}>
              {isBatchPolishing ? 'Барча қаторлар автоматик тузатилмоқда' : 'Бутун ҳужжат бўйича қидирилмоқда'}
            </p>
          </div>
        </div>
      )}

      {/* Batch Summary Modal */}
      {batchSummary && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(15, 23, 42, 0.7)', backdropFilter: 'blur(4px)', zIndex: 10000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ background: 'white', padding: '30px', borderRadius: 20, width: '450px', textAlign: 'center', boxShadow: '0 25px 60px rgba(0,0,0,0.4)' }}>
            <div style={{ background: '#dcfce7', width: '60px', height: '60px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px' }}>
              <Sparkles size={30} color="#16a34a" />
            </div>
            <h3 style={{ margin: '0 0 10px 0', fontSize: '1.3rem', color: '#1e293b' }}>Сайқаллаш якунланди!</h3>
            <p style={{ color: '#64748b', fontSize: '0.9rem', marginBottom: '25px' }}>Ҳужжат тўлиқ таҳлил қилинди ва тузатишлар киритилди.</p>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px', marginBottom: '30px' }}>
              <div style={{ background: '#f8fafc', padding: '15px', borderRadius: 12 }}>
                <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#1e293b' }}>{batchSummary.total}</div>
                <div style={{ fontSize: '0.65rem', color: '#64748b', textTransform: 'uppercase' }}>Қаторлар</div>
              </div>
              <div style={{ background: '#f0fdf4', padding: '15px', borderRadius: 12, border: '1px solid #dcfce7' }}>
                <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#16a34a' }}>{batchSummary.corrected}</div>
                <div style={{ fontSize: '0.65rem', color: '#16a34a', textTransform: 'uppercase' }}>Тузатилди</div>
              </div>
              <div style={{ background: '#f5f3ff', padding: '15px', borderRadius: 12, border: '1px solid #ddd6fe' }}>
                <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#7c3aed' }}>{batchSummary.annotations}</div>
                <div style={{ fontSize: '0.65rem', color: '#7c3aed', textTransform: 'uppercase' }}>Хатолар</div>
              </div>
            </div>

            <button onClick={() => setBatchSummary(null)} style={{ width: '100%', padding: '12px', background: '#1e293b', color: 'white', border: 'none', borderRadius: 10, fontWeight: 700, cursor: 'pointer' }}>
              Натижаларни кўриш
            </button>
          </div>
        </div>
      )}

      {/* Source Language Selection Modal */}
      {showSourceLangModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(15, 23, 42, 0.6)', zIndex: 10000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ background: 'white', padding: '25px', borderRadius: 15, width: '400px', boxShadow: '0 10px 40px rgba(0,0,0,0.2)' }}>
            <h3 style={{ margin: '0 0 10px 0', fontSize: '1.1rem', color: '#1e293b', textAlign: 'center' }}>Лингвистик режим</h3>
            <p style={{ fontSize: '0.8rem', color: '#64748b', textAlign: 'center', marginBottom: '20px' }}>
              Танланган категория: <span style={{ fontWeight: 800, color: '#6366f1' }}>{showSourceLangModal === 'annotated' ? 'Изоҳли луғат' : showSourceLangModal === 'disputed' ? 'Мунозарали' : 'Қисқартмалар'}</span>
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ border: '1.5px solid #6366f1', borderRadius: 12, padding: '12px', background: '#f5f3ff', marginBottom: 10 }}>
                <span style={{ fontSize: '0.7rem', fontWeight: 800, color: '#6366f1', textTransform: 'uppercase', display: 'block', marginBottom: 8 }}>Базадан қидириш (4,365+ та)</span>
                <div style={{ display: 'flex', gap: 6 }}>
                  <input
                    type="text"
                    placeholder="Калит сўзни ёзинг..."
                    value={linguisticSearchQuery}
                    onChange={e => setLinguisticSearchQuery(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && searchLinguisticDatabase(showSourceLangModal, linguisticSearchQuery)}
                    style={{ flex: 1, padding: '8px 12px', borderRadius: 8, border: '1px solid #ddd', fontSize: '0.85rem', outline: 'none' }}
                  />
                  <button onClick={() => searchLinguisticDatabase(showSourceLangModal, linguisticSearchQuery)} style={{ padding: '8px 15px', background: '#6366f1', color: 'white', border: 'none', borderRadius: 8, fontWeight: 700, cursor: 'pointer' }}>
                    <Search size={16} />
                  </button>
                </div>
              </div>

              <div style={{ border: '1px solid #e2e8f0', borderRadius: 12, padding: '12px', background: '#f8fafc' }}>
                <span style={{ fontSize: '0.7rem', fontWeight: 800, color: '#64748b', textTransform: 'uppercase', display: 'block', marginBottom: 8 }}>АИ Таҳлил (Янгиларни топиш)</span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <button onClick={() => startLinguisticAnalysis('English')} style={{ padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: 8, background: 'white', fontWeight: 700, cursor: 'pointer', textAlign: 'left', display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                    <span>English (Original) бўйича таҳлил</span>
                    <span style={{ color: '#6366f1' }}>🤖</span>
                  </button>
                  <button onClick={() => startLinguisticAnalysis('Russian')} style={{ padding: '10px 12px', border: '1px solid #e2e8f0', borderRadius: 8, background: 'white', fontWeight: 700, cursor: 'pointer', textAlign: 'left', display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                    <span>Русча бўйича таҳлил</span>
                    <span style={{ color: '#6366f1' }}>🤖</span>
                  </button>
                </div>
              </div>

              <button onClick={() => setShowSourceLangModal(null)} style={{ marginTop: '5px', padding: '10px', background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: '0.8rem' }}>Бекор қилиш</button>
            </div>
          </div>
        </div>
      )}

      {/* Preview Modal */}
      {linguisticPreview && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(15, 23, 42, 0.8)', zIndex: 10000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ background: 'white', padding: '0', borderRadius: 15, width: '90%', maxWidth: '900px', maxHeight: '85vh', overflow: 'hidden', display: 'flex', flexDirection: 'column', boxShadow: '0 25px 60px rgba(0,0,0,0.4)' }}>
            <div style={{ padding: '15px 20px', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#f8fafc' }}>
              <h3 style={{ margin: 0, fontSize: '1rem', color: '#1e293b' }}>
                {linguisticPreview.mode === 'db' ? 'Базадан топилган натижалар' : 'AI Таҳлил натижалари'}: <span style={{ textTransform: 'capitalize', color: '#6366f1' }}>{linguisticPreview.category === 'annotated' ? 'Изоҳли' : linguisticPreview.category === 'disputed' ? 'Мунозарали' : 'Қисқартмалар'}</span>
              </h3>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                {linguisticPreview.mode === 'db' && (
                  <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Жами: <b>{linguisticPreview.results.length}</b> та</span>
                )}
                <button onClick={() => setLinguisticPreview(null)} style={{ background: 'none', border: 'none', fontSize: '1.2rem', cursor: 'pointer', color: '#94a3b8' }}>✕</button>
              </div>
            </div>
            <div style={{ flex: 1, overflow: 'auto', padding: '20px' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                <thead>
                  <tr style={{ textAlign: 'left', borderBottom: '2px solid #e2e8f0' }}>
                    <th style={{ padding: '10px' }}>EN</th>
                    <th style={{ padding: '10px' }}>RU</th>
                    <th style={{ padding: '10px' }}>UZ</th>
                    <th style={{ padding: '10px' }}>Изоҳ / Контекст</th>
                    <th style={{ padding: '10px', width: '80px' }}>Ҳолат</th>
                  </tr>
                </thead>
                <tbody>
                  {linguisticPreview.results.map((item, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid #f1f5f9', background: item.is_duplicate ? '#fffbeb' : 'white' }}>
                      <td style={{ padding: '10px', fontWeight: 600 }}>{item.en || item.short_form}</td>
                      <td style={{ padding: '10px' }}>{item.ru || item.long_ru}</td>
                      <td style={{ padding: '10px' }}>{item.uz || item.long_uz}</td>
                      <td style={{ padding: '10px', fontSize: '0.75rem', color: '#64748b' }}>
                        {item.description_en || item.context_en || item.long_en}
                      </td>
                      <td style={{ padding: '10px' }}>
                        {item.is_duplicate
                          ? <span style={{ color: '#d97706', fontSize: '0.65rem', fontWeight: 700, background: '#fef3c7', padding: '2px 5px', borderRadius: 4 }}>бор</span>
                          : <span style={{ color: '#16a34a', fontSize: '0.65rem', fontWeight: 700, background: '#dcfce7', padding: '2px 5px', borderRadius: 4 }}>янги</span>
                        }
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{ padding: '15px 20px', borderTop: '1px solid #e2e8f0', textAlign: 'right', background: '#f8fafc' }}>
              <button onClick={() => setLinguisticPreview(null)} style={{ padding: '8px 15px', marginRight: '10px', borderRadius: 8, border: '1px solid #e2e8f0', background: 'white', cursor: 'pointer' }}>Ёпиш</button>
              {linguisticPreview.mode !== 'db' && (
                <button onClick={confirmSaveLinguisticItems} style={{ padding: '8px 25px', borderRadius: 8, border: 'none', background: '#6366f1', color: 'white', fontWeight: 700, cursor: 'pointer' }}>БАРЧАСИНИ САҚЛАШ</button>
              )}
            </div>
          </div>
        </div>
      )}

      <div style={{ flex: 1, overflow: 'hidden', display: 'flex' }}>
        <div style={{ flex: 1, overflow: 'auto' }}>
          <table id="main-table" style={{ minWidth: 920, width: '100%', borderCollapse: 'collapse', tableLayout: 'fixed', display: 'table' }}>
          <colgroup>
            <col style={{ width: 32 }} />
            <col style={{ width: `${colWidths[0]}%` }} />
            <col style={{ width: `${colWidths[1]}%` }} />
            <col style={{ width: `${colWidths[2]}%` }} />
            <col style={{ width: `${colWidths[3]}%` }} />
          </colgroup>
          <thead style={{ position: 'sticky', top: 0, zIndex: 5 }}>
            <tr>
              <th style={{ padding: '5px 7px', fontSize: '0.62rem', background: '#f1f5f9', borderBottom: '2px solid #e2e8f0', width: 32 }}>#</th>

              <th style={{ position: 'relative', textAlign: 'left', padding: '5px 7px', fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: '#64748b', fontWeight: 700, background: '#f1f5f9', borderBottom: '2px solid #e2e8f0', overflow: 'visible' }}>
                English (Original)
                <div onMouseDown={e => startResizing(0, e)}
                  style={{ position: 'absolute', right: -6, top: 0, bottom: 0, width: 12, cursor: 'col-resize', zIndex: 20, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <div style={{ width: 2, height: '60%', background: '#cbd5e1', borderRadius: 2, transition: 'background .15s' }}
                    onMouseEnter={e => (e.currentTarget.style.background = '#3b82f6', e.currentTarget.style.width = '3px')}
                    onMouseLeave={e => (e.currentTarget.style.background = '#cbd5e1', e.currentTarget.style.width = '2px')} />
                </div>
              </th>

              <th style={{ position: 'relative', textAlign: 'left', padding: '5px 7px', fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: '#64748b', fontWeight: 700, background: '#f1f5f9', borderBottom: '2px solid #e2e8f0', overflow: 'visible' }}>
                Russian
                <div onMouseDown={e => startResizing(1, e)}
                  style={{ position: 'absolute', right: -6, top: 0, bottom: 0, width: 12, cursor: 'col-resize', zIndex: 20, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <div style={{ width: 2, height: '60%', background: '#cbd5e1', borderRadius: 2, transition: 'background .15s' }}
                    onMouseEnter={e => (e.currentTarget.style.background = '#3b82f6', e.currentTarget.style.width = '3px')}
                    onMouseLeave={e => (e.currentTarget.style.background = '#cbd5e1', e.currentTarget.style.width = '2px')} />
                </div>
              </th>

              <th style={{ position: 'relative', textAlign: 'left', padding: '5px 7px', fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: '#64748b', fontWeight: 700, background: '#f1f5f9', borderBottom: '2px solid #e2e8f0', overflow: 'visible' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  Uzbek
                  <button onClick={async () => {
                    const texts = data.map(r => r.uz_proposed || r.uz_v1)
                    const res = await fetch(`${API_BASE}/api/transliterate-batch`, {
                      method: 'POST', headers: authHeaders,
                      body: JSON.stringify({ texts, target: 'latin' })
                    })
                    const r = await res.json()
                    const newData = [...data]
                    r.texts.forEach((txt: string, i: number) => {
                      if (newData[i].uz_proposed) newData[i].uz_proposed = txt
                      else newData[i].uz_v1 = txt
                    })
                    setData(newData)
                  }} style={{ background: '#334155', border: 'none', color: '#93c5fd', fontSize: '0.55rem', padding: '2px 5px', borderRadius: 4, cursor: 'pointer', fontWeight: 800 }}>К→Л</button>
                </div>
                <div onMouseDown={e => startResizing(2, e)}
                  style={{ position: 'absolute', right: -6, top: 0, bottom: 0, width: 12, cursor: 'col-resize', zIndex: 20, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <div style={{ width: 2, height: '60%', background: '#cbd5e1', borderRadius: 2, transition: 'background .15s' }}
                    onMouseEnter={e => (e.currentTarget.style.background = '#3b82f6', e.currentTarget.style.width = '3px')}
                    onMouseLeave={e => (e.currentTarget.style.background = '#cbd5e1', e.currentTarget.style.width = '2px')} />
                </div>
              </th>

              <th style={{ textAlign: 'left', padding: '5px 7px', fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: '#64748b', fontWeight: 700, background: '#f1f5f9', borderBottom: '2px solid #e2e8f0' }}>Izoh</th>
            </tr>
          </thead>
          <tbody>
            {data.map((row, idx) => (
              <React.Fragment key={idx}>
                {dropIdx === idx && dragIdx !== null && dragIdx !== idx && (
                  <tr><td colSpan={5} style={{ padding: 0, height: 3, background: '#3b82f6' }} /></tr>
                )}
                <tr
                  style={{
                    background: row.type === 'marker' ? '#dbeafe' : dragIdx === idx ? '#fef9c3' : 'white',
                    borderBottom: '1px solid #e9edf2',
                    opacity: dragIdx === idx ? 0.5 : 1,
                    transition: 'opacity .15s'
                  }}
                  onDragOver={e => handleDragOver(e, idx)}
                  onDragLeave={handleDragLeave}
                  onDrop={e => handleDrop(e, idx)}
                >
                  <td
                    draggable
                    onDragStart={() => handleDragStart(idx)}
                    onDragEnd={handleDragEnd}
                    style={{ padding: '4px 2px', verticalAlign: 'top', borderRight: '1px solid #e9edf2', textAlign: 'center', width: 32, cursor: 'grab' }}
                    title="Ушлаб суринг"
                  >
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                      <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#94a3b8', lineHeight: 1 }}>{row.display_no || row.sentence_no}</span>
                      {row.type === 'content' && (
                        <>
                          <button onClick={() => saveSingleRow(idx)} disabled={savingRow === idx} title="Saqlash"
                            style={{ background: 'none', border: '1px solid #ddd', borderRadius: 3, padding: '2px 3px', cursor: 'pointer', color: '#64748b', display: 'flex', lineHeight: 1 }}>
                            {savingRow === idx ? <Loader2 size={10} style={{ animation: 'spin .8s linear infinite' }} /> : <Save size={10} />}
                          </button>
                          <button onClick={() => onMagicSplit(idx)} title="AI Bo'lish"
                            style={{ background: 'none', border: '1px solid #ddd', borderRadius: 3, padding: '2px 3px', cursor: 'pointer', color: '#6366f1', display: 'flex', lineHeight: 1 }}>
                            <Sparkles size={10} />
                          </button>
                          <button onClick={() => deleteRow(idx)} title="O'chirish"
                            style={{ background: 'none', border: '1px solid #ddd', borderRadius: 3, padding: '2px 3px', cursor: 'pointer', color: '#94a3b8', display: 'flex', lineHeight: 1 }}>
                            <Trash2 size={10} />
                          </button>
                        </>
                      )}
                    </div>
                  </td>

                  <td style={{ padding: '3px 6px', verticalAlign: 'top', borderRight: '1px solid #e9edf2', fontSize: '0.65rem', color: '#64748b', lineHeight: 1.25, fontWeight: row.type === 'marker' ? 800 : 400, cursor: row.type === 'content' ? 'text' : 'default' }}
                    onClick={row.type === 'content' ? (e) => {
                      const sel = window.getSelection()?.toString().trim()
                      const word = sel && sel.length >= 2 ? sel.replace(/[.,;:!?()]/g, '').trim() : ''
                      if (word && word.split(' ').length <= 5) {
                        const px = Math.min(e.clientX, window.innerWidth - 310)
                        const py = Math.min(e.clientY + 22, window.innerHeight - 240)
                        setPopup({ visible: true, x: px, y: py, word, lang: 'en', rowIdx: idx, synonyms: [], loading: true })
                        fetch(`${API_BASE}/api/linguistic/synonyms`, {
                          method: 'POST', headers: authHeaders,
                          body: JSON.stringify({ word, lang: 'en', context_en: row.en, source_lang: 'English' })
                        }).then(r => r.json()).then(r => setPopup(p => ({ ...p, synonyms: r.synonyms || [], loading: false }))).catch(() => setPopup(p => ({ ...p, loading: false })))
                      }
                    } : undefined}
                  >
                    {terms.length > 0 ? <TermHighlighter text={row.en} terms={terms} /> : <RichContent text={row.en} />}
                  </td>

                  <LangCell v1={row.ru_v1} proposed={row.ru_proposed} rowIdx={idx} lang="ru"
                    isMarker={row.type === 'marker'} isImproving={improvingRow?.idx === idx && improvingRow?.lang === 'ru'}
                    onV1Change={v => update(idx, 'ru_v1', v)}
                    onProposedChange={v => update(idx, 'ru_proposed', v)}
                    onImprove={() => improveRow(idx, 'ru')} onWordClick={handleWordClick}
                    onBlockDrop={handleBlockDrop} token={token || undefined}
                    contextEn={row.en} contextRu={row.ru_proposed || row.ru_v1} contextUz={row.uz_proposed || row.uz_v1} />

                  <LangCell v1={row.uz_v1} proposed={row.uz_proposed} rowIdx={idx} lang="uz"
                    isMarker={row.type === 'marker'} isImproving={improvingRow?.idx === idx && improvingRow?.lang === 'uz'}
                    onV1Change={v => update(idx, 'uz_v1', v)}
                    onProposedChange={v => update(idx, 'uz_proposed', v)}
                    onImprove={() => improveRow(idx, 'uz')} onWordClick={handleWordClick}
                    onBlockDrop={handleBlockDrop} token={token || undefined}
                    contextEn={row.en} contextRu={row.ru_proposed || row.ru_v1} contextUz={row.uz_proposed || row.uz_v1} />

                  <td style={{ padding: '7px 7px', verticalAlign: 'top', borderLeft: '1px solid #e9edf2' }}>
                    <textarea value={row.notes || ''} onChange={e => update(idx, 'notes', e.target.value)}
                      placeholder="Izoh..."
                      style={{ width: '100%', minHeight: 80, fontSize: '0.72rem', border: '1px solid #e8e5d5', borderRadius: 4, padding: '5px 6px', background: '#fffef5', resize: 'vertical', outline: 'none', fontFamily: 'inherit', lineHeight: 1.4, boxSizing: 'border-box' }} />
                  </td>
                </tr>

                {row.type === 'content' && (
                  <tr>
                    <td colSpan={5} style={{ padding: '0 0 0 28px', height: 14 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 4, opacity: 0, transition: 'opacity .15s' }}
                        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.opacity = '1' }}
                        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.opacity = '0' }}>
                        <button onClick={() => insertRowAfter(idx)}
                          style={{ display: 'flex', alignItems: 'center', gap: 3, padding: '1px 7px', background: '#eff6ff', color: '#3b82f6', border: '1px dashed #93c5fd', borderRadius: 4, fontSize: '0.65rem', fontWeight: 700, cursor: 'pointer' }}>
                          <Plus size={10} /> + band
                        </button>
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>

        {/* Synonym Sidebar */}
        <SynonymPopup popup={popup} onApplyVariant={applyVariant} />
      </div>

      <style jsx global>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        * { box-sizing: border-box; }
        body { margin: 0; }
        ::-webkit-scrollbar { width: 7px; height: 7px; }
        ::-webkit-scrollbar-track { background: #f1f5f9; }
        ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #94a3b8; }
      `}</style>
    </div>
  )
}
