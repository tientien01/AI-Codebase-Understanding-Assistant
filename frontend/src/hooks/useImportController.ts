import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { uploadFormData } from '../api/upload'
import type { ImportMode, ImportPreview, Page } from '../types/api'

type ImportControllerDeps = {
  request: <T>(url: string, options?: RequestInit) => Promise<T>
  apiV1: string
  loadRepositories: () => Promise<void>
  loadIndexStatus: (repositoryId: string) => Promise<void>
  setSelectedRepositoryId: (repositoryId: string) => void
  setPage: (page: Page) => void
  setApiError: (message: string) => void
}

export function useImportController({
  request,
  apiV1,
  loadRepositories,
  loadIndexStatus,
  setSelectedRepositoryId,
  setPage,
  setApiError,
}: ImportControllerDeps) {
  const [projectName, setProjectName] = useState('fastapi-react-sample')
  const [githubUrl, setGithubUrlState] = useState('')
  const [importMode, setImportMode] = useState<ImportMode>('folder')
  const [folderFiles, setFolderFiles] = useState<File[]>([])
  const [zipFile, setZipFile] = useState<File | null>(null)
  const [importSessionId, setImportSessionId] = useState('')
  const [importPreview, setImportPreview] = useState<ImportPreview | null>(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [isPreviewLoading, setIsPreviewLoading] = useState(false)
  const lastPreviewKey = useRef('')

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

  function clearImportPreview() {
    setImportSessionId('')
    setImportPreview(null)
    setUploadProgress(0)
    setIsPreviewLoading(false)
    lastPreviewKey.current = ''
  }

  function updateGithubUrl(value: string) {
    setGithubUrlState(value)
    setImportSessionId('')
    setImportPreview(null)
    setUploadProgress(0)
  }

  async function submitImport(event: FormEvent) {
    event.preventDefault()
    if (importSessionId && importPreview) {
      await confirmImportSession(importSessionId)
      return
    }
    if (importMode === 'github') {
      await uploadGithubRepository()
      return
    }
    if (importMode === 'zip') {
      await uploadZipRepository()
      return
    }
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
    await createPreviewFromUpload(`${apiV1}/import-sessions/upload-zip`, formData)
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
    await createPreviewFromUpload(`${apiV1}/import-sessions/upload-folder`, formData)
  }

  async function uploadGithubRepository() {
    if (!isValidGithubUrl(githubUrl)) {
      setApiError('Enter a valid public GitHub repository URL.')
      return
    }
    setIsPreviewLoading(true)
    setUploadProgress(0)
    try {
      const session = await request<{ import_session_id: string }>(`${apiV1}/import-sessions/github`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: githubUrl.trim(), name: projectName || undefined }),
      })
      await loadImportPreview(session.import_session_id)
    } finally {
      setIsPreviewLoading(false)
    }
  }

  async function createPreviewFromUpload(url: string, formData: FormData) {
    setIsPreviewLoading(true)
    try {
      const session = await uploadWithErrorHandling(url, formData)
      await loadImportPreview(session.import_session_id)
    } finally {
      setIsPreviewLoading(false)
    }
  }

  async function loadImportPreview(nextImportSessionId: string) {
    const preview = await request<ImportPreview>(`${apiV1}/import-sessions/${nextImportSessionId}/preview`)
    setImportSessionId(nextImportSessionId)
    setImportPreview(preview)
  }

  async function confirmImportSession(nextImportSessionId: string) {
    const result = await request<{ repository_id: string }>(`${apiV1}/import-sessions/${nextImportSessionId}/confirm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: projectName, start_indexing: true, index_profile: 'balanced', duplicate_action: 'import_as_new' }),
    })
    setSelectedRepositoryId(result.repository_id)
    setImportSessionId('')
    setImportPreview(null)
    await loadRepositories()
    await loadIndexStatus(result.repository_id)
    setPage('indexing')
  }

  async function uploadWithErrorHandling(url: string, formData: FormData) {
    try {
      return await uploadFormData<{ import_session_id: string }>({
        url,
        formData,
        onProgress: setUploadProgress,
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Upload failed'
      setApiError(message)
      throw error
    }
  }

  return {
    projectName,
    githubUrl,
    importMode,
    folderFiles,
    zipFile,
    importPreview,
    uploadProgress,
    isPreviewLoading,
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
