'use client'

import React, { useState, useEffect, useRef } from 'react'
import { Brain, Send, Paperclip, Image as ImageIcon, Mic, Wand2, Languages, MessageSquare, Loader2, X, Bot, User as UserIcon, FileText, Sparkles, Pill, BarChart3, CheckCircle2 } from 'lucide-react'
import api from '../../services/api'
import { useAuth } from '../../components/LoginGuard'

type Mode = 'chat' | 'edit' | 'translate'
type Lang = 'en' | 'ru' | 'uz-lat' | 'uz-cyr'

interface Message {
  role: 'user' | 'assistant'
  content: string
  attachments?: Array<{ name: string; kind: string; url?: string; size_mb?: number }>
  engine?: string
  ts?: number
}

const LANG_LABELS: Record<Lang, string> = {
  'en': '🇬🇧 English',
  'ru': '🇷🇺 Русский',
  'uz-lat': "🇺🇿 O'zbek",
  'uz-cyr': '🇺🇿 Ўзбек',
}

export default function AssistantPage() {
  const { token } = useAuth()
  const [mode, setMode] = useState<Mode>('chat')
  const [engine, setEngine] = useState<string>('auto')
  const [engines, setEngines] = useState<any[]>([])
  const [lang, setLang] = useState<Lang>('uz-lat')
  const [sourceLang, setSourceLang] = useState<Lang>('en')
  const [targetLang, setTargetLang] = useState<Lang>('uz-lat')

  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [pendingFiles, setPendingFiles] = useState<Array<{ name: string; kind: string; text?: string; base64?: string; mime?: string; size_mb: number }>>([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const imgInputRef = useRef<HTMLInputElement>(null)
  const audioInputRef = useRef<HTMLInputElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!token) return
    api.assistant.engines().then(r => setEngines(r.engines || [])).catch(() => {})
  }, [token])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleFileUpload = async (file: File) => {
    if (file.size > 50 * 1024 * 1024) {
      alert(`Файл ${(file.size / 1024 / 1024).toFixed(1)} MB — лимит 50 MB`)
      return
    }
    try {
      setLoading(true)
      const r = await api.assistant.upload(file)
      setPendingFiles(prev => [...prev, {
        name: r.filename,
        kind: r.kind,
        text: r.text,
        base64: r.base64,
        mime: r.mime,
        size_mb: r.size_mb,
      }])
    } catch (e: any) {
      alert('Юклашда хато: ' + (e?.message || e))
    } finally {
      setLoading(false)
    }
  }

  const removeFile = (idx: number) => {
    setPendingFiles(prev => prev.filter((_, i) => i !== idx))
  }

  const sendMessage = async () => {
    const text = input.trim()
    if (!text && pendingFiles.length === 0) return

    // Build user message with attached files
    const attachments = pendingFiles.map(f => ({
      name: f.name,
      kind: f.kind,
      size_mb: f.size_mb,
      url: f.base64 ? `data:${f.mime};base64,${f.base64}` : undefined,
    }))

    // Concatenate file text into the message
    let fullMessage = text
    for (const f of pendingFiles) {
      if (f.text && f.kind !== 'image') {
        fullMessage += `\n\n[${f.kind.toUpperCase()} файл: ${f.name}]\n${f.text}`
      } else if (f.kind === 'image') {
        fullMessage += `\n\n[Расм юкланган: ${f.name}]`
      }
    }

    const userMsg: Message = { role: 'user', content: text || `[${pendingFiles.length} файл]`, attachments, ts: Date.now() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setPendingFiles([])
    setLoading(true)

    try {
      let response: any
      const history = messages.slice(-6).map(m => ({ role: m.role, content: m.content }))
      if (mode === 'chat') {
        response = await api.assistant.chat(fullMessage, { engine, lang: lang.startsWith('uz') ? 'uz' : lang, history })
      } else if (mode === 'edit') {
        response = await api.assistant.edit(fullMessage, { engine, lang: lang.startsWith('uz') ? 'uz' : lang })
      } else {
        const sl = sourceLang.startsWith('uz') ? 'uz' : sourceLang
        const tl = targetLang.startsWith('uz') ? 'uz' : targetLang
        response = await api.assistant.translate(fullMessage, { engine, source_lang: sl, target_lang: tl })
      }
      const assistantMsg: Message = {
        role: 'assistant',
        content: response.text || '⚠️ Бўш жавоб',
        engine: response.engine || engine,
        ts: Date.now(),
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch (e: any) {
      setMessages(prev => [...prev, { role: 'assistant', content: '❌ Хато: ' + (e?.message || e), ts: Date.now() }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const handleNormalizeDrug = async () => {
    const word = input.trim() || prompt('Дори номини киритинг:') || ''
    if (!word) return
    setLoading(true)
    try {
      const r = await api.tilshunos.decomposeTerm(word)
      const m = await fetch(`${api.API_BASE}/api/tilshunos/normalize-drug`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${localStorage.getItem('token')}` }, body: JSON.stringify({ name: word }) })
      const norm = m.ok ? await m.json() : null
      let response = `**💊 Дори таҳлили: "${word}"**\n\n`
      if (norm?.best) {
        response += `**Канон INN:** ${norm.best.inn}\n**Бренд:** ${norm.best.brand_name || '—'}\n**ATC код:** ${norm.best.atc_code || '—'}\n**Шакл:** ${norm.best.form || '—'}\n**Доза:** ${norm.best.dose || '—'}\n\n`
      } else {
        response += `_Базада топилмади_\n\n`
      }
      if (r.found) {
        response += `**🧬 Морфема таҳлили:**\n`
        if (r.prefix) response += `- Префикс: \`${r.prefix}\` — ${r.prefix_meaning}\n`
        if (r.root) response += `- Ўзак: \`${r.root}\`\n`
        if (r.suffix) response += `- Суффикс: \`${r.suffix}\` — ${r.suffix_meaning}\n`
      }
      setMessages(prev => [...prev, { role: 'user', content: word, ts: Date.now() }, { role: 'assistant', content: response, engine: 'drug_analyzer', ts: Date.now() }])
      setInput('')
    } catch (e: any) {
      alert('Хато: ' + (e?.message || e))
    } finally { setLoading(false) }
  }

  const handleGrammarScore = async () => {
    const text = input.trim()
    if (!text) return alert('Матн ёзинг')
    setLoading(true)
    try {
      const r = await api.tilshunos.grammarScore(text)
      const score = Math.round((r.score || 0) * 100)
      const emoji = score >= 80 ? '🟢' : score >= 50 ? '🟡' : '🔴'
      setMessages(prev => [...prev, { role: 'user', content: text, ts: Date.now() }, { role: 'assistant', content: `**${emoji} Грамматика баҳоси: ${score}/100**\n\nBERT pseudo-perplexity скори асосида.\n${score >= 80 ? 'Гап табиий ва грамматик жиҳатдан тўғри.' : score >= 50 ? 'Гап ўртача — тузатишлар қилиш мумкин.' : 'Гап мураккаб ёки грамматик хатолар бор.'}`, engine: 'bert_perplexity', ts: Date.now() }])
      setInput('')
    } catch (e: any) {
      alert('Хато: ' + (e?.message || e))
    } finally { setLoading(false) }
  }

  return (
    <div style={{ maxWidth: 1400, margin: '0 auto', padding: '0 4px', display: 'flex', flexDirection: 'column', height: 'calc(100vh - 80px)' }}>
      {/* Hero */}
      <div style={{
        background: 'linear-gradient(135deg, #FFF8F0 0%, #FFEFDC 100%)',
        borderRadius: 18, padding: '16px 24px', border: '1.5px solid #FDE3C5',
        marginBottom: 12, display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap',
      }}>
        <div style={{ width: 46, height: 46, borderRadius: 12, background: 'linear-gradient(135deg, #7C3AED, #6D28D9)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Brain size={24} color="white" />
        </div>
        <div style={{ flex: 1 }}>
          <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 800, color: '#5B21B6' }}>Фармацевт ёрдамчиси</h1>
          <p style={{ margin: 0, fontSize: '0.85rem', color: '#7C3AED' }}>Сунъий идрок — таҳрир, таржима, чат, файл/расм/аудио тахлили</p>
        </div>
      </div>

      {/* Mode tabs + Engine + Lang */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap', alignItems: 'center' }}>
        {[
          { k: 'chat', label: 'Чат', icon: MessageSquare },
          { k: 'edit', label: 'Илмий таҳрир', icon: Wand2 },
          { k: 'translate', label: 'Илмий таржима', icon: Languages },
        ].map(({ k, label, icon: Icon }) => (
          <button key={k} onClick={() => setMode(k as Mode)} style={{
            padding: '8px 16px', borderRadius: 10,
            background: mode === k ? 'linear-gradient(135deg, #7C3AED, #6D28D9)' : 'white',
            color: mode === k ? 'white' : '#6B7280',
            border: mode === k ? 'none' : '1.5px solid var(--border)',
            fontWeight: 700, fontSize: '0.85rem', cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: 6,
          }}>
            <Icon size={14} /> {label}
          </button>
        ))}

        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <Sparkles size={14} color="#7C3AED" />
          <select value={engine} onChange={e => setEngine(e.target.value)} style={{
            padding: '8px 12px', borderRadius: 10, border: '1.5px solid var(--border)',
            fontSize: '0.82rem', fontWeight: 600, background: 'white', cursor: 'pointer',
          }}>
            {engines.map(e => (
              <option key={e.key} value={e.key} disabled={!e.available}>
                {e.available ? '🟢' : '⚪'} {e.label}
              </option>
            ))}
          </select>

          {mode === 'translate' ? (
            <>
              <select value={sourceLang} onChange={e => setSourceLang(e.target.value as Lang)} style={{ padding: '8px 12px', borderRadius: 10, border: '1.5px solid var(--border)', fontSize: '0.82rem', fontWeight: 600 }}>
                {Object.entries(LANG_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
              <span>→</span>
              <select value={targetLang} onChange={e => setTargetLang(e.target.value as Lang)} style={{ padding: '8px 12px', borderRadius: 10, border: '1.5px solid var(--border)', fontSize: '0.82rem', fontWeight: 600 }}>
                {Object.entries(LANG_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </>
          ) : (
            <select value={lang} onChange={e => setLang(e.target.value as Lang)} style={{ padding: '8px 12px', borderRadius: 10, border: '1.5px solid var(--border)', fontSize: '0.82rem', fontWeight: 600 }}>
              {Object.entries(LANG_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          )}
        </div>
      </div>

      {/* Messages area */}
      <div style={{
        flex: 1, background: 'var(--bg-card)', border: '1.5px solid var(--border)', borderRadius: 14,
        padding: 16, overflowY: 'auto', marginBottom: 12,
      }}>
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 60 }}>
            <Bot size={64} style={{ opacity: 0.3, marginBottom: 12 }} />
            <p style={{ fontSize: '1rem', fontWeight: 600 }}>Саломат бўлинг! Фармацевт ёрдамчисига хуш келибсиз.</p>
            <p style={{ fontSize: '0.85rem', marginTop: 8 }}>
              Сиз нима истайсиз? Чат, илмий таҳрир, ёки таржима? Файл, расм ёки аудио ҳам юбора оласиз (макс 50 MB).
            </p>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} style={{
            display: 'flex', gap: 12, marginBottom: 16,
            justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start',
          }}>
            {m.role === 'assistant' && (
              <div style={{ width: 36, height: 36, borderRadius: '50%', background: '#7C3AED', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <Bot size={18} color="white" />
              </div>
            )}
            <div style={{
              maxWidth: '75%',
              padding: '12px 16px',
              borderRadius: 14,
              background: m.role === 'user' ? 'linear-gradient(135deg, #7C3AED, #6D28D9)' : 'var(--bg-secondary)',
              color: m.role === 'user' ? 'white' : 'var(--text-primary)',
              fontSize: '0.92rem', lineHeight: 1.6, whiteSpace: 'pre-wrap',
            }}>
              {m.content}
              {m.attachments && m.attachments.length > 0 && (
                <div style={{ marginTop: 8, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {m.attachments.map((a, ai) => (
                    <div key={ai} style={{ padding: '4px 8px', background: m.role === 'user' ? 'rgba(255,255,255,0.2)' : '#E5E7EB', borderRadius: 6, fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: 4 }}>
                      {a.kind === 'image' ? <ImageIcon size={11} /> : a.kind === 'audio' ? <Mic size={11} /> : <FileText size={11} />}
                      {a.name} ({a.size_mb} MB)
                    </div>
                  ))}
                </div>
              )}
              {m.engine && m.role === 'assistant' && (
                <div style={{ marginTop: 6, fontSize: '0.65rem', color: '#9CA3AF', fontWeight: 600 }}>
                  ⚙ {m.engine}
                </div>
              )}
            </div>
            {m.role === 'user' && (
              <div style={{ width: 36, height: 36, borderRadius: '50%', background: '#0EA5E9', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <UserIcon size={18} color="white" />
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
            <div style={{ width: 36, height: 36, borderRadius: '50%', background: '#7C3AED', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Bot size={18} color="white" />
            </div>
            <div style={{ padding: '12px 16px', borderRadius: 14, background: 'var(--bg-secondary)' }}>
              <Loader2 size={16} className="animate-spin" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Pending files */}
      {pendingFiles.length > 0 && (
        <div style={{ display: 'flex', gap: 6, marginBottom: 8, flexWrap: 'wrap' }}>
          {pendingFiles.map((f, i) => (
            <div key={i} style={{ padding: '6px 10px', background: '#EDE9FE', border: '1.5px solid #C4B5FD', borderRadius: 8, display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.78rem' }}>
              {f.kind === 'image' ? <ImageIcon size={12} /> : f.kind === 'audio' ? <Mic size={12} /> : <FileText size={12} />}
              <span style={{ fontWeight: 600 }}>{f.name}</span>
              <span style={{ color: '#9CA3AF' }}>({f.size_mb} MB)</span>
              <button onClick={() => removeFile(i)} style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#9CA3AF' }}><X size={12} /></button>
            </div>
          ))}
        </div>
      )}

      {/* Input area */}
      <div style={{
        background: 'white', border: '1.5px solid var(--border)', borderRadius: 14, padding: 12,
        display: 'flex', gap: 8, alignItems: 'flex-end',
      }}>
        <button onClick={() => fileInputRef.current?.click()} title="Файл (txt/pdf/docx, макс 50 МБ)" style={{ padding: 10, background: 'transparent', border: 'none', cursor: 'pointer', color: '#6B7280' }}>
          <Paperclip size={20} />
        </button>
        <button onClick={() => imgInputRef.current?.click()} title="Расм (jpg/png, макс 50 МБ)" style={{ padding: 10, background: 'transparent', border: 'none', cursor: 'pointer', color: '#6B7280' }}>
          <ImageIcon size={20} />
        </button>
        <button onClick={() => audioInputRef.current?.click()} title="Аудио (mp3/wav/m4a, макс 50 МБ)" style={{ padding: 10, background: 'transparent', border: 'none', cursor: 'pointer', color: '#6B7280' }}>
          <Mic size={20} />
        </button>
        <button onClick={handleNormalizeDrug} title="Дори INN/ATC + морфема таҳлили" style={{ padding: 10, background: 'transparent', border: 'none', cursor: 'pointer', color: '#7C3AED' }}>
          <Pill size={20} />
        </button>
        <button onClick={handleGrammarScore} title="BERT грамматика баҳоси" style={{ padding: 10, background: 'transparent', border: 'none', cursor: 'pointer', color: '#16A34A' }}>
          <CheckCircle2 size={20} />
        </button>

        <input ref={fileInputRef} type="file" accept=".txt,.md,.csv,.pdf,.docx" style={{ display: 'none' }} onChange={e => { const f = e.target.files?.[0]; if (f) handleFileUpload(f); e.target.value = '' }} />
        <input ref={imgInputRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={e => { const f = e.target.files?.[0]; if (f) handleFileUpload(f); e.target.value = '' }} />
        <input ref={audioInputRef} type="file" accept="audio/*" style={{ display: 'none' }} onChange={e => { const f = e.target.files?.[0]; if (f) handleFileUpload(f); e.target.value = '' }} />

        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={mode === 'chat' ? 'Саволингизни ёзинг...' : mode === 'edit' ? 'Тузатилиши керак бўлган матнни ёзинг...' : 'Таржима қилинадиган матнни ёзинг...'}
          rows={1}
          style={{
            flex: 1, padding: '10px 14px', border: 'none', outline: 'none',
            fontSize: '0.92rem', fontFamily: 'inherit', resize: 'none', maxHeight: 200,
          }}
        />

        <button onClick={sendMessage} disabled={loading || (!input.trim() && pendingFiles.length === 0)} style={{
          padding: '10px 18px', borderRadius: 10, border: 'none',
          background: 'linear-gradient(135deg, #7C3AED, #6D28D9)',
          color: 'white', cursor: loading ? 'not-allowed' : 'pointer',
          opacity: (loading || (!input.trim() && pendingFiles.length === 0)) ? 0.5 : 1,
          fontWeight: 700, display: 'flex', alignItems: 'center', gap: 6,
        }}>
          {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
          Юбориш
        </button>
      </div>

      <p style={{ textAlign: 'center', fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 6 }}>
        💡 Файл лимити: 50 МБ. Қўллаб-қувватланади: txt, pdf, docx, jpg, png, mp3, wav, m4a
      </p>
    </div>
  )
}
