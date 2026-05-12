'use client'

import { useEffect, useState } from 'react'
import { getFileIcon, isImage } from '@/lib/file-icons'
import { useAuthStore } from '@/store/authStore'

interface Props {
  fileId?: number
  name?: string
  mimetype?: string
  /** Tamanho em px do ícone OU lado do thumbnail quadrado. Default 18 */
  size?: number
  /** Mostra thumbnail real (lazy) se for imagem. Default true. */
  thumbnail?: boolean
  /** Classe extra no container. */
  className?: string
}

/**
 * Renderiza ícone do tipo de arquivo, ou — se for imagem e `thumbnail` true e
 * houver `fileId` — uma miniatura real puxada via /web/content.
 */
export function FileIcon({
  fileId, name, mimetype, size = 18, thumbnail = true, className = '',
}: Props) {
  const { Icon, colorClass, label } = getFileIcon(mimetype, name)
  const showThumb = thumbnail && fileId != null && isImage(mimetype, name)
  const [thumbFailed, setThumbFailed] = useState(false)

  // reset on file change
  useEffect(() => { setThumbFailed(false) }, [fileId])

  if (showThumb && !thumbFailed) {
    return (
      <ThumbImage
        fileId={fileId!}
        size={size}
        alt={name || label}
        className={className}
        onError={() => setThumbFailed(true)}
      />
    )
  }

  return (
    <Icon
      size={size}
      className={`${colorClass} shrink-0 ${className}`}
      aria-label={label}
    />
  )
}

function ThumbImage({
  fileId, size, alt, className, onError,
}: {
  fileId: number; size: number; alt: string; className?: string; onError?: () => void
}) {
  const baseUrl = useAuthStore((s) => s.baseUrl) || ''
  // proxy: o /api/odoo/[...path]/route.ts aceita ?__t=<base> pra <img> tag
  const ts = useStableTimestamp(fileId)
  const src = `/api/odoo/web/content?model=dms.file&id=${fileId}&field=content&download=false&__t=${encodeURIComponent(baseUrl)}&_=${ts}`

  // dimensão visual (px); object-cover crop pra quadrado
  const style = { width: size, height: size }

  return (
    /* eslint-disable-next-line @next/next/no-img-element */
    <img
      src={src}
      alt={alt}
      loading="lazy"
      decoding="async"
      onError={onError}
      style={style}
      className={`rounded-md object-cover bg-bg-muted shrink-0 ${className}`}
    />
  )
}

/** Timestamp estável por fileId — evita re-fetch a cada render. */
function useStableTimestamp(key: number): number {
  const [ts] = useState(() => Date.now())
  // se quiser invalidar quando key muda, troque por useMemo([key])
  void key
  return ts
}
