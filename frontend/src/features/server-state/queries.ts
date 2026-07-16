import { useEffect } from 'react'
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query'
import { serverApi } from '../../api/server'
import type { ChatMessage, GraphProjectionInput, GraphView, Repository } from '../../types/api'
import { queryKeys } from './keys'
import { indexRefetchInterval, isTerminalJobStatus } from './policy'

export function useRepositoriesQuery() {
  return useQuery({
    queryKey: queryKeys.repositories,
    queryFn: ({ signal }) => serverApi.repositories(signal),
  })
}

export function useSettingsQuery() {
  return useQuery({
    queryKey: queryKeys.settings,
    queryFn: ({ signal }) => serverApi.settings(signal),
  })
}

export function useIgnorePatternsQuery() {
  return useQuery({
    queryKey: queryKeys.ignorePatterns,
    queryFn: ({ signal }) => serverApi.ignorePatterns(signal),
  })
}

export function useIndexStatusQuery(repositoryId: string | undefined, polling: boolean) {
  const queryClient = useQueryClient()
  const query = useQuery({
    queryKey: queryKeys.status(repositoryId ?? 'unselected'),
    queryFn: ({ signal }) => serverApi.indexStatus(repositoryId!, signal),
    enabled: Boolean(repositoryId),
    refetchInterval: polling
      ? (query) => indexRefetchInterval(query.state.data, {
          hidden: typeof document !== 'undefined' && document.hidden,
          repositoryId: repositoryId ?? 'unselected',
          failureCount: query.state.fetchFailureCount,
        })
      : false,
  })

  useEffect(() => {
    if (!polling || !isTerminalJobStatus(query.data?.status)) return
    void queryClient.invalidateQueries({ queryKey: queryKeys.repositories })
  }, [polling, query.data?.status, queryClient])

  return query
}

export function useOverviewQuery(repository: Repository | undefined, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.overview(repository?.id ?? 'unselected', repository?.current_index_version),
    queryFn: ({ signal }) => serverApi.overview(repository!.id, signal),
    enabled: Boolean(repository && enabled),
  })
}

export function useEndpointsQuery(repository: Repository | undefined, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.endpoints(repository?.id ?? 'unselected', repository?.current_index_version),
    queryFn: ({ signal }) => serverApi.endpoints(repository!.id, signal),
    enabled: Boolean(repository && enabled),
  })
}

export function useGraphQuery(repository: Repository | undefined, view: GraphView, projection: GraphProjectionInput, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.graph(repository?.id ?? 'unselected', repository?.current_index_version, view, projection),
    queryFn: ({ signal }) => serverApi.graph(repository!.id, view, projection, signal),
    enabled: Boolean(repository && enabled),
  })
}

export function useGraphExpansion(repository: Repository | undefined) {
  const queryClient = useQueryClient()
  return async (view: GraphView, projection: GraphProjectionInput) => {
    if (!repository) return null
    return queryClient.fetchQuery({
      queryKey: queryKeys.graph(repository.id, repository.current_index_version, view, projection),
      queryFn: ({ signal }) => serverApi.graph(repository.id, view, projection, signal),
      staleTime: Number.POSITIVE_INFINITY,
    })
  }
}

export function useFileTreeQuery(repository: Repository | undefined, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.fileTree(repository?.id ?? 'unselected', repository?.current_index_version),
    queryFn: ({ signal }) => serverApi.fileTree(repository!.id, signal),
    enabled: Boolean(repository && enabled),
  })
}

export function useFileContentQuery(repository: Repository | undefined, filePath: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.fileContent(repository?.id ?? 'unselected', repository?.current_index_version, filePath ?? 'unselected'),
    queryFn: ({ signal }) => serverApi.fileContent(repository!.id, filePath!, signal),
    enabled: Boolean(repository && filePath && enabled),
    placeholderData: keepPreviousData,
  })
}

export function useEvidenceQuery(repository: Repository | undefined, evidenceId: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.evidence(repository?.id ?? 'unselected', repository?.current_index_version, evidenceId ?? 'unselected'),
    queryFn: ({ signal }) => serverApi.evidence(repository!.id, evidenceId!, signal),
    enabled: Boolean(repository && evidenceId && enabled),
  })
}

export function useSearchResultsQuery(repository: Repository | undefined, query: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.search(repository?.id ?? 'unselected', repository?.current_index_version, query ?? ''),
    queryFn: ({ signal }) => serverApi.search(repository!.id, query!, signal),
    enabled: Boolean(repository && query?.trim() && enabled),
  })
}

export function useChatTranscriptQuery(repository: Repository | undefined) {
  return useQuery({
    queryKey: queryKeys.chat(repository?.id ?? 'unselected', repository?.current_index_version),
    queryFn: async (): Promise<ChatMessage[]> => initialChatTranscript,
    enabled: false,
    initialData: initialChatTranscript,
    staleTime: Number.POSITIVE_INFINITY,
  })
}

export function useImportPreviewQuery(sessionId: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.importPreview(sessionId || 'unselected'),
    queryFn: ({ signal }) => serverApi.importPreview(sessionId, signal),
    enabled: Boolean(sessionId && enabled),
    staleTime: Number.POSITIVE_INFINITY,
    gcTime: 5 * 60_000,
  })
}

export function useImportSessionStatusQuery(sessionId: string) {
  return useQuery({
    queryKey: queryKeys.importStatus(sessionId || 'unselected'),
    queryFn: ({ signal }) => serverApi.importSessionStatus(sessionId, signal),
    enabled: Boolean(sessionId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status && ['preview_ready', 'failed', 'cancelled'].includes(status) ? false : 750
    },
  })
}

const initialChatTranscript: ChatMessage[] = []
