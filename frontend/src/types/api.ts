export type Page =
  | 'projects'
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
  source_label?: string
  source_uri?: string
  status: string
  current_index_version?: number
  detected_stack: string[]
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
  index_version?: number
  total_files: number
  processed_files: number
  skipped_files: number
  failed_files: number
  progress: number
  stats: Record<string, number>
  started_at?: string
  finished_at?: string
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
  index_version?: number
  is_stale?: boolean
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

export type GraphDirection = 'outgoing' | 'incoming' | 'both'

export type GraphProjectionInput = {
  indexVersion?: number
  rootKeys: string[]
  nodeTypes: string[]
  edgeTypes: string[]
  direction: GraphDirection
  maxDepth: number
  maxNodes: number
  maxEdges: number
  minConfidence: number
  supportLevels: string[]
}

export type GraphData = {
  nodes: {
    id: string
    type: string
    label: string
    file_path?: string
    start_line?: number
    end_line?: number
    summary?: string
    tags?: string[]
    complexity?: string
    layer?: string
    coverage?: 'mapped' | 'analyzing' | 'deep_indexed' | 'skipped' | 'failed'
    scope_path?: string
    role?: string
    metadata?: Record<string, string>
  }[]
  edges: {
    source: string
    target: string
    type: string
    confidence: number
    evidence_level?: 'map' | 'deep' | 'inferred'
    weight?: number
    metadata?: Record<string, string>
  }[]
  repository_id?: string
  index_version?: number
  view?: string
  projection?: {
    index_version?: number
    root_keys: string[]
    node_types: string[]
    edge_types: string[]
    direction: GraphDirection
    max_depth: number
    max_nodes: number
    max_edges: number
    min_confidence: number
    support_levels: string[]
  }
  counts?: {
    available_nodes: number
    included_nodes: number
    available_edges: number
    included_edges: number
    available_counts_are_estimates: boolean
  }
  coverage?: {
    state: 'ready' | 'limited'
    measured: Record<string, number>
    unknown: string[]
  }
  truncation?: {
    truncated: boolean
    reason?: string | null
    continuation_token?: string | null
  }
  unsupported_hops?: string[]
  can_expand?: boolean
  provenance?: {
    source: string
    deterministic_order: boolean
    support_levels: string[]
  }
}

export type GraphView = 'project-map' | 'dependencies' | 'api-flow' | 'function-flow' | 'data-flow'

export type SearchResult = {
  evidence_id: string
  file_path: string
  title: string
  preview: string
  start_line: number
  end_line: number
  score: number
  result_type?: string
  retrieval_source?: string
  matched_terms?: string[]
  index_version?: number
  is_stale?: boolean
}

export type ImpactItem = {
  node_id: string
  node_type: string
  label: string
  file_path?: string
  depth: number
  confidence: number
  via_edge?: string
  reason: string
}

export type ImpactResult = {
  repository_id: string
  target?: {
    node_id: string
    node_type: string
    label: string
    file_path?: string
    line_range?: string
  }
  risk_level: string
  risk_score: number
  direct: ImpactItem[]
  indirect: ImpactItem[]
  affected_files: ImpactItem[]
  affected_endpoints: ImpactItem[]
  affected_tests: ImpactItem[]
  affected_symbols: ImpactItem[]
  suggested_checks: string[]
  missing_relations: string[]
}

export type EvidenceValidationItem = {
  evidence_id: string
  is_valid: boolean
  is_stale: boolean
  reason?: string
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

export type ImportMode = 'github' | 'folder' | 'zip'

export type ImportActivityLog = {
  timestamp: string
  level: string
  stage: string
  message: string
  details: Record<string, string>
}

export type ImportPreview = {
  import_session_id: string
  status: string
  project_summary: {
    suggested_name: string
    source_type: string
    repository_size_bytes: number
    estimated_index_time_seconds: number
  }
  detected_stack: string[]
  file_statistics: {
    total_files: number
    supported_files: number
    skipped_files: number
    language_files?: Record<string, number>
    python_files: number
    javascript_files: number
    typescript_files: number
    markdown_files: number
    config_files: number
  }
  folder_preview: string[]
  ignore_summary: { pattern: string; skipped_count: number; reason: string }[]
  security_warnings: { file_path: string; risk_type: string; action: string }[]
  indexing_plan: string[]
  possible_duplicates: { repository_id: string; name: string; match_reason: string }[]
  activity_logs: ImportActivityLog[]
}

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
  | 'braces'
  | 'file'
  | 'grid'
  | 'list'
  | 'bell'
  | 'help'
  | 'plus'
  | 'more'
  | 'refresh'
  | 'route'
  | 'pause'
  | 'warning'
  | 'check'
  | 'git'
