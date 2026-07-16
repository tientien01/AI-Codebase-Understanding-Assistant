import type { FileTreeNode, IndexStatus, Repository } from '../types/api'

export function isRepositoryUsable(repository?: Repository) {
  return Boolean(repository && ['indexed', 'indexed_with_warnings'].includes(repository.status))
}

export function reconcileRepositoryIndexStatus(repository: Repository | undefined, status: IndexStatus | null | undefined) {
  if (!repository || isRepositoryUsable(repository)) return repository
  const activeVersion = status?.index_version
  const repositoryVersion = repository.current_index_version ?? 0
  const activeJob = ['queued', 'running', 'paused', 'cancelling'].includes(status?.status ?? '')
  const successful = status?.status === 'completed' || status?.status === 'completed_with_warnings'
  if (
    status
    && status.repository_id === repository.id
    && successful
    && repositoryVersion > 0
    && activeVersion === repositoryVersion
  ) {
    // The job may be old, but the matching positive version is already active.
    // Restore access to that version without promoting any newer candidate.
    return {
      ...repository,
      status: status.status === 'completed_with_warnings' ? 'indexed_with_warnings' : 'indexed',
    }
  }

  if (
    status
    && status.repository_id === repository.id
    && activeJob
    && repositoryVersion > 0
    && Number.isInteger(activeVersion)
    && Number(activeVersion) > repositoryVersion
  ) {
    // Compatibility for re-index attempts started before the backend preserved
    // the active repository lifecycle. The candidate remains a running job;
    // only the already activated repository version becomes queryable.
    return { ...repository, status: 'indexed' }
  }

  if (
    !status
    || !successful
    || status.repository_id !== repository.id
    || !Number.isInteger(activeVersion)
    || Number(activeVersion) <= 0
    || Number(activeVersion) <= repositoryVersion
  ) return repository

  // Bridge only a newly activated version while the repository-list refresh is
  // in flight. An equal/older completed job may belong to a previous attempt.
  return {
    ...repository,
    status: status.status === 'completed_with_warnings' ? 'indexed_with_warnings' : 'indexed',
    current_index_version: activeVersion,
    total_files: status.total_files,
    indexed_files: status.processed_files,
    symbols: status.stats.symbols ?? repository.symbols,
    endpoints: status.stats.endpoints ?? repository.endpoints,
    chunks: status.stats.chunks ?? repository.chunks,
    graph_nodes: status.stats.graph_nodes ?? repository.graph_nodes,
    last_indexed_at: status.finished_at ?? repository.last_indexed_at,
  }
}

export function canChat(repository?: Repository) {
  return isRepositoryUsable(repository)
}

export function findFirstFile(nodes: FileTreeNode[]): FileTreeNode | null {
  for (const node of nodes) {
    if (node.type === 'file') return node
    const child = findFirstFile(node.children)
    if (child) return child
  }
  return null
}
