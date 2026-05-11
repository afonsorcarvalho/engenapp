'use client'

import { useState } from 'react'
import { Link2, Check, Loader2 } from 'lucide-react'
import { ecmApi } from '@/lib/ecm-api'
import toast from 'react-hot-toast'

interface Props {
  fileId: number
  className?: string
  /** quando true, ao gerar mostra modal com URL completa pra copiar manual */
  showModal?: boolean
}

export function ShareButton({ fileId, className = '', showModal = true }: Props) {
  const [busy, setBusy] = useState(false)
  const [copied, setCopied] = useState(false)
  const [url, setUrl] = useState<string | null>(null)
  const [modalOpen, setModalOpen] = useState(false)

  async function share() {
    if (busy) return
    setBusy(true)
    try {
      const u = await ecmApi.getShareUrl(fileId)
      setUrl(u)
      await navigator.clipboard.writeText(u).catch(() => {})
      setCopied(true)
      toast.success('Link copiado para a área de transferência')
      setTimeout(() => setCopied(false), 2500)
      if (showModal) setModalOpen(true)
    } catch (e: any) {
      toast.error(e?.message || 'Falha ao gerar link')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <button
        onClick={share}
        disabled={busy}
        className={`flex items-center justify-center gap-1.5 ${className}`}
      >
        {busy ? <Loader2 size={14} className="animate-spin" /> : copied ? <Check size={14} /> : <Link2 size={14} />}
        {copied ? 'Copiado!' : 'Compartilhar link'}
      </button>

      {modalOpen && url && (
        <div className="fixed inset-0 z-[60] grid place-items-center bg-black/60 backdrop-blur-sm p-4" onClick={() => setModalOpen(false)}>
          <div className="glass max-w-lg w-full p-5 rounded-2xl" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-medium mb-2 flex items-center gap-2"><Link2 size={16} /> Link público gerado</h3>
            <p className="text-xs text-ink-muted mb-3">
              Quem tiver o link consegue baixar o arquivo sem login.
            </p>
            <div className="flex gap-2">
              <input
                value={url}
                readOnly
                onFocus={(e) => e.currentTarget.select()}
                className="flex-1 px-2 py-1.5 rounded bg-bg-soft border border-line text-xs outline-none focus:border-accent"
              />
              <button
                onClick={async () => {
                  await navigator.clipboard.writeText(url).catch(() => {})
                  setCopied(true)
                  toast.success('Copiado')
                  setTimeout(() => setCopied(false), 2000)
                }}
                className="px-3 py-1.5 rounded bg-accent hover:bg-accent-soft text-xs font-medium"
              >
                {copied ? 'Copiado' : 'Copiar'}
              </button>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button onClick={() => setModalOpen(false)} className="text-xs px-3 py-1.5 rounded bg-bg-muted hover:bg-bg">Fechar</button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
