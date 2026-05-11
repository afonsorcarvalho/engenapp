'use client'

import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import { useTheme } from 'next-themes'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Settings, LogOut, Moon, Sun, User as UserIcon } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'

export function UserMenu() {
  const router = useRouter()
  const { username, baseUrl, logout } = useAuthStore()
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  useEffect(() => setMounted(true), [])

  const initial = (username || '?').slice(0, 1).toUpperCase()
  const isDark = mounted && theme === 'dark'

  async function doLogout() {
    await logout()
    router.replace('/login')
  }

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button
          className="w-9 h-9 rounded-full bg-accent text-white grid place-items-center font-semibold text-sm hover:bg-accent-soft transition shrink-0"
          aria-label="Menu do usuário"
        >
          {initial}
        </button>
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          sideOffset={8}
          className="z-50 w-64 rounded-xl border border-line bg-bg-soft shadow-xl p-1 text-sm"
        >
          <div className="px-3 py-2 border-b border-line">
            <p className="font-medium truncate flex items-center gap-2">
              <UserIcon size={14} className="text-ink-muted" /> {username || 'Usuário'}
            </p>
            <p className="text-[11px] text-ink-dim truncate mt-0.5">{baseUrl}</p>
          </div>

          <DropdownMenu.Item
            onSelect={() => setTheme(isDark ? 'light' : 'dark')}
            className="flex items-center gap-2 px-3 py-2 rounded-md cursor-pointer outline-none data-[highlighted]:bg-bg-muted"
          >
            {isDark ? <Sun size={14} /> : <Moon size={14} />}
            <span>{isDark ? 'Modo claro' : 'Modo escuro'}</span>
          </DropdownMenu.Item>

          <DropdownMenu.Item
            onSelect={() => router.push('/settings')}
            className="flex items-center gap-2 px-3 py-2 rounded-md cursor-pointer outline-none data-[highlighted]:bg-bg-muted"
          >
            <Settings size={14} />
            <span>Configurações</span>
          </DropdownMenu.Item>

          <DropdownMenu.Separator className="h-px bg-line my-1" />

          <DropdownMenu.Item
            onSelect={doLogout}
            className="flex items-center gap-2 px-3 py-2 rounded-md cursor-pointer outline-none text-red-400 data-[highlighted]:bg-red-500/10"
          >
            <LogOut size={14} />
            <span>Sair</span>
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  )
}
