'use client'

import { useEffect, useRef, useState } from 'react'
import { Upload as UploadIcon } from 'lucide-react'

interface Props {
  onFiles: (files: File[]) => void
  /** Quando true exibe sempre (modo "área dedicada"). Se false fica overlay global. */
  inline?: boolean
}

export function UploadDropzone({ onFiles, inline = false }: Props) {
  const [dragging, setDragging] = useState(false)
  const enterCount = useRef(0)

  useEffect(() => {
    if (inline) return
    function onWindowDragEnter(e: DragEvent) {
      if (!hasFiles(e)) return
      e.preventDefault()
      enterCount.current++
      setDragging(true)
    }
    function onWindowDragOver(e: DragEvent) {
      if (!hasFiles(e)) return
      e.preventDefault()
    }
    function onWindowDragLeave(e: DragEvent) {
      enterCount.current--
      if (enterCount.current <= 0) {
        enterCount.current = 0
        setDragging(false)
      }
    }
    function onWindowDrop(e: DragEvent) {
      if (!hasFiles(e)) return
      e.preventDefault()
      enterCount.current = 0
      setDragging(false)
      const files = Array.from(e.dataTransfer?.files ?? [])
      if (files.length) onFiles(files)
    }
    window.addEventListener('dragenter', onWindowDragEnter)
    window.addEventListener('dragover', onWindowDragOver)
    window.addEventListener('dragleave', onWindowDragLeave)
    window.addEventListener('drop', onWindowDrop)
    return () => {
      window.removeEventListener('dragenter', onWindowDragEnter)
      window.removeEventListener('dragover', onWindowDragOver)
      window.removeEventListener('dragleave', onWindowDragLeave)
      window.removeEventListener('drop', onWindowDrop)
    }
  }, [inline, onFiles])

  function pick() {
    const input = document.createElement('input')
    input.type = 'file'
    input.multiple = true
    input.onchange = () => {
      const files = Array.from(input.files ?? [])
      if (files.length) onFiles(files)
    }
    input.click()
  }

  if (inline) {
    return (
      <button
        onClick={pick}
        className="w-full glass rounded-2xl p-10 flex flex-col items-center justify-center gap-3 hover:border-accent transition"
      >
        <UploadIcon size={32} className="text-accent" />
        <p className="text-sm">Clique para selecionar arquivos</p>
        <p className="text-xs text-ink-dim">ou arraste para qualquer lugar da janela</p>
      </button>
    )
  }

  if (!dragging) return null

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-bg/85 backdrop-blur-sm pointer-events-none">
      <div className="glass border-2 border-dashed border-accent rounded-3xl px-16 py-12 text-center">
        <UploadIcon size={48} className="text-accent mx-auto mb-3" />
        <p className="text-lg font-medium">Solte para enviar ao ECM</p>
        <p className="text-sm text-ink-muted">Arquivos serão classificados em seguida</p>
      </div>
    </div>
  )
}

function hasFiles(e: DragEvent): boolean {
  if (!e.dataTransfer) return false
  return Array.from(e.dataTransfer.types ?? []).includes('Files')
}
