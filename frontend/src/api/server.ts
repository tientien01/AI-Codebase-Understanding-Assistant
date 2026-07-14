import { API_V1, requestJson } from './client'
import type {
  Citation,
  Evidence,
  FileContent,
  FileTreeNode,
  GraphData,
  GraphView,
  ImpactResult,
  ImportPreview,
  IndexStatus,
  Overview,
  Repository,
  SearchResult,
} from '../types/api'

export const serverApi = {
  repositories: (signal?: AbortSignal) => requestJson<Repository[]>(`${API_V1}/repositories`, { signal }),
  overview: (repositoryId: string, signal?: AbortSignal) =>
    requestJson<Overview>(`${API_V1}/repositories/${repositoryId}/overview`, { signal }),
  indexStatus: (repositoryId: string, signal?: AbortSignal) =>
    requestJson<IndexStatus>(`${API_V1}/repositories/${repositoryId}/index/status`, { signal }),
  graph: (repositoryId: string, view: GraphView, signal?: AbortSignal) =>
    requestJson<GraphData>(`${API_V1}/repositories/${repositoryId}/graph/${view}`, { signal }),
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

function jsonRequest(body: unknown): RequestInit {
  return {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }
}
