import { API_V1, requestJson } from './client'
import type {
  Citation,
  Evidence,
  FileContent,
  FileTreeNode,
  GraphData,
  GraphProjectionInput,
  GraphView,
  ImpactResult,
  IgnorePatternsResponse,
  ImportPreview,
  IndexStatus,
  Overview,
  Repository,
  SearchResult,
  SettingsResponse,
} from '../types/api'

export const serverApi = {
  repositories: (signal?: AbortSignal) => requestJson<Repository[]>(`${API_V1}/repositories`, { signal }),
  settings: (signal?: AbortSignal) => requestJson<SettingsResponse>(`${API_V1}/settings`, { signal }),
  ignorePatterns: (signal?: AbortSignal) => requestJson<IgnorePatternsResponse>(`${API_V1}/settings/ignore-patterns`, { signal }),
  overview: (repositoryId: string, signal?: AbortSignal) =>
    requestJson<Overview>(`${API_V1}/repositories/${repositoryId}/overview`, { signal }),
  indexStatus: (repositoryId: string, signal?: AbortSignal) =>
    requestJson<IndexStatus>(`${API_V1}/repositories/${repositoryId}/index/status`, { signal }),
  graph: (repositoryId: string, view: GraphView, projection: GraphProjectionInput, signal?: AbortSignal) =>
    requestJson<GraphData>(`${API_V1}/repositories/${repositoryId}/graph/${view}?${graphProjectionParams(projection)}`, { signal }),
  fileTree: (repositoryId: string, signal?: AbortSignal) =>
    requestJson<FileTreeNode[]>(`${API_V1}/repositories/${repositoryId}/files/tree`, { signal }),
  fileContent: (repositoryId: string, filePath: string, signal?: AbortSignal) =>
    requestJson<FileContent>(`${API_V1}/repositories/${repositoryId}/files/content?path=${encodeURIComponent(filePath)}`, { signal }),
  evidence: (repositoryId: string, evidenceId: string, signal?: AbortSignal) =>
    requestJson<Evidence>(`${API_V1}/repositories/${repositoryId}/evidence/${encodeURIComponent(evidenceId)}`, { signal }),
  search: (repositoryId: string, query: string, signal?: AbortSignal) =>
    requestJson<{ results: SearchResult[] }>(`${API_V1}/repositories/${repositoryId}/search?q=${encodeURIComponent(query)}`, { signal }),
  reindex: (repositoryId: string) => requestJson(`${API_V1}/repositories/${repositoryId}/index`, jsonRequest({ force_reindex: false })),
  pauseJob: (repositoryId: string, jobId: string) =>
    requestJson(`${API_V1}/repositories/${repositoryId}/index/jobs/${jobId}/pause`, { method: 'POST' }),
  resumeJob: (repositoryId: string, jobId: string) =>
    requestJson(`${API_V1}/repositories/${repositoryId}/index/jobs/${jobId}/resume`, { method: 'POST' }),
  cancelJob: (repositoryId: string, jobId: string) =>
    requestJson(`${API_V1}/repositories/${repositoryId}/index/jobs/${jobId}/cancel`, { method: 'POST' }),
  deleteRepository: (repositoryId: string) => requestJson(`${API_V1}/repositories/${repositoryId}`, { method: 'DELETE' }),
  deleteAllRepositories: () => requestJson(`${API_V1}/repositories/bulk-delete`, jsonRequest({ delete_all: true })),
  expandGraph: (repositoryId: string, scopePath: string) =>
    requestJson(`${API_V1}/repositories/${repositoryId}/graph/expand`, jsonRequest({ scope_path: scopePath })),
  impact: (repositoryId: string, targetType: string, targetRef: string) =>
    requestJson<ImpactResult>(`${API_V1}/repositories/${repositoryId}/impact`, jsonRequest({
      target_type: targetType,
      target_ref: targetRef,
      max_depth: 3,
    })),
  chat: (repositoryId: string, message: string) =>
    requestJson<{ answer: string; citations: Citation[]; evidence_sufficient: boolean }>(
      `${API_V1}/repositories/${repositoryId}/chat`,
      jsonRequest({ message, options: { max_retrieval_rounds: 2 } }),
    ),
  createGithubImport: (url: string, name?: string) =>
    requestJson<{ import_session_id: string }>(`${API_V1}/import-sessions/github`, jsonRequest({ url, name })),
  importPreview: (sessionId: string, signal?: AbortSignal) =>
    requestJson<ImportPreview>(`${API_V1}/import-sessions/${sessionId}/preview`, { signal }),
  confirmImport: (sessionId: string, name: string) =>
    requestJson<{ repository_id: string }>(`${API_V1}/import-sessions/${sessionId}/confirm`, jsonRequest({
      name,
      start_indexing: true,
      index_profile: 'balanced',
      duplicate_action: 'import_as_new',
    })),
}

export function graphProjectionParams(projection: GraphProjectionInput) {
  const params = new URLSearchParams({
    direction: projection.direction,
    max_depth: String(projection.maxDepth),
    max_nodes: String(projection.maxNodes),
    max_edges: String(projection.maxEdges),
    min_confidence: String(projection.minConfidence),
  })
  if (projection.indexVersion !== undefined) params.set('index_version', String(projection.indexVersion))
  for (const root of normalizedValues(projection.rootKeys)) params.append('root_keys', root)
  for (const nodeType of normalizedValues(projection.nodeTypes)) params.append('node_types', nodeType)
  for (const edgeType of normalizedValues(projection.edgeTypes)) params.append('edge_types', edgeType)
  for (const support of normalizedValues(projection.supportLevels)) params.append('support_levels', support)
  return params.toString()
}

function normalizedValues(values: string[]) {
  return [...new Set(values.map((value) => value.trim()).filter(Boolean))].sort()
}

function jsonRequest(body: unknown): RequestInit {
  return {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }
}
