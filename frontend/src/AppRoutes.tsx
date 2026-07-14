import type { FormEvent, ReactNode } from 'react'
import { AssistantPanel } from './components/chat/AssistantChat'
import { ImportPage, IndexingPage, ProjectsPage } from './pages/management'
import { RouteRecoveryPage } from './pages/routing'
import { pathForPage } from './routing/routes'
import type { ValidAppRoute } from './routing/routes'
import { toAsyncViewState, useIgnorePatternsQuery, useIndexStatusQuery, useSettingsQuery } from './features/server-state'
import {
  ApiDetails,
  ApiExplorerPage,
  AssistantFullPage,
  CodeExplorerPage,
  EvaluationPage,
  EvidencePage,
  EvidenceSummary,
  GraphPage,
  ImpactPage,
  OverviewPage,
  SearchFilters,
  SearchPage,
  SettingsPage,
  WorkspacePage,
} from './pages/workspace'
import type {
  ChatMessage,
  Citation,
  Evidence,
  FileContent,
  FileTreeNode,
  GraphData,
  GraphProjectionInput,
  GraphView,
  ImpactResult,
  ImportMode,
  ImportPreview,
  ImportSessionStatus,
  IndexStatus,
  Overview,
  Page,
  Repository,
  SearchResult,
} from './types/api'
import { canChat } from './utils/repository'

type AppRoutesProps = {
  route: ValidAppRoute
  page: Page
  repositories: Repository[]
  selectedRepository?: Repository
  overview: Overview | null
  indexStatus: IndexStatus | null
  graph: GraphData | null
  graphView: GraphView
  graphProjection: GraphProjectionInput
  fileTree: FileTreeNode[]
  selectedFilePath: string
  fileContent: FileContent | null
  selectedEvidence: Evidence | null
  chatInput: string
  chatMessages: ChatMessage[]
  searchQuery: string
  searchResults: SearchResult[]
  impactTargetType: string
  impactTargetRef: string
  impactResult: ImpactResult | null
  projectName: string
  githubUrl: string
  importMode: ImportMode
  folderFiles: File[]
  folderSelectedCount: number
  folderExcludedCount: number
  zipFile: File | null
  importPreview: ImportPreview | null
  importStatus: ImportSessionStatus | null
  uploadProgress: number
  elapsedSeconds: number
  canPreparePreview: boolean
  isConfirming: boolean
  isPreviewLoading: boolean
  setPage: (page: Page) => void
  setChatInput: (value: string) => void
  setSearchQuery: (value: string) => void
  setImpactTargetType: (value: string) => void
  setImpactTargetRef: (value: string) => void
  setProjectName: (value: string) => void
  setGithubUrl: (value: string) => void
  setImportMode: (mode: ImportMode) => void
  setFolderFiles: (files: File[]) => void
  setZipFile: (file: File | null) => void
  clearImportPreview: () => void
  cancelImportSession: () => void
  submitImport: (event: FormEvent) => void
  openWorkspace: (repositoryId: string) => void
  reindexRepository: (repositoryId: string) => void
  pauseIndexingJob: (repositoryId: string, jobId: string) => void
  resumeIndexingJob: (repositoryId: string, jobId: string) => void
  cancelIndexingJob: (repositoryId: string, jobId: string) => void
  deleteRepository: (repositoryId: string) => void
  deleteAllRepositories: () => void
  loadFileContent: (repositoryId: string, filePath: string) => void
  sendChatMessage: (event?: FormEvent) => void
  openEvidence: (citation: Citation) => void
  runSearch: (event?: FormEvent) => void
  runImpactAnalysis: (event?: FormEvent) => void
  openImpact: (targetType: string, targetRef: string) => void
  analyzeGraphArea: (scopePath: string) => void
  changeGraphView: (view: GraphView) => void
  changeGraphProjection: (patch: Partial<GraphProjectionInput>) => void
  isWorkspacePage: boolean
}

export function AppRoutes(props: AppRoutesProps) {
  const {
    page,
    repositories,
    selectedRepository,
    overview,
    indexStatus,
    graph,
    graphView,
    graphProjection,
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
    projectName,
    githubUrl,
    importMode,
    folderFiles,
    folderSelectedCount,
    folderExcludedCount,
    zipFile,
    importPreview,
    importStatus,
    uploadProgress,
    elapsedSeconds,
    canPreparePreview,
    isConfirming,
    isPreviewLoading,
    isWorkspacePage,
    route,
  } = props

  if (route.detail === 'symbol') {
    return (
      <RouteRecoveryPage
        title="Symbol detail is not available yet"
        description="The symbol identity is preserved in this deep link, but the current API does not expose the bounded symbol-detail read model required to render it safely."
        requestedPath={route.pathname}
        actionPath={pathForPage('code', route.repositoryId)}
        actionLabel="Open Code Explorer"
      />
    )
  }
  if (route.detail === 'conversation') {
    return (
      <RouteRecoveryPage
        title="Conversation replay is not available yet"
        description="The conversation identity is preserved, but public owned-history loading is outside UI-001. Start from the current assistant without showing unrelated messages."
        requestedPath={route.pathname}
        actionPath={pathForPage('assistant', route.repositoryId)}
        actionLabel="Open Assistant"
      />
    )
  }

  if (page === 'projects') {
    return (
      <ProjectsPage
        repositories={repositories}
        onNewProject={() => props.setPage('import')}
        onOpen={props.openWorkspace}
        onReindex={props.reindexRepository}
        onDelete={props.deleteRepository}
        onDeleteAll={props.deleteAllRepositories}
        onViewIndexJobs={() => props.setPage('indexing')}
      />
    )
  }
  if (page === 'import') {
    return (
      <ImportPage
        mode={importMode}
        projectName={projectName}
        githubUrl={githubUrl}
        folderCount={folderFiles.length}
        folderSelectedCount={folderSelectedCount}
        folderExcludedCount={folderExcludedCount}
        zipFileName={zipFile?.name ?? ''}
        preview={importPreview}
        importStatus={importStatus}
        uploadProgress={uploadProgress}
        elapsedSeconds={elapsedSeconds}
        canPreparePreview={canPreparePreview}
        isConfirming={isConfirming}
        isPreviewLoading={isPreviewLoading}
        onModeChange={(mode) => {
          props.setImportMode(mode)
          props.clearImportPreview()
        }}
        onNameChange={props.setProjectName}
        onGithubUrlChange={props.setGithubUrl}
        onFolderFiles={(files) => {
          props.setFolderFiles(files)
          props.clearImportPreview()
        }}
        onZipFile={(file) => {
          props.setZipFile(file)
          props.clearImportPreview()
        }}
        onSubmit={props.submitImport}
        onCancel={props.cancelImportSession}
      />
    )
  }
  if (page === 'indexing') {
    return (
      <IndexingPage
        status={indexStatus}
        repository={selectedRepository}
        onOpen={() => selectedRepository && props.openWorkspace(selectedRepository.id)}
        onPause={() => selectedRepository && indexStatus?.job_id && props.pauseIndexingJob(selectedRepository.id, indexStatus.job_id)}
        onResume={() => selectedRepository && indexStatus?.job_id && props.resumeIndexingJob(selectedRepository.id, indexStatus.job_id)}
        onCancel={() => selectedRepository && indexStatus?.job_id && props.cancelIndexingJob(selectedRepository.id, indexStatus.job_id)}
      />
    )
  }
  if (page === 'overview') {
    return (
      <AssistantWorkspace
        main={
          <OverviewPage
            overview={overview}
            onQuestion={props.setChatInput}
            onExploreArchitecture={() => props.changeGraphView('project-map')}
            onOpenFile={(filePath) => selectedRepository && props.loadFileContent(selectedRepository.id, filePath)}
          />
        }
        {...props}
      />
    )
  }
  if (page === 'code') {
    return (
      <AssistantWorkspace
        main={<CodeExplorerPage fileTree={fileTree} selectedFilePath={selectedFilePath} selectedLine={route.line} fileContent={fileContent} overview={overview} onSelectFile={(filePath) => selectedRepository && props.loadFileContent(selectedRepository.id, filePath)} />}
        {...props}
      />
    )
  }
  if (page === 'graph') {
    return (
      <GraphPage
        graph={graph}
        graphView={graphView}
        projection={graphProjection}
        overview={overview}
        onGraphView={props.changeGraphView}
        onProjection={props.changeGraphProjection}
        onAnalyzeArea={props.analyzeGraphArea}
        onOpenSource={(node) => node.file_path && selectedRepository && props.loadFileContent(selectedRepository.id, node.file_path)}
        onOpenImpact={(node) => props.openImpact(impactTargetTypeFor(node.type), node.id)}
      />
    )
  }
  if (page === 'api') return <WorkspacePage main={<ApiExplorerPage overview={overview} />} side={<ApiDetails overview={overview} />} />
  if (page === 'assistant') {
    return <WorkspacePage main={<AssistantFullPage input={chatInput} messages={chatMessages} disabled={!canChat(selectedRepository)} onInput={props.setChatInput} onSubmit={props.sendChatMessage} onEvidence={props.openEvidence} />} side={<EvidenceSummary />} />
  }
  if (page === 'impact') {
    return (
      <WorkspacePage
        main={
          <ImpactPage
            overview={overview}
            targetType={impactTargetType}
            targetRef={impactTargetRef}
            result={impactResult}
            onTargetType={props.setImpactTargetType}
            onTargetRef={props.setImpactTargetRef}
            onRun={props.runImpactAnalysis}
          />
        }
        side={<EvidenceSummary />}
      />
    )
  }
  if (page === 'search') return <WorkspacePage main={<SearchPage query={searchQuery} results={searchResults} onQuery={props.setSearchQuery} onSearch={props.runSearch} onEvidence={props.openEvidence} />} side={<SearchFilters />} />
  if (page === 'evidence') return <WorkspacePage main={<EvidencePage evidence={selectedEvidence} />} side={<EvidenceSummary />} />
  if (page === 'evaluation') {
    return <EvaluationRoute repository={selectedRepository} />
  }
  return <SettingsRoute isWorkspace={isWorkspacePage} />
}

function impactTargetTypeFor(nodeType: string) {
  if (['file', 'endpoint', 'model', 'schema'].includes(nodeType)) return nodeType
  return 'symbol'
}

function SettingsRoute({ isWorkspace }: { isWorkspace: boolean }) {
  const settingsQuery = useSettingsQuery()
  const ignorePatternsQuery = useIgnorePatternsQuery()
  return (
    <SettingsPage
      isWorkspace={isWorkspace}
      settings={settingsQuery.data}
      ignorePatterns={ignorePatternsQuery.data}
      settingsState={toAsyncViewState(settingsQuery)}
      ignorePatternsState={toAsyncViewState(ignorePatternsQuery, {
        enabled: true,
        empty: (data) => Boolean(data && typeof data === 'object' && 'effective_patterns' in data
          && Array.isArray(data.effective_patterns) && data.effective_patterns.length === 0),
      })}
      onRetry={() => {
        void settingsQuery.refetch()
        void ignorePatternsQuery.refetch()
      }}
    />
  )
}

function EvaluationRoute({ repository }: { repository?: Repository }) {
  const indexStatusQuery = useIndexStatusQuery(repository?.id, false)
  return (
    <WorkspacePage
      main={
        <EvaluationPage
          repository={repository}
          indexStatus={indexStatusQuery.data ?? null}
          indexState={toAsyncViewState(indexStatusQuery, { enabled: Boolean(repository) })}
          onRetry={() => { void indexStatusQuery.refetch() }}
        />
      }
      side={<EvidenceSummary />}
    />
  )
}

function AssistantWorkspace({ main, selectedRepository, chatInput, chatMessages, setChatInput, sendChatMessage, openEvidence }: AppRoutesProps & { main: ReactNode }) {
  return (
    <WorkspacePage
      main={main}
      side={<AssistantPanel input={chatInput} messages={chatMessages} disabled={!canChat(selectedRepository)} onInput={setChatInput} onSubmit={sendChatMessage} onEvidence={openEvidence} />}
    />
  )
}
