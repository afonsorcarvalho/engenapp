'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '@/store/authStore'
import { useSettingsStore } from '@/store/settingsStore'
import { getElectron } from '@/lib/electron'
import { ecmApi } from '@/lib/ecm-api'
import toast from 'react-hot-toast'
import { ArrowLeft, FolderOpen, Power } from 'lucide-react'

export default function SettingsPage() {
  const router = useRouter()
  const { baseUrl, db, username, logout } = useAuthStore()
  const s = useSettingsStore()
  const setS = useSettingsStore((st) => st.set)
  const [watching, setWatching] = useState(false)

  const dirs = useQuery({
    queryKey: ['directories'],
    queryFn: () => ecmApi.listDirectories(),
  })
  const types = useQuery({
    queryKey: ['document-types'],
    queryFn: () => ecmApi.listDocumentTypes(),
  })

  useEffect(() => {
    const el = getElectron()
    if (!el) return
    el.watcher.status().then((st) => {
      setWatching(st.running)
      if (st.folder && !s.watchedFolder) setS({ watchedFolder: st.folder })
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function pickFolder() {
    const el = getElectron()
    if (!el) return
    const p = await el.app.pickFolder()
    if (p) setS({ watchedFolder: p })
  }
  async function pickProcessed() {
    const el = getElectron()
    if (!el) return
    const p = await el.app.pickFolder()
    if (p) setS({ watchProcessedFolder: p })
  }

  async function toggleWatch() {
    const el = getElectron()
    if (!el) return
    if (watching) {
      await el.watcher.stop()
      setWatching(false)
      toast.success('Sincronização desligada')
    } else {
      if (!s.watchedFolder) { toast.error('Selecione uma pasta local'); return }
      if (!s.watchDestinationDirectoryId) { toast.error('Selecione a Pasta DMS destino'); return }
      await el.watcher.start(s.watchedFolder)
      setWatching(true)
      toast.success('Sincronização ativa')
    }
  }

  async function doLogout() {
    await logout()
    router.replace('/login')
  }

  const isElectron = !!getElectron()

  return (
    <div className="min-h-screen max-w-3xl mx-auto p-8">
      <button onClick={() => router.back()} className="text-sm text-ink-muted flex items-center gap-1 mb-6 hover:text-ink">
        <ArrowLeft size={16} /> Voltar
      </button>
      <h1 className="text-2xl font-semibold mb-6">Configurações</h1>

      <Card title="Sessão">
        <Row label="Servidor" value={baseUrl} />
        <Row label="Banco" value={db} />
        <Row label="Usuário" value={username} />
        <button onClick={doLogout} className="mt-3 text-sm px-3 py-2 rounded-lg bg-bg-muted hover:bg-bg flex items-center gap-2">
          <Power size={14} /> Sair (limpa credenciais)
        </button>
      </Card>

      <Card title="Pasta sincronizada (Watch folder)">
        {!isElectron && (
          <div className="text-xs px-3 py-2 mb-3 rounded bg-yellow-500/15 text-yellow-300">
            Watch folder só funciona no app desktop (Electron). No browser, esta seção é só visual.
          </div>
        )}
        <p className="text-sm text-ink-muted mb-4">
          Arquivos adicionados na pasta local são enviados automaticamente para o ECM,
          classificados pelo tipo padrão e salvos na pasta DMS escolhida.
        </p>

        <Field label="Pasta local (monitorada)">
          <div className="flex gap-2">
            <input
              value={s.watchedFolder}
              readOnly
              placeholder="Nenhuma pasta selecionada"
              className="flex-1 px-3 py-2 rounded-lg bg-bg-soft border border-line outline-none text-sm"
            />
            <button onClick={pickFolder} className="px-3 py-2 rounded-lg bg-bg-muted hover:bg-bg text-sm flex items-center gap-1.5">
              <FolderOpen size={14} /> Escolher
            </button>
          </div>
        </Field>

        <Field label="Pasta DMS destino">
          <select
            value={s.watchDestinationDirectoryId ?? ''}
            onChange={(e) => {
              const id = e.target.value ? Number(e.target.value) : null
              const name = id ? dirs.data?.find((d) => d.id === id)?.name || '' : ''
              setS({ watchDestinationDirectoryId: id, watchDestinationDirectoryName: name })
            }}
            className="w-full px-3 py-2 rounded-lg bg-bg-soft border border-line outline-none focus:border-accent text-sm"
          >
            <option value="">— Selecionar —</option>
            {dirs.data?.map((d) => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>
        </Field>

        <Field label="Tipo de documento padrão (opcional)">
          <select
            value={s.watchDefaultDocumentTypeId ?? ''}
            onChange={(e) => setS({ watchDefaultDocumentTypeId: e.target.value ? Number(e.target.value) : null })}
            className="w-full px-3 py-2 rounded-lg bg-bg-soft border border-line outline-none focus:border-accent text-sm"
          >
            <option value="">— Sem tipo —</option>
            {types.data?.map((t) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
        </Field>

        <Field label="Após upload">
          <select
            value={s.watchPostAction}
            onChange={(e) => setS({ watchPostAction: e.target.value as any })}
            className="w-full px-3 py-2 rounded-lg bg-bg-soft border border-line outline-none focus:border-accent text-sm"
          >
            <option value="move">Mover para pasta "Processed"</option>
            <option value="delete">Deletar local</option>
            <option value="keep">Manter (alerta de duplicado pode ocorrer)</option>
          </select>
        </Field>

        {s.watchPostAction === 'move' && (
          <Field label="Pasta de arquivados (Processed) — opcional">
            <div className="flex gap-2">
              <input
                value={s.watchProcessedFolder}
                readOnly
                placeholder="Padrão: <pasta-local>/Processed"
                className="flex-1 px-3 py-2 rounded-lg bg-bg-soft border border-line outline-none text-sm"
              />
              <button onClick={pickProcessed} className="px-3 py-2 rounded-lg bg-bg-muted hover:bg-bg text-sm">Escolher</button>
            </div>
          </Field>
        )}

        <label className="flex items-center gap-2 text-sm mt-3 select-none">
          <input
            type="checkbox"
            checked={s.watchAutoStart}
            onChange={(e) => setS({ watchAutoStart: e.target.checked })}
          />
          Ativar sincronização automaticamente ao iniciar o app
        </label>

        <button
          onClick={toggleWatch}
          disabled={!isElectron}
          className={`mt-4 px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-40 ${
            watching ? 'bg-red-500/20 text-red-300 hover:bg-red-500/30' : 'bg-accent hover:bg-accent-soft'
          }`}
        >
          {watching ? 'Parar sincronização' : 'Iniciar sincronização'}
        </button>
      </Card>
    </div>
  )
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="glass rounded-xl p-5 mb-4">
      <h2 className="text-sm uppercase tracking-wide text-ink-muted mb-3">{title}</h2>
      {children}
    </section>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block mb-3">
      <span className="block text-xs uppercase tracking-wide text-ink-muted mb-1.5">{label}</span>
      {children}
    </label>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-sm flex gap-3 py-1">
      <span className="text-ink-muted w-24">{label}</span>
      <span className="break-all">{value}</span>
    </div>
  )
}
