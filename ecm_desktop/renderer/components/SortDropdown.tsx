'use client'

import { useEffect, useRef, useState } from 'react'
import { ArrowDownAZ, ArrowUpAZ, Calendar, HardDrive, ChevronDown, Check } from 'lucide-react'
import clsx from 'clsx'

export type SortKey = 'write_date' | 'create_date' | 'name' | 'size'
export type SortDir = 'asc' | 'desc'

export interface SortState {
  key: SortKey
  dir: SortDir
}

interface Props {
  value: SortState
  onChange: (next: SortState) => void
}

const OPTIONS: { key: SortKey; label: string; defaultDir: SortDir }[] = [
  { key: 'write_date', label: 'Última modificação', defaultDir: 'desc' },
  { key: 'create_date', label: 'Data de criação', defaultDir: 'desc' },
  { key: 'name', label: 'Nome', defaultDir: 'asc' },
  { key: 'size', label: 'Tamanho', defaultDir: 'desc' },
]

function iconFor(key: SortKey, dir: SortDir) {
  if (key === 'name') return dir === 'asc' ? ArrowDownAZ : ArrowUpAZ
  if (key === 'size') return HardDrive
  return Calendar
}

export function SortDropdown({ value, onChange }: Props) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!ref.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDocClick)
    return () => document.removeEventListener('mousedown', onDocClick)
  }, [])

  const Icon = iconFor(value.key, value.dir)
  const currentLabel = OPTIONS.find((o) => o.key === value.key)?.label ?? 'Ordenar'

  function selectKey(opt: typeof OPTIONS[number]) {
    if (opt.key === value.key) {
      onChange({ key: value.key, dir: value.dir === 'asc' ? 'desc' : 'asc' })
    } else {
      onChange({ key: opt.key, dir: opt.defaultDir })
    }
  }

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-bg-soft border border-line hover:border-accent text-xs"
        title="Ordenar"
      >
        <Icon size={13} />
        <span className="text-ink-muted">{currentLabel}</span>
        <span className="text-ink-dim text-[10px]">{value.dir === 'asc' ? '↑' : '↓'}</span>
        <ChevronDown size={12} className={clsx('transition-transform', open && 'rotate-180')} />
      </button>
      {open && (
        <div className="absolute right-0 mt-1 w-52 rounded-lg border border-line bg-bg-soft shadow-lg z-30 py-1">
          {OPTIONS.map((opt) => {
            const active = opt.key === value.key
            return (
              <button
                key={opt.key}
                onClick={() => { selectKey(opt); /* mantém aberto pra toggle dir */ }}
                className={clsx(
                  'w-full text-left px-3 py-1.5 text-xs flex items-center gap-2 hover:bg-bg-muted',
                  active && 'text-accent',
                )}
              >
                {active ? <Check size={12} /> : <span className="w-3" />}
                <span className="flex-1">{opt.label}</span>
                {active && (
                  <span className="text-[10px] text-ink-dim">
                    {value.dir === 'asc' ? '↑ asc' : '↓ desc'}
                  </span>
                )}
              </button>
            )
          })}
          <div className="my-1 border-t border-line" />
          <button
            onClick={() => onChange({ ...value, dir: value.dir === 'asc' ? 'desc' : 'asc' })}
            className="w-full text-left px-3 py-1.5 text-xs flex items-center gap-2 hover:bg-bg-muted text-ink-muted"
          >
            <span className="w-3" />
            Inverter direção
          </button>
        </div>
      )}
    </div>
  )
}

export function sortFiles<T extends {
  name?: string
  write_date?: string
  create_date?: string
  size?: number
}>(files: T[], { key, dir }: SortState): T[] {
  const factor = dir === 'asc' ? 1 : -1
  const copy = [...files]
  copy.sort((a, b) => {
    let cmp = 0
    if (key === 'name') {
      cmp = (a.name || '').localeCompare(b.name || '')
    } else if (key === 'size') {
      cmp = (a.size ?? 0) - (b.size ?? 0)
    } else {
      const av = (a[key as 'write_date' | 'create_date'] as string) || ''
      const bv = (b[key as 'write_date' | 'create_date'] as string) || ''
      cmp = av.localeCompare(bv)
    }
    return cmp * factor
  })
  return copy
}
