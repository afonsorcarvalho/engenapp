'use client'

import { useEffect, useMemo, useState } from 'react'
import dynamic from 'next/dynamic'
import { X, Download, Loader2, FileText } from 'lucide-react'
import { ecmApi } from '@/lib/ecm-api'
import { ShareButton } from './ShareButton'

const PdfRenderer = dynamic(() => import('./PdfRenderer'), { ssr: false })

interface Props {
  fileId: number | null
  fileName?: string
  mimetype?: string
  onClose: () => void
}

export function FilePreviewModal({ fileId, fileName, mimetype, onClose }: Props) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [pages, setPages] = useState(0)
  const [pageNum, setPageNum] = useState(1)
  const [ocrText, setOcrText] = useState<string | null>(null)
  const [canDownload, setCanDownload] = useState<boolean>(true)

  const isPdf = useMemo(
    () => (mimetype || '').toLowerCase().includes('pdf') || (fileName || '').toLowerCase().endsWith('.pdf'),
    [mimetype, fileName],
  )
  const isImage = useMemo(
    () => (mimetype || '').toLowerCase().startsWith('image/') || /\.(png|jpe?g|gif|webp|bmp)$/i.test(fileName || ''),
    [mimetype, fileName],
  )

  useEffect(() => {
    let cancelled = false
    let createdBlob: string | null = null
    setBlobUrl(null); setError(null); setLoading(true); setPages(0); setPageNum(1); setOcrText(null); setCanDownload(true)
    if (!fileId) return

    async function load(id: number) {
      try {
        // Endpoint Odoo padrão: /web/content?model=dms.file&id=N&field=content&download=false
        // cache-buster + no-store para evitar 304 Not Modified (body vazio) na 2ª abertura
        const url = `/api/odoo/web/content?model=dms.file&id=${id}&field=content&download=false&_t=${Date.now()}`
        const r = await fetch(url, {
          credentials: 'include',
          cache: 'no-store',
          headers: { 'X-Odoo-Target': odooTarget(), 'Cache-Control': 'no-cache' },
        })
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        const ct = r.headers.get('content-type') || ''
        console.log('[FilePreview] content-type:', ct, 'status:', r.status, 'url:', url)
        const blob = await r.blob()
        if (ct.includes('text/html')) {
          throw new Error('Servidor retornou HTML (provavelmente sessão expirada). Faça login novamente.')
        }
        if (cancelled) return
        createdBlob = URL.createObjectURL(blob)
        setBlobUrl(createdBlob)

        try {
          const f = await ecmApi.readFile(id, ['ocr_text', 'ocr_state', 'can_download'])
          if (!cancelled) {
            setOcrText(f.ocr_text || null)
            setCanDownload(f.can_download !== false)
          }
        } catch {}
      } catch (e: any) {
        if (!cancelled) setError(e?.message || 'Erro ao baixar')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load(fileId)
    return () => {
      cancelled = true
      if (createdBlob) URL.revokeObjectURL(createdBlob)
    }
  }, [fileId])

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
      if (isPdf && e.key === 'ArrowLeft') setPageNum((p) => Math.max(1, p - 1))
      if (isPdf && e.key === 'ArrowRight') setPageNum((p) => Math.min(pages || 1, p + 1))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose, isPdf, pages])

  if (!fileId) return null

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex flex-col">
      <header className="flex items-center gap-3 px-5 py-3 border-b border-white/10 text-white">
        <FileText size={18} className="text-accent shrink-0" />
        <p className="text-sm truncate flex-1 text-white">{fileName || `Arquivo #${fileId}`}</p>
        {!canDownload && (
          <span className="text-xs px-2 py-1 rounded border border-amber-500/40 bg-amber-500/10 text-amber-300">
            Download restrito
          </span>
        )}
        {fileId && canDownload && (
          <ShareButton
            fileId={fileId}
            className="text-sm px-3 py-1.5 rounded-lg bg-white/10 border border-white/15 hover:border-accent text-white"
          />
        )}
        {blobUrl && canDownload && (
          <a href={blobUrl} download={fileName || `arquivo_${fileId}`}
             className="text-sm px-3 py-1.5 rounded-lg bg-white/10 border border-white/15 hover:border-accent text-white flex items-center gap-1.5">
            <Download size={14} /> Baixar
          </a>
        )}
        <button
          onClick={onClose}
          className="p-2 rounded text-white hover:bg-white/10"
          title="Fechar (Esc)"
        >
          <X size={18} />
        </button>
      </header>

      <div className="flex-1 grid grid-cols-[1fr_360px] overflow-hidden">
        <div className="overflow-hidden bg-bg/80 flex flex-col">
          {loading && (
            <div className="m-auto text-ink-muted flex items-center gap-2">
              <Loader2 size={18} className="animate-spin" /> Carregando…
            </div>
          )}
          {error && <p className="m-auto text-red-300">{error}</p>}
          {!loading && !error && blobUrl && isPdf && (
            <PdfRenderer
              url={blobUrl}
              pageNum={pageNum}
              totalPages={pages}
              onPageChange={setPageNum}
              onPagesLoaded={setPages}
            />
          )}
          {!loading && !error && blobUrl && isImage && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={blobUrl} alt={fileName || ''} className="max-w-full max-h-full object-contain" />
          )}
          {!loading && !error && blobUrl && !isPdf && !isImage && (
            <div className="text-ink-muted text-center">
              <p>Pré-visualização indisponível para este formato.</p>
              <p className="text-xs mt-1">Use o botão "Baixar" no topo.</p>
            </div>
          )}
        </div>

        <aside className="border-l border-line bg-bg-soft overflow-y-auto">
          <div className="px-4 py-3 border-b border-line text-xs uppercase tracking-wide text-ink-muted">
            Texto extraído (OCR)
          </div>
          {ocrText ? (
            <pre className="p-4 text-xs whitespace-pre-wrap text-ink-muted leading-relaxed">{ocrText}</pre>
          ) : (
            <p className="p-4 text-xs text-ink-dim">
              Nenhum texto OCR disponível para este arquivo.
            </p>
          )}
        </aside>
      </div>
    </div>
  )
}

function odooTarget(): string {
  try {
    const raw = localStorage.getItem('ecm-auth')
    if (!raw) return ''
    const { state } = JSON.parse(raw)
    return state?.baseUrl || ''
  } catch { return '' }
}
