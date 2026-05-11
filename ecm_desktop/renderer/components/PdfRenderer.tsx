'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'
import {
  ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Maximize2,
  Minimize2, Search, X,
} from 'lucide-react'

if (typeof window !== 'undefined') {
  pdfjs.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs'
}

interface Props {
  url: string
  pageNum: number
  onPagesLoaded: (n: number) => void
  onPageChange: (n: number) => void
  totalPages: number
}

type FitMode = 'width' | 'height' | 'page' | 'custom'

const ZOOM_STEP = 0.15
const ZOOM_MIN = 0.4
const ZOOM_MAX = 4

export default function PdfRenderer({ url, pageNum, onPagesLoaded, onPageChange, totalPages }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [scale, setScale] = useState(1)
  const [fitMode, setFitMode] = useState<FitMode>('width')
  const [naturalSize, setNaturalSize] = useState<{ w: number; h: number } | null>(null)
  const [search, setSearch] = useState('')
  const [searchOpen, setSearchOpen] = useState(false)
  const [matches, setMatches] = useState<number[]>([]) // page numbers
  const [matchIdx, setMatchIdx] = useState(0)

  // Recalcula scale conforme fit
  const recomputeFit = useCallback(() => {
    if (!containerRef.current || !naturalSize) return
    const box = containerRef.current.getBoundingClientRect()
    const pad = 48
    if (fitMode === 'width') {
      setScale((box.width - pad) / naturalSize.w)
    } else if (fitMode === 'height') {
      setScale((box.height - pad - 60) / naturalSize.h)
    } else if (fitMode === 'page') {
      const sW = (box.width - pad) / naturalSize.w
      const sH = (box.height - pad - 60) / naturalSize.h
      setScale(Math.min(sW, sH))
    }
  }, [fitMode, naturalSize])

  useEffect(() => { recomputeFit() }, [recomputeFit])
  useEffect(() => {
    const onResize = () => recomputeFit()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [recomputeFit])

  // Atalhos
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
        e.preventDefault(); setSearchOpen((v) => !v)
      }
      if ((e.ctrlKey || e.metaKey) && (e.key === '+' || e.key === '=')) {
        e.preventDefault(); zoomIn()
      }
      if ((e.ctrlKey || e.metaKey) && e.key === '-') {
        e.preventDefault(); zoomOut()
      }
      if ((e.ctrlKey || e.metaKey) && e.key === '0') {
        e.preventDefault(); setFitMode('width')
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function zoomIn() {
    setFitMode('custom')
    setScale((s) => Math.min(ZOOM_MAX, s + ZOOM_STEP))
  }
  function zoomOut() {
    setFitMode('custom')
    setScale((s) => Math.max(ZOOM_MIN, s - ZOOM_STEP))
  }

  async function runSearch(query: string) {
    if (!query.trim()) { setMatches([]); setMatchIdx(0); return }
    // pdfjs: percorre páginas e busca no textContent
    const pdf = await pdfjs.getDocument(url).promise
    const found: number[] = []
    for (let p = 1; p <= pdf.numPages; p++) {
      const page = await pdf.getPage(p)
      const tc = await page.getTextContent()
      const txt = tc.items.map((it: any) => it.str).join(' ').toLowerCase()
      if (txt.includes(query.toLowerCase())) found.push(p)
    }
    setMatches(found)
    setMatchIdx(0)
    if (found.length) onPageChange(found[0])
  }

  function gotoMatch(delta: number) {
    if (!matches.length) return
    const idx = (matchIdx + delta + matches.length) % matches.length
    setMatchIdx(idx)
    onPageChange(matches[idx])
  }

  return (
    <div className="w-full h-full flex flex-col" ref={containerRef}>
      {/* Toolbar */}
      <div className="flex items-center gap-1 px-2 py-1.5 border-b border-line bg-bg-soft text-sm sticky top-0 z-10">
        <Btn onClick={() => onPageChange(Math.max(1, pageNum - 1))} disabled={pageNum <= 1}><ChevronLeft size={14} /></Btn>
        <span className="px-1 text-xs">{pageNum} / {totalPages || '?'}</span>
        <Btn onClick={() => onPageChange(Math.min(totalPages || pageNum, pageNum + 1))} disabled={pageNum >= totalPages}><ChevronRight size={14} /></Btn>

        <Sep />

        <Btn onClick={zoomOut}><ZoomOut size={14} /></Btn>
        <span className="px-1 text-xs w-12 text-center">{Math.round(scale * 100)}%</span>
        <Btn onClick={zoomIn}><ZoomIn size={14} /></Btn>

        <Sep />

        <Btn onClick={() => setFitMode('width')} active={fitMode === 'width'} title="Ajustar largura"><Maximize2 size={14} /></Btn>
        <Btn onClick={() => setFitMode('height')} active={fitMode === 'height'} title="Ajustar altura"><Minimize2 size={14} /></Btn>
        <Btn onClick={() => setFitMode('page')} active={fitMode === 'page'} title="Página inteira">
          <span className="text-[10px] px-1">FIT</span>
        </Btn>

        <Sep />

        <Btn onClick={() => setSearchOpen((v) => !v)} active={searchOpen} title="Buscar (Ctrl+F)"><Search size={14} /></Btn>

        {searchOpen && (
          <div className="flex items-center gap-1 ml-2">
            <input
              autoFocus
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') runSearch(search)
                if (e.key === 'Escape') { setSearchOpen(false); setSearch(''); setMatches([]) }
              }}
              placeholder="Buscar no PDF…"
              className="px-2 py-1 bg-bg border border-line rounded text-xs w-44 outline-none focus:border-accent"
            />
            {matches.length > 0 && (
              <>
                <span className="text-[10px] text-ink-dim">{matchIdx + 1}/{matches.length}</span>
                <Btn onClick={() => gotoMatch(-1)}><ChevronLeft size={12} /></Btn>
                <Btn onClick={() => gotoMatch(1)}><ChevronRight size={12} /></Btn>
              </>
            )}
            {search && matches.length === 0 && (
              <span className="text-[10px] text-ink-dim">sem resultado</span>
            )}
            <Btn onClick={() => { setSearchOpen(false); setSearch(''); setMatches([]) }}><X size={12} /></Btn>
          </div>
        )}
      </div>

      {/* Page area */}
      <div className="flex-1 overflow-auto grid place-items-start justify-center py-6">
        <Document
          file={url}
          onLoadSuccess={(p) => onPagesLoaded(p.numPages)}
          loading={<div className="text-ink-muted">Carregando PDF…</div>}
        >
          <Page
            pageNumber={pageNum}
            scale={scale}
            onLoadSuccess={(p) => {
              if (!naturalSize) setNaturalSize({ w: p.originalWidth, h: p.originalHeight })
            }}
            renderTextLayer
            renderAnnotationLayer={false}
            customTextRenderer={(item: { str: string }) => highlightText(item.str, search)}
          />
        </Document>
      </div>
    </div>
  )
}

function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' } as Record<string, string>)[c]!,
  )
}
function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}
function highlightText(text: string, query: string): string {
  if (!query.trim()) return escapeHtml(text)
  try {
    const re = new RegExp(`(${escapeRegex(query.trim())})`, 'gi')
    return escapeHtml(text).replace(re, '<mark class="ecm-pdf-hl">$1</mark>')
  } catch {
    return escapeHtml(text)
  }
}

function Btn({
  onClick, disabled, active, title, children,
}: { onClick: () => void; disabled?: boolean; active?: boolean; title?: string; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={`p-1.5 rounded hover:bg-bg-muted disabled:opacity-30 ${active ? 'bg-bg-muted text-accent' : ''}`}
    >
      {children}
    </button>
  )
}
function Sep() { return <div className="w-px h-5 bg-line mx-1" /> }
