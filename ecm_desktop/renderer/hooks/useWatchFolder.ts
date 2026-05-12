'use client'

import { useEffect, useRef } from 'react'
import toast from 'react-hot-toast'
import path from 'path-browserify'
import { getElectron } from '@/lib/electron'
import { useSettingsStore } from '@/store/settingsStore'
import { useAuthStore } from '@/store/authStore'
import { ecmApi } from '@/lib/ecm-api'

/** Registra listener watcher → auto-upload + move/delete pós-upload. */
export function useWatchFolder() {
  const isAuth = useAuthStore((s) => s.isAuthenticated)
  const {
    watchedFolder,
    watchDestinationDirectoryId,
    watchDefaultDocumentTypeId,
    watchAutoStart,
    watchPostAction,
    watchProcessedFolder,
  } = useSettingsStore()

  const inFlight = useRef<Set<string>>(new Set())

  useEffect(() => {
    const el = getElectron()
    if (!el || !isAuth) return

    // auto-start se config marcado e há pasta
    if (watchAutoStart && watchedFolder) {
      el.watcher.status().then((s) => {
        if (!s.running) el.watcher.start(watchedFolder).catch(() => {})
      })
    }

    const off = el.watcher.onFileDetected(async (f) => {
      if (!watchDestinationDirectoryId) {
        toast('Watch folder: defina uma Pasta DMS destino nas Configurações.', { icon: '⚠️' })
        return
      }
      if (inFlight.current.has(f.path)) return
      inFlight.current.add(f.path)
      const tid = toast.loading(`Enviando ${f.name}…`)
      try {
        const base64 = await el.fs.readBase64(f.path)
        await ecmApi.uploadFile({
          name: f.name,
          directoryId: watchDestinationDirectoryId,
          contentBase64: base64,
          documentTypeId: watchDefaultDocumentTypeId || undefined,
        })
        toast.success(`Enviado: ${f.name}`, { id: tid })
        await el.app.notify('ECM: documento enviado', f.name).catch(() => {})

        // pós-upload
        if (watchPostAction === 'delete') {
          await el.fs.unlink(f.path).catch(() => {})
        } else if (watchPostAction === 'move') {
          const dest = watchProcessedFolder ||
            path.join(path.dirname(f.path), 'Processed')
          await el.fs.moveTo(f.path, dest).catch(() => {})
        }
      } catch (e: any) {
        toast.error(`Falha em ${f.name}: ${e?.message || 'erro'}`, { id: tid })
      } finally {
        inFlight.current.delete(f.path)
      }
    })

    return off
  }, [
    isAuth,
    watchedFolder,
    watchDestinationDirectoryId,
    watchDefaultDocumentTypeId,
    watchAutoStart,
    watchPostAction,
    watchProcessedFolder,
  ])
}
