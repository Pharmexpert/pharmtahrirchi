'use client'

import React, { useEffect, useState } from 'react'
import { History, X, Loader2, User, Clock, GitCommit } from 'lucide-react'
import api from '../services/api'

interface Props {
  textId: string
  sentenceNo: number
  lang?: string
  onClose: () => void
}

export default function DocumentVersionsModal({ textId, sentenceNo, lang, onClose }: Props) {
  const [versions, setVersions] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.tilshunos.getDocVersions(textId, sentenceNo, lang)
      .then(r => setVersions(r.versions || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [textId, sentenceNo, lang])

  return (
    <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div onClick={e => e.stopPropagation()} style={{ background: 'white', borderRadius: 16, padding: 24, width: 'min(720px, 92vw)', maxHeight: '85vh', overflow: 'auto', boxShadow: '0 20px 60px rgba(0,0,0,0.3)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: 8 }}>
            <History size={22} color="#7C3AED" /> Версия тарихи
          </h3>
          <button onClick={onClose} style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#6B7280' }}>
            <X size={22} />
          </button>
        </div>
        <div style={{ fontSize: '0.75rem', color: '#6B7280', marginBottom: 14 }}>
          Проект: <strong>{textId}</strong> · Гап #{sentenceNo} {lang && `· ${lang}`}
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: 40 }}><Loader2 className="animate-spin" /></div>
        ) : versions.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 40, color: '#9CA3AF' }}>Версия тарихи йўқ</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {versions.map((v, i) => (
              <div key={v.id} style={{
                padding: 12, border: `1.5px solid ${i === 0 ? '#7C3AED' : '#E5E7EB'}`,
                borderRadius: 10, background: i === 0 ? '#F5F3FF' : 'white',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                  <GitCommit size={14} color={i === 0 ? '#7C3AED' : '#6B7280'} />
                  <span style={{ fontWeight: 700, fontSize: '0.82rem', color: i === 0 ? '#5B21B6' : '#374151' }}>
                    v{v.version}{i === 0 && ' (joriy)'}
                  </span>
                  <span style={{ marginLeft: 'auto', fontSize: '0.7rem', color: '#9CA3AF', display: 'flex', alignItems: 'center', gap: 4 }}>
                    <Clock size={11} /> {new Date(v.created_at).toLocaleString('ru-RU')}
                  </span>
                </div>
                {v.author_name && (
                  <div style={{ fontSize: '0.72rem', color: '#6B7280', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 4 }}>
                    <User size={11} /> {v.author_name} · {v.action || 'edit'}
                  </div>
                )}
                <div style={{ fontSize: '0.85rem', color: '#374151', padding: 8, background: '#F9FAFB', borderRadius: 6, whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>
                  {v.content}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
