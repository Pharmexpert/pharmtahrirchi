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
  // Long timeout for AI inference (CPU Llama/Mistral can take 60-120 sec)
  const isAiEndpoint = path.includes('/assistant/') || path.includes('/ai-improve') || path.includes('/translate') || path.includes('/check')
  const timeoutMs = isAiEndpoint ? 180000 : 30000  // 3 min for AI, 30s for others
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs)

  try {
    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
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
  } catch (e: any) {
    if (e.name === 'AbortError') {
      throw new ApiError(408, `Сўров вақти тугади (${timeoutMs / 1000}с). Локал AI моделлар секин ишлаши мумкин — қайта уриниб кўринг.`)
    }
    throw e
  } finally {
    clearTimeout(timeoutId)
  }
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
  add: (word: string, lang = 'uz') => post<{ ok: boolean; word?: string; error?: string }>('/api/dictionary/add', { word, lang }),
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
  downloadBlob: async (filename: string): Promise<Blob> => {
    const res = await fetch(`${API_BASE}/api/files/${encodeURIComponent(filename)}/download`, {
      headers: authHeaders(''),
    })
    if (!res.ok) throw new ApiError(res.status, `HTTP ${res.status}`)
    return res.blob()
  },
  listFolders: () => get<{ folders: any[] }>('/api/folders'),
  createFolder: (name: string, parent: string) =>
    post<{ success: boolean }>('/api/folders/create', { name, parent }),
  deleteFolder: (folderPath: string) =>
    del<{ success: boolean }>(`/api/folders/${encodeURIComponent(folderPath)}`),
  move: (filename: string, target_folder: string) =>
    post<{ success: boolean }>('/api/files/move', { filename, target_folder }),
  moveFolder: (folder: string, target: string) =>
    post<{ success: boolean }>('/api/folders/move', { folder, target }),
  renameFolder: (path: string, new_name: string) =>
    put<{ success: boolean }>('/api/folders/rename', { path, new_name }),
  uploadSimple: async (file: File): Promise<{ success: boolean; filename: string }> => {
    const fd = new FormData()
    fd.append('file', file)
    const res = await fetch(`${API_BASE}/api/files/upload`, {
      method: 'POST',
      headers: authHeaders(''),
      body: fd,
    })
    if (!res.ok) throw new ApiError(res.status, `HTTP ${res.status}`)
    return res.json()
  },
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
  delete: (id: number) => del<{ success: boolean }>(`/api/dashboard/${id}`),
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
  all: () => get<{ annotated: any[]; disputed: any[]; abbreviations: any[] }>('/api/linguistic/all'),
  save: (data: Record<string, unknown>) => post<{ success: boolean }>('/api/linguistic/save', data),
  update: (category: string, id: number, data: Record<string, unknown>) =>
    put<{ success: boolean }>(`/api/linguistic/update/${category}/${id}`, data),
  remove: (category: string, id: number) =>
    del<{ success: boolean }>(`/api/linguistic/delete/${category}/${id}`),
  transliterate: (text: string, target: string) =>
    post<{ text: string }>('/api/transliterate', { text, target }),
  normalizeDrug: (name: string) =>
    post<any>('/api/tilshunos/normalize-drug', { name }),
}

export const billing = {
  plans: () => get<any>('/api/billing/plans'),
  subscription: () => get<any>('/api/billing/subscription'),
  checkout: (plan: string) => post<any>('/api/billing/checkout', { plan }),
}

// ═══════════════════════════════════════════════════
// Admin
// ═══════════════════════════════════════════════════

export const admin = {
  dbStats: () => get<import('../types/api').DbStats>('/api/admin/db-stats'),
  dbSnapshots: (limit = 20) => get<{ history: Record<string, Array<{ count: number; at: string }>> }>(`/api/admin/db-snapshots?limit=${limit}`),
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
  canEditDb: (userId: string, can_edit: boolean) =>
    post<{ success: boolean; can_edit_db: number }>('/api/admin/can-edit-db', { userId, can_edit }),
  blockUser: (userId: string, blocked: boolean) =>
    post<{ success: boolean; is_blocked: number }>('/api/admin/users/block', { userId, blocked }),
  userActivity: (userId: string, limit = 100) =>
    get<{ user: any; activity: any[] }>(`/api/admin/users/${encodeURIComponent(userId)}/activity?limit=${limit}`),
  // Pharma DB
  drugs: (q = '', limit = 100) => get<{ drugs: any[]; total: number }>(`/api/admin/drugs?q=${encodeURIComponent(q)}&limit=${limit}`),
  addDrug: (drug: any) => post<{ success: boolean; id?: number; error?: string }>('/api/admin/drugs', drug),
  seedDrugs: () => post<{ success: boolean; inserted?: number }>('/api/admin/drugs/seed', {}),
  seedUzbekRules: () => post<{ success: boolean; spelling_rules_inserted?: number; sayqallash_total?: number; definitions_added?: number; suffixes_added?: number }>('/api/admin/uzbek-rules/seed', {}),
  monitoring: (period: 'daily' | 'weekly' | 'monthly' = 'daily') =>
    get<{
      period: string
      users_total: number
      users_active: number
      sayqallash_total: number
      sayqallash_new: number
      ai_calls_total: number
      ai_usage: Record<string, number>
      edits_total: number
      top_users: Array<{ user_id: string; user_name: string; count: number }>
      daily_chart: Array<{ date: string; count: number }>
      ai_chart: Array<{ date: string; count: number }>
      drugs_total: number
      terms_total: number
      projects_total: number
      alignments_total: number
    }>(`/api/admin/monitoring/overview?period=${period}`),
  medicalTerms: (q = '', limit = 100) => get<{ terms: any[]; total: number }>(`/api/admin/medical-terms?q=${encodeURIComponent(q)}&limit=${limit}`),
  addMedicalTerm: (term: any) => post<{ success: boolean; id?: number; error?: string }>('/api/admin/medical-terms', term),
  addRule: (rule: Record<string, unknown>) => post<{ success: boolean }>('/api/admin/rules', rule),
  updateRule: (id: number, rule: Record<string, unknown>) => put<{ success: boolean }>(`/api/admin/rules/${id}`, rule),
  deleteRule: (id: number) => del<{ success: boolean }>(`/api/admin/rules/${id}`),
  setRuleQuality: (id: number, quality_flag: string) =>
    post<{ status: string }>(`/api/admin/rules/${id}/quality`, { quality_flag }),
  // Seed / import endpoints
  importKmashrab: () => post<any>('/api/admin/wordlists/import-kmashrab', {}),
  importExtras: () => post<any>('/api/admin/wordlists/import-extras', {}),
  importTahrirchi: () => post<any>('/api/admin/tahrirchi/import-datasets', {}),
  segmentDomains: () => post<any>('/api/admin/sayqallash/domain-segment', {}),
  importWhoInn: () => post<any>('/api/admin/drugs/import-who', {}),
  dbBackup: () => post<any>('/api/admin/db/backup', {}),
  // New Uzbek spellcheck sources
  importUzbekSpell: () => post<any>('/api/admin/wordlists/import-uzbek-spell', {}),
  importUzbekNet: () => post<any>('/api/admin/wordlists/import-uzbek-net', {}),
  importUzhungenQoida: () => post<any>('/api/admin/wordlists/import-uzhungen-qoida', {}),
  // Post-processing
  buildFreqRankings: () => post<any>('/api/admin/post-process/freq-rankings', {}),
  mergeAffixDescriptions: () => post<any>('/api/admin/post-process/merge-affix', {}),
  autoRepRules: () => post<any>('/api/admin/post-process/auto-rep-rules', {}),
  importPharmacopoeia: () => post<any>('/api/admin/pharmacopoeia/import', {}),
  importDisputedBoard: () => post<any>('/api/admin/disputed-board/import', {}),
  disputedBoard: (q = '') => get<{ rows: any[]; total: number }>(`/api/admin/disputed-board${q ? `?q=${encodeURIComponent(q)}` : ''}`),
  importPharmaDb: () => post<any>('/api/admin/pharma-db/import', {}),
  importPharmaColors: () => post<any>('/api/admin/pharma-db/import-colors', {}),
  importPharmaReports: () => post<any>('/api/admin/pharma-reports/import', {}),
  importIzohliLugat: () => post<any>('/api/admin/izohli-lugat/import', {}),
  importSiUnits: () => post<any>('/api/admin/si-units/import', {}),
  importUzbekQoidalari: () => post<any>('/api/admin/uzbek-qoidalari/import', {}),
  importPromtResources: () => post<any>('/api/admin/promt-resources/import', {}),
  translateAnnotatedBatch: (limit = 100) => post<{ success: boolean; processed?: number; updated?: number; remaining_before?: number; remaining_after?: number; error?: string }>(`/api/admin/annotated/translate-batch?limit=${limit}`, {}),
  dataFilesCheck: () => get<{ files: any[]; total: number; present: number; missing: number }>('/api/admin/data-files/check'),
  pharmaToc: (q = '', edition = '') => get<{ rows: any[]; total: number }>(`/api/admin/pharma-db/toc?${new URLSearchParams({ q, edition }).toString()}`),
  pharmaRegistry: (q = '', country = '', atc = '') => get<{ rows: any[]; total: number }>(`/api/admin/pharma-db/registry?${new URLSearchParams({ q, country, atc }).toString()}`),
  pharmaColors: (q = '') => get<{ rows: any[]; total: number }>(`/api/admin/pharma-db/colors${q ? `?q=${encodeURIComponent(q)}` : ''}`),
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

// ═══════════════════════════════════════════════════
// Phase 2: Morphology Analyzer
// ═══════════════════════════════════════════════════

export interface MorphMorpheme {
  surface: string
  kind: 'stem' | 'suffix' | 'prefix'
  gloss: string
  category: string
}

export interface MorphAnalysis {
  word: string
  stem: string
  pos: string
  morphemes: MorphMorpheme[]
  tense: string | null
  person: number | null
  number: string | null
  case: string | null
  mood: string | null
  negation: boolean
  breakdown: string
  source: string
  valid: boolean
  valid_order?: boolean
  order_score?: number
  order_issues?: string[]
}

export const morph = {
  analyze: (word: string) =>
    post<MorphAnalysis>('/api/morph/analyze', { word }),
  analyzeText: (text: string) =>
    post<{ analyses: MorphAnalysis[]; unknowns: string[]; total_words: number; recognized: number; unknown: number }>(
      '/api/morph/analyze-text',
      { text }
    ),
  validate: (words: string[]) =>
    post<{ results: Record<string, boolean>; total: number }>('/api/morph/validate', { words }),
  flags: () => get<{ flags: Record<string, any>; total: number }>('/api/morph/flags'),
}

// ═══════════════════════════════════════════════════
// Phase 4: Grammar Checker
// ═══════════════════════════════════════════════════

export interface GrammarIssue {
  word: string
  from_index: number
  to_index: number
  issue_type: string
  message: string
  suggestions: string[]
  source: string
  confidence: number
}

export const grammar = {
  check: (text: string, lang = 'uz') =>
    post<{ issues: GrammarIssue[]; total: number; by_type: Record<string, number>; lang: string }>(
      '/api/grammar/check',
      { text, lang }
    ),
  lexiconSearch: (word: string, k = 10) =>
    post<{ results: Array<{ word: string; frequency: number; similarity: number }>; total: number }>(
      '/api/grammar/lexicon-search',
      { word, k }
    ),
}

// ═══════════════════════════════════════════════════
// Phase 5: Self-Learning Loop
// ═══════════════════════════════════════════════════

export interface LearnResult {
  success: boolean
  rule_id?: number
  rule_action?: 'inserted' | 'updated'
  bert_indexed?: boolean
  faiss_added?: boolean
  lexicon_added?: boolean
  activity_logged?: boolean
  reason?: string
}

export const learn = {
  correction: (payload: {
    wrong: string
    correct: string
    context?: string
    error_type?: string
    lang?: string
  }) => post<LearnResult>('/api/learn/correction', payload),
  batch: (corrections: Array<{
    wrong: string
    correct: string
    context?: string
    error_type?: string
    lang?: string
  }>, lang = 'uz') =>
    post<{ success: boolean; total: number; inserted: number; updated: number; bert_indexed: number; lexicon_added: number; results: LearnResult[] }>(
      '/api/learn/batch',
      { corrections, lang }
    ),
  stats: (since_days = 7) =>
    get<{
      since_days: number
      total_recent_actions: number
      by_error_type: Record<string, number>
      top_users: Array<{ user: string; count: number }>
      total_learned_rules: number
      total_rules: number
      learning_ratio: number
    }>(`/api/learn/stats?since_days=${since_days}`),
}

// ═══════════════════════════════════════════════════
// Phase 7: NLP Admin / Health
// ═══════════════════════════════════════════════════

export const nlp = {
  health: () => get<{ overall: string; components: Record<string, any> }>('/api/nlp/health'),
  growNow: () => post<{ success: boolean; summary: any }>('/api/nlp/grow-now', {}),
  growthHistory: (limit = 30) => get<{ runs: any[]; limit: number }>(`/api/nlp/growth-history?limit=${limit}`),
  dashboardSummary: () => get<{ last_7_days: any; last_30_days: any; recent_nightly_runs: any[] }>('/api/nlp/dashboard-summary'),
}

// ═══════════════════════════════════════════════════
// Phase 8: Tilshunos (Linguist) integrated workflow
// ═══════════════════════════════════════════════════

export interface LinguisticIssue {
  category: string
  subcategory: string
  rule_id: string
  error_type: string
  from_index: number
  to_index: number
  matched_text: string
  suggestion: string
  message: string
  severity: 'low' | 'medium' | 'high'
  source: string
}

export interface TilshunosCheckResult {
  text: string
  lang: string
  issues: LinguisticIssue[]
  by_category: Record<string, number>
  by_severity: Record<string, number>
  total: number
  morphology: any[]
  score: number
  word_count: number
}

export const tilshunos = {
  rulesStats: () => get<{
    canonical_rules: Record<string, number>
    sayqallash_total: number
    sayqallash_by_type: Record<string, number>
    hunspell: Record<string, number>
    tahrirchi_lexicon_words: number
    platform_databases: Record<string, number>
  }>('/api/tilshunos/rules/stats'),

  check: (text: string, lang = 'uz', categories?: string[]) =>
    post<TilshunosCheckResult>('/api/tilshunos/check', { text, lang, categories }),

  classify: (text: string, lang = 'uz') =>
    post<{
      spans: Array<{ from: number; to: number; word: string; category: 'known' | 'annotated' | 'disputed' | 'abbreviation' | 'unknown' }>
      counts: Record<string, number>
    }>('/api/tilshunos/classify', { text, lang }),

  improve: (text: string, lang = 'uz', auto_apply_severity: 'low' | 'medium' | 'high' = 'high') =>
    post<{
      original_text: string
      improved_text: string
      applied_fixes: any[]
      fix_count: number
      remaining_issues: LinguisticIssue[]
    }>('/api/tilshunos/improve', { text, lang, auto_apply_severity }),

  confirm: (payload: { wrong: string; correct: string; context?: string; category?: string; lang?: string }) =>
    post<LearnResult>('/api/tilshunos/confirm', payload),

  learnDiff: (original: string, corrected: string, lang = 'uz', source = 'tilshunos_edit') =>
    post<{ learned: number; pairs: Array<{ wrong: string; correct: string }> }>('/api/tilshunos/learn-diff', { original, corrected, lang, source }),

  translate: (text: string, source_lang: string, target_lang: string) =>
    post<{ translated: string; engine?: string }>('/api/tilshunos/translate', { text, source_lang, target_lang }),

  aiImprove: (text: string, lang = 'uz') =>
    post<{ improved: string; engine?: string }>('/api/tilshunos/ai-improve', { text, lang }),

  grammarScore: (text: string) =>
    post<{ score: number }>('/api/tilshunos/grammar-score', { text }),

  translationQuality: (source: string, target: string) =>
    post<{ semantic_score: number; llm_note?: string }>('/api/tilshunos/translation-quality', { source, target }),

  aiStatus: () =>
    get<{ bert: boolean; mistral: any; llama: any; russian: any; nllb: any; ner: any; gemini: boolean; anthropic: boolean }>('/api/tilshunos/ai-status'),

  publicAiEngines: () =>
    get<{ engines: Record<string, any> }>('/api/ai-engines'),

  extractEntities: (text: string) =>
    post<{ entities: Array<{ text: string; from: number; to: number; type: string; score?: number }>; stats: Record<string, number> }>('/api/tilshunos/extract-entities', { text }),

  extractLinguistic: (text: string) =>
    post<{ annotated: any[]; disputed: any[]; abbreviations: any[] }>('/api/tilshunos/extract-linguistic', { text }),

  learnLinguistic: (category: 'annotated' | 'disputed' | 'abbreviations', items: any[]) =>
    post<{ success: boolean; added?: number; error?: string }>('/api/tilshunos/learn-linguistic', { category, items }),

  decomposeTerm: (word: string) =>
    post<{ found: boolean; prefix?: string; root?: string; suffix?: string; meaning?: string; prefix_meaning?: string; suffix_meaning?: string }>('/api/tilshunos/decompose-term', { word }),

  styleRules: (category?: string) =>
    get<{ rules: any[]; total: number }>(`/api/tilshunos/style-rules${category ? `?category=${category}` : ''}`),

  checkStyle: (text: string) =>
    post<{ violations: Array<{ rule_id: string; category: string; severity: string; description: string; suggestion: string; from: number; to: number; matched: string }>; total: number }>('/api/tilshunos/check-style', { text }),

  saveDocVersion: (payload: { text_id: string; sentence_no: number; lang: string; content: string; author_id?: string; author_name?: string; action?: string }) =>
    post<{ success: boolean; version?: number }>('/api/document-versions/save', payload),

  getDocVersions: (text_id: string, sentence_no: number, lang?: string) =>
    get<{ versions: any[] }>(`/api/document-versions/${encodeURIComponent(text_id)}/${sentence_no}${lang ? `?lang=${lang}` : ''}`),

  updateParagraphProgress: (payload: { text_id: string; sentence_no: number; status: string; reviewer_id?: string; reviewer_name?: string; notes?: string; ai_score?: number }) =>
    post<{ success: boolean }>('/api/paragraph-progress/update', payload),

  getParagraphProgress: (text_id: string) =>
    get<{ rows: any[]; stats: Record<string, number>; total: number }>(`/api/paragraph-progress/${encodeURIComponent(text_id)}`),

  trainingLogExport: (kind?: string, limit = 10000) => {
    const qs = new URLSearchParams()
    if (kind) qs.set('kind', kind)
    qs.set('limit', String(limit))
    return get<{ training_log: any[]; training_log_count: number; sayqallash_rules: any[]; sayqallash_count: number; total: number }>(`/api/tilshunos/training-log/export?${qs.toString()}`)
  },

  extractText: async (file: File): Promise<{ text: string }> => {
    const fd = new FormData()
    fd.append('file', file)
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null
    const res = await fetch(`${API_BASE}/api/tilshunos/extract-text`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: fd,
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },
}

// ═══════════════════════════════════════════════════
// Pharmacist Assistant
// ═══════════════════════════════════════════════════
export const assistant = {
  engines: () => get<{ engines: Array<{ key: string; label: string; available: boolean; mode?: string; model?: string; languages?: string[]; capabilities?: string[] }> }>('/api/assistant/engines'),
  chat: (message: string, opts: { engine?: string; lang?: string; history?: Array<{ role: string; content: string }>; system?: string } = {}) =>
    post<{ text: string; engine?: string; error?: string }>('/api/assistant/chat', { message, ...opts }),
  edit: (text: string, opts: { engine?: string; lang?: string } = {}) =>
    post<{ text: string; engine?: string; error?: string }>('/api/assistant/edit', { text, ...opts }),
  translate: (text: string, opts: { engine?: string; source_lang?: string; target_lang?: string } = {}) =>
    post<{ text: string; engine?: string; error?: string }>('/api/assistant/translate', { text, ...opts }),
  upload: async (file: File, kind = 'auto') => {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('kind', kind)
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null
    const res = await fetch(`${API_BASE}/api/assistant/upload`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: fd,
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json() as Promise<{ filename: string; size: number; size_mb: number; kind: string; text?: string; base64?: string; mime?: string; transcribed?: boolean }>
  },

  // Chat history
  saveChat: (payload: { session_id?: string; title?: string; messages: any[]; engine?: string; lang?: string; mode?: string }) =>
    post<{ success: boolean; session_id?: string }>('/api/assistant/history/save', payload),
  listChats: () =>
    get<{ chats: Array<{ id: number; session_id: string; title: string; engine: string; lang: string; mode: string; created_at: string; updated_at: string }> }>('/api/assistant/history/list'),
  getChat: (session_id: string) =>
    get<{ found: boolean; chat?: { session_id: string; title: string; messages: any[]; engine: string; lang: string; mode: string } }>(`/api/assistant/history/${encodeURIComponent(session_id)}`),
  deleteChat: (session_id: string) =>
    del<{ success: boolean }>(`/api/assistant/history/${encodeURIComponent(session_id)}`),
}

// Unified analyze (4-layer)
export const analyze = {
  full: (text: string, lang = 'uz', layers?: string[]) =>
    post<{
      morph: any[]
      sayqallash: any[]
      syntax: any[]
      style: any[]
      total: number
      summary: { morph_count: number; sayqallash_count: number; syntax_count: number; style_count: number }
    }>('/api/analyze/full', { text, lang, layers }),
}

// Syntax (Phase 3)
export const syntax = {
  analyze: (text: string) => post<any>('/api/syntax/analyze', { text }),
  check: (text: string) => post<{ errors: any[]; count: number }>('/api/syntax/check', { text }),
  reorder: (text: string) => post<{ original: string; canonical: string }>('/api/syntax/reorder', { text }),
  saveRule: (wrong: string, correct: string, explanation = '') =>
    post<{ success: boolean; id?: number }>('/api/syntax/save-rule', { wrong, correct, explanation }),
  templates: (limit = 50) => get<{ templates: any[] }>(`/api/syntax/templates?limit=${limit}`),
  stats: () => get<Record<string, number>>('/api/syntax/stats'),
  parts: (word: string) => get<{ word: string; roles: Array<{ role: string; freq: number; percentage: number }>; total_observations: number }>(`/api/syntax/parts/${encodeURIComponent(word)}`),
  assignRole: (word: string, role: string, pos?: string, context?: string) =>
    post<{ success: boolean; action: string; frequency: number }>('/api/syntax/assign-role', { word, role, pos, context }),
  // GECTurk endpoints
  verifyRules: (limit = 5000) => post<any>('/api/syntax/verify-rules', { limit }),
  noisyRules: (limit = 100) => get<{ rules: any[] }>(`/api/syntax/noisy-rules?limit=${limit}`),
  deleteNoisy: (confirm: boolean) => post<{ deleted: number }>('/api/syntax/delete-noisy', { confirm }),
  generateSynth: (limit_sentences = 1000, transforms_per_sent = 5) =>
    post<any>('/api/syntax/generate-synth', { limit_sentences, transforms_per_sent }),
  exportTraining: () => post<{ exported: number; path: string }>('/api/syntax/export-training', {}),
}

// Re-export everything as default namespace
const api = {
  auth, projects, editor, sayqallash, dictionary, synonyms,
  files, upload, dashboard, linguistic, admin, profile, user, specialists,
  morph, grammar, learn, nlp, tilshunos, assistant, billing, syntax, analyze,
  API_BASE,
}

export default api
