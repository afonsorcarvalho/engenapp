'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/authStore'
import toast from 'react-hot-toast'
import { LockKeyhole } from 'lucide-react'

export default function LoginPage() {
  const router = useRouter()
  const { configure, login } = useAuthStore()
  const [baseUrl, setBaseUrl] = useState('http://localhost:8083')
  const [db, setDb] = useState('odoo_ecm_test')
  const [user, setUser] = useState('admin')
  const [pass, setPass] = useState('')
  const [remember, setRemember] = useState(true)
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    try {
      configure(baseUrl, db)
      await login(user, pass, { remember })
      toast.success('Conectado')
      router.push('/')
    } catch (e: any) {
      toast.error(e?.message || 'Falha no login')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen grid place-items-center px-6">
      <form onSubmit={onSubmit} className="glass w-full max-w-md p-8 rounded-2xl space-y-5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-accent grid place-items-center"><LockKeyhole size={20} /></div>
          <div>
            <h1 className="text-xl font-semibold">AFR ECM Desktop</h1>
            <p className="text-sm text-ink-muted">Entrar na sua instância</p>
          </div>
        </div>

        <div className="space-y-3">
          <Field label="URL do servidor" value={baseUrl} onChange={setBaseUrl} placeholder="http://localhost:8083" />
          <Field label="Banco de dados" value={db} onChange={setDb} placeholder="odoo_ecm_test" />
          <Field label="Usuário" value={user} onChange={setUser} placeholder="admin" />
          <Field label="Senha" value={pass} onChange={setPass} type="password" />
          <label className="flex items-center gap-2 text-sm text-ink-muted select-none">
            <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
            Lembrar credenciais neste PC
          </label>
        </div>

        <button
          type="submit"
          disabled={busy || !pass}
          className="w-full py-2.5 rounded-xl bg-accent hover:bg-accent-soft transition disabled:opacity-50 font-medium"
        >
          {busy ? 'Conectando…' : 'Entrar'}
        </button>
      </form>
    </div>
  )
}

function Field({
  label, value, onChange, type = 'text', placeholder,
}: { label: string; value: string; onChange: (v: string) => void; type?: string; placeholder?: string }) {
  return (
    <label className="block">
      <span className="block text-xs uppercase tracking-wide text-ink-muted mb-1">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full px-3 py-2 rounded-lg bg-bg-soft border border-line outline-none focus:border-accent transition"
      />
    </label>
  )
}
