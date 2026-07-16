import { useMutation, useQueryClient } from '@tanstack/react-query'
import { serverApi } from '../../api/server'
import type { AssistantRequestContext } from '../../types/api'
import { queryKeys } from './keys'

export function useServerMutations(repositoryId: string | undefined, indexVersion?: number) {
  const queryClient = useQueryClient()

  const reindex = useMutation({
    mutationFn: (targetRepositoryId: string) => serverApi.reindex(targetRepositoryId),
    onSuccess: async (_data, targetRepositoryId) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.repositories }),
        queryClient.invalidateQueries({ queryKey: queryKeys.status(targetRepositoryId) }),
      ])
    },
  })

  const jobAction = useMutation({
    mutationFn: ({ action, targetRepositoryId, jobId }: JobActionInput) => {
      if (action === 'pause') return serverApi.pauseJob(targetRepositoryId, jobId)
      if (action === 'resume') return serverApi.resumeJob(targetRepositoryId, jobId)
      return serverApi.cancelJob(targetRepositoryId, jobId)
    },
    onSuccess: async (_data, input) => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.status(input.targetRepositoryId) })
      if (input.action === 'cancel') await queryClient.invalidateQueries({ queryKey: queryKeys.repositories })
    },
  })

  const deleteRepository = useMutation({
    mutationFn: (targetRepositoryId: string) => serverApi.deleteRepository(targetRepositoryId),
    onSuccess: async (_data, targetRepositoryId) => {
      queryClient.removeQueries({ queryKey: queryKeys.repository(targetRepositoryId) })
      await queryClient.invalidateQueries({ queryKey: queryKeys.repositories })
    },
  })

  const deleteAllRepositories = useMutation({
    mutationFn: serverApi.deleteAllRepositories,
    onSuccess: async () => {
      queryClient.removeQueries({ queryKey: ['repository'] })
      await queryClient.invalidateQueries({ queryKey: queryKeys.repositories })
    },
  })

  const expandGraph = useMutation({
    mutationFn: ({ targetRepositoryId, scopePath }: { targetRepositoryId: string; scopePath: string }) =>
      serverApi.expandGraph(targetRepositoryId, scopePath),
    onSuccess: async (_data, input) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.repositories }),
        queryClient.invalidateQueries({ queryKey: queryKeys.status(input.targetRepositoryId) }),
        queryClient.invalidateQueries({
          queryKey: queryKeys.graphFamily(input.targetRepositoryId, input.targetRepositoryId === repositoryId ? indexVersion : undefined),
        }),
      ])
    },
  })

  const impact = useMutation({
    mutationFn: ({ targetRepositoryId, targetType, targetRef }: ImpactInput) =>
      serverApi.impact(targetRepositoryId, targetType, targetRef),
  })

  const chat = useMutation({
    mutationFn: ({ targetRepositoryId, message, context, conversationId }: ChatInput) =>
      serverApi.chat(targetRepositoryId, message, context, conversationId),
    onSuccess: (response, input) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.conversations(input.targetRepositoryId) })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.conversation(input.targetRepositoryId, response.conversation_id),
      })
    },
  })

  return { reindex, jobAction, deleteRepository, deleteAllRepositories, expandGraph, impact, chat }
}

type JobActionInput = {
  action: 'pause' | 'resume' | 'cancel'
  targetRepositoryId: string
  jobId: string
}

type ImpactInput = {
  targetRepositoryId: string
  targetType: string
  targetRef: string
}

type ChatInput = {
  targetRepositoryId: string
  indexVersion?: number
  message: string
  context?: AssistantRequestContext
  conversationId?: string
}
