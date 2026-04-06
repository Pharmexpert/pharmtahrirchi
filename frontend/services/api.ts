/**
 * Centralized API client for Pharma Aligner.
 * Eliminates duplicated fetch() calls across components.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('pharma_token')
}

function authHeaders(contentType = 'application/json'): Record<string, string> {
  const token = getToken()
  const headers: Record<string, string> = {}
  if (contentType) headers['Content-Type'] = contentType
  if (token) headers['Authorization'] = `Bearer ${token}`
  return headers
}

class ApiError extends Error {
  status: number
  detail: string
  constructor(status: number, detail: string) {
    super(detail)
    this.status = status
    this.detail = detail
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${path}`
  const res = await fetch(url, {
    ...options,
    headers: {
      ...authHeaders(),
      ...options.headers,
    },
  })

  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const err = await res.json()
      detail = err.detail || err.message || detail
    } catch {}
    throw new ApiError(res.status, detail)
  }

  const contentType = res.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    return res.json()
  }
  return res as unknown as T
}

function get<T>(path: string): Promise<T> {
  return request<T>(path)
}

function post<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined,
  })
}

function put<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: 'PUT',
    body: body ? JSON.stringify(body) : undefined,
  })
}

function del<T>(path: string): Promise<T> {
  return request<T>(path, { method: 'DELETE' })
}

// ═══════════════════════════════════════════════════
// Auth
// ═══════════════════════════════════════════════════

export const auth = {
  me: () => get<{ user: import('../types/api').User }>('/api/auth/me'),
  login: (email: string, password: string) =>
    post<import('../types/api').AuthResponse>('/api/auth/login', { email, password }),
  register: (data: { email: string; name: string; password: string; department?: string }) =>
    post<{ success: boolean; message: string }>('/api/auth/register', data),
  google: (credential: string) =>
    post<import('../types/api').AuthResponse>('/api/auth/google', { credential }),
  forgotPassword: (email: string) =>
    post<{ success: boolean; message: string }>('/api/auth/forgot-password', { email }),
  resetPassword: (email: string, code: string, password: string) =>
    post<{ success: boolean; message: string }>('/api/auth/reset-password', { email, code, password }),
}

// ═══════════════════════════════════════════════════
// Projects
// ═══════════════════════════════════════════════════

export const projects = {
  list: () => get<{ projects: import('../types/api').Project[] }>('/api/projects'),
  delete: (id: string) => del<{ success: boolean }>(`/api/projects/${id}`),
  finish: (id: string, data: unknown[], specialist_name: string) =>
    post<{ status: string }>(`/api/projects/${id}/finish`, { data, specialist_name }),
  export: (id: string) => request<Response>(`/api/projects/${id}/export`),
  preview: (id: string) => get<{ alignments: import('../types/api').RowData[] }>(`/api/projects/${id}/preview`),
  polishingSummary: (id: string) =>
    get<{ status: string; summary?: import('../types/api').PolishingSummary }>(`/api/projects/${id}/polishing-summary`),
}

// ═══════════════════════════════════════════════════
// Editor / Alignments
// ═══════════════════════════════════════════════════

export const editor = {
  history: (textId: string) => get<{ alignments: import('../types/api').RowData[] }>(`/api/history/${textId}`),
  save: (project_id: string, data: unknown[], specialist_name: string) =>
    post<{ status: string }>('/api/save', { project_id, data, specialist_name }),
  saveRow: (payload: Record<string, unknown>) => post<{ status: string; new_id?: number }>('/api/save-row', payload),
  deleteRow: (textId: string, sentenceNo: number) =>
    del<{ status: string }>(`/api/delete-row/${textId}/${sentenceNo}`),
  exportDocx: (filename: string, data: unknown[]) =>
    request<Response>('/api/export', { method: 'POST', body: JSON.stringify({ filename, data }) }),
  alignDocument: (data: unknown[]) =>
    post<import('../types/api').AlignDocumentResponse>('/api/align-document', { data }),
  improveRow: (payload: Record<string, unknown>) =>
    post<Record<string, unknown>>('/api/improve-row', payload),
  splitRow: (row: Record<string, unknown>) =>
    post<{ row1: import('../types/api').RowData; row2: import('../types/api').RowData }>('/api/split-row', { row }),
  autoNotes: (v1: string, proposed: string, lang: string) =>
    post<{ notes: string }>('/api/auto-notes', { v1, proposed, lang }),
}

// ═══════════════════════════════════════════════════
// Sayqallash (GEC)
// ═══════════════════════════════════════════════════

export const sayqallash = {
  check: (text: string, lang: string, context_en?: string) =>
    post<import('../types/api').SayqallashResponse>('/sayqallash', { text, lang, context_en }),
  batch: (items: Array<{ text: string; lang: string; context_en?: string }>) =>
    post<{ results: import('../types/api').SayqallashResponse[] }>('/api/sayqallash/batch', { items }),
  batchRows: (rows: Array<{ id?: number; text: string; en?: string }>, lang: string) =>
    post<{ results: Array<{ id?: number; corrected: string; annotations: unknown[] }> }>('/api/sayqallash-batch', { rows, lang }),
  learnBatch: (corrections: Array<{ old_value: string; new_value: string; error_type?: string }>, lang: string) =>
    post<{ success: boolean; count: number }>('/api/sayqallash/learn-batch', { corrections, lang }),
}

// ═══════════════════════════════════════════════════
// Dictionary & NLP
// ═══════════════════════════════════════════════════

export const dictionary = {
  autocomplete: (prefix: string, limit = 10) =>
    post<{ words: import('../types/api').DictionaryWord[] }>('/api/dictionary/autocomplete', { prefix, limit }),
  suggest: (word: string) =>
    post<{ suggestions: import('../types/api').DictionarySuggestion[]; in_dictionary: boolean }>('/api/dictionary/suggest', { word }),
  bertSynonyms: (word: string, context: string, lang: string) =>
    post<{ synonyms: string[]; source: string }>('/api/bert/synonyms', { word, context, lang }),
  words: (language: string, page: number, per_page: number, search: string) =>
    get<{ words: any[]; total: number; total_pages: number }>(`/api/dictionary/words?language=${language}&page=${page}&per_page=${per_page}&search=${encodeURIComponent(search)}`),
  affixFlags: (language: string, page: number, per_page: number, search: string) =>
    get<{ flags: any[]; total: number; total_pages: number }>(`/api/dictionary/affix-flags?language=${language}&page=${page}&per_page=${per_page}&search=${encodeURIComponent(search)}`),
  translate: (word: string) => post<{ ru: string; en: string; definition: string }>('/api/dictionary/translate', { word }),
  translations: (words: string) => get<{ translations: Record<string, any> }>(`/api/dictionary/translations?words=${encodeURIComponent(words)}`),
}

// ═══════════════════════════════════════════════════
// Synonyms
// ═══════════════════════════════════════════════════

export const synonyms = {
  list: (word?: string, lang?: string) => {
    const params = new URLSearchParams()
    if (word) params.set('word', word)
    if (lang) params.set('lang', lang)
    const qs = params.toString()
    return get<{ synonyms: import('../types/api').Synonym[]; total: number }>(`/api/synonyms${qs ? `?${qs}` : ''}`)
  },
  save: (word: string, synonym: string, lang: string) =>
    post<{ status: string }>('/api/synonyms/save', { word, synonym, lang }),
  select: (word: string, synonym: string, lang: string) =>
    post<{ status: string }>('/api/synonyms/select', { word, synonym, lang }),
  delete: (id: number) => del<{ status: string }>(`/api/synonyms/${id}`),
  update: (id: number, data: { word?: string; synonym?: string }) =>
    put<{ status: string }>(`/api/synonyms/${id}`, data),
  listGrouped: (word?: string, lang?: string) => {
    const params = new URLSearchParams()
    if (word) params.set('word', word)
    if (lang) params.set('lang', lang)
    params.set('grouped', 'true')
    return get<{ groups: any[]; total_words: number; total_synonyms: number }>(`/api/synonyms?${params}`)
  },
  suggestEdits: (payload: Record<string, string>) =>
    post<import('../types/api').SynonymSuggestion>('/suggest-edits', payload),
}

// ═══════════════════════════════════════════════════
// Files
// ═══════════════════════════════════════════════════

export const files = {
  list: () => get<{ files: import('../types/api').UploadedFile[] }>('/api/files'),
  upload: async (file: File, onProgress?: (pct: number) => void): Promise<{ success: boolean; filename: string; original: string }> => {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      xhr.open('POST', `${API_BASE}/api/files/upload`)
      const token = getToken()
      if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)
      if (onProgress) {
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100))
        }
      }
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) resolve(JSON.parse(xhr.responseText))
        else reject(new ApiError(xhr.status, xhr.statusText))
      }
      xhr.onerror = () => reject(new Error('Upload failed'))
      const fd = new FormData()
      fd.append('file', file)
      xhr.send(fd)
    })
  },
  download: (filename: string) => `${API_BASE}/api/files/${filename}/download`,
  preview: (filename: string) => get<{ preview: string; filename: string }>(`/api/files/${filename}/preview`),
  delete: (filename: string) => del<{ success: boolean }>(`/api/files/${filename}`),
  open: (filename: string, mode = 'auto') =>
    post<{ filename: string; data: import('../types/api').RowData[]; text_id: string }>(`/api/files/${filename}/open?mode=${mode}`, {}),
}

// ═══════════════════════════════════════════════════
// Upload & Process
// ═══════════════════════════════════════════════════

export const upload = {
  process: async (
    file: File,
    mode = 'auto',
    textId = '',
    onProgress?: (pct: number) => void
  ): Promise<{ filename: string; data: import('../types/api').RowData[]; text_id: string }> => {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      xhr.open('POST', `${API_BASE}/api/upload?mode=${mode}&text_id=${encodeURIComponent(textId)}`)
      const token = getToken()
      if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)
      if (onProgress) {
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100))
        }
      }
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) resolve(JSON.parse(xhr.responseText))
        else reject(new ApiError(xhr.status, xhr.statusText))
      }
      xhr.onerror = () => reject(new Error('Upload failed'))
      const fd = new FormData()
      fd.append('file', file)
      xhr.send(fd)
    })
  },
}

// ═══════════════════════════════════════════════════
// Dashboard
// ═══════════════════════════════════════════════════

export const dashboard = {
  all: () => get<{ entries: import('../types/api').DashboardEntry[] }>('/api/dashboard/all'),
  record: (entry: Record<string, string>) => post<{ success: boolean }>('/api/dashboard/record', entry),
}

// ═══════════════════════════════════════════════════
// Linguistic
// ═══════════════════════════════════════════════════

export const linguistic = {
  analyze: (payload: Record<string, unknown>) =>
    post<{ results: import('../types/api').LinguisticItem[] }>('/api/linguistic/analyze', payload),
  synonyms: (payload: Record<string, string>) =>
    post<{ synonyms: string[] }>('/api/linguistic/synonyms', payload),
  transliterateBatch: (texts: string[], target: string) =>
    post<{ texts: string[] }>('/api/transliterate-batch', { texts, target }),
}

// ═══════════════════════════════════════════════════
// Admin
// ═══════════════════════════════════════════════════

export const admin = {
  dbStats: () => get<import('../types/api').DbStats>('/api/admin/db-stats'),
  rules: (lang?: string) => {
    const qs = lang ? `?lang=${lang}` : ''
    return get<{ rules: import('../types/api').SayqallashRule[] }>(`/api/admin/rules${qs}`)
  },
  users: () => get<{ users: any[] }>('/api/admin/users'),
  activity: (limit = 200) => get<{ entries: any[] }>(`/api/admin/activity?limit=${limit}`),
  approve: (user_id: string, status: 'approved' | 'rejected') =>
    post<{ success: boolean }>('/api/admin/approve', { user_id, status }),
  role: (user_id: string, role: string) =>
    post<{ success: boolean }>('/api/admin/role', { user_id, role }),
  addRule: (rule: Record<string, unknown>) => post<{ success: boolean }>('/api/admin/rules', rule),
  updateRule: (id: number, rule: Record<string, unknown>) => put<{ success: boolean }>(`/api/admin/rules/${id}`, rule),
  deleteRule: (id: number) => del<{ success: boolean }>(`/api/admin/rules/${id}`),
}

// ═══════════════════════════════════════════════════
// Profile
// ═══════════════════════════════════════════════════

export const profile = {
  update: (data: { name?: string; email?: string }) => post<{ status: string }>('/api/profile/update', data),
  changePassword: (old_password: string, new_password: string) =>
    post<{ status: string }>('/api/profile/password', { old_password, new_password }),
}

// ═══════════════════════════════════════════════════
// User
// ═══════════════════════════════════════════════════

export const user = {
  me: () => get<import('../types/api').User>('/api/user/me'),
  update: (data: Record<string, unknown>) => put<{ success: boolean }>('/api/user/me', data),
}

// ═══════════════════════════════════════════════════
// Specialists
// ═══════════════════════════════════════════════════

export const specialists = {
  list: () => get<{ specialists: string[] }>('/api/specialists'),
}

// Re-export everything as default namespace
const api = {
  auth, projects, editor, sayqallash, dictionary, synonyms,
  files, upload, dashboard, linguistic, admin, profile, user, specialists,
  API_BASE,
}

export default api
