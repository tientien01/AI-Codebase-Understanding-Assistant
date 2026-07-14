import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { API_V1, safeErrorMessage } from '../api/client'
import { serverApi } from '../api/server'
import { uploadFormData } from '../api/upload'
import { useImportPreviewQuery, useImportSessionStatusQuery } from '../features/server-state'
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
  const [folderSelectedCount, setFolderSelectedCount] = useState(0)
  const [folderExcludedCount, setFolderExcludedCount] = useState(0)
  const [zipFile, setZipFile] = useState<File | null>(null)
  const [importSessionId, setImportSessionId] = useState('')
  const [uploadProgress, setUploadProgress] = useState(0)
  const [acquisitionStartedAt, setAcquisitionStartedAt] = useState<number | null>(null)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [isPreparingUpload, setIsPreparingUpload] = useState(false)

  const statusQuery = useImportSessionStatusQuery(importSessionId)
  const previewReady = statusQuery.data?.status === 'preview_ready'
  const previewQuery = useImportPreviewQuery(importSessionId, previewReady)
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
  const cancelSession = useMutation({ mutationFn: (sessionId: string) => serverApi.cancelImport(sessionId) })
  const asyncState = { kind: 'initial' as const }

  function clearImportPreview() {
    if (importSessionId) queryClient.removeQueries({ queryKey: queryKeys.importPreview(importSessionId) })
    if (importSessionId) queryClient.removeQueries({ queryKey: queryKeys.importStatus(importSessionId) })
    setImportSessionId('')
    setUploadProgress(0)
    setAcquisitionStartedAt(null)
    setElapsedSeconds(0)
    setIsPreparingUpload(false)
    githubSession.reset()
    uploadSession.reset()
    confirmSession.reset()
    cancelSession.reset()
  }

  function updateGithubUrl(value: string) {
    setGithubUrlState(value)
    clearImportPreview()
  }

  function updateFolderFiles(files: File[]) {
    clearImportPreview()
    const eligibleFiles = files.filter((file) => !isLocallyExcluded(file))
    setFolderSelectedCount(files.length)
    setFolderExcludedCount(files.length - eligibleFiles.length)
    setFolderFiles(eligibleFiles)
  }

  function updateZipFile(file: File | null) {
    clearImportPreview()
    setZipFile(file)
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
      setApiError('Choose a project folder with indexable files before importing.')
      return
    }
    const totalBytes = folderFiles.reduce((total, file) => total + file.size, 0)
    setUploadProgress(0)
    setAcquisitionStartedAt(Date.now())
    setIsPreparingUpload(true)
    let activeSessionId = ''
    try {
      setApiError('')
      const session = await serverApi.startFolderImport(projectName || folderRootName(folderFiles), folderFiles.length, totalBytes)
      activeSessionId = session.import_session_id
      setImportSessionId(session.import_session_id)
      let uploadedBytes = 0
      for (const batch of fileBatches(folderFiles, 200)) {
        const batchBytes = batch.reduce((total, file) => total + file.size, 0)
        const formData = new FormData()
        for (const file of batch) {
          const uploadFile = file as File & { webkitRelativePath?: string }
          formData.append('files', file)
          formData.append('relative_paths', uploadFile.webkitRelativePath || file.name)
        }
        await uploadFormData({
          url: `${API_V1}/import-sessions/${session.import_session_id}/upload-folder-batch`,
          formData,
          onProgress: (batchProgress) => {
            const sentBytes = uploadedBytes + (batchBytes * batchProgress / 100)
            setUploadProgress(totalBytes > 0 ? Math.min(99, Math.round((sentBytes / totalBytes) * 100)) : 0)
          },
        })
        uploadedBytes += batchBytes
        setUploadProgress(totalBytes > 0 ? Math.min(99, Math.round((uploadedBytes / totalBytes) * 100)) : 0)
      }
      await serverApi.completeFolderImport(session.import_session_id)
      setUploadProgress(100)
    } catch (error) {
      if (activeSessionId) {
        await serverApi.cancelImport(activeSessionId).catch(() => undefined)
        queryClient.removeQueries({ queryKey: queryKeys.importStatus(activeSessionId) })
        queryClient.removeQueries({ queryKey: queryKeys.importPreview(activeSessionId) })
        setImportSessionId('')
      }
      setUploadProgress(0)
      setAcquisitionStartedAt(null)
      setApiError(safeErrorMessage(error))
    } finally {
      setIsPreparingUpload(false)
    }
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
      setAcquisitionStartedAt(Date.now())
      setImportSessionId(session.import_session_id)
    } catch (error) {
      setApiError(safeErrorMessage(error))
    }
  }

  async function createPreviewFromUpload(url: string, formData: FormData) {
    setAcquisitionStartedAt(Date.now())
    setIsPreparingUpload(true)
    try {
      setApiError('')
      const session = await uploadSession.mutateAsync({ url, formData })
      setImportSessionId(session.import_session_id)
    } catch (error) {
      setApiError(safeErrorMessage(error))
    } finally {
      setIsPreparingUpload(false)
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

  async function cancelImportSession() {
    if (!importSessionId) {
      clearImportPreview()
      return
    }
    try {
      await cancelSession.mutateAsync(importSessionId)
      clearImportPreview()
    } catch (error) {
      setApiError(safeErrorMessage(error))
    }
  }

  useEffect(() => {
    if (!acquisitionStartedAt || ['preview_ready', 'failed', 'cancelled'].includes(statusQuery.data?.status ?? '')) return
    const update = () => setElapsedSeconds(Math.max(0, Math.floor((Date.now() - acquisitionStartedAt) / 1_000)))
    update()
    const timer = window.setInterval(update, 1_000)
    return () => window.clearInterval(timer)
  }, [acquisitionStartedAt, statusQuery.data?.status])

  useEffect(() => {
    if (statusQuery.data?.status === 'failed') {
      setApiError(statusQuery.data.error_message || 'Repository preview preparation failed.')
    } else if (statusQuery.isError) {
      setApiError(safeErrorMessage(statusQuery.error))
    } else if (previewQuery.isError) {
      setApiError(safeErrorMessage(previewQuery.error))
    }
  }, [previewQuery.error, previewQuery.isError, setApiError, statusQuery.data?.error_message, statusQuery.data?.status, statusQuery.error, statusQuery.isError])

  return {
    projectName,
    githubUrl,
    importMode,
    folderFiles,
    folderSelectedCount,
    folderExcludedCount,
    zipFile,
    importPreview: previewQuery.data ?? null,
    importStatus: statusQuery.data ?? null,
    uploadProgress,
    elapsedSeconds,
    isConfirming: confirmSession.isPending,
    isPreviewLoading: githubSession.isPending || uploadSession.isPending || isPreparingUpload || Boolean(importSessionId && !previewQuery.data && !statusQuery.isError && !previewQuery.isError && statusQuery.data?.status !== 'failed' && statusQuery.data?.status !== 'cancelled'),
    canPreparePreview: importMode === 'github' ? isValidGithubUrl(githubUrl) : importMode === 'zip' ? Boolean(zipFile) : folderFiles.length > 0,
    asyncState,
    setProjectName,
    setGithubUrl: updateGithubUrl,
    setImportMode,
    setFolderFiles: updateFolderFiles,
    setZipFile: updateZipFile,
    clearImportPreview,
    cancelImportSession,
    submitImport,
  }
}

const LOCAL_EXCLUDED_DIRECTORIES = new Set(['.git', 'node_modules', 'venv', '.venv', 'dist', 'build', '__pycache__'])

function isLocallyExcluded(file: File) {
  const relativePath = (file as File & { webkitRelativePath?: string }).webkitRelativePath || file.name
  const directoryParts = relativePath.replace(/\\/g, '/').split('/').slice(1, -1)
  return directoryParts.some((part) => LOCAL_EXCLUDED_DIRECTORIES.has(part.toLowerCase()))
}

function folderRootName(files: File[]) {
  const first = files[0] as (File & { webkitRelativePath?: string }) | undefined
  return first?.webkitRelativePath?.replace(/\\/g, '/').split('/')[0] || first?.name || 'Imported folder'
}

function fileBatches(files: File[], batchSize: number) {
  const batches: File[][] = []
  for (let index = 0; index < files.length; index += batchSize) batches.push(files.slice(index, index + batchSize))
  return batches
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
