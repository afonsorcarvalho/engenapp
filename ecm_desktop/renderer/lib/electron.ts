// Bridge tipada pro preload contextBridge

export interface EcmElectronApi {
  app: {
    getVersion: () => Promise<string>
    openExternal: (url: string) => Promise<void>
    notify: (title: string, body?: string) => Promise<void>
    pickFolder: () => Promise<string | null>
  }
  credentials: {
    save: (key: string, value: string) => Promise<void>
    load: (key: string) => Promise<string | null>
    clear: (key: string) => Promise<void>
  }
  watcher: {
    start: (folder: string) => Promise<{ ok: boolean }>
    stop: () => Promise<void>
    status: () => Promise<{ running: boolean; folder?: string }>
    onFileDetected: (cb: (f: { path: string; name: string; size: number }) => void) => () => void
  }
}

export function getElectron(): EcmElectronApi | null {
  if (typeof window === 'undefined') return null
  return (window as any).ecm || null
}
