import React from 'react'
import { Sparkles } from 'lucide-react'

export default function RichContent({ text, style }: { text: string; style?: React.CSSProperties }) {
  if (!text) return <span style={{ color: '#cbd5e1' }}>-</span>

  const imgRe = /§IMG:([^§]+)§/g
  const tblRe = /§TBL:([^§]+)§/g
  const imgPlain = /§IMG§/g

  const hasSpecial = imgRe.test(text) || tblRe.test(text) || imgPlain.test(text)
  if (!hasSpecial) return <span style={style}>{text}</span>

  const parts: React.ReactNode[] = []
  let lastIdx = 0
  const allRe = /§(IMG|TBL):([^§]+)§|§IMG§/g
  let m
  while ((m = allRe.exec(text)) !== null) {
    if (m.index > lastIdx) parts.push(<span key={'t' + lastIdx}>{text.slice(lastIdx, m.index)}</span>)
    if (m[0] === '§IMG§') {
      parts.push(<div key={'i' + m.index} style={{ color: '#94a3b8', fontSize: '0.75rem', fontStyle: 'italic' }}>[Rasm]</div>)
    } else if (m[1] === 'IMG') {
      parts.push(<img key={'i' + m.index} src={m[2]} alt="[Rasm]" style={{ maxWidth: '100%', display: 'block', margin: '4px 0', borderRadius: 3 }} />)
    } else if (m[1] === 'TBL') {
      parts.push(<div key={'t' + m.index} dangerouslySetInnerHTML={{ __html: m[2] }} style={{ margin: '4px 0', overflowX: 'auto' }} />)
    } else if (m[1] === 'MAT') {
      parts.push(<div key={'m' + m.index} style={{ display: 'inline-flex', alignItems: 'center', gap: 4, background: '#f5f3ff', color: '#7c3aed', padding: '2px 8px', borderRadius: 12, fontSize: '0.68rem', fontWeight: 700, margin: '2px 0', border: '1px solid #ddd6fe' }}>
        <Sparkles size={10} /> Formula
      </div>)
    }
    lastIdx = m.index + m[0].length
  }
  if (lastIdx < text.length) parts.push(<span key={'e'}>{text.slice(lastIdx)}</span>)
  return <div style={style}>{parts}</div>
}
