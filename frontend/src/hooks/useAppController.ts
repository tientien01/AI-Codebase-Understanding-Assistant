import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import type { NavigateFunction } from 'react-router-dom'
import { requestJson, API_V1 } from '../api/client'
import { pathForPage } from '../routing/routes'
import type { AppRoute } from '../routing/routes'
import type {
  ChatMessage,
  Citation,
  Evidence,
  FileContent,
  FileTreeNode,
  GraphData,
  GraphView,
  ImpactResult,
  IndexStatus,
  Overview,
  Page,
  Repository,
  SearchResult,
} from '../types/api'
import { findFirstFile, isRepositoryUsable } from '../utils/repository'
import { useImportController } from './useImportController'

const workspacePages: Page[] = ['overview', 'code', 'graph', 'api', 'assistant', 'impact', 'search', 'evidence', 'evaluation']
const graphViews: GraphView[] = ['project-map', 'dependencies', 'api-flow', 'function-flow', 'data-flow']

export function useAppController(route: AppRoute, navigate: NavigateFunction) {
  const page = route.status === 'valid' ? route.page : 'projects'
  const [repositories, setRepositories] = useState<Repository[]>([])
  const [repositoriesLoaded, setRepositoriesLoaded] = useState(false)
  const [repositoriesLoadFailed, setRepositoriesLoadFailed] = useState(false)
  const [selectedRepositoryId, setSelectedRepositoryId] = useState('')
  const [overview, setOverview] = useState<Overview | null>(null)
  const [indexStatus, setIndexStatus] = useState<IndexStatus | null>(null)
  const [graph, setGraph] = useState<GraphData | null>(null)
  const [graphViewFallback, setGraphView] = useState<GraphView>('project-map')
  const [fileTree, setFileTree] = useState<FileTreeNode[]>([])
  const [selectedFilePath, setSelectedFilePath] = useState('')
  const [fileContent, setFileContent] = useState<FileContent | null>(null)
  const [selectedEvidence, setSelectedEvidence] = useState<Evidence | null>(null)
  const [chatInput, setChatInput] = useState('How does the login flow work?')
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content: 'Import and index a repository, then ask architecture, API flow, debugging, onboarding, or impact questions.',
      evidenceSufficient: false,
    },
  ])
  const [searchQueryDraft, setSearchQueryDraft] = useState('login auth token')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [impactTargetType, setImpactTargetType] = useState('symbol')
  const [impactTargetRefDraft, setImpactTargetRefDraft] = useState('login')
  const [impactResult, setImpactResult] = useState<ImpactResult | null>(null)
  const [apiError, setApiError] = useState('')

  const routeRepositoryId = route.status === 'valid' ? route.repositoryId : undefined
  const routeFilePath = route.status === 'valid' ? route.filePath : undefined
  const routeEvidenceId = route.status === 'valid' ? route.evidenceId : undefined
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
  const selectedRepository = useMemo(() => {
    if (routeRepositoryId) return repositories.find((repository) => repository.id === routeRepositoryId)
    return repositories.find((repository) => repository.id === selectedRepositoryId) ?? repositories[0]
  }, [repositories, routeRepositoryId, selectedRepositoryId])
  const isWorkspacePage = Boolean(routeRepositoryId && workspacePages.includes(page))

  useEffect(() => {
    void loadRepositories()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!selectedRepository) return
    void loadIndexStatus(selectedRepository.id)
    if (isRepositoryUsable(selectedRepository)) {
      void loadWorkspaceData(selectedRepository.id)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedRepository?.id, selectedRepository?.status])

  useEffect(() => {
    if (route.status !== 'valid' || !selectedRepository || route.repositoryId !== selectedRepository.id) return
    if (!isRepositoryUsable(selectedRepository)) return
    if (route.page === 'code' && route.filePath) void fetchFileContent(selectedRepository.id, route.filePath)
    if (route.page === 'evidence' && route.evidenceId) void fetchEvidence(selectedRepository.id, route.evidenceId)
    // Route identity is the authority for direct-link restoration.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [route.pathname, routeFilePath, routeEvidenceId, selectedRepository?.id, selectedRepository?.status])

  useEffect(() => {
    if (page !== 'indexing' || !selectedRepository) return
    const timer = window.setInterval(() => {
      void loadIndexStatus(selectedRepository.id)
      void loadRepositories()
    }, 2500)
    return () => window.clearInterval(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, selectedRepository?.id])

  async function request<T>(url: string, options?: RequestInit): Promise<T> {
    setApiError('')
    try {
      return await requestJson<T>(url, options)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Request failed'
      setApiError(message)
      throw error
    }
  }

  async function loadRepositories() {
    setRepositoriesLoadFailed(false)
    try {
      const data = await request<Repository[]>(`${API_V1}/repositories`)
      setRepositories(data)
      if (!selectedRepositoryId && data[0]) setSelectedRepositoryId(data[0].id)
    } catch {
      setRepositories([])
      setRepositoriesLoadFailed(true)
    } finally {
      setRepositoriesLoaded(true)
    }
  }

  async function loadWorkspaceData(repositoryId: string) {
    await Promise.all([loadOverview(repositoryId), loadGraph(repositoryId), loadFileTree(repositoryId)])
  }

  async function loadOverview(repositoryId: string) {
    try {
      setOverview(await request<Overview>(`${API_V1}/repositories/${repositoryId}/overview`))
    } catch {
      setOverview(null)
    }
  }

  async function loadIndexStatus(repositoryId: string) {
    try {
      setIndexStatus(await request<IndexStatus>(`${API_V1}/repositories/${repositoryId}/index/status`))
    } catch {
      setIndexStatus(null)
    }
  }

  async function loadGraph(repositoryId: string, view: GraphView = graphView) {
    try {
      setGraph(await request<GraphData>(`${API_V1}/repositories/${repositoryId}/graph/${view}`))
    } catch {
      setGraph(null)
    }
  }

  async function changeGraphView(view: GraphView) {
    setGraphView(view)
    if (selectedRepository) {
      navigate(pathForPage('graph', selectedRepository.id, {
        graphView: view,
        graphRoot: route.status === 'valid' ? route.graphRoot : undefined,
        graphDepth: route.status === 'valid' ? route.graphDepth : undefined,
      }))
      await loadGraph(selectedRepository.id, view)
    }
  }

  async function loadFileTree(repositoryId: string) {
    try {
      const tree = await request<FileTreeNode[]>(`${API_V1}/repositories/${repositoryId}/files/tree`)
      setFileTree(tree)
      const firstFile = findFirstFile(tree)
      const routeOwnsFile = route.status === 'valid' && route.repositoryId === repositoryId && Boolean(route.filePath)
      if (firstFile && !selectedFilePath && !routeOwnsFile) await fetchFileContent(repositoryId, firstFile.path)
    } catch {
      setFileTree([])
    }
  }

  async function fetchFileContent(repositoryId: string, filePath: string) {
    const content = await request<FileContent>(`${API_V1}/repositories/${repositoryId}/files/content?path=${encodeURIComponent(filePath)}`)
    setSelectedFilePath(filePath)
    setFileContent(content)
  }

  function openFile(repositoryId: string, filePath: string) {
    navigate(pathForPage('code', repositoryId, { filePath }))
  }

  async function reindexRepository(repositoryId: string) {
    setSelectedRepositoryId(repositoryId)
    await request(`${API_V1}/repositories/${repositoryId}/index`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ force_reindex: false }),
    })
    await loadRepositories()
    await loadIndexStatus(repositoryId)
    navigate(pathForPage('indexing'))
  }

  async function pauseIndexingJob(repositoryId: string, jobId: string) {
    await request(`${API_V1}/repositories/${repositoryId}/index/jobs/${jobId}/pause`, { method: 'POST' })
    await loadIndexStatus(repositoryId)
  }

  async function resumeIndexingJob(repositoryId: string, jobId: string) {
    await request(`${API_V1}/repositories/${repositoryId}/index/jobs/${jobId}/resume`, { method: 'POST' })
    await loadIndexStatus(repositoryId)
  }

  async function cancelIndexingJob(repositoryId: string, jobId: string) {
    await request(`${API_V1}/repositories/${repositoryId}/index/jobs/${jobId}/cancel`, { method: 'POST' })
    await loadRepositories()
    await loadIndexStatus(repositoryId)
  }

  async function deleteRepository(repositoryId: string) {
    const repository = repositories.find((item) => item.id === repositoryId)
    const label = repository?.name ?? repositoryId
    if (!window.confirm(`Delete project "${label}" from AI Codebase Assistant? Uploaded source and index data will be removed.`)) return
    await request(`${API_V1}/repositories/${repositoryId}`, { method: 'DELETE' })
    if (selectedRepositoryId === repositoryId) {
      setSelectedRepositoryId('')
      setOverview(null)
      setIndexStatus(null)
      setGraph(null)
      setFileTree([])
      setSelectedFilePath('')
      setFileContent(null)
      setSelectedEvidence(null)
      navigate(pathForPage('projects'))
    }
    await loadRepositories()
  }

  async function deleteAllRepositories() {
    if (!repositories.length) return
    if (!window.confirm(`Delete all ${repositories.length} projects from AI Codebase Assistant? Uploaded source and index data will be removed.`)) return
    await request(`${API_V1}/repositories/bulk-delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ delete_all: true }),
    })
    setSelectedRepositoryId('')
    setOverview(null)
    setIndexStatus(null)
    setGraph(null)
    setFileTree([])
    setSelectedFilePath('')
    setFileContent(null)
    setSelectedEvidence(null)
    navigate(pathForPage('projects'))
    await loadRepositories()
  }

  async function openWorkspace(repositoryId: string) {
    setSelectedRepositoryId(repositoryId)
    navigate(pathForPage('overview', repositoryId))
  }

  async function sendChatMessage(event?: FormEvent) {
    event?.preventDefault()
    if (!selectedRepository || !chatInput.trim()) return
    const userText = chatInput.trim()
    setChatInput('')
    setChatMessages((items) => [...items, { role: 'user', content: userText }])
    const response = await request<{ answer: string; citations: Citation[]; evidence_sufficient: boolean }>(
      `${API_V1}/repositories/${selectedRepository.id}/chat`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userText, options: { max_retrieval_rounds: 2 } }),
      },
    )
    setChatMessages((items) => [...items, { role: 'assistant', content: response.answer, citations: response.citations, evidenceSufficient: response.evidence_sufficient }])
  }

  async function fetchEvidence(repositoryId: string, evidenceId: string) {
    const evidence = await request<Evidence>(`${API_V1}/repositories/${repositoryId}/evidence/${encodeURIComponent(evidenceId)}`)
    setSelectedEvidence(evidence)
  }

  function openEvidence(citation: Citation) {
    if (!selectedRepository) return
    navigate(pathForPage('evidence', selectedRepository.id, { evidenceId: citation.evidence_id }))
  }

  async function runSearch(event?: FormEvent) {
    event?.preventDefault()
    if (!selectedRepository) return
    navigate(pathForPage('search', selectedRepository.id, { searchQuery }))
    const response = await request<{ results: SearchResult[] }>(`${API_V1}/repositories/${selectedRepository.id}/search?q=${encodeURIComponent(searchQuery)}`)
    setSearchResults(response.results)
  }

  async function analyzeGraphArea(scopePath: string) {
    if (!selectedRepository || !scopePath) return
    await request(`${API_V1}/repositories/${selectedRepository.id}/graph/expand`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scope_path: scopePath }),
    })
    await loadRepositories()
    await loadIndexStatus(selectedRepository.id)
    await loadGraph(selectedRepository.id)
  }

  async function runImpactAnalysis(event?: FormEvent) {
    event?.preventDefault()
    if (!selectedRepository || !impactTargetRef.trim()) return
    navigate(pathForPage('impact', selectedRepository.id, {
      impactTarget: impactTargetRef.trim(),
      compareIndexVersionId: route.status === 'valid' ? route.compareIndexVersionId : undefined,
    }))
    const result = await request<ImpactResult>(`${API_V1}/repositories/${selectedRepository.id}/impact`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target_type: impactTargetType,
        target_ref: impactTargetRef.trim(),
        max_depth: 3,
      }),
    })
    setImpactResult(result)
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

  const importController = useImportController({
    request,
    apiV1: API_V1,
    loadRepositories,
    loadIndexStatus,
    setSelectedRepositoryId,
    setPage,
    setApiError,
  })

  return {
    page,
    repositories,
    repositoriesLoaded,
    repositoriesLoadFailed,
    selectedRepository,
    overview,
    indexStatus,
    graph,
    graphView,
    fileTree,
    selectedFilePath,
    fileContent,
    selectedEvidence,
    chatInput,
    chatMessages,
    searchQuery,
    searchResults,
    impactTargetType,
    impactTargetRef,
    impactResult,
    ...importController,
    apiError,
    isWorkspacePage,
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
    reloadRepositories: loadRepositories,
    sendChatMessage,
    openEvidence,
    runSearch,
    analyzeGraphArea,
    runImpactAnalysis,
    changeGraphView,
  }
}
