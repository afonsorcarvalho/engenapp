import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { odoo } from '@/lib/odoo-client'
import { getElectron } from '@/lib/electron'

interface AuthState {
  baseUrl: string
  db: string
  username: string
  uid: number | null
  isAuthenticated: boolean
  configure(baseUrl: string, db: string): void
  login(login: string, password: string, opts?: { remember?: boolean }): Promise<void>
  logout(): Promise<void>
  restore(): Promise<void>
}

const SECRET_KEY = 'ecm.login.bundle'

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      baseUrl: '',
      db: '',
      username: '',
      uid: null,
      isAuthenticated: false,

      configure(baseUrl, db) {
        odoo.configure(baseUrl)
        set({ baseUrl, db })
      },

      async login(login, password, opts) {
        const { baseUrl, db } = get()
        if (!baseUrl || !db) throw new Error('Configure baseUrl e db antes de logar')
        odoo.configure(baseUrl)
        const r = await odoo.authenticate(db, login, password)
        set({ uid: r.uid, username: r.username || login, isAuthenticated: true })
        if (opts?.remember) {
          const el = getElectron()
          if (el) {
            await el.credentials.save(SECRET_KEY, JSON.stringify({ baseUrl, db, login, password }))
          }
        }
      },

      async logout() {
        try { await odoo.logout() } catch {}
        const el = getElectron()
        if (el) await el.credentials.clear(SECRET_KEY)
        set({ uid: null, username: '', isAuthenticated: false })
      },

      async restore() {
        const el = getElectron()
        if (!el) return
        const raw = await el.credentials.load(SECRET_KEY)
        if (!raw) return
        try {
          const { baseUrl, db, login, password } = JSON.parse(raw)
          odoo.configure(baseUrl)
          set({ baseUrl, db })
          const r = await odoo.authenticate(db, login, password)
          set({ uid: r.uid, username: r.username || login, isAuthenticated: true })
        } catch (e) {
          console.warn('restore credentials failed:', e)
        }
      },
    }),
    {
      name: 'ecm-auth',
      partialize: (s) => ({ baseUrl: s.baseUrl, db: s.db, username: s.username }),
    },
  ),
)
