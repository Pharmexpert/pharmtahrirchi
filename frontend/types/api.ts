// ═══════════════════════════════════════════════════
// Core Data Models
// ═══════════════════════════════════════════════════

export interface RowData {
  type: 'marker' | 'content'
  en: string
  ru_v1: string
  ru_proposed: string
  uz_v1: string
  uz_proposed: string
  status: 'aligned' | 'review'
  sentence_no: number
  display_no: string
  text_id: string
  notes: string
  specialist_name?: string
}

export interface User {
  id: string
  email: string
  name: string
  role: 'admin' | 'foydalanuvchi'
  status: 'pending' | 'approved' | 'rejected'
  avatar_url?: string
  department?: string
  last_login?: string
  created_at?: string
  password_hash?: string
}

export interface Project {
  id: string
  name: string
  specialist_name: string
  user_id: string
  status: 'active' | 'finished'
  original_filename?: string
  file_path?: string
  source_lang?: string
  created_at: string
  updated_at: string
}

export interface SayqallashRule {
  id: number
  wrong_form: string
  correct_form: string
  error_type: string
  context?: string
  lang: 'uz' | 'ru' | 'en'
  frequency: number
  source: 'user_edit' | 'seed' | 'ai' | 'user_feedback'
  modified_by?: string
  created_at: string
  updated_at?: string
}

export interface Synonym {
  id: number
  word: string
  synonym: string
  lang: string
  frequency: number
  source: 'ai' | 'user' | 'manual'
  created_by?: string
  created_at: string
}

export interface DashboardEntry {
  id: number
  en: string
  ru: string
  uz: string
  specialist_name: string
  text_id: string
  action_type: string
  notes?: string
  created_at: string
}

export interface UploadedFile {
  filename: string
  original_name?: string
  original_filename?: string
  size: number
  created_at?: string
  modified_at?: number
  extension?: string
  folder?: string
  path?: string
  project_id?: string
  project_name?: string
  specialist_name?: string
  user_id?: string | null
  owner_name?: string
  folder_path?: string
}

// ═══════════════════════════════════════════════════
// API Response Types
// ═══════════════════════════════════════════════════

export interface AuthResponse {
  success: boolean
  token: string
  user: User
  message?: string
}

export interface Annotation {
  old_value: string
  new_value: string
  from_index: number
  to_index: number
  error_type: string
  source?: 'rules' | 'ai' | 'bert'
}

export interface SayqallashResponse {
  annotations: Annotation[]
  corrected_text: string
  rules_count: number
  confidence: number
  cached?: boolean
}

export interface ImproveRowResponse {
  [key: string]: string | Annotation[]  // e.g. uz_v2, ru_v2
  annotations: Annotation[]
  rationale: string
}

export interface AlignDocumentResponse {
  data: RowData[]
}

export interface PolishingSummary {
  total: number
  corrected: number
  annotations: number
  timestamp: string
}

export interface DictionaryWord {
  word: string
  frequency: number
}

export interface DictionarySuggestion {
  word: string
  frequency: number
  distance: number
}

export interface SynonymSuggestion {
  synonyms: string[]
  note: string
}

export interface DbStats {
  projects: number
  alignments: number
  rules: number
  users: number
  dashboard_entries: number
  synonyms: number
  annotated_words: number
  disputed_words: number
  abbreviations: number
}

export interface LinguisticItem {
  id?: number
  word: string
  definition?: string
  en?: string
  ru?: string
  uz?: string
  source_lang?: string
  status?: string
  text_id?: string
  user_id?: string
}
