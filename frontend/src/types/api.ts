export type Page =
  | 'dashboard'
  | 'import'
  | 'indexing'
  | 'overview'
  | 'code'
  | 'graph'
  | 'api'
  | 'assistant'
  | 'impact'
  | 'search'
  | 'evidence'
  | 'evaluation'
  | 'settings'

export type Repository = {
  id: string
  name: string
  source_type: string
  source_uri?: string
  status: string
  total_files: number
  indexed_files: number
  symbols: number
  endpoints: number
  chunks: number
  graph_nodes: number
  last_indexed_at?: string
}

export type IndexStatus = {
  repository_id: string
  job_id?: string
  status: string
  current_step: string
  total_files: number
  processed_files: number
  skipped_files: number
  failed_files: number
  progress: number
  stats: Record<string, number>
  logs: string[]
  warnings: string[]
  error_code?: string
  error_message?: string
}

export type Overview = {
  repository_id: string
  name: string
  detected_stack: string[]
  important_files: { file_path: string; reason: string }[]
  modules: { name: string; summary: string; file_count: number }[]
  endpoints: { method: string; path: string; handler: string; file_path: string; start_line: number; end_line: number }[]
  documentation_gaps: string[]
  stats: Record<string, number>
}

export type Citation = {
  evidence_id: string
  file_path: string
  symbol_name?: string
  start_line: number
  end_line: number
}

export type Evidence = Citation & {
  repository_id: string
  source_type: string
  content_preview: string
  relevance_reason: string
  confidence_score: number
  retrieval_source: string
  metadata: Record<string, string>
}

export type ChatMessage = {
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  evidenceSufficient?: boolean
}

export type GraphData = {
  nodes: { id: string; type: string; label: string; file_path?: string }[]
  edges: { source: string; target: string; type: string; confidence: number }[]
}

export type SearchResult = {
  evidence_id: string
  file_path: string
  title: string
  preview: string
  start_line: number
  end_line: number
  score: number
}

export type FileTreeNode = {
  name: string
  path: string
  type: 'file' | 'directory'
  children: FileTreeNode[]
}

export type FileContent = {
  file_path: string
  language: string
  content: string
  lines: string[]
  symbols: Citation[]
}

export type ImportMode = 'github' | 'folder' | 'zip' | 'local'

export type IconName =
  | 'home'
  | 'folder'
  | 'clock'
  | 'star'
  | 'layers'
  | 'settings'
  | 'nodes'
  | 'share'
  | 'sliders'
  | 'spark'
  | 'target'
  | 'search'
  | 'chart'
  | 'code'
  | 'grid'
  | 'list'
  | 'bell'
  | 'help'
  | 'plus'
  | 'more'
  | 'refresh'
  | 'pause'
  | 'warning'
  | 'check'
  | 'git'
