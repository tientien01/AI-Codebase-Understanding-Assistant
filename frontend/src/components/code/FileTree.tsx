import type { FileTreeNode } from '../../types/api'

export function FileTree({
  nodes,
  selectedFilePath,
  onSelectFile,
  depth = 0,
}: {
  nodes: FileTreeNode[]
  selectedFilePath: string
  onSelectFile: (filePath: string) => void
  depth?: number
}) {
  return (
    <div className="file-tree">
      {nodes.map((node) => (
        <div key={node.path}>
          {node.type === 'file' ? (
            <button className={selectedFilePath === node.path ? 'active' : ''} style={{ paddingLeft: `${12 + depth * 16}px` }} onClick={() => onSelectFile(node.path)}>
              <span>File</span>{node.name}
            </button>
          ) : (
            <div className="tree-folder" style={{ paddingLeft: `${12 + depth * 16}px` }}><span>Dir</span>{node.name}</div>
          )}
          {node.children.length > 0 && <FileTree nodes={node.children} selectedFilePath={selectedFilePath} onSelectFile={onSelectFile} depth={depth + 1} />}
        </div>
      ))}
    </div>
  )
}
