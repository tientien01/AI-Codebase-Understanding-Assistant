import { useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import type { UseQueryResult } from '@tanstack/react-query'
import type { NavigateFunction } from 'react-router-dom'
import { safeErrorMessage } from '../api/client'
import {
  toAsyncViewState,
  toMutationAsyncViewState,
  useChatTranscriptQuery,
  useConversationListQuery,
  useDebouncedValue,
  useEvidenceQuery,
  useEndpointsQuery,
  useFileContentQuery,
  useFileTreeQuery,
  useGraphQuery,
  useGraphExpansion,
  useIndexStatusQuery,
  useOverviewQuery,
  useRepositoriesQuery,
  useSearchResultsQuery,
  useServerMutations,
} from '../features/server-state'
import { pathForPage } from '../routing/routes'
import type { AppRoute } from '../routing/routes'
import type {
  AssistantRequestContext,
  ChatResponse,
  Citation,
  ApiEndpoint,
  GraphData,
  GraphDirection,
  GraphProjectionInput,
  GraphView,
  Page,
  Repository,
} from '../types/api'
import { findFirstFile, isRepositoryUsable, reconcileRepositoryIndexStatus } from '../utils/repository'
import { decodeValueTraceContext, encodeValueTraceContext } from '../utils/valueTrace'
import type { ValueTraceContext } from '../utils/valueTrace'
import { useImportController } from './useImportController'

const workspacePages: Page[] = ['overview', 'code', 'graph', 'api', 'assistant', 'impact', 'search', 'evidence', 'evaluation']
const overviewPages: Page[] = ['overview', 'code', 'graph', 'impact']
const graphViews: GraphView[] = ['project-map', 'dependencies', 'api-flow', 'function-flow', 'data-flow']
const emptyRepositories: Repository[] = []
const requestFlowNodeTypes = ['endpoint', 'api_call', 'function', 'method']
const requestFlowEdgeTypes = ['calls_api', 'exposes_endpoint', 'calls']
const callFlowNodeTypes = ['function', 'method', 'builtin_call', 'stdlib_call', 'framework_call', 'external_call', 'unresolved_call']
const callFlowEdgeTypes = ['calls', 'calls_builtin', 'calls_stdlib', 'calls_framework', 'calls_external', 'calls_unresolved']
const valueFlowNodeTypes = ['dfg_node']
const defaultGraphProjection: Omit<GraphProjectionInput, 'indexVersion' | 'rootKeys' | 'maxDepth'> = {
  nodeTypes: [],
  edgeTypes: [],
  direction: 'both',
  maxNodes: 80,
  maxEdges: 160,
  minConfidence: 0,
  supportLevels: [],
  projectionMode: 'seeds',
  dependencyScope: 'adaptive',
  seedLimit: 12,
  neighborOffset: 0,
}

export function useAppController(route: AppRoute, navigate: NavigateFunction) {
  const page = route.status === 'valid' ? route.page : 'projects'
  const [selectedRepositoryId, setSelectedRepositoryId] = useState('')
  const [graphViewFallback, setGraphViewFallback] = useState<GraphView>('project-map')
  const [graphProjectionControls, setGraphProjectionControls] = useState(defaultGraphProjection)
  const [chatInput, setChatInput] = useState('How does the login flow work?')
  const [activeConversation, setActiveConversation] = useState<{ repositoryId: string; conversationId: string }>()
  const [chatOutcomes, setChatOutcomes] = useState<Record<string, Pick<ChatResponse, 'generation_mode' | 'provider_state' | 'retrieval_mode'>>>({})
  const [searchQueryDraft, setSearchQueryDraft] = useState('login auth token')
  const [impactTargetType, setImpactTargetType] = useState('symbol')
  const [impactTargetRefDraft, setImpactTargetRefDraft] = useState('login')
  const [apiError, setApiError] = useState('')

  const routeRepositoryId = route.status === 'valid' ? route.repositoryId : undefined
  const routeGraphView = route.status === 'valid' && route.graphView && graphViews.includes(route.graphView as GraphView)
    ? route.graphView as GraphView
    : undefined
  const graphView = routeGraphView ?? graphViewFallback
  const codeTraceRoot = route.status === 'valid' && route.page === 'code' ? route.codeTrace : undefined
  const activeGraphView: GraphView = codeTraceRoot ? 'data-flow' : graphView
  const searchQuery = route.status === 'valid' && route.page === 'search' && route.searchQuery !== undefined
    ? route.searchQuery
    : searchQueryDraft
  const impactTargetRef = route.status === 'valid' && route.page === 'impact' && route.impactTarget !== undefined
    ? route.impactTarget
    : impactTargetRefDraft
  const debouncedSearchQuery = useDebouncedValue(
    route.status === 'valid' && route.page === 'search' ? route.searchQuery?.trim() : undefined,
    300,
  )

  const repositoriesQuery = useRepositoriesQuery()
  const repositories = repositoriesQuery.data ?? emptyRepositories
  const repositoryFromList = useMemo(() => {
    if (routeRepositoryId) return repositories.find((repository) => repository.id === routeRepositoryId)
    return repositories.find((repository) => repository.id === selectedRepositoryId) ?? repositories[0]
  }, [repositories, routeRepositoryId, selectedRepositoryId])
  const indexStatusQuery = useIndexStatusQuery(repositoryFromList?.id, page === 'indexing')
  const selectedRepository = useMemo(
    () => reconcileRepositoryIndexStatus(repositoryFromList, indexStatusQuery.data),
    [indexStatusQuery.data, repositoryFromList],
  )
  const usableRepository = isRepositoryUsable(selectedRepository) ? selectedRepository : undefined
  const isWorkspacePage = Boolean(routeRepositoryId && workspacePages.includes(page))
  const graphProjection: GraphProjectionInput = {
    ...graphProjectionControls,
    indexVersion: usableRepository?.current_index_version,
    rootKeys: route.status === 'valid' && route.page === 'graph' && route.graphRoot
      ? [route.graphRoot]
      : codeTraceRoot
        ? [codeTraceRoot]
        : [],
    maxDepth: route.status === 'valid' && route.page === 'graph' && route.graphDepth !== undefined ? route.graphDepth : 2,
  }

  const overviewQuery = useOverviewQuery(usableRepository, overviewPages.includes(page))
  const endpointsQuery = useEndpointsQuery(usableRepository, page === 'api')
  const graphQuery = useGraphQuery(usableRepository, activeGraphView, graphProjection, page === 'graph' || Boolean(codeTraceRoot))
  const fetchGraphExpansion = useGraphExpansion(usableRepository)
  const fileTreeQuery = useFileTreeQuery(usableRepository, page === 'code')
  const defaultFilePath = page === 'code' ? findFirstFile(fileTreeQuery.data ?? [])?.path : undefined
  const selectedFilePath = route.status === 'valid' && route.page === 'code'
    ? route.filePath ?? defaultFilePath ?? ''
    : ''
  const fileContentQuery = useFileContentQuery(usableRepository, selectedFilePath || undefined, page === 'code')
  const derivedChatContext = useMemo<AssistantRequestContext | undefined>(() => {
    if (page === 'overview') return { page: 'overview' }
    if (
      page !== 'code'
      || !selectedFilePath
      || fileContentQuery.data?.file_path !== selectedFilePath
    ) return undefined
    const selectedLine = route.status === 'valid' && route.page === 'code' ? route.line : undefined
    const selectedSymbol = selectedLine
      ? fileContentQuery.data.symbols.find(
          (symbol) => symbol.start_line <= selectedLine && selectedLine <= symbol.end_line,
        )
      : undefined
    return {
      page: 'code',
      file_path: selectedFilePath,
      ...(selectedLine ? { start_line: selectedLine, end_line: selectedLine } : {}),
      ...(selectedSymbol?.symbol_name ? { symbol_name: selectedSymbol.symbol_name } : {}),
    }
  }, [fileContentQuery.data, page, route, selectedFilePath])
  const derivedChatContextKey = derivedChatContext ? JSON.stringify(derivedChatContext) : undefined
  const [dismissedChatContextKey, setDismissedChatContextKey] = useState<string>()
  const chatContext = derivedChatContextKey !== dismissedChatContextKey ? derivedChatContext : undefined
  const evidenceQuery = useEvidenceQuery(
    usableRepository,
    route.status === 'valid' && route.page === 'evidence' ? route.evidenceId : undefined,
    page === 'evidence',
  )
  const searchResultsQuery = useSearchResultsQuery(
    usableRepository,
    debouncedSearchQuery,
    page === 'search' && Boolean(debouncedSearchQuery),
  )
  const routeConversationId = route.status === 'valid' && route.page === 'assistant'
    ? route.conversationId
    : undefined
  const activeConversationId = routeConversationId
    ?? (activeConversation && activeConversation.repositoryId === selectedRepository?.id
      ? activeConversation.conversationId
      : undefined)
  const conversationListQuery = useConversationListQuery(
    selectedRepository,
    ['overview', 'code', 'assistant'].includes(page),
  )
  const chatTranscriptQuery = useChatTranscriptQuery(selectedRepository, activeConversationId)
  const chatMessages = (chatTranscriptQuery.data?.messages ?? []).map((message) => ({
    messageId: message.message_id,
    role: message.role,
    content: message.content,
    citations: message.citations,
    evidenceSufficient: message.evidence_sufficient,
    indexVersion: message.index_version,
    createdAt: message.created_at,
    generationMode: chatOutcomes[message.message_id]?.generation_mode,
    providerState: chatOutcomes[message.message_id]?.provider_state,
    retrievalMode: chatOutcomes[message.message_id]?.retrieval_mode,
  }))
  const mutations = useServerMutations(selectedRepository?.id, selectedRepository?.current_index_version)

  const importController = useImportController({
    setSelectedRepositoryId,
    setPage,
    setApiError,
  })

  const pageQuery = activePageQuery({
    page,
    repositoriesQuery,
    indexStatusQuery,
    overviewQuery,
    endpointsQuery,
    graphQuery,
    fileTreeQuery,
    fileContentQuery,
    evidenceQuery,
    searchResultsQuery,
    hasFilePath: Boolean(selectedFilePath),
    hasSearchQuery: Boolean(debouncedSearchQuery),
  })
  const pageState = page === 'impact'
    ? toMutationAsyncViewState(mutations.impact)
    : page === 'import'
      ? importController.asyncState
      : toAsyncViewState(pageQuery.query, { enabled: pageQuery.enabled, empty: pageQuery.empty })

  function openWorkspace(repositoryId: string) {
    setSelectedRepositoryId(repositoryId)
    navigate(pathForPage('overview', repositoryId))
  }

  function openFile(repositoryId: string, filePath: string, line?: number) {
    const traceRoot = codeTraceRoot
      ?? (route.status === 'valid' && route.page === 'graph' && decodeValueTraceContext(route.graphRoot) ? route.graphRoot : undefined)
    navigate(pathForPage('code', repositoryId, { filePath, line, codeTrace: traceRoot }))
  }

  function selectCodeLine(filePath: string, line: number) {
    if (!selectedRepository) return
    navigate(pathForPage('code', selectedRepository.id, {
      filePath,
      line,
      codeTrace: codeTraceRoot,
    }), { replace: true })
  }

  function openEvidence(citation: Citation) {
    if (!selectedRepository) return
    navigate(pathForPage('evidence', selectedRepository.id, { evidenceId: citation.evidence_id }))
  }

  function clearCodeLine() {
    if (!selectedRepository || route.status !== 'valid' || route.page !== 'code') return
    navigate(pathForPage('code', selectedRepository.id, {
      filePath: selectedFilePath,
      codeTrace: codeTraceRoot,
    }), { replace: true })
  }

  function selectApiEndpoint(endpointKey: string) {
    if (!selectedRepository) return
    navigate(pathForPage('api', selectedRepository.id, { endpointKey }))
  }

  function openApiFlow(endpoint: ApiEndpoint) {
    if (!selectedRepository) return
    const endpointKey = endpoint.endpoint_key
    if (!endpointKey) return
    setGraphViewFallback('api-flow')
    setGraphProjectionControls({
      ...defaultGraphProjection,
      nodeTypes: requestFlowNodeTypes,
      edgeTypes: requestFlowEdgeTypes,
      direction: 'outgoing',
      maxNodes: 32,
      maxEdges: 64,
      projectionMode: 'neighbors',
    })
    navigate(pathForPage('graph', selectedRepository.id, {
      graphView: 'api-flow',
      graphRoot: endpointKey,
      graphDepth: 2,
    }))
  }

  async function reindexRepository(repositoryId: string) {
    setSelectedRepositoryId(repositoryId)
    const result = await runAction(() => mutations.reindex.mutateAsync(repositoryId))
    if (result.ok) navigate(pathForPage('indexing'))
  }

  async function pauseIndexingJob(repositoryId: string, jobId: string) {
    await runAction(() => mutations.jobAction.mutateAsync({ action: 'pause', targetRepositoryId: repositoryId, jobId }))
  }

  async function resumeIndexingJob(repositoryId: string, jobId: string) {
    await runAction(() => mutations.jobAction.mutateAsync({ action: 'resume', targetRepositoryId: repositoryId, jobId }))
  }

  async function cancelIndexingJob(repositoryId: string, jobId: string) {
    await runAction(() => mutations.jobAction.mutateAsync({ action: 'cancel', targetRepositoryId: repositoryId, jobId }))
  }

  async function deleteRepository(repositoryId: string) {
    const repository = repositories.find((item) => item.id === repositoryId)
    const label = repository?.name ?? repositoryId
    if (!window.confirm(`Delete project "${label}" from AI Codebase Assistant? Uploaded source and index data will be removed.`)) return
    const result = await runAction(() => mutations.deleteRepository.mutateAsync(repositoryId))
    if (!result.ok) return
    if (selectedRepositoryId === repositoryId || routeRepositoryId === repositoryId) {
      setSelectedRepositoryId('')
      navigate(pathForPage('projects'))
    }
  }

  async function deleteAllRepositories() {
    if (!repositories.length) return
    if (!window.confirm(`Delete all ${repositories.length} projects from AI Codebase Assistant? Uploaded source and index data will be removed.`)) return
    const result = await runAction(() => mutations.deleteAllRepositories.mutateAsync())
    if (!result.ok) return
    setSelectedRepositoryId('')
    navigate(pathForPage('projects'))
  }

  async function analyzeGraphArea(scopePath: string) {
    if (!selectedRepository || !scopePath) return
    await runAction(() => mutations.expandGraph.mutateAsync({ targetRepositoryId: selectedRepository.id, scopePath }))
  }

  async function runImpactAnalysis(event?: FormEvent) {
    event?.preventDefault()
    if (!selectedRepository || !impactTargetRef.trim()) return
    navigate(pathForPage('impact', selectedRepository.id, {
      impactTarget: impactTargetRef.trim(),
      compareIndexVersionId: route.status === 'valid' ? route.compareIndexVersionId : undefined,
    }))
    await runAction(() => mutations.impact.mutateAsync({
      targetRepositoryId: selectedRepository.id,
      targetType: impactTargetType,
      targetRef: impactTargetRef.trim(),
    }))
  }

  async function sendChatMessage(event?: FormEvent) {
    event?.preventDefault()
    if (!selectedRepository || !chatInput.trim()) return
    const userText = chatInput.trim()
    setChatInput('')
    const result = await runAction(() => mutations.chat.mutateAsync({
      targetRepositoryId: selectedRepository.id,
      indexVersion: selectedRepository.current_index_version,
      message: userText,
      context: chatContext,
      conversationId: activeConversationId,
    }))
    if (!result.ok) return
    setChatOutcomes((current) => ({ ...current, [result.data.message_id]: result.data }))
    const conversationId = result.data.conversation_id
    setActiveConversation({ repositoryId: selectedRepository.id, conversationId })
    if (page === 'assistant') {
      navigate(pathForPage('assistant', selectedRepository.id, { conversationId }), { replace: true })
    }
  }

  function startNewChat() {
    if (!selectedRepository) return
    setActiveConversation(undefined)
    setChatInput('')
    if (page === 'assistant') navigate(pathForPage('assistant', selectedRepository.id))
  }

  function selectConversation(conversationId: string) {
    if (!selectedRepository) return
    setActiveConversation({ repositoryId: selectedRepository.id, conversationId })
    if (page === 'assistant') {
      navigate(pathForPage('assistant', selectedRepository.id, { conversationId }))
    }
  }

  async function runSearch(event?: FormEvent) {
    event?.preventDefault()
    if (!selectedRepository || !searchQuery.trim()) return
    const nextPath = pathForPage('search', selectedRepository.id, { searchQuery: searchQuery.trim() })
    if (route.status === 'valid' && route.page === 'search' && route.searchQuery?.trim() === searchQuery.trim()) {
      await searchResultsQuery.refetch()
    } else {
      navigate(nextPath)
    }
  }

  async function changeGraphView(view: GraphView) {
    setGraphViewFallback(view)
    if (!selectedRepository) return
    navigate(pathForPage('graph', selectedRepository.id, {
      graphView: view,
      // Canonical roots belong to one projection vocabulary and may not exist
      // in another view. A new relationship question starts without stale focus.
      graphRoot: undefined,
      graphDepth: route.status === 'valid' ? route.graphDepth : undefined,
    }))
  }

  function changeGraphProjection(patch: Partial<GraphProjectionInput>) {
    const next = { ...graphProjection, ...patch }
    setGraphProjectionControls({
      nodeTypes: next.nodeTypes,
      edgeTypes: next.edgeTypes,
      direction: next.direction,
      maxNodes: next.maxNodes,
      maxEdges: next.maxEdges,
      minConfidence: next.minConfidence,
      supportLevels: next.supportLevels,
      projectionMode: next.projectionMode,
      dependencyScope: next.dependencyScope,
      seedLimit: next.seedLimit,
      neighborOffset: next.neighborOffset,
    })
    if (route.status === 'valid' && route.page === 'graph' && route.repositoryId) {
      navigate(pathForPage('graph', route.repositoryId, {
        graphView,
        graphRoot: next.rootKeys[0],
        graphDepth: next.maxDepth,
      }), { replace: true })
    }
  }

  function traceValue(context: ValueTraceContext) {
    if (!selectedRepository) return
    const graphRoot = encodeValueTraceContext(context)
    setGraphViewFallback('data-flow')
    setGraphProjectionControls({
      ...defaultGraphProjection,
      nodeTypes: valueFlowNodeTypes,
      direction: 'both',
      maxNodes: 24,
      maxEdges: 48,
      projectionMode: 'seeds',
      dependencyScope: undefined,
      seedLimit: 24,
    })
    if (route.status === 'valid' && route.page === 'code' && context.kind === 'token') {
      navigate(pathForPage('code', selectedRepository.id, {
        filePath: context.filePath,
        line: context.line,
        codeTrace: graphRoot,
      }))
      return
    }
    navigate(pathForPage('graph', selectedRepository.id, {
      graphView: 'data-flow',
      graphRoot,
      graphDepth: 1,
    }))
  }

  function closeCodeTrace() {
    if (!selectedRepository || route.status !== 'valid' || route.page !== 'code') return
    navigate(pathForPage('code', selectedRepository.id, { filePath: selectedFilePath, line: route.line }), { replace: true })
  }

  function openCodeTraceInGraph() {
    if (!selectedRepository || !codeTraceRoot) return
    navigate(pathForPage('graph', selectedRepository.id, { graphView: 'data-flow', graphRoot: codeTraceRoot, graphDepth: 1 }))
  }

  function returnToTraceSource() {
    if (!selectedRepository || route.status !== 'valid' || route.page !== 'graph') return
    const context = decodeValueTraceContext(route.graphRoot)
    if (!context) return
    const line = context.kind === 'token' ? context.line : context.startLine
    navigate(pathForPage('code', selectedRepository.id, { filePath: context.filePath, line, codeTrace: route.graphRoot }))
  }

  async function expandGraphNode(nodeId: string, direction: GraphDirection, neighborOffset = 0): Promise<GraphData | null> {
    if (!usableRepository || !['dependencies', 'api-flow', 'function-flow', 'data-flow'].includes(activeGraphView)) return null
    const requestFlow = activeGraphView === 'api-flow'
    const callFlow = activeGraphView === 'function-flow'
    const valueFlow = activeGraphView === 'data-flow'
    const expansionProjection: GraphProjectionInput = {
      ...graphProjection,
      rootKeys: [nodeId],
      direction,
      maxDepth: 1,
      maxNodes: 13,
      maxEdges: 24,
      projectionMode: 'neighbors',
      neighborOffset,
      nodeTypes: requestFlow ? requestFlowNodeTypes : callFlow ? callFlowNodeTypes : valueFlow ? valueFlowNodeTypes : graphProjection.nodeTypes,
      edgeTypes: requestFlow ? requestFlowEdgeTypes : callFlow ? callFlowEdgeTypes : graphProjection.edgeTypes,
    }
    setApiError('')
    try {
      return await fetchGraphExpansion(activeGraphView, expansionProjection)
    } catch (error) {
      setApiError(safeErrorMessage(error))
      return null
    }
  }

  function setSearchQuery(value: string) {
    setSearchQueryDraft(value)
    if (route.status === 'valid' && route.page === 'search' && route.repositoryId) {
      navigate(pathForPage('search', route.repositoryId, { searchQuery: value, searchTypes: route.searchTypes }), { replace: true })
    }
  }

  function setImpactTargetRef(value: string) {
    setImpactTargetRefDraft(value)
    if (route.status === 'valid' && route.page === 'impact' && route.repositoryId) {
      navigate(pathForPage('impact', route.repositoryId, {
        impactTarget: value,
        compareIndexVersionId: route.compareIndexVersionId,
      }), { replace: true })
    }
  }

  function openImpact(targetType: string, targetRef: string) {
    setImpactTargetType(targetType)
    setImpactTargetRefDraft(targetRef)
    if (!selectedRepository) return
    navigate(pathForPage('impact', selectedRepository.id, { impactTarget: targetRef }))
  }

  function setPage(nextPage: Page) {
    const needsRepository = workspacePages.includes(nextPage)
    navigate(pathForPage(nextPage, needsRepository ? selectedRepository?.id : undefined))
  }

  async function runAction<T>(action: () => Promise<T>): Promise<{ ok: true; data: T } | { ok: false }> {
    setApiError('')
    try {
      return { ok: true, data: await action() }
    } catch (error) {
      setApiError(safeErrorMessage(error))
      return { ok: false }
    }
  }

  return {
    page,
    repositories,
    repositoriesLoaded: !repositoriesQuery.isPending,
    repositoriesLoadFailed: repositoriesQuery.isError,
    selectedRepository,
    overview: overviewQuery.data ?? null,
    apiEndpoints: endpointsQuery.data?.items ?? [],
    indexStatus: indexStatusQuery.data ?? null,
    graph: graphQuery.data ?? null,
    graphView: activeGraphView,
    graphProjection,
    fileTree: fileTreeQuery.data ?? [],
    selectedFilePath,
    fileContent: fileContentQuery.data ?? null,
    selectedEvidence: evidenceQuery.data ?? null,
    chatInput,
    chatMessages,
    conversations: conversationListQuery.data?.items ?? [],
    activeConversationId,
    activeConversationStale: chatTranscriptQuery.data?.conversation?.is_stale ?? false,
    chatReplayLoading: chatTranscriptQuery.isPending && Boolean(activeConversationId),
    chatReplayError: chatTranscriptQuery.isError,
    chatContext,
    searchQuery,
    searchResults: searchResultsQuery.data?.results ?? [],
    impactTargetType,
    impactTargetRef,
    impactResult: mutations.impact.data ?? null,
    ...importController,
    apiError,
    isWorkspacePage,
    pageState,
    setPage,
    setChatInput,
    clearChatContext: () => derivedChatContextKey && setDismissedChatContextKey(derivedChatContextKey),
    setSearchQuery,
    setImpactTargetType,
    setImpactTargetRef,
    openImpact,
    openWorkspace,
    reindexRepository,
    pauseIndexingJob,
    resumeIndexingJob,
    cancelIndexingJob,
    deleteRepository,
    deleteAllRepositories,
    loadFileContent: openFile,
    selectCodeLine,
    clearCodeLine,
    reloadRepositories: repositoriesQuery.refetch,
    retryActivePage: pageQuery.query ? () => { void pageQuery.refetch() } : undefined,
    sendChatMessage,
    startNewChat,
    selectConversation,
    openEvidence,
    selectApiEndpoint,
    openApiFlow,
    runSearch,
    analyzeGraphArea,
    runImpactAnalysis,
    changeGraphView,
    traceValue,
    closeCodeTrace,
    openCodeTraceInGraph,
    returnToTraceSource,
    changeGraphProjection,
    expandGraphNode,
  }
}

type PageQuery = {
  query?: UseQueryResult<unknown, Error>
  enabled: boolean
  empty?: (data: unknown) => boolean
  refetch: () => Promise<unknown>
}

function activePageQuery(input: {
  page: Page
  repositoriesQuery: UseQueryResult<Repository[], Error>
  indexStatusQuery: UseQueryResult<unknown, Error>
  overviewQuery: UseQueryResult<unknown, Error>
  endpointsQuery: UseQueryResult<unknown, Error>
  graphQuery: UseQueryResult<unknown, Error>
  fileTreeQuery: UseQueryResult<unknown, Error>
  fileContentQuery: UseQueryResult<unknown, Error>
  evidenceQuery: UseQueryResult<unknown, Error>
  searchResultsQuery: UseQueryResult<unknown, Error>
  hasFilePath: boolean
  hasSearchQuery: boolean
}): PageQuery {
  const asPageQuery = (query: UseQueryResult<unknown, Error>, enabled = true, empty?: (data: unknown) => boolean): PageQuery => ({
    query,
    enabled,
    empty,
    refetch: query.refetch,
  })
  if (input.page === 'projects') return asPageQuery(input.repositoriesQuery, true, (data) => Array.isArray(data) && data.length === 0)
  if (input.page === 'indexing') return asPageQuery(input.indexStatusQuery)
  if (input.page === 'overview') return asPageQuery(input.overviewQuery)
  if (input.page === 'api') {
    return asPageQuery(input.endpointsQuery, true, (data) => {
      const response = data as { items?: unknown[] }
      return Array.isArray(response.items) && response.items.length === 0
    })
  }
  if (input.page === 'graph') return asPageQuery(input.graphQuery)
  if (input.page === 'code') {
    return input.hasFilePath
      ? asPageQuery(input.fileContentQuery)
      : asPageQuery(input.fileTreeQuery, true, (data) => Array.isArray(data) && data.length === 0)
  }
  if (input.page === 'evidence') return asPageQuery(input.evidenceQuery)
  if (input.page === 'search') {
    return asPageQuery(input.searchResultsQuery, input.hasSearchQuery, (data) => {
      const response = data as { results?: unknown[] }
      return Array.isArray(response.results) && response.results.length === 0
    })
  }
  return { enabled: false, refetch: async () => undefined }
}
