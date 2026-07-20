import type { FormEvent, ReactNode } from 'react'
import { CollapsibleAssistantPanel } from './components/chat/AssistantChat'
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
  ConversationSummary,
  AssistantRequestContext,
  ApiEndpoint,
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
import { endpointKeyFor } from './utils/apiEndpoint'
import { canChat } from './utils/repository'
import type { ValueTraceContext } from './utils/valueTrace'
import { ValueTracePanel } from './pages/workspace/GraphPage'

type AppRoutesProps = {
  route: ValidAppRoute
  page: Page
  repositories: Repository[]
  selectedRepository?: Repository
  overview: Overview | null
  apiEndpoints: ApiEndpoint[]
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
  conversations: ConversationSummary[]
  activeConversationId?: string
  activeConversationStale: boolean
  chatPending: boolean
  chatReplayLoading: boolean
  chatReplayError: boolean
  chatContext?: AssistantRequestContext
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
  clearChatContext: () => void
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
  loadFileContent: (repositoryId: string, filePath: string, line?: number) => void
  selectCodeLine: (filePath: string, line: number) => void
  clearCodeLine: () => void
  sendChatMessage: (event?: FormEvent) => void
  startNewChat: () => void
  selectConversation: (conversationId: string) => void
  deleteConversation: (conversationId: string) => void
  openEvidence: (citation: Citation) => void
  selectApiEndpoint: (endpointKey: string) => void
  openApiFlow: (endpoint: ApiEndpoint) => void
  runSearch: (event?: FormEvent) => void
  runImpactAnalysis: (event?: FormEvent) => void
  openImpact: (targetType: string, targetRef: string) => void
  projectSearchQuery?: string
  analyzeGraphArea: (scopePath: string) => void
  changeGraphView: (view: GraphView) => void
  traceValue: (context: ValueTraceContext) => void
  closeCodeTrace: () => void
  openCodeTraceInGraph: () => void
  returnToTraceSource: () => void
  changeGraphProjection: (patch: Partial<GraphProjectionInput>) => void
  expandGraphNode: (nodeId: string, direction: GraphProjectionInput['direction'], neighborOffset?: number) => Promise<GraphData | null>
  isWorkspacePage: boolean
}

export function AppRoutes(props: AppRoutesProps) {
  const {
    page,
    repositories,
    selectedRepository,
    overview,
    apiEndpoints,
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
        searchQuery={props.projectSearchQuery}
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
            onExploreFlow={() => props.changeGraphView('api-flow')}
            onOpenFile={(filePath) => selectedRepository && props.loadFileContent(selectedRepository.id, filePath)}
          />
        }
        {...props}
      />
    )
  }
  if (page === 'code') {
    const tracePanel = route.codeTrace ? (
      <ValueTracePanel
        key={route.codeTrace}
        graph={graph}
        projection={graphProjection}
        overview={overview}
        onGraphView={props.changeGraphView}
        onProjection={props.changeGraphProjection}
        onExpandNode={props.expandGraphNode}
        onAnalyzeArea={props.analyzeGraphArea}
        onOpenSource={(node) => node.file_path && selectedRepository && props.loadFileContent(selectedRepository.id, node.file_path, node.start_line)}
        onCloseEmbedded={props.closeCodeTrace}
        onOpenFullGraph={props.openCodeTraceInGraph}
      />
    ) : null
    return (
      <AssistantWorkspace
        main={<CodeExplorerPage repositoryId={selectedRepository?.id ?? 'unselected'} fileTree={fileTree} selectedFilePath={selectedFilePath} selectedLine={route.line} fileContent={fileContent} overview={overview} tracePanel={tracePanel} onSelectFile={(filePath) => selectedRepository && props.loadFileContent(selectedRepository.id, filePath)} onSelectLine={props.selectCodeLine} onClearSelectedLine={props.clearCodeLine} onTraceValue={props.traceValue} />}
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
        onExpandNode={props.expandGraphNode}
        onAnalyzeArea={props.analyzeGraphArea}
        onOpenSource={(node) => node.file_path && selectedRepository && props.loadFileContent(selectedRepository.id, node.file_path, node.start_line)}
        onTraceValue={props.traceValue}
        onReturnToSource={props.returnToTraceSource}
      />
    )
  }
  if (page === 'api') {
    const selectedEndpoint = apiEndpoints.find((endpoint) => endpointKeyFor(endpoint) === route.endpointKey)
    return (
      <WorkspacePage
        main={(
          <ApiExplorerPage
            endpoints={apiEndpoints}
            selectedEndpointKey={route.endpointKey}
            onSelectEndpoint={props.selectApiEndpoint}
          />
        )}
        side={(
          <ApiDetails
            endpoint={selectedEndpoint}
            requestedEndpointKey={route.endpointKey}
            onOpenSource={(endpoint) => selectedRepository && props.loadFileContent(
              selectedRepository.id,
              endpoint.file_path,
              endpoint.start_line,
            )}
            onTraceFlow={props.openApiFlow}
          />
        )}
      />
    )
  }
  if (page === 'assistant') {
    return (
      <WorkspacePage
        main={(
          <AssistantFullPage
            input={chatInput}
            messages={chatMessages}
            conversations={props.conversations}
            activeConversationId={props.activeConversationId}
            activeConversationStale={props.activeConversationStale}
            pending={props.chatPending}
            replayLoading={props.chatReplayLoading}
            replayError={props.chatReplayError}
            disabled={!canChat(selectedRepository) || props.chatReplayError}
            onInput={props.setChatInput}
            onSubmit={props.sendChatMessage}
            onEvidence={props.openEvidence}
            onNewChat={props.startNewChat}
            onSelectConversation={props.selectConversation}
            onDeleteConversation={props.deleteConversation}
          />
        )}
        side={<EvidenceSummary />}
      />
    )
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
  if (page === 'evidence') return <WorkspacePage main={<EvidencePage evidence={selectedEvidence} onOpenCode={(filePath, line) => selectedRepository && props.loadFileContent(selectedRepository.id, filePath, line)} />} side={null} />
  if (page === 'evaluation') {
    return <EvaluationRoute repository={selectedRepository} />
  }
  return <SettingsRoute isWorkspace={isWorkspacePage} />
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

function AssistantWorkspace({ main, selectedRepository, chatInput, chatMessages, chatContext, conversations, activeConversationId, activeConversationStale, chatPending, chatReplayLoading, chatReplayError, setChatInput, clearChatContext, sendChatMessage, startNewChat, selectConversation, deleteConversation, openEvidence }: AppRoutesProps & { main: ReactNode }) {
  return (
    <WorkspacePage
      main={main}
      compactSide
      side={
        <CollapsibleAssistantPanel
          input={chatInput}
          messages={chatMessages}
          context={chatContext}
          conversations={conversations}
          activeConversationId={activeConversationId}
          activeConversationStale={activeConversationStale}
          pending={chatPending}
          replayLoading={chatReplayLoading}
          replayError={chatReplayError}
          disabled={!canChat(selectedRepository) || chatReplayError}
          suggestions={['Explain the architecture', 'Trace the login flow', 'Where should I start reading?']}
          onInput={setChatInput}
          onRemoveContext={clearChatContext}
          onNewChat={startNewChat}
          onSelectConversation={selectConversation}
          onDeleteConversation={deleteConversation}
          onSubmit={sendChatMessage}
          onEvidence={openEvidence}
        />
      }
    />
  )
}
