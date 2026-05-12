'use client'

import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Pencil, Save, X, RefreshCw, Lock, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { ecmApi, EcmFileSummary, EcmDirectory, EcmDocumentType } from '@/lib/ecm-api'

const CONFIDENTIALITY: { value: string; label: string }[] = [
  { value: 'public', label: 'Público' },
  { value: 'internal', label: 'Interno' },
  { value: 'restricted', label: 'Restrito' },
  { value: 'confidential', label: 'Confidencial' },
]

interface Props {
  file: EcmFileSummary
  directories: EcmDirectory[]
}

interface FormState {
  document_type_id: number | null
  directory_id: number | null
  confidentiality: string
  expiration_date: string | null
  ocr_enabled: boolean
}

function initialForm(file: EcmFileSummary): FormState {
  return {
    document_type_id: file.document_type_id ? file.document_type_id[0] : null,
    directory_id: file.directory_id ? file.directory_id[0] : null,
    confidentiality: file.confidentiality ?? 'internal',
    expiration_date: typeof file.expiration_date === 'string' ? file.expiration_date : null,
    ocr_enabled: file.ocr_enabled === true,
  }
}

export function FilePropertiesEditor({ file, directories }: Props) {
  const qc = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState<FormState>(() => initialForm(file))
  const [saving, setSaving] = useState(false)
  const [reproc, setReproc] = useState(false)

  // reset quando troca de arquivo OU sai do modo edit
  useEffect(() => {
    setForm(initialForm(file))
    setEditing(false)
  }, [file.id])

  const types = useQuery({
    queryKey: ['document-types'],
    queryFn: () => ecmApi.listDocumentTypes(),
    staleTime: 5 * 60_000,
  })

  const canWrite = file.permission_write !== false
  const isApproved = file.approval_state === 'approved'
  const readOnly = !canWrite || isApproved

  function cancel() {
    setForm(initialForm(file))
    setEditing(false)
  }

  async function save() {
    if (saving) return
    const vals: Record<string, unknown> = {}
    const original = initialForm(file)
    if (form.document_type_id !== original.document_type_id) {
      vals.document_type_id = form.document_type_id || false
    }
    if (form.directory_id !== original.directory_id) {
      if (!form.directory_id) {
        toast.error('Pasta é obrigatória.')
        return
      }
      vals.directory_id = form.directory_id
    }
    if (form.confidentiality !== original.confidentiality) {
      vals.confidentiality = form.confidentiality
    }
    if (form.expiration_date !== original.expiration_date) {
      vals.expiration_date = form.expiration_date || false
    }
    if (form.ocr_enabled !== original.ocr_enabled) {
      vals.ocr_enabled = form.ocr_enabled
    }
    if (Object.keys(vals).length === 0) {
      setEditing(false)
      return
    }
    setSaving(true)
    try {
      await ecmApi.updateFile(file.id, vals)
      toast.success('Propriedades atualizadas')
      qc.invalidateQueries({ queryKey: ['files'] })
      setEditing(false)
    } catch (e: any) {
      toast.error(e?.message || 'Falha ao salvar (verifique permissões).')
    } finally {
      setSaving(false)
    }
  }

  async function reprocess() {
    if (reproc) return
    setReproc(true)
    try {
      await ecmApi.reprocessOcr(file.id)
      toast.success('OCR reenfileirado')
      qc.invalidateQueries({ queryKey: ['files'] })
    } catch (e: any) {
      toast.error(e?.message || 'Falha ao reprocessar OCR')
    } finally {
      setReproc(false)
    }
  }

  return (
    <>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs uppercase tracking-wide text-ink-muted">Propriedades</span>
        {!editing && (
          readOnly ? (
            <span
              className="text-[11px] text-ink-dim flex items-center gap-1"
              title={isApproved ? 'Arquivo aprovado é imutável.' : 'Sem permissão de escrita.'}
            >
              <Lock size={11} /> {isApproved ? 'Aprovado' : 'Somente leitura'}
            </span>
          ) : (
            <button
              onClick={() => setEditing(true)}
              className="text-[11px] flex items-center gap-1 px-2 py-0.5 rounded hover:bg-bg-muted text-ink-muted hover:text-accent"
              title="Editar propriedades"
            >
              <Pencil size={11} /> Editar
            </button>
          )
        )}
      </div>

      <div className="text-sm space-y-2">
        <Field label="Tipo">
          {editing ? (
            <select
              value={form.document_type_id ?? ''}
              onChange={(e) => setForm({ ...form, document_type_id: e.target.value ? Number(e.target.value) : null })}
              className="w-full bg-bg-soft border border-line rounded px-2 py-1 text-sm outline-none focus:border-accent"
            >
              <option value="">—</option>
              {types.data?.map((t: EcmDocumentType) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          ) : (
            <span className="break-all">
              {file.document_type_id ? file.document_type_id[1] : '—'}
            </span>
          )}
        </Field>

        <Field label="Pasta">
          {editing ? (
            <select
              value={form.directory_id ?? ''}
              onChange={(e) => setForm({ ...form, directory_id: e.target.value ? Number(e.target.value) : null })}
              className="w-full bg-bg-soft border border-line rounded px-2 py-1 text-sm outline-none focus:border-accent"
            >
              <option value="">—</option>
              {directories.map((d) => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          ) : (
            <span className="break-all">
              {file.directory_id ? file.directory_id[1] : '—'}
            </span>
          )}
        </Field>

        <Field label="Confid.">
          {editing ? (
            <select
              value={form.confidentiality}
              onChange={(e) => setForm({ ...form, confidentiality: e.target.value })}
              className="w-full bg-bg-soft border border-line rounded px-2 py-1 text-sm outline-none focus:border-accent"
            >
              {CONFIDENTIALITY.map((c) => (
                <option key={c.value} value={c.value}>{c.label}</option>
              ))}
            </select>
          ) : (
            <span>{CONFIDENTIALITY.find((c) => c.value === file.confidentiality)?.label ?? '—'}</span>
          )}
        </Field>

        <Field label="OCR">
          <div className="flex items-center gap-2 flex-wrap">
            {editing ? (
              <label className="flex items-center gap-1.5 text-xs">
                <input
                  type="checkbox"
                  checked={form.ocr_enabled}
                  onChange={(e) => setForm({ ...form, ocr_enabled: e.target.checked })}
                  className="accent-accent"
                />
                Habilitado
              </label>
            ) : (
              <>
                <span>{file.ocr_state ?? '—'}</span>
                {file.ocr_enabled !== undefined && (
                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                    file.ocr_enabled ? 'bg-emerald-500/15 text-emerald-300' : 'bg-bg-muted text-ink-dim'
                  }`}>
                    {file.ocr_enabled ? 'ON' : 'OFF'}
                  </span>
                )}
                {!readOnly && file.ocr_state !== 'processing' && file.ocr_state !== 'pending' && (
                  <button
                    onClick={reprocess}
                    disabled={reproc}
                    className="text-[10px] flex items-center gap-1 px-1.5 py-0.5 rounded bg-bg-muted hover:bg-bg text-ink-muted hover:text-accent disabled:opacity-50"
                    title="Reprocessar OCR"
                  >
                    {reproc ? <Loader2 size={10} className="animate-spin" /> : <RefreshCw size={10} />}
                    Reproc.
                  </button>
                )}
              </>
            )}
          </div>
        </Field>

        <Field label="Vencimento">
          {editing ? (
            <input
              type="date"
              value={form.expiration_date ?? ''}
              onChange={(e) => setForm({ ...form, expiration_date: e.target.value || null })}
              className="w-full bg-bg-soft border border-line rounded px-2 py-1 text-sm outline-none focus:border-accent"
            />
          ) : (
            <span>{file.expiration_date || '—'}</span>
          )}
        </Field>
      </div>

      {editing && (
        <div className="flex justify-end gap-1.5 mt-3">
          <button
            onClick={cancel}
            disabled={saving}
            className="text-xs px-2.5 py-1 rounded bg-bg-muted hover:bg-bg flex items-center gap-1"
          >
            <X size={12} /> Cancelar
          </button>
          <button
            onClick={save}
            disabled={saving}
            className="text-xs px-2.5 py-1 rounded bg-accent hover:bg-accent-soft text-white disabled:opacity-50 flex items-center gap-1"
          >
            {saving ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
            Salvar
          </button>
        </div>
      )}
    </>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-2 items-start">
      <span className="text-ink-muted w-20 shrink-0 pt-0.5">{label}</span>
      <div className="flex-1 min-w-0">{children}</div>
    </div>
  )
}
