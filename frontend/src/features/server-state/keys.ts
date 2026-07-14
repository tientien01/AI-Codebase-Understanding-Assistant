export type IndexVersionIdentity = number | 'active'

export const queryKeys = {
  repositories: ['repositories'] as const,
  repository: (repositoryId: string) => ['repository', repositoryId] as const,
  status: (repositoryId: string) => ['repository', repositoryId, 'status'] as const,
  version: (repositoryId: string, indexVersion?: number) =>
    ['repository', repositoryId, 'version', indexVersion ?? 'active'] as const,
  overview: (repositoryId: string, indexVersion?: number) =>
    [...queryKeys.version(repositoryId, indexVersion), 'overview'] as const,
  graphFamily: (repositoryId: string, indexVersion?: number) =>
    [...queryKeys.version(repositoryId, indexVersion), 'graph'] as const,
  graph: (repositoryId: string, indexVersion: number | undefined, view: string) =>
    [...queryKeys.graphFamily(repositoryId, indexVersion), view] as const,
  fileTree: (repositoryId: string, indexVersion?: number) =>
    [...queryKeys.version(repositoryId, indexVersion), 'file-tree'] as const,
  fileContent: (repositoryId: string, indexVersion: number | undefined, filePath: string) =>
    [...queryKeys.version(repositoryId, indexVersion), 'file', filePath] as const,
  evidence: (repositoryId: string, indexVersion: number | undefined, evidenceId: string) =>
    [...queryKeys.version(repositoryId, indexVersion), 'evidence', evidenceId] as const,
  search: (repositoryId: string, indexVersion: number | undefined, query: string) =>
    [...queryKeys.version(repositoryId, indexVersion), 'search', query] as const,
  chat: (repositoryId: string, indexVersion?: number) =>
    [...queryKeys.version(repositoryId, indexVersion), 'chat'] as const,
  importPreview: (sessionId: string) => ['import-session', sessionId, 'preview'] as const,
}
