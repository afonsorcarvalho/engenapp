'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/authStore'
import { useEcmStore } from '@/store/ecmStore'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ecmApi } from '@/lib/ecm-api'
import { FileText, Search, Upload, Camera, Settings } from 'lucide-react'
import toast from 'react-hot-toast'
import { FolderTree } from '@/components/FolderTree'
import { UploadDropzone } from '@/components/UploadDropzone'
import { ClassifyWizard } from '@/components/ClassifyWizard'
import { UploadQueueBar } from '@/components/UploadQueueBar'
import { useUploadQueue } from '@/hooks/useUploadQueue'
import { FilePreviewModal } from '@/components/FilePreviewModal'

export default function HomePage() {
  const router = useRouter()
  const qc = useQueryClient()
  const { isAuthenticated, restore, username, baseUrl } = useAuthStore()
  const { currentDirectoryId, setCurrentDirectory, selectedFileId, selectFile } = useEcmStore()

  const [wizardOpen, setWizardOpen] = useState(false)
  const [pendingFiles, setPendingFiles] = useState<File[]>([])
  const [previewId, setPreviewId] = useState<number | null>(null)
  const upload = useUploadQueue()

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

  function confirmUpload({ directoryId, items }: { directoryId: number; items: { file: File; documentTypeId?: number }[] }) {
    upload.enqueue({ directoryId, items })
    setWizardOpen(false)
    setPendingFiles([])
    toast.success(`${items.length} arquivo(s) enviados à fila`)
  }

  if (!isAuthenticated) {
    return <div className="grid place-items-center h-screen text-ink-muted">Restaurando sessão…</div>
  }

  const selectedFile = files.data?.find((f) => f.id === selectedFileId) || null

  return (
    <div className="grid grid-cols-[260px_1fr_320px] h-screen overflow-hidden">
      <UploadDropzone onFiles={handleFilesDropped} />

      {/* Sidebar esquerda */}
      <aside className="border-r border-line bg-bg-soft p-3 overflow-y-auto">
        <div className="text-xs uppercase tracking-wide text-ink-muted mb-2 px-2">Pastas</div>
        {dirs.isLoading && <p className="text-xs text-ink-dim px-2">Carregando…</p>}
        {dirs.data && (
          <FolderTree
            directories={dirs.data}
            currentId={currentDirectoryId}
            onSelect={setCurrentDirectory}
          />
        )}
      </aside>

      {/* Centro */}
      <main className="overflow-y-auto">
        <header className="sticky top-0 z-10 backdrop-blur bg-bg/80 border-b border-line px-6 py-3 flex items-center gap-3">
          <div className="flex-1 max-w-xl">
            <div className="flex items-center gap-2 px-3 py-2 bg-bg-soft border border-line rounded-lg">
              <Search size={16} className="text-ink-dim" />
              <input
                placeholder="Buscar nome ou texto OCR…"
                className="bg-transparent outline-none text-sm flex-1"
              />
              <span className="text-[10px] text-ink-dim border border-line rounded px-1.5 py-0.5">Ctrl K</span>
            </div>
          </div>
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
        </header>

        <section className="p-6">
          <div className="flex items-baseline justify-between mb-4">
            <h2 className="text-lg font-medium">
              {currentDirectoryId
                ? dirs.data?.find((d) => d.id === currentDirectoryId)?.name ?? 'Pasta'
                : 'Todos arquivos (recentes)'}
            </h2>
            <span className="text-xs text-ink-dim">{files.data?.length ?? 0} arquivo(s)</span>
          </div>

          {files.isLoading && <p className="text-sm text-ink-muted">Carregando…</p>}

          {files.data && files.data.length === 0 && (
            <div className="glass rounded-xl p-10 text-center text-ink-muted">
              <p className="mb-2">Pasta vazia.</p>
              <p className="text-xs">Arraste arquivos para qualquer lugar da janela para enviar.</p>
            </div>
          )}

          <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
            {files.data?.map((f) => (
              <button
                key={f.id}
                onClick={() => selectFile(f.id)}
                onDoubleClick={() => setPreviewId(f.id)}
                className={`glass p-3 rounded-xl hover:border-accent transition text-left ${
                  selectedFileId === f.id ? 'border-accent ring-1 ring-accent/40' : ''
                }`}
              >
                <div className="flex items-center gap-2 mb-2">
                  <FileText size={18} className="text-accent shrink-0" />
                  <p className="text-sm truncate font-medium">{f.name}</p>
                </div>
                <div className="text-xs text-ink-dim flex flex-wrap gap-2">
                  {f.document_type_id && <span>{f.document_type_id[1]}</span>}
                  {f.ocr_state && <OcrBadge state={f.ocr_state} />}
                </div>
              </button>
            ))}
          </div>
        </section>
      </main>

      {/* Direita */}
      <aside className="border-l border-line bg-bg-soft p-4 overflow-y-auto">
        {selectedFile ? (
          <>
            <div className="text-xs uppercase tracking-wide text-ink-muted mb-2">Arquivo</div>
            <h3 className="font-medium mb-3 break-words">{selectedFile.name}</h3>
            <div className="text-sm space-y-1">
              <Row label="Tipo" value={selectedFile.document_type_id ? selectedFile.document_type_id[1] : '—'} />
              <Row label="Pasta" value={selectedFile.directory_id ? selectedFile.directory_id[1] : '—'} />
              <Row label="Confid." value={selectedFile.confidentiality ?? '—'} />
              <Row label="OCR" value={selectedFile.ocr_state ?? '—'} />
              <Row label="Vencimento" value={selectedFile.expiration_date || '—'} />
            </div>
            <button
              onClick={() => setPreviewId(selectedFile.id)}
              className="mt-4 w-full text-sm px-3 py-2 rounded-lg bg-accent hover:bg-accent-soft"
            >
              Abrir / Visualizar
            </button>
          </>
        ) : (
          <>
            <div className="text-xs uppercase tracking-wide text-ink-muted mb-2">Sessão</div>
            <div className="text-sm space-y-1">
              <p><span className="text-ink-muted">Usuário:</span> {username}</p>
              <p className="break-all"><span className="text-ink-muted">Servidor:</span> {baseUrl}</p>
            </div>
            <hr className="border-line my-4" />
            <button
              onClick={() => router.push('/settings')}
              className="w-full text-sm px-3 py-2 rounded-lg bg-bg-muted hover:bg-bg flex items-center gap-2"
            >
              <Settings size={14} /> Configurações
            </button>
          </>
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

      <FilePreviewModal
        fileId={previewId}
        fileName={files.data?.find((f) => f.id === previewId)?.name}
        mimetype={files.data?.find((f) => f.id === previewId)?.mimetype}
        onClose={() => setPreviewId(null)}
      />
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2">
      <span className="text-ink-muted w-20 shrink-0">{label}</span>
      <span className="break-all">{value}</span>
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
