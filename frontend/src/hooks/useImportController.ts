import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { API_V1, safeErrorMessage } from '../api/client'
import { serverApi } from '../api/server'
import { uploadFormData } from '../api/upload'
import { toAsyncViewState, toMutationAsyncViewState, useImportPreviewQuery } from '../features/server-state'
import { queryKeys } from '../features/server-state/keys'
import type { ImportMode, Page } from '../types/api'

type ImportControllerDeps = {
  setSelectedRepositoryId: (repositoryId: string) => void
  setPage: (page: Page) => void
  setApiError: (message: string) => void
}

export function useImportController({ setSelectedRepositoryId, setPage, setApiError }: ImportControllerDeps) {
  const queryClient = useQueryClient()
  const [projectName, setProjectName] = useState('fastapi-react-sample')
  const [githubUrl, setGithubUrlState] = useState('')
  const [importMode, setImportMode] = useState<ImportMode>('folder')
  const [folderFiles, setFolderFiles] = useState<File[]>([])
  const [zipFile, setZipFile] = useState<File | null>(null)
  const [importSessionId, setImportSessionId] = useState('')
  const [uploadProgress, setUploadProgress] = useState(0)
  const lastPreviewKey = useRef('')

  const previewQuery = useImportPreviewQuery(importSessionId)
  const githubSession = useMutation({
    mutationFn: ({ url, name }: { url: string; name?: string }) => serverApi.createGithubImport(url, name),
  })
  const uploadSession = useMutation({
    mutationFn: ({ url, formData }: { url: string; formData: FormData }) => uploadFormData<{ import_session_id: string }>({
      url,
      formData,
      onProgress: setUploadProgress,
    }),
  })
  const confirmSession = useMutation({
    mutationFn: ({ sessionId, name }: { sessionId: string; name: string }) => serverApi.confirmImport(sessionId, name),
    onSuccess: async (result) => {
      setSelectedRepositoryId(result.repository_id)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.repositories }),
        queryClient.invalidateQueries({ queryKey: queryKeys.status(result.repository_id) }),
      ])
    },
  })

  const activeMutation = confirmSession.isPending || confirmSession.isError
    ? confirmSession
    : githubSession.isPending || githubSession.isError
      ? githubSession
      : uploadSession
  const asyncState = importSessionId
    ? toAsyncViewState(previewQuery, { enabled: true })
    : toMutationAsyncViewState(activeMutation)

  function clearImportPreview() {
    if (importSessionId) queryClient.removeQueries({ queryKey: queryKeys.importPreview(importSessionId) })
    setImportSessionId('')
    setUploadProgress(0)
    lastPreviewKey.current = ''
    githubSession.reset()
    uploadSession.reset()
    confirmSession.reset()
  }

  function updateGithubUrl(value: string) {
    setGithubUrlState(value)
    clearImportPreview()
  }

  async function submitImport(event: FormEvent) {
    event.preventDefault()
    if (importSessionId && previewQuery.data) {
      await confirmImportSession(importSessionId)
      return
    }
    if (importMode === 'github') await uploadGithubRepository()
    if (importMode === 'zip') await uploadZipRepository()
    if (importMode === 'folder') await uploadFolderRepository()
  }

  async function uploadZipRepository() {
    if (!zipFile) {
      setApiError('Choose a zip file before importing.')
      return
    }
    const formData = new FormData()
    formData.append('file', zipFile)
    formData.append('name', projectName || zipFile.name.replace(/\.zip$/i, ''))
    await createPreviewFromUpload(`${API_V1}/import-sessions/upload-zip`, formData)
  }

  async function uploadFolderRepository() {
    if (folderFiles.length === 0) {
      setApiError('Choose a project folder before importing.')
      return
    }
    const formData = new FormData()
    for (const file of folderFiles) {
      const uploadFile = file as File & { webkitRelativePath?: string }
      formData.append('files', file)
      formData.append('relative_paths', uploadFile.webkitRelativePath || file.name)
    }
    formData.append('name', projectName || folderFiles[0].name)
    await createPreviewFromUpload(`${API_V1}/import-sessions/upload-folder`, formData)
  }

  async function uploadGithubRepository() {
    if (!isValidGithubUrl(githubUrl)) {
      setApiError('Enter a valid public GitHub repository URL.')
      return
    }
    setUploadProgress(0)
    try {
      setApiError('')
      const session = await githubSession.mutateAsync({ url: githubUrl.trim(), name: projectName || undefined })
      setImportSessionId(session.import_session_id)
    } catch (error) {
      setApiError(safeErrorMessage(error))
    }
  }

  async function createPreviewFromUpload(url: string, formData: FormData) {
    try {
      setApiError('')
      const session = await uploadSession.mutateAsync({ url, formData })
      setImportSessionId(session.import_session_id)
    } catch (error) {
      setApiError(safeErrorMessage(error))
    }
  }

  async function confirmImportSession(sessionId: string) {
    try {
      setApiError('')
      await confirmSession.mutateAsync({ sessionId, name: projectName })
      clearImportPreview()
      setPage('indexing')
    } catch (error) {
      setApiError(safeErrorMessage(error))
    }
  }

  useEffect(() => {
    if (importMode !== 'folder' || folderFiles.length === 0) return
    const key = folderPreviewKey(folderFiles, projectName)
    if (lastPreviewKey.current === key) return
    lastPreviewKey.current = key
    void uploadFolderRepository()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [importMode, folderFiles])

  useEffect(() => {
    if (importMode !== 'zip' || !zipFile) return
    const key = `zip:${zipFile.name}:${zipFile.size}:${projectName}`
    if (lastPreviewKey.current === key) return
    lastPreviewKey.current = key
    void uploadZipRepository()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [importMode, zipFile])

  useEffect(() => {
    if (importMode !== 'github' || !isValidGithubUrl(githubUrl)) return
    const key = `github:${githubUrl.trim()}:${projectName}`
    const timer = window.setTimeout(() => {
      if (lastPreviewKey.current === key) return
      lastPreviewKey.current = key
      void uploadGithubRepository()
    }, 800)
    return () => window.clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [importMode, githubUrl])

  return {
    projectName,
    githubUrl,
    importMode,
    folderFiles,
    zipFile,
    importPreview: previewQuery.data ?? null,
    uploadProgress,
    isPreviewLoading: githubSession.isPending || uploadSession.isPending || previewQuery.isFetching,
    asyncState,
    setProjectName,
    setGithubUrl: updateGithubUrl,
    setImportMode,
    setFolderFiles,
    setZipFile,
    clearImportPreview,
    submitImport,
  }
}

function folderPreviewKey(files: File[], projectName: string) {
  const first = files[0] as (File & { webkitRelativePath?: string }) | undefined
  const last = files[files.length - 1] as (File & { webkitRelativePath?: string }) | undefined
  return [
    'folder',
    projectName,
    files.length,
    first?.webkitRelativePath || first?.name || '',
    first?.size ?? 0,
    last?.webkitRelativePath || last?.name || '',
    last?.size ?? 0,
  ].join(':')
}

function isValidGithubUrl(value: string) {
  try {
    const url = new URL(value.trim())
    const parts = url.pathname.replace(/^\/+|\/+$/g, '').split('/')
    return url.protocol === 'https:' && ['github.com', 'www.github.com'].includes(url.hostname) && parts.length >= 2 && Boolean(parts[0] && parts[1])
  } catch {
    return false
  }
}
