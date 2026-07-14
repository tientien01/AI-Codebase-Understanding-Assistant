import { Icon } from '../common/Icon'
import type { FileTreeNode } from '../../types/api'

export function FileTree({
  nodes,
  selectedFilePath,
  onSelectFile,
}: {
  nodes: FileTreeNode[]
  selectedFilePath: string
  onSelectFile: (filePath: string) => void
}) {
  return (
    <div className="file-tree" aria-label="Repository files">
      {nodes.map((node) => <TreeNode key={node.path} node={node} selectedFilePath={selectedFilePath} onSelectFile={onSelectFile} />)}
    </div>
  )
}

function TreeNode({ node, selectedFilePath, onSelectFile, depth = 0 }: {
  node: FileTreeNode
  selectedFilePath: string
  onSelectFile: (filePath: string) => void
  depth?: number
}) {
  const style = { paddingLeft: `${12 + depth * 16}px` }

  return (
    <div className="tree-node">
      {node.type === 'file' ? (
        <button type="button" className={selectedFilePath === node.path ? 'active' : ''} style={style} onClick={() => onSelectFile(node.path)} title={node.path}>
          <Icon name="file" />
          <span className="tree-node-name">{node.name}</span>
        </button>
      ) : (
        <div className="tree-folder" style={style} title={node.path}>
          <Icon name="folder" />
          <span className="tree-node-name">{node.name}</span>
        </div>
      )}
      {node.children.length > 0 && node.children.map((child) => (
        <TreeNode key={child.path} node={child} selectedFilePath={selectedFilePath} onSelectFile={onSelectFile} depth={depth + 1} />
      ))}
    </div>
  )
}
