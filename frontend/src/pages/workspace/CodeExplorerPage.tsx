import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { FileTree } from '../../components/code/FileTree'
import { Icon } from '../../components/common/Icon'
import { PageTitle, Panel } from '../../components/common/ui'
import type { FileContent, FileTreeNode, Overview } from '../../types/api'
import type { ValueTraceContext } from '../../utils/valueTrace'

export function CodeExplorerPage({
  repositoryId,
  fileTree,
  selectedFilePath,
  selectedLine,
  fileContent,
  overview,
  tracePanel,
  onSelectFile,
  onSelectLine,
  onTraceValue,
}: {
  repositoryId: string
  fileTree: FileTreeNode[]
  selectedFilePath: string
  selectedLine?: number
  fileContent: FileContent | null
  overview: Overview | null
  tracePanel?: ReactNode
  onSelectFile: (filePath: string) => void
  onSelectLine?: (filePath: string, line: number) => void
  onTraceValue?: (context: ValueTraceContext) => void
}) {
  const [fileQuery, setFileQuery] = useState('')
  const [displayContent, setDisplayContent] = useState<FileContent | null>(fileContent)
  const [traceTarget, setTraceTarget] = useState<{ filePath: string; line: number }>()
  const sourceRef = useRef<HTMLPreElement>(null)
  const visibleTree = useMemo(() => filterTree(fileTree, fileQuery), [fileQuery, fileTree])
  const activeContent = fileContent ?? displayContent
  const symbols = activeContent?.symbols ?? []
  const endpoints = (overview?.endpoints ?? []).filter((endpoint) => endpoint.file_path === activeContent?.file_path)
  const hasIntelligence = symbols.length > 0 || endpoints.length > 0
  const isLoadingSelection = Boolean(selectedFilePath && activeContent?.file_path && selectedFilePath !== activeContent.file_path)
  const traceLine = traceTarget && traceTarget.filePath === activeContent?.file_path ? traceTarget.line : selectedLine
  const traceIdentifiers = useMemo(
    () => traceLine && activeContent ? identifiersOnLine(activeContent.lines[traceLine - 1] ?? '') : [],
    [activeContent, traceLine],
  )
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

  useLayoutEffect(() => {
    if (!selectedLine) return
    const target = document.getElementById(`source-line-${selectedLine}`)
    const source = sourceRef.current
    if (target && source) source.scrollTop = Math.max(0, target.offsetTop - source.clientHeight / 2)
  }, [activeContent, selectedLine])

  useLayoutEffect(() => {
    const source = sourceRef.current
    if (!source || !activeContent || selectedLine) return
    source.scrollTop = loadSourceScroll(repositoryId, activeContent.file_path)
  }, [activeContent, repositoryId, selectedLine])

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
          {visibleTree.length ? <FileTree nodes={visibleTree} repositoryId={repositoryId} selectedFilePath={selectedFilePath} searchActive={Boolean(fileQuery.trim())} onSelectFile={onSelectFile} /> : <p className="code-explorer-empty">No matching files found.</p>}
        </Panel>
        <div className={`code-explorer-reader ${tracePanel ? 'trace-open' : ''}`}>
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
            {traceLine && activeContent ? <div className="code-value-trace-bar" role="region" aria-label="Trace value from selected source line">
              <div><Icon name="share" /><span>Line {traceLine}</span><strong>{traceIdentifiers.length ? 'Choose an identifier to trace' : 'No identifier was detected on this line'}</strong></div>
              {traceIdentifiers.length ? <div className="code-value-token-list">{traceIdentifiers.map((value) => <button type="button" key={value} onClick={() => onTraceValue?.({ kind: 'token', filePath: activeContent.file_path, line: traceLine, value })}><Icon name="share" size={12} /> {value}</button>)}</div> : null}
              <button type="button" className="code-value-trace-close" aria-label="Close value trace actions" onClick={() => setTraceTarget(undefined)}>×</button>
            </div> : null}
            <pre className="code-block" ref={sourceRef} tabIndex={0} aria-busy={isLoadingSelection} aria-label={activeContent ? `Source content for ${activeContent.file_path}` : 'Source content'} onScroll={(event) => activeContent && saveSourceScroll(repositoryId, activeContent.file_path, event.currentTarget.scrollTop)}>
              {activeContent ? activeContent.lines.map((line, index) => {
                const lineNumber = index + 1
                return (
                  <span
                    className={`code-line ${lineNumber === selectedLine ? 'selected' : ''} ${lineNumber === traceLine ? 'trace-selected' : ''}`}
                    id={`source-line-${lineNumber}`}
                    key={lineNumber}
                    role="button"
                    tabIndex={0}
                    aria-label={`Select line ${lineNumber} for value trace`}
                    onClick={() => {
                      setTraceTarget({ filePath: activeContent.file_path, line: lineNumber })
                      onSelectLine?.(activeContent.file_path, lineNumber)
                    }}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault()
                        setTraceTarget({ filePath: activeContent.file_path, line: lineNumber })
                        onSelectLine?.(activeContent.file_path, lineNumber)
                      }
                    }}
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
          {tracePanel ? <aside className="code-explorer-trace-panel" aria-label="Embedded value trace">{tracePanel}</aside> : null}
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

function sourceScrollKey(repositoryId: string, filePath: string) {
  return `aica:source-scroll:${repositoryId}:${filePath}`
}

function loadSourceScroll(repositoryId: string, filePath: string): number {
  try {
    const value = Number(window.sessionStorage.getItem(sourceScrollKey(repositoryId, filePath)))
    return Number.isFinite(value) && value >= 0 ? value : 0
  } catch {
    return 0
  }
}

function saveSourceScroll(repositoryId: string, filePath: string, scrollTop: number) {
  try {
    window.sessionStorage.setItem(sourceScrollKey(repositoryId, filePath), String(Math.max(0, scrollTop)))
  } catch {
    // Source reading remains available when session storage is unavailable.
  }
}

const SOURCE_KEYWORDS = new Set([
  'and', 'as', 'async', 'await', 'break', 'case', 'catch', 'class', 'const', 'continue', 'def', 'do', 'else', 'elif',
  'except', 'export', 'extends', 'false', 'finally', 'for', 'from', 'function', 'if', 'import', 'in', 'is', 'let', 'new',
  'none', 'not', 'null', 'of', 'or', 'pass', 'raise', 'return', 'static', 'super', 'switch', 'this', 'throw', 'true',
  'try', 'var', 'while', 'with', 'yield',
])

function identifiersOnLine(line: string): string[] {
  const identifiers = line.match(/[A-Za-z_$][A-Za-z0-9_$]*/g) ?? []
  return [...new Set(identifiers.filter((value) => !SOURCE_KEYWORDS.has(value.toLocaleLowerCase())))].slice(0, 16)
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
