'use client'

import { useEffect, useRef, useState } from 'react'
import { FolderPlus, X, Loader2 } from 'lucide-react'
import { ecmApi, EcmDirectory } from '@/lib/ecm-api'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'

interface Props {
  open: boolean
  onClose: () => void
  directories: EcmDirectory[]
  defaultParentId?: number | null
  onCreated?: (id: number) => void
}

export function NewFolderModal({
  open, onClose, directories, defaultParentId, onCreated,
}: Props) {
  const [name, setName] = useState('')
  const [parentId, setParentId] = useState<number | null>(defaultParentId ?? null)
  const [storageId, setStorageId] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  const qc = useQueryClient()
  const inputRef = useRef<HTMLInputElement>(null)

  const isRoot = parentId == null

  const storages = useQuery({
    queryKey: ['storages'],
    queryFn: () => ecmApi.listStorages(),
    enabled: open && isRoot,
    staleTime: 5 * 60_000,
  })

  const accessGroups = useQuery({
    queryKey: ['access-groups'],
    queryFn: () => ecmApi.listAccessGroups(),
    enabled: open && isRoot,
    staleTime: 5 * 60_000,
  })

  useEffect(() => {
    if (open) {
      setName('')
      setParentId(defaultParentId ?? null)
      setStorageId(null)
      setTimeout(() => inputRef.current?.focus(), 30)
    }
  }, [open, defaultParentId])

  // auto-seleciona primeiro storage quando carrega
  useEffect(() => {
    if (isRoot && !storageId && storages.data && storages.data.length > 0) {
      setStorageId(storages.data[0].id)
    }
  }, [isRoot, storageId, storages.data])

  if (!open) return null

  async function submit() {
    const trimmed = name.trim()
    if (!trimmed || busy) return
    if (isRoot && !storageId) {
      toast.error('Selecione um armazenamento (Storage) para a pasta raiz.')
      return
    }
    setBusy(true)
    try {
      const id = await ecmApi.createDirectory({
        name: trimmed,
        parentId: parentId ?? undefined,
        storageId: isRoot ? storageId ?? undefined : undefined,
        groupIds: isRoot
          ? (accessGroups.data?.map((g) => g.id) ?? undefined)
          : undefined,
      })
      toast.success(`Pasta "${trimmed}" criada`)
      qc.invalidateQueries({ queryKey: ['directories'] })
      onCreated?.(id)
      onClose()
    } catch (e: any) {
      toast.error(e?.message || 'Falha ao criar pasta')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-[60] grid place-items-center bg-black/60 backdrop-blur-sm p-4"
      onClick={onClose}
      onKeyDown={(e) => {
        if (e.key === 'Escape') onClose()
      }}
    >
      <div
        className="glass w-full max-w-md rounded-2xl p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between mb-4">
          <h3 className="font-medium flex items-center gap-2">
            <FolderPlus size={18} /> Nova pasta
          </h3>
          <button onClick={onClose} className="p-1.5 rounded hover:bg-bg-muted">
            <X size={16} />
          </button>
        </header>

        <label className="block mb-3">
          <span className="block text-xs uppercase tracking-wide text-ink-muted mb-1">
            Nome
          </span>
          <input
            ref={inputRef}
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') submit()
            }}
            placeholder="Ex.: Contratos 2026"
            className="w-full bg-bg-soft border border-line rounded-lg px-3 py-2 text-sm outline-none focus:border-accent"
          />
        </label>

        <label className="block mb-3">
          <span className="block text-xs uppercase tracking-wide text-ink-muted mb-1">
            Pasta pai (opcional)
          </span>
          <select
            value={parentId ?? ''}
            onChange={(e) => setParentId(e.target.value ? Number(e.target.value) : null)}
            className="w-full bg-bg-soft border border-line rounded-lg px-3 py-2 text-sm outline-none focus:border-accent"
          >
            <option value="">— Pasta raiz —</option>
            {directories.map((d) => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>
        </label>

        {isRoot && (
          <label className="block mb-5">
            <span className="block text-xs uppercase tracking-wide text-ink-muted mb-1">
              Armazenamento (Storage) <span className="text-red-400">*</span>
            </span>
            <select
              value={storageId ?? ''}
              onChange={(e) => setStorageId(e.target.value ? Number(e.target.value) : null)}
              className="w-full bg-bg-soft border border-line rounded-lg px-3 py-2 text-sm outline-none focus:border-accent"
              disabled={storages.isLoading}
            >
              {storages.isLoading && <option value="">Carregando…</option>}
              {!storages.isLoading && (!storages.data || storages.data.length === 0) && (
                <option value="">Nenhum storage disponível</option>
              )}
              {storages.data?.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.save_type})
                </option>
              ))}
            </select>
            <span className="text-[10px] text-ink-dim mt-1 block">
              Obrigatório para pastas raiz. Subpastas herdam do pai.
            </span>
          </label>
        )}
        {!isRoot && <div className="mb-5" />}

        <footer className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-bg-muted hover:bg-bg text-sm"
          >
            Cancelar
          </button>
          <button
            onClick={submit}
            disabled={!name.trim() || busy}
            className="px-4 py-2 rounded-lg bg-accent hover:bg-accent-soft disabled:opacity-40 text-sm font-medium flex items-center gap-1.5"
          >
            {busy && <Loader2 size={14} className="animate-spin" />}
            Criar
          </button>
        </footer>
      </div>
    </div>
  )
}
