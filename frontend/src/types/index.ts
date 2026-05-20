export interface Reference {
  content: string
  distance: number
  metadata?: Record<string, any>
  type?: 'bm25' | 'vector'
  rrf_score?: number
  rerank_score?: number
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  references?: Reference[]
  error?: string
}

export interface ChatRequest {
  message: string
  session_id?: string
  use_rag?: boolean
  top_k?: number
}

export interface ChatResponse {
  answer: string
  session_id: string
  references?: Reference[]
  sources?: string[]
  error?: string
}
