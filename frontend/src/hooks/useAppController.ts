import { useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import type { UseQueryResult } from '@tanstack/react-query'
import type { NavigateFunction } from 'react-router-dom'
import { safeErrorMessage } from '../api/client'
import {
  toAsyncViewState,
  toMutationAsyncViewState,
  useChatTranscriptQuery,
  useDebouncedValue,
  useEvidenceQuery,
  useFileContentQuery,
  useFileTreeQuery,
  useGraphQuery,
  useIndexStatusQuery,
  useOverviewQuery,
  useRepositoriesQuery,
  useSearchResultsQuery,
  useServerMutations,
} from '../features/server-state'
import { pathForPage } from '../routing/routes'
import type { AppRoute } from '../routing/routes'
import type {
  Citation,
  GraphProjectionInput,
  GraphView,
  Page,
  Repository,
} from '../types/api'
import { findFirstFile, isRepositoryUsable } from '../utils/repository'
import { useImportController } from './useImportController'

const workspacePages: Page[] = ['overview', 'code', 'graph', 'api', 'assistant', 'impact', 'search', 'evidence', 'evaluation']
const overviewPages: Page[] = ['overview', 'code', 'graph', 'api', 'impact']
const graphViews: GraphView[] = ['project-map', 'dependencies', 'api-flow', 'function-flow', 'data-flow']
const emptyRepositories: Repository[] = []
const defaultGraphProjection: Omit<GraphProjectionInput, 'indexVersion' | 'rootKeys' | 'maxDepth'> = {
  nodeTypes: [],
  edgeTypes: [],
  direction: 'both',
  maxNodes: 80,
  maxEdges: 160,
  minConfidence: 0,
  supportLevels: [],
}

export function useAppController(route: AppRoute, navigate: NavigateFunction) {
  const page = route.status === 'valid' ? route.page : 'projects'
  const [selectedRepositoryId, setSelectedRepositoryId] = useState('')
  const [graphViewFallback, setGraphViewFallback] = useState<GraphView>('project-map')
  const [graphProjectionControls, setGraphProjectionControls] = useState(defaultGraphProjection)
  const [chatInput, setChatInput] = useState('How does the login flow work?')
  const [searchQueryDraft, setSearchQueryDraft] = useState('login auth token')
  const [impactTargetType, setImpactTargetType] = useState('symbol')
  const [impactTargetRefDraft, setImpactTargetRefDraft] = useState('login')
  const [apiError, setApiError] = useState('')

  const routeRepositoryId = route.status === 'valid' ? route.repositoryId : undefined
  const routeGraphView = route.status === 'valid' && route.graphView && graphViews.includes(route.graphView as GraphView)
    ? route.graphView as GraphView
    : undefined
  const graphView = routeGraphView ?? graphViewFallback
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
  const selectedRepository = useMemo(() => {
    if (routeRepositoryId) return repositories.find((repository) => repository.id === routeRepositoryId)
    return repositories.find((repository) => repository.id === selectedRepositoryId) ?? repositories[0]
  }, [repositories, routeRepositoryId, selectedRepositoryId])
  const usableRepository = isRepositoryUsable(selectedRepository) ? selectedRepository : undefined
  const isWorkspacePage = Boolean(routeRepositoryId && workspacePages.includes(page))
  const graphProjection: GraphProjectionInput = {
    ...graphProjectionControls,
    indexVersion: usableRepository?.current_index_version,
    rootKeys: route.status === 'valid' && route.page === 'graph' && route.graphRoot ? [route.graphRoot] : [],
    maxDepth: route.status === 'valid' && route.page === 'graph' && route.graphDepth !== undefined ? route.graphDepth : 2,
  }

  const indexStatusQuery = useIndexStatusQuery(selectedRepository?.id, page === 'indexing')
  const overviewQuery = useOverviewQuery(usableRepository, overviewPages.includes(page))
  const graphQuery = useGraphQuery(usableRepository, graphView, graphProjection, page === 'graph')
  const fileTreeQuery = useFileTreeQuery(usableRepository, page === 'code')
  const defaultFilePath = page === 'code' ? findFirstFile(fileTreeQuery.data ?? [])?.path : undefined
  const selectedFilePath = route.status === 'valid' && route.page === 'code'
    ? route.filePath ?? defaultFilePath ?? ''
    : ''
  const fileContentQuery = useFileContentQuery(usableRepository, selectedFilePath || undefined, page === 'code')
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
  const chatTranscriptQuery = useChatTranscriptQuery(selectedRepository)
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

  function openFile(repositoryId: string, filePath: string) {
    navigate(pathForPage('code', repositoryId, { filePath }))
  }

  function openEvidence(citation: Citation) {
    if (!selectedRepository) return
    navigate(pathForPage('evidence', selectedRepository.id, { evidenceId: citation.evidence_id }))
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
    await runAction(() => mutations.chat.mutateAsync({
      targetRepositoryId: selectedRepository.id,
      indexVersion: selectedRepository.current_index_version,
      message: userText,
    }))
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
      graphRoot: route.status === 'valid' ? route.graphRoot : undefined,
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
    })
    if (route.status === 'valid' && route.page === 'graph' && route.repositoryId) {
      navigate(pathForPage('graph', route.repositoryId, {
        graphView,
        graphRoot: next.rootKeys[0],
        graphDepth: next.maxDepth,
      }), { replace: true })
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
    indexStatus: indexStatusQuery.data ?? null,
    graph: graphQuery.data ?? null,
    graphView,
    graphProjection,
    fileTree: fileTreeQuery.data ?? [],
    selectedFilePath,
    fileContent: fileContentQuery.data ?? null,
    selectedEvidence: evidenceQuery.data ?? null,
    chatInput,
    chatMessages: chatTranscriptQuery.data,
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
    setSearchQuery,
    setImpactTargetType,
    setImpactTargetRef,
    openWorkspace,
    reindexRepository,
    pauseIndexingJob,
    resumeIndexingJob,
    cancelIndexingJob,
    deleteRepository,
    deleteAllRepositories,
    loadFileContent: openFile,
    reloadRepositories: repositoriesQuery.refetch,
    retryActivePage: pageQuery.query ? () => { void pageQuery.refetch() } : undefined,
    sendChatMessage,
    openEvidence,
    runSearch,
    analyzeGraphArea,
    runImpactAnalysis,
    changeGraphView,
    changeGraphProjection,
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
  if (['overview', 'api'].includes(input.page)) return asPageQuery(input.overviewQuery)
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
