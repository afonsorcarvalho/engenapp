'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/authStore'
import { useEcmStore } from '@/store/ecmStore'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ecmApi } from '@/lib/ecm-api'
import { Upload, Camera, Building2 } from 'lucide-react'
import { FileIcon } from '@/components/FileIcon'
import { FilePropertiesEditor } from '@/components/FilePropertiesEditor'
import toast from 'react-hot-toast'
import { FolderTree } from '@/components/FolderTree'
import { NewFolderModal } from '@/components/NewFolderModal'
import { RenameFolderModal } from '@/components/RenameFolderModal'
import { Breadcrumb } from '@/components/Breadcrumb'
import type { EcmDirectory } from '@/lib/ecm-api'
import { SortDropdown, SortState, sortFiles } from '@/components/SortDropdown'
import { EmptyState } from '@/components/EmptyState'
import { UploadDropzone } from '@/components/UploadDropzone'
import { ClassifyWizard } from '@/components/ClassifyWizard'
import { UploadQueueBar } from '@/components/UploadQueueBar'
import { FolderPlus } from 'lucide-react'
import { useUploadQueue } from '@/hooks/useUploadQueue'
import { useWatchFolder } from '@/hooks/useWatchFolder'
import { FilePreviewModal } from '@/components/FilePreviewModal'
import { ShareButton } from '@/components/ShareButton'
import { UserMenu } from '@/components/UserMenu'
import { SearchBar } from '@/components/SearchBar'
import { SearchResults } from '@/components/SearchResults'
import { FilterChips } from '@/components/FilterChips'
import { useFileSearch, SearchFilters } from '@/hooks/useFileSearch'

export default function HomePage() {
  const router = useRouter()
  const qc = useQueryClient()
  const { isAuthenticated, restore, username, baseUrl } = useAuthStore()
  const { currentDirectoryId, setCurrentDirectory, selectedFileId, selectFile } = useEcmStore()

  const [wizardOpen, setWizardOpen] = useState(false)
  const [pendingFiles, setPendingFiles] = useState<File[]>([])
  const [previewId, setPreviewId] = useState<number | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [filters, setFilters] = useState<SearchFilters>({})
  const [logoAspect, setLogoAspect] = useState<number | null>(null)
  const [newFolderOpen, setNewFolderOpen] = useState(false)
  const [newFolderParent, setNewFolderParent] = useState<number | null>(null)
  const [renameTarget, setRenameTarget] = useState<EcmDirectory | null>(null)
  const [sort, setSort] = useState<SortState>(() => {
    if (typeof window !== 'undefined') {
      try {
        const raw = localStorage.getItem('ecm-sort')
        if (raw) return JSON.parse(raw)
      } catch {}
    }
    return { key: 'write_date', dir: 'desc' }
  })
  const [sidebarWidth, setSidebarWidth] = useState<number>(() => {
    if (typeof window !== 'undefined') {
      const raw = localStorage.getItem('ecm-sidebar-width')
      const n = raw ? Number(raw) : NaN
      if (Number.isFinite(n) && n >= 180 && n <= 600) return n
    }
    return 260
  })
  const upload = useUploadQueue()
  useWatchFolder()
  const search = useFileSearch(searchQuery, filters)

  useEffect(() => {
    try { localStorage.setItem('ecm-sort', JSON.stringify(sort)) } catch {}
  }, [sort])

  useEffect(() => {
    try { localStorage.setItem('ecm-sidebar-width', String(sidebarWidth)) } catch {}
  }, [sidebarWidth])

  function startResizeSidebar(e: React.MouseEvent) {
    e.preventDefault()
    const startX = e.clientX
    const startW = sidebarWidth
    function onMove(ev: MouseEvent) {
      const next = Math.min(600, Math.max(180, startW + (ev.clientX - startX)))
      setSidebarWidth(next)
    }
    function onUp() {
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }

  function openNewFolder(parentId: number | null = currentDirectoryId) {
    setNewFolderParent(parentId)
    setNewFolderOpen(true)
  }

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const target = e.target as HTMLElement | null
      const inField = target && /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName)
      if (inField) return
      if (previewId !== null) return // modal aberto tem seus próprios atalhos
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'n') {
        e.preventDefault()
        openNewFolder()
        return
      }
      if (e.key === 'Enter' && selectedFileId !== null) {
        e.preventDefault()
        setPreviewId(selectedFileId)
        return
      }
      if ((e.key === 'Delete' || e.key === 'Backspace') && selectedFileId !== null) {
        e.preventDefault()
        handleDeleteSelected()
        return
      }
      if (e.key === 'F2' && currentDirectoryId !== null) {
        e.preventDefault()
        const dir = dirs.data?.find((d) => d.id === currentDirectoryId)
        if (dir) setRenameTarget(dir)
        return
      }
      if (e.shiftKey && (e.key === 'Delete' || e.key === 'Backspace') && currentDirectoryId !== null) {
        e.preventDefault()
        const dir = dirs.data?.find((d) => d.id === currentDirectoryId)
        if (dir) handleDeleteDirectory(dir)
        return
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentDirectoryId, selectedFileId, previewId])

  useEffect(() => {
    if (!isAuthenticated) {
      restore().then(() => {
        if (!useAuthStore.getState().isAuthenticated) router.replace('/login')
      })
    }
  }, [isAuthenticated, restore, router])

  const dirs = useQuery({
    queryKey: ['directories'],
    queryFn: () => ecmApi.listDirectories(),
    enabled: isAuthenticated,
  })

  const company = useQuery({
    queryKey: ['current-company'],
    queryFn: () => ecmApi.getCurrentCompany(),
    enabled: isAuthenticated,
    staleTime: 30 * 60_000,
  })

  const tags = useQuery({
    queryKey: ['tags'],
    queryFn: () => ecmApi.listTags(),
    enabled: isAuthenticated,
    staleTime: 5 * 60_000,
  })

  const files = useQuery({
    queryKey: ['files', currentDirectoryId ?? 'all'],
    queryFn: () => ecmApi.listFiles(currentDirectoryId ?? undefined, 200),
    enabled: isAuthenticated,
    // polling enquanto há OCR pendente
    refetchInterval: (q) => {
      const data = (q.state.data || []) as { ocr_state?: string }[]
      const pending = data.some((f) => f.ocr_state === 'pending' || f.ocr_state === 'processing')
      return pending ? 5000 : false
    },
  })

  // quando upload termina, refetch lista
  useEffect(() => {
    const done = upload.jobs.filter((j) => j.status === 'done').length
    if (done > 0) {
      qc.invalidateQueries({ queryKey: ['files'] })
      qc.invalidateQueries({ queryKey: ['directories'] })
    }
  }, [upload.jobs, qc])

  function handleFilesDropped(droppedFiles: File[]) {
    setPendingFiles(droppedFiles)
    setWizardOpen(true)
  }

  function confirmUpload({ directoryId, tagIds, items }: {
    directoryId: number
    tagIds: number[]
    items: { file: File; documentTypeId?: number }[]
  }) {
    upload.enqueue({ directoryId, tagIds, items })
    setWizardOpen(false)
    setPendingFiles([])
    toast.success(`${items.length} arquivo(s) enviados à fila`)
  }

  if (!isAuthenticated) {
    return <div className="grid place-items-center h-screen text-ink-muted">Restaurando sessão…</div>
  }

  const sortedFiles = useMemo(() => {
    if (!files.data) return []
    return sortFiles(files.data, sort)
  }, [files.data, sort])

  const selectedFile = sortedFiles.find((f) => f.id === selectedFileId) || null

  async function handleMoveFile(fileId: number, targetDirId: number) {
    try {
      await ecmApi.moveFile(fileId, targetDirId)
      toast.success('Arquivo movido')
      qc.invalidateQueries({ queryKey: ['files'] })
      qc.invalidateQueries({ queryKey: ['directories'] })
    } catch (e: any) {
      toast.error(e?.message || 'Falha ao mover arquivo')
    }
  }

  async function handleMoveDirectory(sourceId: number, targetDirId: number) {
    try {
      await ecmApi.moveDirectory(sourceId, targetDirId)
      toast.success('Pasta movida')
      qc.invalidateQueries({ queryKey: ['directories'] })
      qc.invalidateQueries({ queryKey: ['files'] })
    } catch (e: any) {
      toast.error(e?.message || 'Falha ao mover pasta')
    }
  }

  async function handleDeleteDirectory(dir: EcmDirectory) {
    const ok = window.confirm(
      `Excluir a pasta "${dir.name}"?\n\nA pasta deve estar vazia. Arquivos e subpastas devem ser removidos antes.`,
    )
    if (!ok) return
    try {
      await ecmApi.deleteDirectory(dir.id)
      toast.success(`Pasta "${dir.name}" excluída`)
      if (currentDirectoryId === dir.id) setCurrentDirectory(null)
      qc.invalidateQueries({ queryKey: ['directories'] })
      qc.invalidateQueries({ queryKey: ['files'] })
    } catch (e: any) {
      toast.error(e?.message || 'Falha ao excluir pasta (verifique se está vazia)')
    }
  }

  async function handleDeleteSelected() {
    if (!selectedFile) return
    const ok = window.confirm(
      `Mover "${selectedFile.name}" para a lixeira?\n\nDocumentos aprovados não podem ser excluídos.`,
    )
    if (!ok) return
    try {
      await ecmApi.deleteFile(selectedFile.id)
      toast.success('Arquivo movido para a lixeira')
      selectFile(null)
      qc.invalidateQueries({ queryKey: ['files'] })
    } catch (e: any) {
      toast.error(e?.message || 'Falha ao excluir')
    }
  }

  return (
    <div
      className="grid h-screen overflow-hidden"
      style={{ gridTemplateColumns: `${sidebarWidth}px 6px 1fr 320px` }}
    >
      <UploadDropzone onFiles={handleFilesDropped} />

      {/* Sidebar esquerda */}
      <aside className="border-r border-line bg-bg-soft p-3 overflow-y-auto min-w-0">
        <div className="relative px-2 pt-3 pb-4 mb-4 text-center">
          {company.data ? (
            <>
              <div
                className="mx-auto h-20 rounded-xl overflow-hidden border border-white/10 bg-white/5 flex items-center justify-center"
                style={{
                  width: company.data.logo && logoAspect ? `${80 * logoAspect}px` : 80,
                  maxWidth: '100%',
                  aspectRatio: company.data.logo && logoAspect ? logoAspect : 1,
                }}
              >
                {company.data.logo ? (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img
                    src={`data:image/png;base64,${company.data.logo}`}
                    alt={company.data.name}
                    className="w-full h-full object-contain"
                    onLoad={(e) => {
                      const t = e.currentTarget
                      if (t.naturalWidth && t.naturalHeight) {
                        setLogoAspect(t.naturalWidth / t.naturalHeight)
                      }
                    }}
                  />
                ) : (
                  <Building2 size={28} className="text-accent/70" />
                )}
              </div>
              <p
                className="mt-3 text-sm font-semibold tracking-tight text-ink px-2 truncate"
                title={company.data.name}
              >
                {company.data.name}
              </p>
              <p className="mt-0.5 text-[10px] uppercase tracking-[0.2em] text-ink-dim font-medium">
                Gestão de Documentos
              </p>
            </>
          ) : (
            <>
              <div className="mx-auto w-20 h-20 rounded-xl border border-white/10 bg-white/5 animate-pulse" />
              <div className="h-3 w-24 mx-auto mt-3 rounded bg-bg-muted/40 animate-pulse" />
            </>
          )}
          <div className="mt-4 mx-auto h-px w-3/4 bg-gradient-to-r from-transparent via-line to-transparent" />
        </div>
        <div className="text-xs uppercase tracking-wide text-ink-muted mb-2 px-2">Pastas</div>
        {dirs.isLoading && <p className="text-xs text-ink-dim px-2">Carregando…</p>}
        {dirs.data && (
          <FolderTree
            directories={dirs.data}
            currentId={currentDirectoryId}
            onSelect={setCurrentDirectory}
            onNewFolder={(parentId) => openNewFolder(parentId)}
            onRename={(dir) => setRenameTarget(dir)}
            onDelete={(dir) => handleDeleteDirectory(dir)}
            onDropFile={handleMoveFile}
            onDropDirectory={handleMoveDirectory}
          />
        )}
      </aside>

      {/* Splitter sidebar */}
      <div
        onMouseDown={startResizeSidebar}
        onDoubleClick={() => setSidebarWidth(260)}
        title="Arraste para redimensionar (duplo-clique reseta)"
        className="cursor-col-resize bg-transparent hover:bg-accent/30 transition-colors relative group"
      >
        <div className="absolute inset-y-0 left-1/2 -translate-x-1/2 w-px bg-line group-hover:bg-accent" />
      </div>

      {/* Centro */}
      <main className="overflow-y-auto">
        <header className="sticky top-0 z-10 backdrop-blur bg-bg/80 border-b border-line px-6 py-3 space-y-2">
          <div className="flex items-center gap-3">
            <div className="flex-1 max-w-xl">
              <SearchBar value={searchQuery} onChange={setSearchQuery} />
            </div>
            <button
              onClick={() => openNewFolder()}
              className="px-3 py-2 rounded-lg bg-bg-soft border border-line hover:border-accent text-sm flex items-center gap-1.5"
              title="Nova pasta (Ctrl+N)"
            >
              <FolderPlus size={16} /> Nova pasta
            </button>
            <button
              onClick={() => {
                const input = document.createElement('input')
                input.type = 'file'; input.multiple = true
                input.onchange = () => {
                  const fs = Array.from(input.files ?? [])
                  if (fs.length) handleFilesDropped(fs)
                }
                input.click()
              }}
              className="px-3 py-2 rounded-lg bg-accent hover:bg-accent-soft text-sm flex items-center gap-1.5"
            >
              <Upload size={16} /> Upload
            </button>
            <button className="px-3 py-2 rounded-lg bg-bg-soft border border-line hover:border-accent text-sm flex items-center gap-1.5">
              <Camera size={16} /> Capturar
            </button>
            <UserMenu />
          </div>
          {search.isActive && (
            <FilterChips filters={filters} onChange={setFilters} />
          )}
        </header>

        <section className="p-6">
          {search.isActive ? (
            <>
              <div className="flex items-baseline justify-between mb-4">
                <h2 className="text-lg font-medium">Resultados para "{search.query}"</h2>
                <span className="text-xs text-ink-dim">{search.results.length} encontrado(s)</span>
              </div>
              <SearchResults
                query={search.query}
                results={search.results}
                loading={search.isLoading || search.isFetching}
                selectedId={selectedFileId}
                onSelect={selectFile}
                onOpen={(id) => setPreviewId(id)}
              />
            </>
          ) : (
            <>
              <div className="flex items-center justify-between gap-3 mb-4 min-w-0">
                {currentDirectoryId ? (
                  <Breadcrumb
                    directories={dirs.data ?? []}
                    currentId={currentDirectoryId}
                    onSelect={setCurrentDirectory}
                  />
                ) : (
                  <h2 className="text-lg font-medium">Todos arquivos (recentes)</h2>
                )}
                <div className="flex items-center gap-3 shrink-0">
                  <span className="text-xs text-ink-dim">
                    {sortedFiles.length} arquivo(s)
                  </span>
                  <SortDropdown value={sort} onChange={setSort} />
                </div>
              </div>

              {files.isLoading && <p className="text-sm text-ink-muted">Carregando…</p>}

              {files.data && files.data.length === 0 && (
                <EmptyState
                  title={currentDirectoryId ? 'Pasta vazia' : 'Nenhum arquivo'}
                  onUpload={() => {
                    const input = document.createElement('input')
                    input.type = 'file'; input.multiple = true
                    input.onchange = () => {
                      const fs = Array.from(input.files ?? [])
                      if (fs.length) handleFilesDropped(fs)
                    }
                    input.click()
                  }}
                  onNewFolder={() => openNewFolder()}
                />
              )}

              <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                {sortedFiles.map((f) => (
                  <button
                    key={f.id}
                    onClick={() => selectFile(f.id)}
                    onDoubleClick={() => setPreviewId(f.id)}
                    draggable
                    onDragStart={(e) => {
                      e.dataTransfer.setData('application/x-ecm-file', String(f.id))
                      e.dataTransfer.effectAllowed = 'move'
                    }}
                    className={`glass p-3 rounded-xl hover:border-accent transition text-left ${
                      selectedFileId === f.id ? 'border-accent ring-1 ring-accent/40' : ''
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <FileIcon
                        fileId={f.id}
                        name={f.name}
                        mimetype={f.mimetype}
                        size={32}
                      />
                      <p className="text-sm truncate font-medium">{f.name}</p>
                    </div>
                    <div className="text-xs text-ink-dim flex flex-wrap gap-2 items-center">
                      {f.document_type_id && <span>{f.document_type_id[1]}</span>}
                      {f.ocr_state && <OcrBadge state={f.ocr_state} />}
                      {f.tag_ids && f.tag_ids.length > 0 && (
                        <span className="px-1.5 py-0.5 rounded bg-bg-muted">
                          {f.tag_ids.length} tag{f.tag_ids.length > 1 ? 's' : ''}
                        </span>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            </>
          )}
        </section>
      </main>

      {/* Direita */}
      <aside className="border-l border-line bg-bg-soft p-4 overflow-y-auto">
        {selectedFile ? (
          <>
            <div className="text-xs uppercase tracking-wide text-ink-muted mb-2">Arquivo</div>
            <h3 className="font-medium mb-3 break-words">{selectedFile.name}</h3>
            <FilePropertiesEditor file={selectedFile} directories={dirs.data ?? []} />
            {selectedFile.tag_ids && selectedFile.tag_ids.length > 0 && tags.data && (
              <div className="mt-3 flex flex-wrap gap-1">
                {selectedFile.tag_ids
                  .map((id) => tags.data!.find((t) => t.id === id))
                  .filter(Boolean)
                  .map((t) => (
                    <span
                      key={t!.id}
                      className="text-[11px] px-2 py-0.5 rounded-full bg-accent/15 text-accent border border-accent/30"
                    >
                      #{t!.name}
                    </span>
                  ))}
              </div>
            )}
            {selectedFile.can_download === false && (
              <div className="mt-3 text-xs px-2 py-1.5 rounded border border-amber-500/40 bg-amber-500/10 text-amber-300">
                Download restrito para este tipo de documento.
              </div>
            )}
            <button
              onClick={() => setPreviewId(selectedFile.id)}
              className="mt-4 w-full text-sm px-3 py-2 rounded-lg bg-accent hover:bg-accent-soft"
            >
              Abrir / Visualizar
            </button>
            {selectedFile.can_download !== false && (
              <ShareButton
                fileId={selectedFile.id}
                className="mt-2 w-full text-sm px-3 py-2 rounded-lg bg-bg-muted hover:bg-bg border border-line"
              />
            )}
          </>
        ) : (
          <div className="text-center text-ink-dim text-sm mt-12">
            <p>Selecione um arquivo</p>
            <p className="text-xs mt-1">para ver detalhes e ações</p>
          </div>
        )}
      </aside>

      <ClassifyWizard
        open={wizardOpen}
        files={pendingFiles}
        directories={dirs.data ?? []}
        defaultDirectoryId={currentDirectoryId}
        onConfirm={confirmUpload}
        onCancel={() => { setWizardOpen(false); setPendingFiles([]) }}
      />

      <UploadQueueBar
        jobs={upload.jobs}
        onClearDone={upload.clearDone}
        onRemove={upload.remove}
      />

      <NewFolderModal
        open={newFolderOpen}
        onClose={() => setNewFolderOpen(false)}
        directories={dirs.data ?? []}
        defaultParentId={newFolderParent}
        onCreated={(id) => setCurrentDirectory(id)}
      />

      <RenameFolderModal
        open={renameTarget !== null}
        onClose={() => setRenameTarget(null)}
        directoryId={renameTarget?.id ?? null}
        currentName={renameTarget?.name ?? ''}
      />

      <FilePreviewModal
        fileId={previewId}
        fileName={
          files.data?.find((f) => f.id === previewId)?.name ??
          search.results.find((f) => f.id === previewId)?.name
        }
        mimetype={
          files.data?.find((f) => f.id === previewId)?.mimetype ??
          search.results.find((f) => f.id === previewId)?.mimetype
        }
        onClose={() => setPreviewId(null)}
      />
    </div>
  )
}

function OcrBadge({ state }: { state: string }) {
  const map: Record<string, string> = {
    pending: 'bg-yellow-500/15 text-yellow-300',
    processing: 'bg-blue-500/15 text-blue-300',
    done: 'bg-emerald-500/15 text-emerald-300',
    failed: 'bg-red-500/15 text-red-300',
    skipped: 'bg-bg-muted text-ink-dim',
  }
  return <span className={`px-1.5 py-0.5 rounded ${map[state] ?? 'bg-bg-muted'}`}>OCR {state}</span>
}
