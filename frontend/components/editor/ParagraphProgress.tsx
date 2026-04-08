'use client'

import React, { useEffect, useState } from 'react'
import { CheckCircle2, Circle, AlertCircle, Eye } from 'lucide-react'
import api from '../../services/api'

interface Props {
  textId: string
  sentenceNo: number
  currentStatus?: string
  onUpdate?: (status: string) => void
}

const STATUS_CONFIG: Record<string, { icon: any; color: string; bg: string; label: string }> = {
  pending: { icon: Circle, color: '#9CA3AF', bg: '#F3F4F6', label: 'Кутилмоқда' },
  in_review: { icon: Eye, color: '#0EA5E9', bg: '#DBEAFE', label: 'Текширувда' },
  needs_revision: { icon: AlertCircle, color: '#DC2626', bg: '#FEE2E2', label: 'Тузатиш керак' },
  approved: { icon: CheckCircle2, color: '#16A34A', bg: '#DCFCE7', label: 'Тасдиқланди' },
}

export default function ParagraphProgress({ textId, sentenceNo, currentStatus = 'pending', onUpdate }: Props) {
  const [status, setStatus] = useState(currentStatus)
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setStatus(currentStatus)
  }, [currentStatus])

  const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending
  const Icon = config.icon

  const changeStatus = async (newStatus: string) => {
    if (!textId) return
    setLoading(true)
    try {
      await api.tilshunos.updateParagraphProgress({
        text_id: textId,
        sentence_no: sentenceNo,
        status: newStatus,
      })
      setStatus(newStatus)
      onUpdate?.(newStatus)
      setOpen(false)
    } catch (_) {}
    finally { setLoading(false) }
  }

  return (
    <div style={{ position: 'relative', display: 'inline-block' }}>
      <button
        onClick={() => setOpen(!open)}
        title={`Статус: ${config.label}`}
        style={{
          display: 'flex', alignItems: 'center', gap: 3,
          padding: '2px 6px', background: config.bg, color: config.color,
          border: `1px solid ${config.color}44`, borderRadius: 4,
          fontSize: '0.6rem', fontWeight: 700, cursor: 'pointer',
        }}
      >
        <Icon size={10} /> {config.label}
      </button>

      {open && (
        <>
          <div onClick={() => setOpen(false)} style={{ position: 'fixed', inset: 0, zIndex: 90 }} />
          <div style={{
            position: 'absolute', top: '100%', left: 0, marginTop: 4,
            background: 'white', border: '1.5px solid #E5E7EB', borderRadius: 8,
            boxShadow: '0 4px 12px rgba(0,0,0,0.1)', zIndex: 100, minWidth: 160,
          }}>
            {Object.entries(STATUS_CONFIG).map(([key, cfg]) => {
              const ItemIcon = cfg.icon
              return (
                <button
                  key={key}
                  onClick={() => changeStatus(key)}
                  disabled={loading || key === status}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 6,
                    width: '100%', padding: '6px 10px', textAlign: 'left',
                    background: key === status ? cfg.bg : 'transparent',
                    border: 'none', cursor: key === status ? 'default' : 'pointer',
                    fontSize: '0.72rem', fontWeight: 600, color: cfg.color,
                  }}
                >
                  <ItemIcon size={11} /> {cfg.label}
                </button>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
