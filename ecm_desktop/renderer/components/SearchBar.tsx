'use client'

import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react'
import { Search, X } from 'lucide-react'

interface Props {
  value: string
  onChange: (v: string) => void
  placeholder?: string
}

export interface SearchBarHandle {
  focus: () => void
}

export const SearchBar = forwardRef<SearchBarHandle, Props>(function SearchBar(
  { value, onChange, placeholder = 'Buscar nome ou texto OCR…' },
  ref,
) {
  const inputRef = useRef<HTMLInputElement | null>(null)

  useImperativeHandle(ref, () => ({
    focus: () => inputRef.current?.focus(),
  }))

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        inputRef.current?.focus()
        inputRef.current?.select()
      }
      if (e.key === 'Escape' && document.activeElement === inputRef.current) {
        onChange('')
        inputRef.current?.blur()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onChange])

  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-bg-soft border border-line rounded-lg focus-within:border-accent transition">
      <Search size={16} className="text-ink-dim" />
      <input
        ref={inputRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="bg-transparent outline-none text-sm flex-1 min-w-0"
      />
      {value ? (
        <button onClick={() => onChange('')} className="text-ink-dim hover:text-ink p-0.5"><X size={14} /></button>
      ) : (
        <span className="text-[10px] text-ink-dim border border-line rounded px-1.5 py-0.5 shrink-0">Ctrl K</span>
      )}
    </div>
  )
})
