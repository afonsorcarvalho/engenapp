'use client'

import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ecmApi, EcmDirectory } from '@/lib/ecm-api'
import { X, Tag as TagIcon } from 'lucide-react'
import { FileIcon } from '@/components/FileIcon'

interface PendingFile {
  id: string
  file: File
  documentTypeId?: number
}

interface Props {
  open: boolean
  files: File[]
  directories: EcmDirectory[]
  defaultDirectoryId: number | null
  onConfirm: (args: {
    directoryId: number
    tagIds: number[]
    items: { file: File; documentTypeId?: number }[]
  }) => void
  onCancel: () => void
}

export function ClassifyWizard({ open, files, directories, defaultDirectoryId, onConfirm, onCancel }: Props) {
  const [directoryId, setDirectoryId] = useState<number | null>(defaultDirectoryId)
  const [items, setItems] = useState<PendingFile[]>([])
  const [tagIds, setTagIds] = useState<number[]>([])

  useEffect(() => {
    setDirectoryId(defaultDirectoryId)
  }, [defaultDirectoryId])

  useEffect(() => {
    if (!open) return
    setItems(files.map((f, i) => ({ id: `${Date.now()}_${i}`, file: f })))
    setTagIds([])
  }, [open, files])

  const types = useQuery({
    queryKey: ['document-types'],
    queryFn: () => ecmApi.listDocumentTypes(),
    enabled: open,
  })

  const tags = useQuery({
    queryKey: ['tags'],
    queryFn: () => ecmApi.listTags(),
    enabled: open,
  })

  function toggleTag(id: number) {
    setTagIds((prev) => prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id])
  }

  if (!open) return null

  function setType(id: string, typeId?: number) {
    setItems((prev) => prev.map((it) => (it.id === id ? { ...it, documentTypeId: typeId } : it)))
  }

  function applyToAll(typeId?: number) {
    setItems((prev) => prev.map((it) => ({ ...it, documentTypeId: typeId })))
  }

  function confirm() {
    if (!directoryId) return
    onConfirm({
      directoryId,
      tagIds,
      items: items.map((it) => ({ file: it.file, documentTypeId: it.documentTypeId })),
    })
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/60 backdrop-blur-sm p-6">
      <div className="glass rounded-2xl w-full max-w-3xl max-h-[85vh] flex flex-col">
        <header className="p-5 border-b border-line flex items-center justify-between">
          <div>
            <h2 className="font-medium">Classificar {items.length} arquivo(s)</h2>
            <p className="text-xs text-ink-muted">Escolha pasta e tipo de documento</p>
          </div>
          <button onClick={onCancel} className="p-1.5 rounded hover:bg-bg-muted"><X size={18} /></button>
        </header>

        <div className="p-5 border-b border-line grid grid-cols-2 gap-4">
          <Select
            label="Pasta destino"
            value={directoryId ?? ''}
            onChange={(v) => setDirectoryId(v ? Number(v) : null)}
          >
            <option value="">Selecione…</option>
            {directories.map((d) => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </Select>
          <Select
            label="Aplicar tipo a todos (opcional)"
            value=""
            onChange={(v) => applyToAll(v ? Number(v) : undefined)}
          >
            <option value="">— Nenhum / personalizado por arquivo —</option>
            {types.data?.map((t) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </Select>
        </div>

        <div className="p-5 border-b border-line">
          <div className="text-xs uppercase tracking-wide text-ink-muted mb-2 flex items-center gap-1.5">
            <TagIcon size={12} /> Tags (aplicadas a todos)
          </div>
          {tags.isLoading && <p className="text-xs text-ink-dim">Carregando tags…</p>}
          {tags.data && tags.data.length === 0 && (
            <p className="text-xs text-ink-dim">Nenhuma tag cadastrada.</p>
          )}
          <div className="flex flex-wrap gap-1.5">
            {tags.data?.map((t) => {
              const active = tagIds.includes(t.id)
              return (
                <button
                  key={t.id}
                  onClick={() => toggleTag(t.id)}
                  className={`text-xs px-2 py-1 rounded-full border transition ${
                    active
                      ? 'bg-accent text-white border-accent'
                      : 'bg-bg-soft border-line hover:border-accent text-ink-muted'
                  }`}
                >
                  {t.name}
                </button>
              )
            })}
          </div>
        </div>

        <div className="p-5 overflow-y-auto flex-1 space-y-2">
          {items.map((it) => (
            <div key={it.id} className="flex items-center gap-3 p-3 rounded-lg bg-bg-soft border border-line">
              <FileIcon
                name={it.file.name}
                mimetype={it.file.type}
                size={20}
                thumbnail={false}
              />
              <div className="min-w-0 flex-1">
                <p className="text-sm truncate">{it.file.name}</p>
                <p className="text-xs text-ink-dim">{formatBytes(it.file.size)}</p>
              </div>
              <select
                value={it.documentTypeId ?? ''}
                onChange={(e) => setType(it.id, e.target.value ? Number(e.target.value) : undefined)}
                className="bg-bg border border-line rounded px-2 py-1.5 text-sm outline-none"
              >
                <option value="">— Tipo —</option>
                {types.data?.map((t) => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
            </div>
          ))}
        </div>

        <footer className="p-5 border-t border-line flex justify-end gap-2">
          <button onClick={onCancel} className="px-4 py-2 rounded-lg bg-bg-muted hover:bg-bg text-sm">Cancelar</button>
          <button
            onClick={confirm}
            disabled={!directoryId}
            className="px-4 py-2 rounded-lg bg-accent hover:bg-accent-soft disabled:opacity-40 text-sm font-medium"
          >
            Enviar
          </button>
        </footer>
      </div>
    </div>
  )
}

function Select({ label, value, onChange, children }: {
  label: string; value: string | number; onChange: (v: string) => void; children: React.ReactNode
}) {
  return (
    <label className="block">
      <span className="block text-xs uppercase tracking-wide text-ink-muted mb-1">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full bg-bg-soft border border-line rounded-lg px-3 py-2 text-sm outline-none focus:border-accent"
      >
        {children}
      </select>
    </label>
  )
}

function formatBytes(b: number): string {
  if (b < 1024) return `${b} B`
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`
  return `${(b / 1024 / 1024).toFixed(1)} MB`
}
