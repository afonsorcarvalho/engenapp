'use client'

import { FolderOpen, Upload, FolderPlus } from 'lucide-react'

interface Props {
  title?: string
  message?: string
  onUpload?: () => void
  onNewFolder?: () => void
}

export function EmptyState({
  title = 'Pasta vazia',
  message = 'Arraste arquivos para qualquer lugar da janela para enviar — ou use os botões abaixo.',
  onUpload,
  onNewFolder,
}: Props) {
  return (
    <div className="glass rounded-2xl px-8 py-14 text-center max-w-md mx-auto">
      <div className="w-20 h-20 mx-auto mb-4 grid place-items-center rounded-2xl bg-accent/10 border border-accent/20">
        <FolderOpen size={36} className="text-accent" />
      </div>
      <h3 className="text-lg font-medium mb-1">{title}</h3>
      <p className="text-sm text-ink-muted mb-6">{message}</p>
      <div className="flex justify-center gap-2 flex-wrap">
        {onUpload && (
          <button
            onClick={onUpload}
            className="px-4 py-2 rounded-lg bg-accent hover:bg-accent-soft text-sm flex items-center gap-1.5"
          >
            <Upload size={15} /> Upload
          </button>
        )}
        {onNewFolder && (
          <button
            onClick={onNewFolder}
            className="px-4 py-2 rounded-lg bg-bg-soft border border-line hover:border-accent text-sm flex items-center gap-1.5"
          >
            <FolderPlus size={15} /> Nova pasta
          </button>
        )}
      </div>
    </div>
  )
}
