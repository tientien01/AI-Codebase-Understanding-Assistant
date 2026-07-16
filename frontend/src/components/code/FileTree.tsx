import { useLayoutEffect, useRef, useState } from 'react'
import { Icon } from '../common/Icon'
import type { FileTreeNode } from '../../types/api'

type FileTreeProps = {
  nodes: FileTreeNode[]
  repositoryId: string
  selectedFilePath: string
  searchActive?: boolean
  onSelectFile: (filePath: string) => void
}

export function FileTree(props: FileTreeProps) {
  return <PersistentFileTree key={props.repositoryId} {...props} />
}

function PersistentFileTree({
  nodes,
  repositoryId,
  selectedFilePath,
  searchActive = false,
  onSelectFile,
}: FileTreeProps) {
  const treeRef = useRef<HTMLDivElement>(null)
  const expansionKey = `aica:file-tree:${repositoryId}:expanded`
  const scrollKey = `aica:file-tree:${repositoryId}:scroll`
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(() => loadExpandedPaths(expansionKey, selectedFilePath))

  useLayoutEffect(() => {
    const tree = treeRef.current
    if (!tree) return
    tree.scrollTop = loadScrollTop(scrollKey)
  }, [scrollKey])

  function updateExpanded(updater: (current: Set<string>) => Set<string>) {
    setExpandedPaths((current) => {
      const next = updater(current)
      saveExpandedPaths(expansionKey, next)
      return next
    })
  }

  function toggleFolder(path: string) {
    updateExpanded((current) => {
      const next = new Set(current)
      if (next.has(path)) next.delete(path)
      else next.add(path)
      return next
    })
  }

  function revealActiveFile() {
    updateExpanded((current) => new Set([...current, ...ancestorPaths(selectedFilePath)]))
    requestAnimationFrame(() => {
      treeRef.current?.querySelector<HTMLElement>('[aria-current="page"]')?.scrollIntoView?.({ block: 'nearest' })
    })
  }

  return (
    <div className="file-tree-shell">
      <div className="file-tree-actions" aria-label="File tree actions">
        <button type="button" onClick={() => updateExpanded(() => new Set())}>Collapse all</button>
        <button type="button" disabled={!selectedFilePath} onClick={revealActiveFile}>Reveal active</button>
      </div>
      <div
        className="file-tree"
        aria-label="Repository files"
        role="tree"
        ref={treeRef}
        onScroll={(event) => saveScrollTop(scrollKey, event.currentTarget.scrollTop)}
      >
        {nodes.map((node) => (
          <TreeNode
            key={node.path}
            node={node}
            selectedFilePath={selectedFilePath}
            expandedPaths={expandedPaths}
            searchActive={searchActive}
            onToggleFolder={toggleFolder}
            onSelectFile={onSelectFile}
          />
        ))}
      </div>
    </div>
  )
}

function TreeNode({
  node,
  selectedFilePath,
  expandedPaths,
  searchActive,
  onToggleFolder,
  onSelectFile,
  depth = 0,
}: {
  node: FileTreeNode
  selectedFilePath: string
  expandedPaths: Set<string>
  searchActive: boolean
  onToggleFolder: (path: string) => void
  onSelectFile: (filePath: string) => void
  depth?: number
}) {
  const style = { paddingLeft: `${12 + depth * 16}px` }
  const expanded = searchActive || expandedPaths.has(node.path)

  return (
    <div className="tree-node" role="treeitem" aria-expanded={node.type === 'directory' ? expanded : undefined}>
      {node.type === 'file' ? (
        <button
          type="button"
          className={selectedFilePath === node.path ? 'active' : ''}
          style={style}
          onClick={() => onSelectFile(node.path)}
          title={node.path}
          aria-current={selectedFilePath === node.path ? 'page' : undefined}
        >
          <Icon name="file" />
          <span className="tree-node-name">{node.name}</span>
        </button>
      ) : (
        <button type="button" className="tree-folder" style={style} title={node.path} onClick={() => onToggleFolder(node.path)} aria-label={`${expanded ? 'Collapse' : 'Expand'} ${node.name}`}>
          <span className={`tree-chevron ${expanded ? 'expanded' : ''}`} aria-hidden="true">›</span>
          <Icon name="folder" />
          <span className="tree-node-name">{node.name}</span>
        </button>
      )}
      {node.children.length > 0 && expanded ? (
        <div role="group">
          {node.children.map((child) => (
            <TreeNode
              key={child.path}
              node={child}
              selectedFilePath={selectedFilePath}
              expandedPaths={expandedPaths}
              searchActive={searchActive}
              onToggleFolder={onToggleFolder}
              onSelectFile={onSelectFile}
              depth={depth + 1}
            />
          ))}
        </div>
      ) : null}
    </div>
  )
}

function ancestorPaths(filePath: string): string[] {
  const parts = filePath.split('/').filter(Boolean)
  return parts.slice(0, -1).map((_, index) => parts.slice(0, index + 1).join('/'))
}

function loadExpandedPaths(key: string, selectedFilePath: string): Set<string> {
  try {
    const stored = window.sessionStorage.getItem(key)
    if (stored) return new Set(JSON.parse(stored) as string[])
  } catch {
    // Invalid or unavailable session state falls back to the active file ancestry.
  }
  return new Set(ancestorPaths(selectedFilePath))
}

function saveExpandedPaths(key: string, paths: Set<string>) {
  try {
    window.sessionStorage.setItem(key, JSON.stringify([...paths].sort()))
  } catch {
    // The tree remains usable when storage is unavailable.
  }
}

function loadScrollTop(key: string): number {
  try {
    const value = Number(window.sessionStorage.getItem(key))
    return Number.isFinite(value) && value >= 0 ? value : 0
  } catch {
    return 0
  }
}

function saveScrollTop(key: string, scrollTop: number) {
  try {
    window.sessionStorage.setItem(key, String(Math.max(0, scrollTop)))
  } catch {
    // Scroll persistence is an enhancement, not a tree availability requirement.
  }
}
