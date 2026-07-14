import { useEffect, useMemo, useState } from 'react'
import { FileTree } from '../../components/code/FileTree'
import { Icon } from '../../components/common/Icon'
import { PageTitle, Panel } from '../../components/common/ui'
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
  const [fileQuery, setFileQuery] = useState('')
  const [displayContent, setDisplayContent] = useState<FileContent | null>(fileContent)
  const visibleTree = useMemo(() => filterTree(fileTree, fileQuery), [fileQuery, fileTree])
  const activeContent = fileContent ?? displayContent
  const symbols = activeContent?.symbols ?? []
  const endpoints = (overview?.endpoints ?? []).filter((endpoint) => endpoint.file_path === activeContent?.file_path)
  const hasIntelligence = symbols.length > 0 || endpoints.length > 0
  const isLoadingSelection = Boolean(selectedFilePath && activeContent?.file_path && selectedFilePath !== activeContent.file_path)
  const openTabs = useMemo(() => {
    const selected = activeContent?.file_path ?? selectedFilePath
    return [selected, ...endpoints.map((endpoint) => endpoint.file_path)]
      .filter(Boolean)
      .filter((value, index, values) => values.indexOf(value) === index)
      .slice(0, 4)
  }, [activeContent?.file_path, endpoints, selectedFilePath])

  useEffect(() => {
    if (!fileContent) return undefined
    let cancelled = false
    queueMicrotask(() => {
      if (!cancelled) setDisplayContent(fileContent)
    })
    return () => {
      cancelled = true
    }
  }, [fileContent])

  useEffect(() => {
    if (!selectedLine) return
    const target = document.getElementById(`source-line-${selectedLine}`)
    target?.scrollIntoView?.({ block: 'center' })
  }, [activeContent, selectedLine])

  return (
    <div className="code-explorer-page">
      <PageTitle title="Code Explorer" subtitle="Browse source files with parsed symbols, endpoints, imports, and citation-ready line ranges." />
      <div className="code-explorer-grid">
        <Panel title="Files">
          <label className="code-explorer-search">
            <Icon name="search" />
            <span className="sr-only">Search repository files</span>
            <input className="panel-search" value={fileQuery} onChange={(event) => setFileQuery(event.target.value)} placeholder="Search files..." />
          </label>
          {visibleTree.length ? <FileTree nodes={visibleTree} selectedFilePath={selectedFilePath} onSelectFile={onSelectFile} /> : <p className="code-explorer-empty">No matching files found.</p>}
        </Panel>
        <div className="code-explorer-reader">
          <section className="code-explorer-ide" aria-label="Code editor">
            <div className="code-explorer-source-meta">
              <span className="code-explorer-breadcrumb"><Icon name="folder" /> {activeContent?.file_path ?? 'Select a file from the tree'}</span>
              <span className="code-explorer-toolbar">
                {isLoadingSelection ? <span className="code-explorer-loading">Loading selection</span> : null}
                {activeContent ? <span className="code-explorer-language"><Icon name="code" /> {activeContent.language}</span> : null}
                <button type="button" disabled title="Open in editor is not wired to a local IDE yet"><Icon name="monitor" /> Open in Editor</button>
                <button type="button" disabled aria-label="More editor actions" title="More editor actions"><Icon name="more" /></button>
              </span>
            </div>
            <div className="code-explorer-tabs" aria-label="Open files">
              {openTabs.length ? openTabs.map((path) => (
                <button type="button" className={path === activeContent?.file_path ? 'active' : ''} key={path} onClick={() => onSelectFile(path)} title={path}>
                  <Icon name={path.endsWith('.md') ? 'book' : 'file'} />
                  {fileName(path)}
                </button>
              )) : (
                <span><Icon name="file" /> No file selected</span>
              )}
            </div>
            <pre className="code-block" tabIndex={0} aria-busy={isLoadingSelection} aria-label={activeContent ? `Source content for ${activeContent.file_path}` : 'Source content'}>
              {activeContent ? activeContent.lines.map((line, index) => {
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
            <div className="code-explorer-statusbar">
              <span>Ln {selectedLine ?? 1}, Col 1</span>
              <span>Spaces: 2</span>
              {activeContent ? <span>{activeContent.language}</span> : null}
            </div>
          </section>
          {hasIntelligence ? (
            <section className="code-explorer-intelligence" aria-label="File intelligence">
              {symbols.length ? (
                <div className="code-explorer-intelligence-group">
                  <h2><Icon name="braces" /> Symbols</h2>
                  <div className="code-explorer-symbol-list">
                    {symbols.map((symbol) => (
                      <div key={`${symbol.file_path}-${symbol.start_line}`}>
                        <strong>{symbol.symbol_name ?? 'symbol'}</strong>
                        <span>Lines {symbol.start_line}-{symbol.end_line}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
              {endpoints.length ? (
                <div className="code-explorer-intelligence-group">
                  <h2><Icon name="route" /> API endpoints</h2>
                  <div className="code-explorer-endpoint-list">
                    {endpoints.map((endpoint) => (
                      <div key={`${endpoint.method}-${endpoint.path}`}>
                        <strong>{endpoint.method} {endpoint.path}</strong>
                        <span>{endpoint.handler}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </section>
          ) : null}
        </div>
      </div>
    </div>
  )
}

function fileName(path: string) {
  return path.split(/[\\/]/).pop() ?? path
}

function filterTree(nodes: FileTreeNode[], query: string): FileTreeNode[] {
  const normalizedQuery = query.trim().toLocaleLowerCase()
  if (!normalizedQuery) return nodes

  return nodes.flatMap((node) => {
    const children = filterTree(node.children, normalizedQuery)
    if (node.name.toLocaleLowerCase().includes(normalizedQuery) || children.length) return [{ ...node, children }]
    return []
  })
}
