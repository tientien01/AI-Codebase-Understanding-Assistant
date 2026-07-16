export type IndexVersionIdentity = number | 'active'

export const queryKeys = {
  repositories: ['repositories'] as const,
  settings: ['settings'] as const,
  ignorePatterns: ['settings', 'ignore-patterns'] as const,
  repository: (repositoryId: string) => ['repository', repositoryId] as const,
  status: (repositoryId: string) => ['repository', repositoryId, 'status'] as const,
  version: (repositoryId: string, indexVersion?: number) =>
    ['repository', repositoryId, 'version', indexVersion ?? 'active'] as const,
  overview: (repositoryId: string, indexVersion?: number) =>
    [...queryKeys.version(repositoryId, indexVersion), 'overview'] as const,
  endpoints: (repositoryId: string, indexVersion?: number) =>
    [...queryKeys.version(repositoryId, indexVersion), 'api-endpoints'] as const,
  graphFamily: (repositoryId: string, indexVersion?: number) =>
    [...queryKeys.version(repositoryId, indexVersion), 'graph'] as const,
  graph: (repositoryId: string, indexVersion: number | undefined, view: string, projection?: GraphProjectionInput) =>
    [...queryKeys.graphFamily(repositoryId, indexVersion), view, normalizeGraphProjection(projection)] as const,
  fileTree: (repositoryId: string, indexVersion?: number) =>
    [...queryKeys.version(repositoryId, indexVersion), 'file-tree'] as const,
  fileContent: (repositoryId: string, indexVersion: number | undefined, filePath: string) =>
    [...queryKeys.version(repositoryId, indexVersion), 'file', filePath] as const,
  evidence: (repositoryId: string, indexVersion: number | undefined, evidenceId: string) =>
    [...queryKeys.version(repositoryId, indexVersion), 'evidence', evidenceId] as const,
  search: (repositoryId: string, indexVersion: number | undefined, query: string) =>
    [...queryKeys.version(repositoryId, indexVersion), 'search', query] as const,
  conversations: (repositoryId: string) => ['repository', repositoryId, 'conversations'] as const,
  conversation: (repositoryId: string, conversationId: string) =>
    [...queryKeys.conversations(repositoryId), conversationId] as const,
  importPreview: (sessionId: string) => ['import-session', sessionId, 'preview'] as const,
  importStatus: (sessionId: string) => ['import-session', sessionId, 'status'] as const,
}

export function normalizeGraphProjection(projection?: GraphProjectionInput) {
  if (!projection) return 'default'
  return {
    ...projection,
    rootKeys: [...new Set(projection.rootKeys)].sort(),
    nodeTypes: [...new Set(projection.nodeTypes)].sort(),
    edgeTypes: [...new Set(projection.edgeTypes)].sort(),
    supportLevels: [...new Set(projection.supportLevels)].sort(),
  }
}
import type { GraphProjectionInput } from '../../types/api'
