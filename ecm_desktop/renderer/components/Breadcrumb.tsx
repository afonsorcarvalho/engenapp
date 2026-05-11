'use client'

import { useMemo } from 'react'
import { Home, ChevronRight } from 'lucide-react'
import type { EcmDirectory } from '@/lib/ecm-api'

interface Props {
  directories: EcmDirectory[]
  currentId: number | null
  onSelect: (id: number | null) => void
}

function buildPath(dirs: EcmDirectory[], id: number | null): EcmDirectory[] {
  if (!id) return []
  const map = new Map<number, EcmDirectory>()
  dirs.forEach((d) => map.set(d.id, d))
  const path: EcmDirectory[] = []
  let cur: EcmDirectory | undefined = map.get(id)
  let guard = 0
  while (cur && guard++ < 40) {
    path.unshift(cur)
    const parentId = cur.parent_id ? cur.parent_id[0] : null
    cur = parentId ? map.get(parentId) : undefined
  }
  return path
}

export function Breadcrumb({ directories, currentId, onSelect }: Props) {
  const path = useMemo(() => buildPath(directories, currentId), [directories, currentId])

  return (
    <nav className="flex items-center gap-1 text-sm text-ink-muted flex-wrap min-w-0">
      <button
        onClick={() => onSelect(null)}
        className="flex items-center gap-1 px-2 py-1 rounded-md hover:bg-bg-muted hover:text-ink"
        title="Todos arquivos"
      >
        <Home size={14} />
        <span>Todos</span>
      </button>
      {path.map((d, i) => (
        <span key={d.id} className="flex items-center gap-1 min-w-0">
          <ChevronRight size={14} className="text-ink-dim shrink-0" />
          <button
            onClick={() => onSelect(d.id)}
            className={`px-2 py-1 rounded-md truncate max-w-[200px] ${
              i === path.length - 1
                ? 'text-ink font-medium'
                : 'hover:bg-bg-muted hover:text-ink'
            }`}
            title={d.name}
          >
            {d.name}
          </button>
        </span>
      ))}
    </nav>
  )
}
