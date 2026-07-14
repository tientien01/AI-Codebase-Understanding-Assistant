import { useEffect } from 'react'
import { FileTree } from '../../components/code/FileTree'
import { InDevelopmentInline, ListRow, PageTitle, Panel } from '../../components/common/ui'
import type { FileContent, FileTreeNode, Overview } from '../../types/api'

export function CodeExplorerPage({
  fileTree,
  selectedFilePath,
  selectedLine,
  fileContent,
  overview,
  onSelectFile,
}: {
  fileTree: FileTreeNode[]
  selectedFilePath: string
  selectedLine?: number
  fileContent: FileContent | null
  overview: Overview | null
  onSelectFile: (filePath: string) => void
}) {
  useEffect(() => {
    if (!selectedLine) return
    const target = document.getElementById(`source-line-${selectedLine}`)
    target?.scrollIntoView?.({ block: 'center' })
  }, [fileContent, selectedLine])

  return (
    <div>
      <PageTitle title="Code Explorer" subtitle="Browse source files with parsed symbols, endpoints, imports, and citation-ready line ranges." />
      <div className="code-explorer-grid">
        <Panel title="File Tree">
          <input className="panel-search" placeholder="Search file" />
          {fileTree.length ? <FileTree nodes={fileTree} selectedFilePath={selectedFilePath} onSelectFile={onSelectFile} /> : <p>No file tree available.</p>}
        </Panel>
        <Panel title={fileContent?.file_path ?? 'No file selected'}>
          <div className="file-tabs">
            <span>{fileContent?.file_path ?? 'empty'}</span>
          </div>
          <pre className="code-block">
            {fileContent ? fileContent.lines.map((line, index) => {
              const lineNumber = index + 1
              return (
                <span
                  className={lineNumber === selectedLine ? 'code-line selected' : 'code-line'}
                  id={`source-line-${lineNumber}`}
                  key={lineNumber}
                >
                  {`${String(lineNumber).padStart(4, ' ')}  ${line}\n`}
                </span>
              )
            }) : 'Import and index a repository to inspect code.'}
          </pre>
        </Panel>
        <Panel title="Detected Intelligence">
          <h3>Symbols</h3>
          {(fileContent?.symbols ?? []).length ? (
            fileContent?.symbols.map((symbol) => <ListRow key={`${symbol.file_path}-${symbol.start_line}`} title={symbol.symbol_name ?? 'symbol'} detail={`Lines ${symbol.start_line}-${symbol.end_line}`} />)
          ) : (
            <p>No symbol found for this file.</p>
          )}
          <h3>Endpoints</h3>
          {(overview?.endpoints ?? []).filter((endpoint) => endpoint.file_path === fileContent?.file_path).map((endpoint) => (
            <ListRow key={`${endpoint.method}-${endpoint.path}`} title={`${endpoint.method} ${endpoint.path}`} detail={endpoint.handler} />
          ))}
          <h3>Call Relationships</h3>
          <InDevelopmentInline text="Jump to definition and references need richer graph query APIs." />
        </Panel>
      </div>
    </div>
  )
}
