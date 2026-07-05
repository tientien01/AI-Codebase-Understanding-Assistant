import type { FileTreeNode, Repository } from '../types/api'

export function isRepositoryUsable(repository?: Repository) {
  return Boolean(repository && ['indexed', 'indexed_with_warnings'].includes(repository.status))
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
