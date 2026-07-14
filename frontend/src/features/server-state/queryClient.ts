import { QueryClient } from '@tanstack/react-query'
import { retryDelay, shouldRetry } from './policy'

export function createAppQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        gcTime: 10 * 60_000,
        staleTime: 30_000,
        retry: shouldRetry,
        retryDelay,
        refetchOnReconnect: true,
        refetchOnWindowFocus: true,
      },
      mutations: {
        retry: false,
      },
    },
  })
}
