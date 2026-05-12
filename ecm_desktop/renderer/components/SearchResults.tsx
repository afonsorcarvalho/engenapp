'use client'

import { Loader2 } from 'lucide-react'
import { FileIcon } from '@/components/FileIcon'
import { buildSnippet } from '@/hooks/useFileSearch'
import type { EcmFileSummary } from '@/lib/ecm-api'

interface Props {
  query: string
  results: (EcmFileSummary & { ocr_text?: string })[]
  loading: boolean
  selectedId: number | null
  onSelect: (id: number) => void
  onOpen: (id: number) => void
}

export function SearchResults({ query, results, loading, selectedId, onSelect, onOpen }: Props) {
  if (loading && results.length === 0) {
    return (
      <div className="flex items-center gap-2 text-ink-muted text-sm">
        <Loader2 size={16} className="animate-spin" /> Buscando…
      </div>
    )
  }
  if (results.length === 0) {
    return <div className="glass rounded-xl p-8 text-center text-ink-muted">Nenhum resultado para "{query}".</div>
  }
  return (
    <ul className="space-y-2">
      {results.map((f) => {
        const snippet = buildSnippet(f.ocr_text, query)
        const isSelected = selectedId === f.id
        return (
          <li key={f.id}>
            <button
              onClick={() => onSelect(f.id)}
              onDoubleClick={() => onOpen(f.id)}
              className={`w-full glass p-4 rounded-xl text-left hover:border-accent transition ${
                isSelected ? 'border-accent ring-1 ring-accent/40' : ''
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <FileIcon
                  fileId={f.id}
                  name={f.name}
                  mimetype={f.mimetype}
                  size={24}
                />
                <p className="text-sm font-medium truncate"><Highlighted text={f.name} query={query} /></p>
                {f.ocr_state && <OcrPill state={f.ocr_state} />}
              </div>
              <div className="text-xs text-ink-dim flex gap-2 flex-wrap mb-1">
                {f.directory_id && <span>📁 {f.directory_id[1]}</span>}
                {f.document_type_id && <span>📄 {f.document_type_id[1]}</span>}
              </div>
              {snippet && (
                <p className="text-xs text-ink-muted leading-relaxed mt-2">
                  <Highlighted text={snippet} query={query} />
                </p>
              )}
            </button>
          </li>
        )
      })}
    </ul>
  )
}

function Highlighted({ text, query }: { text: string; query: string }) {
  if (!query) return <>{text}</>
  const re = new RegExp(`(${escapeRe(query)})`, 'gi')
  const parts = text.split(re)
  return (
    <>
      {parts.map((p, i) =>
        re.test(p) ? <mark key={i} className="bg-yellow-300/60 text-inherit rounded px-0.5">{p}</mark> : <span key={i}>{p}</span>,
      )}
    </>
  )
}
function escapeRe(s: string) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') }

function OcrPill({ state }: { state: string }) {
  const map: Record<string, string> = {
    pending: 'bg-yellow-500/15 text-yellow-300',
    processing: 'bg-blue-500/15 text-blue-300',
    done: 'bg-emerald-500/15 text-emerald-300',
    failed: 'bg-red-500/15 text-red-300',
    skipped: 'bg-bg-muted text-ink-dim',
  }
  return <span className={`ml-auto text-[10px] px-1.5 py-0.5 rounded ${map[state] ?? 'bg-bg-muted'}`}>{state}</span>
}
