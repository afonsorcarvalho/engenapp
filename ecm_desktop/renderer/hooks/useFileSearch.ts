'use client'

import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ecmApi, EcmFileSummary } from '@/lib/ecm-api'

export interface SearchFilters {
  documentTypeIds?: number[]
  ocrState?: 'done' | 'pending' | 'failed' | null
  expirationStatus?: 'expired' | 'critical' | 'warning' | null
}

const MIN_CHARS = 2
const DEBOUNCE_MS = 300

export function useFileSearch(query: string, filters: SearchFilters = {}) {
  const [debounced, setDebounced] = useState(query)

  useEffect(() => {
    const t = setTimeout(() => setDebounced(query.trim()), DEBOUNCE_MS)
    return () => clearTimeout(t)
  }, [query])

  const enabled = debounced.length >= MIN_CHARS

  const q = useQuery({
    queryKey: ['search-files', debounced, filters],
    queryFn: async () => {
      const all = await ecmApi.searchFiles(debounced, { withOcrText: true, limit: 100 })
      return applyFilters(all, filters)
    },
    enabled,
    staleTime: 10_000,
  })

  return {
    query: debounced,
    isActive: enabled,
    isLoading: q.isLoading,
    isFetching: q.isFetching,
    results: (q.data ?? []) as (EcmFileSummary & { ocr_text?: string })[],
    error: q.error,
  }
}

function applyFilters(rows: (EcmFileSummary & { ocr_text?: string })[], f: SearchFilters) {
  return rows.filter((r) => {
    if (f.documentTypeIds && f.documentTypeIds.length) {
      const id = r.document_type_id ? r.document_type_id[0] : null
      if (id == null || !f.documentTypeIds.includes(id)) return false
    }
    if (f.ocrState && r.ocr_state !== f.ocrState) return false
    if (f.expirationStatus && r.expiration_status !== f.expirationStatus) return false
    return true
  })
}

/** Extrai snippet com contexto em torno da palavra encontrada. */
export function buildSnippet(text: string | undefined, query: string, ctx = 80): string | null {
  if (!text || !query) return null
  const q = query.trim().toLowerCase()
  if (!q) return null
  const idx = text.toLowerCase().indexOf(q)
  if (idx < 0) return null
  const start = Math.max(0, idx - ctx)
  const end = Math.min(text.length, idx + q.length + ctx)
  const prefix = start > 0 ? '… ' : ''
  const suffix = end < text.length ? ' …' : ''
  return prefix + text.slice(start, end).replace(/\s+/g, ' ') + suffix
}
