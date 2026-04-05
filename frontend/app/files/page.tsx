'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { FolderOpen, Upload, Download, Trash2, Eye, Play, Loader2, CheckCircle2, AlertCircle, X, FileText, FileIcon, Search, RefreshCw, HardDrive } from 'lucide-react'
import { useAuth } from '../../components/LoginGuard'
import { useRouter } from 'next/navigation'

interface UploadedFile {
  filename: string
  original_filename?: string
  path: string
  size: number
  modified_at: number
  extension: string
  folder?: string
  project_id?: string
  project_name?: string
  specialist_name?: string
}

interface Folder {
  name: string
  path: string
  file_count: number
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatDate(ts: number): string {
  const d = new Date(ts * 1000)
  return d.toLocaleDateString('uz-UZ', { year: '2-digit', month: '2-digit', day: '2-digit' }) + ' ' +
    d.toLocaleTimeString('uz-UZ', { hour: '2-digit', minute: '2-digit' })
}

function getFileIcon(ext: string): string {
  if (ext === '.docx') return '📄'
  if (ext === '.pdf') return '📕'
  if (ext === '.xlsx' || ext === '.xls') return '📊'
  return '📁'
}

export default function FilesPage() {
  const { token, user } = useAuth()
  const router = useRouter()
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const [files, setFiles] = useState<UploadedFile[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [search, setSearch] = useState('')
  const [previewFile, setPreviewFile] = useState<{ filename: string; content: string } | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [openingFile, setOpeningFile] = useState<string | null>(null)
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [folders, setFolders] = useState<Folder[]>([])
  const [currentFolder, setCurrentFolder] = useState('')
  const [showNewFolder, setShowNewFolder] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')
  const [dragFile, setDragFile] = useState<string | null>(null)

  const showToast = (msg: string, type: 'success' | 'error' = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3000)
  }

  const fetchFiles = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/files`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setFiles(data.files || [])
      }
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }, [API_BASE, token])

  const fetchFolders = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/folders`, { headers: { Authorization: `Bearer ${token}` } })
      if (res.ok) setFolders((await res.json()).folders || [])
    } catch {}
  }, [API_BASE, token])

  useEffect(() => { fetchFiles(); fetchFolders() }, [fetchFiles, fetchFolders])

  const createFolder = async () => {
    if (!newFolderName.trim()) return
    try {
      await fetch(`${API_BASE}/api/folders/create`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ name: newFolderName.trim(), parent: currentFolder })
      })
      showToast('Папка яратилди ✓')
      setNewFolderName(''); setShowNewFolder(false); fetchFolders(); fetchFiles()
    } catch { showToast('Хатолик', 'error') }
  }

  const deleteFolder = async (folderPath: string) => {
    if (!confirm(`"${folderPath}" папкани ўчиришни тасдиқлайсизми?`)) return
    try {
      await fetch(`${API_BASE}/api/folders/${encodeURIComponent(folderPath)}`, {
        method: 'DELETE', headers: { Authorization: `Bearer ${token}` }
      })
      showToast('Папка ўчирилди ✓'); fetchFolders(); fetchFiles()
    } catch { showToast('Хатолик', 'error') }
  }

  const moveFile = async (filename: string, targetFolder: string) => {
    try {
      await fetch(`${API_BASE}/api/files/move`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ filename, target_folder: targetFolder })
      })
      showToast('Файл кўчирилди ✓'); fetchFiles()
    } catch { showToast('Хатолик', 'error') }
  }

  const handleUpload = async (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return
    setUploading(true)
    try {
      for (let i = 0; i < fileList.length; i++) {
        const file = fileList[i]
        const formData = new FormData()
        formData.append('file', file)
        await fetch(`${API_BASE}/api/files/upload`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
          body: formData
        })
      }
      showToast(`${fileList.length} та файл юкланди ✓`)
      fetchFiles()
    } catch { showToast('Юклашда хатолик', 'error') }
    finally { setUploading(false) }
  }

  const handleDownload = async (filename: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/files/${encodeURIComponent(filename)}/download`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (!res.ok) throw new Error()
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url; a.download = filename
      document.body.appendChild(a); a.click()
      setTimeout(() => { document.body.removeChild(a); URL.revokeObjectURL(url) }, 200)
      showToast('Юклаб олинди ✓')
    } catch { showToast('Юклашда хатолик', 'error') }
  }

  const handleDelete = async (filename: string) => {
    if (!confirm('Файлни ўчиришни тасдиқлайсизми?')) return
    try {
      const res = await fetch(`${API_BASE}/api/files/${encodeURIComponent(filename)}`, {
        method: 'DELETE', headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        showToast('Ўчирилди ✓')
        fetchFiles()
      }
    } catch { showToast('Ўчиришда хатолик', 'error') }
  }

  const handlePreview = async (filename: string) => {
    setPreviewLoading(true)
    setPreviewFile({ filename, content: '' })
    try {
      const res = await fetch(`${API_BASE}/api/files/${encodeURIComponent(filename)}/preview`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setPreviewFile({ filename, content: data.preview || '' })
      }
    } catch { setPreviewFile({ filename, content: '[Preview хатоси]' }) }
    finally { setPreviewLoading(false) }
  }

  const handleOpenInEditor = async (filename: string) => {
    setOpeningFile(filename)
    try {
      const res = await fetch(`${API_BASE}/api/files/${encodeURIComponent(filename)}/open`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        // Store processing result in sessionStorage and redirect to editor
        sessionStorage.setItem('editor_data', JSON.stringify(data))
        router.push('/')
      } else {
        showToast('Файлни очишда хатолик', 'error')
      }
    } catch { showToast('Файлни очишда хатолик', 'error') }
    finally { setOpeningFile(null) }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    handleUpload(e.dataTransfer.files)
  }

  const filtered = files.filter(f => {
    const q = search.toLowerCase()
    const matchSearch = !q || (f.filename || '').toLowerCase().includes(q) || (f.original_filename || '').toLowerCase().includes(q) || (f.specialist_name || '').toLowerCase().includes(q)
    const matchFolder = (f.folder || '') === currentFolder
    return matchSearch && matchFolder
  })

  const currentFolders = folders.filter(f => {
    if (!currentFolder) return !f.path.includes('/')
    return f.path.startsWith(currentFolder + '/') && !f.path.slice(currentFolder.length + 1).includes('/')
  })

  const totalSize = files.reduce((sum, f) => sum + f.size, 0)

  return (
    <div>
      {/* Toast */}
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

      {/* Hero Header */}
      <div style={{
        background: '#F0F7FF', borderRadius: '20px', padding: '32px 36px',
        border: '1.5px solid #BFDBFE', marginBottom: '28px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        flexWrap: 'wrap', gap: '20px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          <div style={{
            width: 52, height: 52, borderRadius: '14px',
            background: 'linear-gradient(135deg, #2563EB 0%, #7C3AED 100%)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '1.6rem', boxShadow: '0 4px 16px rgba(37,99,235,0.3)'
          }}>
            📂
          </div>
          <div>
            <h1 style={{ fontSize: '1.7rem', fontWeight: 800, marginBottom: '4px', letterSpacing: '-0.5px' }}>
              Файллар директорияси
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 0 }}>
              Юкланган ҳужжатлар архиви — DOCX, PDF
            </p>
            <div style={{ display: 'flex', gap: '20px', marginTop: '4px' }}>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                <FileText size={12} style={{ display: 'inline', marginRight: 4, verticalAlign: 'middle' }} />
                Жами: <strong>{files.length}</strong> файл
              </span>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                <HardDrive size={12} style={{ display: 'inline', marginRight: 4, verticalAlign: 'middle' }} />
                Ҳажми: <strong>{formatFileSize(totalSize)}</strong>
              </span>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button onClick={fetchFiles} style={{
            padding: '8px 16px', borderRadius: '10px', border: '1.5px solid #BFDBFE',
            background: 'white', color: '#2563EB', fontWeight: 700, fontSize: '0.8rem',
            cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px'
          }}>
            <RefreshCw size={14} /> Янгилаш
          </button>
          <label style={{
            padding: '10px 22px', borderRadius: '12px', border: 'none',
            background: 'linear-gradient(135deg, #2563EB, #7C3AED)', color: 'white',
            fontWeight: 800, cursor: 'pointer', display: 'flex', alignItems: 'center',
            gap: '8px', fontSize: '0.85rem', boxShadow: '0 4px 16px rgba(37,99,235,0.4)'
          }}>
            <Upload size={16} /> ФАЙЛ ЮКЛАШ
            <input type="file" accept=".docx,.pdf,.xlsx" multiple style={{ display: 'none' }}
              onChange={e => handleUpload(e.target.files)} />
          </label>
        </div>
      </div>

      {/* Search + Drop Zone */}
      <div style={{ marginBottom: '20px', display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: '250px' }}>
          <Search size={15} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input placeholder="Файл номи, мутахассис бўйича қидириш..." value={search} onChange={e => setSearch(e.target.value)}
            style={{
              width: '100%', padding: '12px 14px 12px 40px', borderRadius: '12px',
              border: '1.5px solid var(--border)', background: 'var(--bg-card)',
              fontSize: '0.9rem', outline: 'none', boxSizing: 'border-box'
            }} />
        </div>
        <div
          onDrop={handleDrop}
          onDragOver={e => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          style={{
            padding: '10px 28px', borderRadius: '12px',
            border: `2px dashed ${dragOver ? '#2563EB' : '#CBD5E1'}`,
            background: dragOver ? '#EFF6FF' : '#F8FAFC',
            color: dragOver ? '#2563EB' : '#94A3B8', fontWeight: 600,
            fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '8px',
            cursor: 'pointer', transition: 'all 0.2s', minWidth: '200px', justifyContent: 'center'
          }}
        >
          {uploading ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> : <Upload size={16} />}
          {uploading ? 'Юкланмоқда...' : 'Ёки файлни бу ерга тортинг'}
        </div>
      </div>

      {/* Folder Bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', flexWrap: 'wrap' }}>
        <button onClick={() => setCurrentFolder('')} style={{
          padding: '6px 14px', borderRadius: '8px', fontSize: '0.82rem', fontWeight: 700, cursor: 'pointer',
          border: currentFolder ? '1px solid var(--border)' : '1.5px solid #B48C64',
          background: currentFolder ? 'white' : '#FFF8F0', color: currentFolder ? 'var(--text-secondary)' : '#B48C64'
        }}>📁 Асосий</button>
        {currentFolder && (
          <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>/ {currentFolder}</span>
        )}
        <div style={{ flex: 1 }} />
        {showNewFolder ? (
          <div style={{ display: 'flex', gap: '6px' }}>
            <input value={newFolderName} onChange={e => setNewFolderName(e.target.value)} placeholder="Папка номи..."
              style={{ padding: '6px 12px', borderRadius: '8px', border: '1.5px solid #B48C64', fontSize: '0.82rem', width: '180px' }}
              autoFocus onKeyDown={e => { if (e.key === 'Enter') createFolder(); if (e.key === 'Escape') setShowNewFolder(false) }} />
            <button onClick={createFolder} style={{ padding: '6px 12px', borderRadius: '8px', border: 'none', background: '#B48C64', color: 'white', fontSize: '0.8rem', fontWeight: 700, cursor: 'pointer' }}>✓</button>
            <button onClick={() => setShowNewFolder(false)} style={{ padding: '6px 8px', borderRadius: '8px', border: '1px solid #ccc', background: 'white', fontSize: '0.8rem', cursor: 'pointer' }}>✕</button>
          </div>
        ) : (
          <button onClick={() => setShowNewFolder(true)} style={{
            padding: '6px 14px', borderRadius: '8px', border: '1.5px dashed #B48C64',
            background: 'transparent', color: '#B48C64', fontSize: '0.82rem', fontWeight: 700, cursor: 'pointer'
          }}>+ Янги папка</button>
        )}
      </div>

      {/* Subfolders */}
      {currentFolders.length > 0 && (
        <div style={{ display: 'flex', gap: '10px', marginBottom: '12px', flexWrap: 'wrap' }}>
          {currentFolders.map(f => (
            <div key={f.path} style={{
              padding: '12px 18px', borderRadius: '12px', border: '1px solid var(--border)',
              background: 'var(--bg-card)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '10px',
              minWidth: '140px', transition: 'all 0.15s'
            }}
              onClick={() => setCurrentFolder(f.path)}
              onDragOver={e => { e.preventDefault(); e.currentTarget.style.border = '2px solid #B48C64' }}
              onDragLeave={e => { e.currentTarget.style.border = '1px solid var(--border)' }}
              onDrop={e => { e.preventDefault(); e.currentTarget.style.border = '1px solid var(--border)'; if (dragFile) moveFile(dragFile, f.path) }}
            >
              <span style={{ fontSize: '1.5rem' }}>📁</span>
              <div>
                <div style={{ fontWeight: 700, fontSize: '0.85rem' }}>{f.name}</div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{f.file_count} файл</div>
              </div>
              <button onClick={e => { e.stopPropagation(); deleteFolder(f.path) }} style={{
                marginLeft: 'auto', padding: '4px', borderRadius: '6px', border: '1px solid #FECACA',
                background: '#FEF2F2', color: '#DC2626', cursor: 'pointer', fontSize: '0.7rem'
              }}><Trash2 size={12} /></button>
            </div>
          ))}
        </div>
      )}

      {/* File List */}
      <div style={{
        background: 'var(--bg-card)', borderRadius: '16px',
        border: '1px solid var(--border)', overflow: 'hidden',
        boxShadow: '0 2px 8px rgba(0,0,0,0.04)'
      }}>
        {loading ? (
          <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <Loader2 size={28} style={{ animation: 'spin 1s linear infinite', marginBottom: 12 }} />
            <p>Юкланмоқда...</p>
          </div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: '80px 40px', textAlign: 'center' }}>
            <div style={{ fontSize: '4rem', marginBottom: 16 }}>📂</div>
            <p style={{ fontWeight: 700, fontSize: '1.1rem', color: 'var(--text-primary)', marginBottom: 8 }}>Файллар ҳали юкланмаган</p>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>DOCX ёки PDF файлларни юклаш учун «ФАЙЛ ЮКЛАШ» тугмасини босинг</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {/* Header */}
            <div style={{
              display: 'grid', gridTemplateColumns: '40px 1fr 100px 120px 110px 200px',
              padding: '14px 20px', background: 'var(--bg-secondary)',
              borderBottom: '2px solid var(--border)', gap: '12px'
            }}>
              <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>№</span>
              <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>ФАЙЛ НОМИ</span>
              <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>ҲАЖМ</span>
              <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>МУТАХАССИС</span>
              <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>САНА</span>
              <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', textAlign: 'right' }}>АМАЛЛАР</span>
            </div>

            {/* File Rows */}
            {filtered.map((file, i) => (
              <div key={file.filename}
                draggable
                onDragStart={() => setDragFile(file.filename)}
                onDragEnd={() => setDragFile(null)}
                style={{
                  display: 'grid', gridTemplateColumns: '40px 1fr 100px 120px 110px 200px',
                  padding: '14px 20px', borderBottom: '1px solid var(--border)',
                  gap: '12px', alignItems: 'center', transition: 'background 0.15s',
                  cursor: 'grab', opacity: dragFile === file.filename ? 0.5 : 1
                }}
                onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = 'var(--bg-secondary)'}
                onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = ''}
              >
                <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-muted)' }}>{i + 1}</span>

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', overflow: 'hidden' }}>
                  <span style={{ fontSize: '1.5rem', flexShrink: 0 }}>{getFileIcon(file.extension)}</span>
                  <div style={{ overflow: 'hidden' }}>
                    <div style={{ fontWeight: 700, fontSize: '0.88rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {file.original_filename || file.filename}
                    </div>
                    {file.project_id && (
                      <div style={{ fontSize: '0.72rem', color: '#2563EB', fontWeight: 600 }}>
                        Лойиҳа: {file.project_id}
                      </div>
                    )}
                  </div>
                </div>

                <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontWeight: 500 }}>
                  {formatFileSize(file.size)}
                </span>

                <span style={{ fontSize: '0.82rem', color: '#16A34A', fontWeight: 600 }}>
                  {file.specialist_name || '—'}
                </span>

                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  {formatDate(file.modified_at)}
                </span>

                <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                  <button onClick={() => handlePreview(file.filename)} title="Кўриш"
                    style={{ padding: '7px 10px', borderRadius: '8px', border: '1px solid #BFDBFE', background: '#EFF6FF', color: '#2563EB', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.72rem', fontWeight: 600 }}>
                    <Eye size={13} /> Preview
                  </button>
                  <button onClick={() => handleOpenInEditor(file.filename)} disabled={!!openingFile} title="Таҳрирда очиш"
                    style={{
                      padding: '7px 10px', borderRadius: '8px', border: 'none',
                      background: openingFile === file.filename ? '#94A3B8' : 'linear-gradient(135deg, #2563EB, #7C3AED)',
                      color: 'white', cursor: openingFile ? 'not-allowed' : 'pointer',
                      display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.72rem', fontWeight: 600
                    }}>
                    {openingFile === file.filename ? <Loader2 size={13} style={{ animation: 'spin 1s linear infinite' }} /> : <Play size={13} />}
                    Очиш
                  </button>
                  <button onClick={() => handleDownload(file.filename)} title="Юклаб олиш"
                    style={{ padding: '7px', borderRadius: '8px', border: '1px solid #BBF7D0', background: '#F0FDF4', color: '#16A34A', cursor: 'pointer' }}>
                    <Download size={14} />
                  </button>
                  <button onClick={() => handleDelete(file.filename)} title="Ўчириш"
                    style={{ padding: '7px', borderRadius: '8px', border: '1px solid #FECACA', background: '#FEF2F2', color: '#DC2626', cursor: 'pointer' }}>
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Preview Modal */}
      {previewFile && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(6px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '20px'
        }}>
          <div style={{
            background: 'var(--bg-card)', borderRadius: '20px', width: '100%', maxWidth: '800px',
            maxHeight: '85vh', display: 'flex', flexDirection: 'column', boxShadow: '0 24px 64px rgba(0,0,0,0.25)'
          }}>
            <div style={{ padding: '20px 28px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#F0F7FF', borderRadius: '20px 20px 0 0' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <Eye size={20} color="#2563EB" />
                <h3 style={{ fontWeight: 800, fontSize: '1rem', margin: 0 }}>Файл preview: {previewFile.filename}</h3>
              </div>
              <button onClick={() => setPreviewFile(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
                <X size={20} />
              </button>
            </div>
            <div style={{ padding: '24px 28px', overflowY: 'auto', flex: 1 }}>
              {previewLoading ? (
                <div style={{ textAlign: 'center', padding: '40px' }}>
                  <Loader2 size={28} style={{ animation: 'spin 1s linear infinite', color: '#2563EB' }} />
                  <p style={{ marginTop: 12, color: 'var(--text-muted)' }}>Preview юкланмоқда...</p>
                </div>
              ) : (
                <pre style={{
                  fontFamily: "'Inter', monospace", fontSize: '0.85rem', lineHeight: '1.7',
                  whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: 'var(--text-primary)',
                  background: '#F8FAFC', padding: '20px', borderRadius: '12px',
                  border: '1px solid var(--border)', margin: 0
                }}>
                  {previewFile.content || 'Матн топилмади'}
                </pre>
              )}
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
