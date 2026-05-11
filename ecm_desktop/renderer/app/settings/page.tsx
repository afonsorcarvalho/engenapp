'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/authStore'
import { getElectron } from '@/lib/electron'
import toast from 'react-hot-toast'
import { ArrowLeft, FolderOpen, Power } from 'lucide-react'

export default function SettingsPage() {
  const router = useRouter()
  const { baseUrl, db, username, logout } = useAuthStore()
  const [watchedFolder, setWatchedFolder] = useState<string>('')
  const [watching, setWatching] = useState(false)

  useEffect(() => {
    const el = getElectron()
    if (!el) return
    el.watcher.status().then((s) => {
      setWatching(s.running)
      if (s.folder) setWatchedFolder(s.folder)
    })
  }, [])

  async function pickFolder() {
    const el = getElectron()
    if (!el) return
    const p = await el.app.pickFolder()
    if (p) setWatchedFolder(p)
  }

  async function toggleWatch() {
    const el = getElectron()
    if (!el) return
    if (watching) {
      await el.watcher.stop()
      setWatching(false)
      toast.success('Watch folder desligada')
    } else {
      if (!watchedFolder) { toast.error('Selecione uma pasta'); return }
      await el.watcher.start(watchedFolder)
      setWatching(true)
      toast.success('Watch folder ativa')
    }
  }

  async function doLogout() {
    await logout()
    router.replace('/login')
  }

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
        <p className="text-sm text-ink-muted mb-3">
          Arquivos adicionados a esta pasta são enviados automaticamente para o ECM.
        </p>
        <div className="flex gap-2">
          <input
            value={watchedFolder}
            readOnly
            placeholder="Nenhuma pasta selecionada"
            className="flex-1 px-3 py-2 rounded-lg bg-bg-soft border border-line outline-none text-sm"
          />
          <button onClick={pickFolder} className="px-3 py-2 rounded-lg bg-bg-muted hover:bg-bg text-sm flex items-center gap-1.5">
            <FolderOpen size={14} /> Escolher
          </button>
        </div>
        <button
          onClick={toggleWatch}
          className={`mt-3 px-4 py-2 rounded-lg text-sm font-medium ${
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

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-sm flex gap-3 py-1">
      <span className="text-ink-muted w-24">{label}</span>
      <span className="break-all">{value}</span>
    </div>
  )
}
