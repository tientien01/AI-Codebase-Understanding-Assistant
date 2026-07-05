import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { requestJson, API_V1 } from '../api/client'
import type {
  ChatMessage,
  Citation,
  Evidence,
  FileContent,
  FileTreeNode,
  GraphData,
  IndexStatus,
  Overview,
  Page,
  Repository,
  SearchResult,
} from '../types/api'
import { findFirstFile, isRepositoryUsable } from '../utils/repository'
import { useImportController } from './useImportController'

const workspacePages: Page[] = ['overview', 'code', 'graph', 'api', 'assistant', 'impact', 'search', 'evidence', 'evaluation']

export function useAppController() {
  const [page, setPage] = useState<Page>('dashboard')
  const [repositories, setRepositories] = useState<Repository[]>([])
  const [selectedRepositoryId, setSelectedRepositoryId] = useState('')
  const [overview, setOverview] = useState<Overview | null>(null)
  const [indexStatus, setIndexStatus] = useState<IndexStatus | null>(null)
  const [graph, setGraph] = useState<GraphData | null>(null)
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
  const [searchQuery, setSearchQuery] = useState('login auth token')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [apiError, setApiError] = useState('')

  const selectedRepository = useMemo(
    () => repositories.find((repository) => repository.id === selectedRepositoryId) ?? repositories[0],
    [repositories, selectedRepositoryId],
  )
  const isWorkspacePage = workspacePages.includes(page)

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
    try {
      const data = await request<Repository[]>(`${API_V1}/repositories`)
      setRepositories(data)
      if (!selectedRepositoryId && data[0]) setSelectedRepositoryId(data[0].id)
    } catch {
      setRepositories([])
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

  async function loadGraph(repositoryId: string) {
    try {
      setGraph(await request<GraphData>(`${API_V1}/repositories/${repositoryId}/graph`))
    } catch {
      setGraph(null)
    }
  }

  async function loadFileTree(repositoryId: string) {
    try {
      const tree = await request<FileTreeNode[]>(`${API_V1}/repositories/${repositoryId}/files/tree`)
      setFileTree(tree)
      const firstFile = findFirstFile(tree)
      if (firstFile && !selectedFilePath) await loadFileContent(repositoryId, firstFile.path)
    } catch {
      setFileTree([])
    }
  }

  async function loadFileContent(repositoryId: string, filePath: string) {
    const content = await request<FileContent>(`${API_V1}/repositories/${repositoryId}/files/content?path=${encodeURIComponent(filePath)}`)
    setSelectedFilePath(filePath)
    setFileContent(content)
  }

  async function reindexRepository(repositoryId: string) {
    setSelectedRepositoryId(repositoryId)
    await request(`${API_V1}/repositories/${repositoryId}/index`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ force_reindex: true }),
    })
    await loadRepositories()
    await loadIndexStatus(repositoryId)
    setPage('indexing')
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
      setPage('dashboard')
    }
    await loadRepositories()
  }

  async function openWorkspace(repositoryId: string) {
    setSelectedRepositoryId(repositoryId)
    await loadWorkspaceData(repositoryId)
    setPage('overview')
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

  async function openEvidence(citation: Citation) {
    if (!selectedRepository) return
    const evidence = await request<Evidence>(`${API_V1}/repositories/${selectedRepository.id}/evidence/${citation.evidence_id}`)
    setSelectedEvidence(evidence)
    setPage('evidence')
  }

  async function runSearch(event?: FormEvent) {
    event?.preventDefault()
    if (!selectedRepository) return
    const response = await request<{ results: SearchResult[] }>(`${API_V1}/repositories/${selectedRepository.id}/search?q=${encodeURIComponent(searchQuery)}`)
    setSearchResults(response.results)
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
    selectedRepository,
    overview,
    indexStatus,
    graph,
    fileTree,
    selectedFilePath,
    fileContent,
    selectedEvidence,
    chatInput,
    chatMessages,
    searchQuery,
    searchResults,
    ...importController,
    apiError,
    isWorkspacePage,
    setPage,
    setChatInput,
    setSearchQuery,
    openWorkspace,
    reindexRepository,
    deleteRepository,
    loadFileContent,
    sendChatMessage,
    openEvidence,
    runSearch,
  }
}
