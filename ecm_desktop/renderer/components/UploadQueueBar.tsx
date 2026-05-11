'use client'

import type { UploadJob } from '@/hooks/useUploadQueue'
import { CheckCircle2, AlertCircle, Loader2, X } from 'lucide-react'
import clsx from 'clsx'

interface Props {
  jobs: UploadJob[]
  onClearDone: () => void
  onRemove: (id: string) => void
}

export function UploadQueueBar({ jobs, onClearDone, onRemove }: Props) {
  if (jobs.length === 0) return null
  const active = jobs.filter((j) => j.status === 'queued' || j.status === 'uploading').length
  const done = jobs.filter((j) => j.status === 'done').length
  const failed = jobs.filter((j) => j.status === 'failed').length

  return (
    <div className="fixed bottom-4 right-4 z-40 w-80 glass rounded-xl overflow-hidden shadow-xl">
      <header className="px-4 py-2.5 border-b border-line flex items-center gap-2 text-sm">
        <span className="font-medium">Uploads</span>
        <span className="text-ink-dim">
          {active > 0 && `${active} ativo${active > 1 ? 's' : ''}`}
          {active > 0 && (done > 0 || failed > 0) && ' · '}
          {done > 0 && `${done} ok`}
          {done > 0 && failed > 0 && ' · '}
          {failed > 0 && <span className="text-red-300">{failed} falha</span>}
        </span>
        {done > 0 && active === 0 && (
          <button onClick={onClearDone} className="ml-auto text-xs text-ink-muted hover:text-ink">Limpar</button>
        )}
      </header>
      <ul className="max-h-64 overflow-y-auto">
        {jobs.map((j) => (
          <li key={j.id} className="px-4 py-2 border-b border-line last:border-none flex items-center gap-2 text-sm">
            <StatusIcon status={j.status} />
            <div className="flex-1 min-w-0">
              <p className="truncate" title={j.name}>{j.name}</p>
              {j.status === 'uploading' && (
                <div className="h-1 mt-1 bg-bg-muted rounded overflow-hidden">
                  <div className="h-full bg-accent transition-all" style={{ width: `${j.progress}%` }} />
                </div>
              )}
              {j.status === 'failed' && <p className="text-xs text-red-300 truncate">{j.error}</p>}
            </div>
            {(j.status === 'done' || j.status === 'failed') && (
              <button onClick={() => onRemove(j.id)} className="text-ink-dim hover:text-ink p-0.5"><X size={14} /></button>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}

function StatusIcon({ status }: { status: UploadJob['status'] }) {
  if (status === 'done') return <CheckCircle2 size={16} className="text-emerald-400" />
  if (status === 'failed') return <AlertCircle size={16} className="text-red-400" />
  return <Loader2 size={16} className={clsx('text-accent', status === 'uploading' && 'animate-spin')} />
}
