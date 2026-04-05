'use client'

import React from 'react'
import { Search, Loader2 } from 'lucide-react'

interface SynonymPopupData {
  visible: boolean; x: number; y: number
  word: string; lang: 'ru' | 'uz' | 'en'; rowIdx: number
  synonyms: string[]; loading: boolean
}

interface Props {
  popup: SynonymPopupData
  onApplyVariant: (synonym: string) => void
}

export default function SynonymPopup({ popup, onApplyVariant }: Props) {
  return (
    <aside style={{ width: '280px', background: 'white', borderLeft: '1px solid #e2e8f0', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ padding: '12px 15px', borderBottom: '1px solid #e2e8f0', background: '#f8fafc', display: 'flex', alignItems: 'center', gap: 8 }}>
        <Search size={14} color="#6366f1" />
        <span style={{ fontSize: '0.75rem', fontWeight: 800, color: '#1e293b' }}>Синонимлар ва Частота</span>
      </div>
      <div style={{ flex: 1, overflow: 'auto', padding: '10px' }}>
        {popup.word ? (
          <div style={{ marginBottom: 20 }}>
            <div style={{ marginBottom: 10 }}>
              <span style={{ fontSize: '0.62rem', fontWeight: 800, color: '#94a3b8', textTransform: 'uppercase' }}>Танланган сўз</span>
              <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#6366f1' }}>{popup.word}</div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {popup.loading ? (
                <Loader2 size={16} className="spin" style={{ margin: 'auto' }} />
              ) : (
                popup.synonyms.map((s: any, i: number) => {
                  const syn = typeof s === 'string' ? s : s.word
                  const prob = typeof s === 'string' ? 0.5 : (s.probability || 0.5)
                  const freq = typeof s === 'string' ? 0 : (s.frequency || 0)

                  return (
                    <div key={i} onClick={() => onApplyVariant(syn)}
                      style={{ padding: '8px 12px', border: '1px solid #f1f5f9', borderRadius: 8, fontSize: '0.8rem', cursor: 'pointer', background: '#fff', position: 'relative', overflow: 'hidden' }}
                      onMouseEnter={e => e.currentTarget.style.background = '#f8fafc'}
                      onMouseLeave={e => e.currentTarget.style.background = '#fff'}>

                      <div style={{ position: 'absolute', bottom: 0, left: 0, height: 2, background: '#6366f1', width: `${prob * 100}%`, opacity: 0.4 }} />

                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                        <span style={{ fontWeight: 600, color: '#1e293b' }}>{syn}</span>
                        <span style={{ fontSize: '0.6rem', color: '#94a3b8' }}>{freq > 0 ? `${freq}х` : ''}</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <div style={{ flex: 1, height: 3, background: '#f1f5f9', borderRadius: 2 }}>
                          <div style={{ height: '100%', width: `${prob * 100}%`, background: prob > 0.8 ? '#10b981' : '#6366f1', borderRadius: 2 }} />
                        </div>
                        <span style={{ fontSize: '0.55rem', fontWeight: 800, color: '#64748b' }}>{Math.round(prob * 100)}%</span>
                      </div>
                    </div>
                  )
                })
              )}
            </div>
          </div>
        ) : (
          <div style={{ textAlign: 'center', color: '#94a3b8', fontSize: '0.75rem', marginTop: 100 }}>
            Матндаги сўзни устига босинг (Click) <br />синонимларни кўриш учун
          </div>
        )}
      </div>
      <div style={{ padding: '10px', borderTop: '1px solid #e2e8f0', fontSize: '0.65rem', color: '#94a3b8' }}>
        Частота жадвали автоматик янгиланади
      </div>
    </aside>
  )
}
