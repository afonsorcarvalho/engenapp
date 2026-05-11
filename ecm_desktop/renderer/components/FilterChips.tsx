'use client'

import { useQuery } from '@tanstack/react-query'
import { ecmApi } from '@/lib/ecm-api'
import type { SearchFilters } from '@/hooks/useFileSearch'
import { Check, X } from 'lucide-react'
import clsx from 'clsx'

interface Props {
  filters: SearchFilters
  onChange: (next: SearchFilters) => void
}

export function FilterChips({ filters, onChange }: Props) {
  const types = useQuery({
    queryKey: ['document-types'],
    queryFn: () => ecmApi.listDocumentTypes(),
    staleTime: 5 * 60_000,
  })
  const tags = useQuery({
    queryKey: ['tags'],
    queryFn: () => ecmApi.listTags(),
    staleTime: 5 * 60_000,
  })

  function toggleType(id: number) {
    const current = filters.documentTypeIds || []
    const next = current.includes(id) ? current.filter((x) => x !== id) : [...current, id]
    onChange({ ...filters, documentTypeIds: next.length ? next : undefined })
  }
  function toggleTag(id: number) {
    const current = filters.tagIds || []
    const next = current.includes(id) ? current.filter((x) => x !== id) : [...current, id]
    onChange({ ...filters, tagIds: next.length ? next : undefined })
  }
  function setOcr(state: SearchFilters['ocrState']) {
    onChange({ ...filters, ocrState: filters.ocrState === state ? null : state })
  }
  function setExp(state: SearchFilters['expirationStatus']) {
    onChange({ ...filters, expirationStatus: filters.expirationStatus === state ? null : state })
  }

  const hasFilters =
    (filters.documentTypeIds?.length ?? 0) > 0 ||
    (filters.tagIds?.length ?? 0) > 0 ||
    !!filters.ocrState ||
    !!filters.expirationStatus

  return (
    <div className="flex items-center gap-2 flex-wrap">
      {types.data?.map((t) => (
        <Chip
          key={t.id}
          active={filters.documentTypeIds?.includes(t.id)}
          onClick={() => toggleType(t.id)}
        >
          {t.name}
        </Chip>
      ))}
      {tags.data && tags.data.length > 0 && <Sep />}
      {tags.data?.map((t) => (
        <Chip
          key={`tag-${t.id}`}
          active={filters.tagIds?.includes(t.id)}
          onClick={() => toggleTag(t.id)}
        >
          #{t.name}
        </Chip>
      ))}
      <Sep />
      <Chip active={filters.ocrState === 'done'} onClick={() => setOcr('done')}>OCR concluído</Chip>
      <Chip active={filters.ocrState === 'failed'} onClick={() => setOcr('failed')}>OCR falhou</Chip>
      <Sep />
      <Chip active={filters.expirationStatus === 'expired'} onClick={() => setExp('expired')}>Vencidos</Chip>
      <Chip active={filters.expirationStatus === 'critical'} onClick={() => setExp('critical')}>≤7 dias</Chip>
      {hasFilters && (
        <button
          onClick={() => onChange({})}
          className="ml-2 text-xs text-ink-muted hover:text-ink flex items-center gap-1"
        >
          <X size={12} /> Limpar
        </button>
      )}
    </div>
  )
}

function Chip({ active, onClick, children }: { active?: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'px-2.5 py-1 rounded-full border text-xs transition flex items-center gap-1',
        active
          ? 'bg-accent/15 border-accent text-accent'
          : 'bg-bg-soft border-line hover:border-accent text-ink-muted',
      )}
    >
      {active && <Check size={11} />}
      {children}
    </button>
  )
}

function Sep() { return <span className="text-ink-dim mx-1">·</span> }
