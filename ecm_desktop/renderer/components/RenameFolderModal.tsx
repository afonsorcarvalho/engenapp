'use client'

import { useEffect, useRef, useState } from 'react'
import { Pencil, X, Loader2 } from 'lucide-react'
import { ecmApi } from '@/lib/ecm-api'
import { useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'

interface Props {
  open: boolean
  onClose: () => void
  directoryId: number | null
  currentName: string
}

export function RenameFolderModal({ open, onClose, directoryId, currentName }: Props) {
  const [name, setName] = useState(currentName)
  const [busy, setBusy] = useState(false)
  const qc = useQueryClient()
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (open) {
      setName(currentName)
      setTimeout(() => {
        inputRef.current?.focus()
        inputRef.current?.select()
      }, 30)
    }
  }, [open, currentName])

  if (!open || directoryId == null) return null

  async function submit() {
    const trimmed = name.trim()
    if (!trimmed || busy) return
    if (trimmed === currentName) {
      onClose()
      return
    }
    setBusy(true)
    try {
      await ecmApi.renameDirectory(directoryId!, trimmed)
      toast.success(`Renomeado para "${trimmed}"`)
      qc.invalidateQueries({ queryKey: ['directories'] })
      qc.invalidateQueries({ queryKey: ['files'] })
      onClose()
    } catch (e: any) {
      toast.error(e?.message || 'Falha ao renomear')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-[60] grid place-items-center bg-black/60 backdrop-blur-sm p-4"
      onClick={onClose}
      onKeyDown={(e) => { if (e.key === 'Escape') onClose() }}
    >
      <div
        className="glass w-full max-w-md rounded-2xl p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between mb-4">
          <h3 className="font-medium flex items-center gap-2">
            <Pencil size={18} /> Renomear pasta
          </h3>
          <button onClick={onClose} className="p-1.5 rounded hover:bg-bg-muted">
            <X size={16} />
          </button>
        </header>

        <label className="block mb-5">
          <span className="block text-xs uppercase tracking-wide text-ink-muted mb-1">
            Novo nome
          </span>
          <input
            ref={inputRef}
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') submit() }}
            className="w-full bg-bg-soft border border-line rounded-lg px-3 py-2 text-sm outline-none focus:border-accent"
          />
        </label>

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
            Renomear
          </button>
        </footer>
      </div>
    </div>
  )
}
