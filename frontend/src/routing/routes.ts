import type { Page } from '../types/api'

export type RouteOptions = {
  filePath?: string
  line?: number
  symbolKey?: string
  endpointKey?: string
  graphView?: string
  graphRoot?: string
  graphDepth?: number
  impactTarget?: string
  compareIndexVersionId?: string
  searchQuery?: string
  searchTypes?: string
  conversationId?: string
  evidenceId?: string
}

export type ValidAppRoute = RouteOptions & {
  status: 'valid'
  page: Page
  pathname: string
  repositoryId?: string
  detail: 'page' | 'symbol' | 'conversation' | 'evidence'
}

export type InvalidAppRoute = {
  status: 'invalid'
  pathname: string
  reason: 'unknown_route' | 'malformed_identifier' | 'unsafe_source_path' | 'invalid_parameter'
}

export type AppRoute = ValidAppRoute | InvalidAppRoute

const managementPages: Partial<Record<Page, string>> = {
  projects: '/projects',
  import: '/import',
  indexing: '/index-jobs',
  settings: '/settings',
}

const workspaceSegments: Partial<Record<Page, string>> = {
  overview: 'overview',
  code: 'code',
  api: 'api',
  graph: 'graph',
  impact: 'impact',
  search: 'search',
  assistant: 'assistant',
  evaluation: 'evaluation',
}

export function resolveAppRoute(location: { pathname: string; search: string }): AppRoute {
  const { pathname, search } = location
  const management = Object.entries(managementPages).find(([, path]) => path === pathname)
  if (management) return validRoute(management[0] as Page, pathname)

  const rawSegments = pathname.split('/').slice(1)
  if (rawSegments[0] !== 'repositories' || rawSegments.length < 3) {
    return invalidRoute(pathname, 'unknown_route')
  }

  const decoded = decodeSegments(rawSegments)
  if (!decoded) return invalidRoute(pathname, 'malformed_identifier')
  const [, repositoryId, surface, detailId] = decoded
  if (!repositoryId) return invalidRoute(pathname, 'malformed_identifier')

  const query = new URLSearchParams(search)
  if (surface === 'symbols' && decoded.length === 4 && detailId) {
    return validRoute('code', pathname, repositoryId, { detail: 'symbol', symbolKey: detailId })
  }
  if (surface === 'evidence' && decoded.length === 4 && detailId) {
    return validRoute('evidence', pathname, repositoryId, { detail: 'evidence', evidenceId: detailId })
  }
  if (surface === 'assistant' && (decoded.length === 3 || (decoded.length === 4 && detailId))) {
    return validRoute('assistant', pathname, repositoryId, {
      detail: detailId ? 'conversation' : 'page',
      conversationId: detailId,
    })
  }

  const pageEntry = Object.entries(workspaceSegments).find(([, segment]) => segment === surface)
  if (!pageEntry || decoded.length !== 3) return invalidRoute(pathname, 'unknown_route')
  const page = pageEntry[0] as Page

  if (page === 'code') {
    const filePath = query.get('path') || undefined
    if (filePath && !isSafeRelativeSourcePath(filePath)) return invalidRoute(pathname, 'unsafe_source_path')
    const line = positiveInteger(query.get('line'))
    if (query.has('line') && !line) return invalidRoute(pathname, 'invalid_parameter')
    return validRoute(page, pathname, repositoryId, {
      filePath,
      line,
    })
  }
  if (page === 'api') {
    return validRoute(page, pathname, repositoryId, { endpointKey: query.get('endpoint') || undefined })
  }
  if (page === 'graph') {
    const graphView = query.get('view') || undefined
    const graphDepth = positiveInteger(query.get('depth'))
    if (graphView && !['project-map', 'dependencies', 'api-flow', 'function-flow', 'data-flow'].includes(graphView)) {
      return invalidRoute(pathname, 'invalid_parameter')
    }
    if (query.has('depth') && !graphDepth) return invalidRoute(pathname, 'invalid_parameter')
    return validRoute(page, pathname, repositoryId, {
      graphView,
      graphRoot: query.get('root') || undefined,
      graphDepth,
    })
  }
  if (page === 'impact') {
    return validRoute(page, pathname, repositoryId, {
      impactTarget: query.get('target') || undefined,
      compareIndexVersionId: query.get('compare') || undefined,
    })
  }
  if (page === 'search') {
    return validRoute(page, pathname, repositoryId, {
      searchQuery: query.get('q') || undefined,
      searchTypes: query.get('types') || undefined,
    })
  }
  return validRoute(page, pathname, repositoryId)
}

export function pathForPage(page: Page, repositoryId?: string, options: RouteOptions = {}): string {
  const managementPath = managementPages[page]
  if (managementPath) return managementPath
  if (!repositoryId) throw new Error(`Repository identity is required for ${page}.`)

  const repositoryRoot = `/repositories/${encodeRouteSegment(repositoryId)}`
  if (options.symbolKey) return `${repositoryRoot}/symbols/${encodeRouteSegment(options.symbolKey)}`
  if (page === 'evidence') {
    if (!options.evidenceId) throw new Error('Evidence identity is required for the evidence page.')
    return `${repositoryRoot}/evidence/${encodeRouteSegment(options.evidenceId)}`
  }
  if (page === 'assistant' && options.conversationId) {
    return `${repositoryRoot}/assistant/${encodeRouteSegment(options.conversationId)}`
  }

  const segment = workspaceSegments[page]
  if (!segment) throw new Error(`No canonical route exists for ${page}.`)
  const query = new URLSearchParams()
  if (page === 'code' && options.filePath) {
    if (!isSafeRelativeSourcePath(options.filePath)) throw new Error('Source path must be repository-relative.')
    query.set('path', options.filePath)
    if (options.line && options.line > 0) query.set('line', String(Math.floor(options.line)))
  }
  if (page === 'api' && options.endpointKey) query.set('endpoint', options.endpointKey)
  if (page === 'graph') {
    if (options.graphView) query.set('view', options.graphView)
    if (options.graphRoot) query.set('root', options.graphRoot)
    if (options.graphDepth && options.graphDepth > 0) query.set('depth', String(Math.floor(options.graphDepth)))
  }
  if (page === 'impact') {
    if (options.impactTarget) query.set('target', options.impactTarget)
    if (options.compareIndexVersionId) query.set('compare', options.compareIndexVersionId)
  }
  if (page === 'search') {
    if (options.searchQuery) query.set('q', options.searchQuery)
    if (options.searchTypes) query.set('types', options.searchTypes)
  }
  const encodedQuery = query.toString()
  return `${repositoryRoot}/${segment}${encodedQuery ? `?${encodedQuery}` : ''}`
}

export function isSafeRelativeSourcePath(value: string): boolean {
  const hasControlCharacter = [...value].some((character) => {
    const code = character.charCodeAt(0)
    return code < 32 || code === 127
  })
  if (!value || hasControlCharacter || value.startsWith('/') || value.startsWith('\\') || value.includes('\\')) return false
  if (/^[a-zA-Z]:/.test(value)) return false
  return !value.split('/').some((segment) => segment === '..' || segment === '')
}

function validRoute(
  page: Page,
  pathname: string,
  repositoryId?: string,
  options: RouteOptions & { detail?: ValidAppRoute['detail'] } = {},
): ValidAppRoute {
  return {
    status: 'valid',
    page,
    pathname,
    repositoryId,
    detail: options.detail ?? 'page',
    ...options,
  }
}

function invalidRoute(pathname: string, reason: InvalidAppRoute['reason']): InvalidAppRoute {
  return { status: 'invalid', pathname, reason }
}

function decodeSegments(segments: string[]): string[] | null {
  try {
    return segments.map((segment) => decodeURIComponent(segment))
  } catch {
    return null
  }
}

function encodeRouteSegment(value: string): string {
  return encodeURIComponent(value)
}

function positiveInteger(value: string | null): number | undefined {
  if (!value || !/^\d+$/.test(value)) return undefined
  const parsed = Number(value)
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : undefined
}
