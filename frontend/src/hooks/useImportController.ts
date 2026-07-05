import { useState } from 'react'
import type { FormEvent } from 'react'
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
  const [githubUrl, setGithubUrl] = useState('https://github.com/username/awesome-project')
  const [importMode, setImportMode] = useState<ImportMode>('folder')
  const [folderFiles, setFolderFiles] = useState<File[]>([])
  const [zipFile, setZipFile] = useState<File | null>(null)
  const [importSessionId, setImportSessionId] = useState('')
  const [importPreview, setImportPreview] = useState<ImportPreview | null>(null)

  function clearImportPreview() {
    setImportSessionId('')
    setImportPreview(null)
  }

  async function submitImport(event: FormEvent) {
    event.preventDefault()
    if (importSessionId && importPreview) {
      await confirmImportSession(importSessionId)
      return
    }
    if (importMode === 'github') {
      setApiError('GitHub URL import is dang phat trien. Use Upload Folder or Upload ZIP for this baseline.')
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
    const session = await request<{ import_session_id: string }>(`${apiV1}/import-sessions/upload-zip`, { method: 'POST', body: formData })
    await loadImportPreview(session.import_session_id)
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
    const session = await request<{ import_session_id: string }>(`${apiV1}/import-sessions/upload-folder`, { method: 'POST', body: formData })
    await loadImportPreview(session.import_session_id)
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

  return {
    projectName,
    githubUrl,
    importMode,
    folderFiles,
    zipFile,
    importPreview,
    setProjectName,
    setGithubUrl,
    setImportMode,
    setFolderFiles,
    setZipFile,
    clearImportPreview,
    submitImport,
  }
}
