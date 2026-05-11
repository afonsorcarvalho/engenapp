import { contextBridge, ipcRenderer } from 'electron'

const api = {
  app: {
    getVersion: () => ipcRenderer.invoke('app:version') as Promise<string>,
    openExternal: (url: string) => ipcRenderer.invoke('app:openExternal', url),
    notify: (title: string, body?: string) =>
      ipcRenderer.invoke('app:notify', { title, body }),
    pickFolder: () => ipcRenderer.invoke('app:pickFolder') as Promise<string | null>,
  },
  credentials: {
    save: (key: string, value: string) =>
      ipcRenderer.invoke('credentials:save', { key, value }) as Promise<void>,
    load: (key: string) =>
      ipcRenderer.invoke('credentials:load', { key }) as Promise<string | null>,
    clear: (key: string) =>
      ipcRenderer.invoke('credentials:clear', { key }) as Promise<void>,
  },
  watcher: {
    start: (folder: string) =>
      ipcRenderer.invoke('watcher:start', { folder }) as Promise<{ ok: boolean }>,
    stop: () => ipcRenderer.invoke('watcher:stop') as Promise<void>,
    status: () =>
      ipcRenderer.invoke('watcher:status') as Promise<{ running: boolean; folder?: string }>,
    onFileDetected: (cb: (file: { path: string; name: string; size: number }) => void) => {
      const listener = (_e: unknown, payload: { path: string; name: string; size: number }) => cb(payload)
      ipcRenderer.on('watcher:file-detected', listener as any)
      return () => ipcRenderer.removeListener('watcher:file-detected', listener as any)
    },
  },
}

contextBridge.exposeInMainWorld('ecm', api)

export type EcmApi = typeof api
