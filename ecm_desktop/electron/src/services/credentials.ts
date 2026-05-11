import { ipcMain, safeStorage } from 'electron'
import Store from 'electron-store'

interface CredStore { [k: string]: string }

const store = new Store<CredStore>({ name: 'credentials' })

export function registerCredentialsIpc() {
  ipcMain.handle('credentials:save', (_e, { key, value }: { key: string; value: string }) => {
    if (!safeStorage.isEncryptionAvailable()) {
      // Fallback: salva texto puro (apenas dev/Linux sem keyring)
      store.set(key, value)
      return
    }
    const encrypted = safeStorage.encryptString(value).toString('base64')
    store.set(key, encrypted)
  })

  ipcMain.handle('credentials:load', (_e, { key }: { key: string }) => {
    const v = store.get(key)
    if (!v) return null
    if (!safeStorage.isEncryptionAvailable()) return v as string
    try {
      return safeStorage.decryptString(Buffer.from(v as string, 'base64'))
    } catch {
      return null
    }
  })

  ipcMain.handle('credentials:clear', (_e, { key }: { key: string }) => {
    store.delete(key)
  })
}
