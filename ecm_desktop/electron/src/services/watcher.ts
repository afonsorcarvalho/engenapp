import { ipcMain, BrowserWindow } from 'electron'
import chokidar, { FSWatcher } from 'chokidar'
import path from 'node:path'
import fs from 'node:fs/promises'

let watcher: FSWatcher | null = null
let watchedFolder: string | null = null

export function registerWatcherIpc(getWindow: () => BrowserWindow | null) {
  ipcMain.handle('watcher:start', async (_e, { folder }: { folder: string }) => {
    await stopWatcher()
    await fs.mkdir(folder, { recursive: true })
    watchedFolder = folder
    watcher = chokidar.watch(folder, {
      ignoreInitial: true,
      depth: 0,
      awaitWriteFinish: { stabilityThreshold: 1500, pollInterval: 200 },
    })
    watcher.on('add', async (filePath: string) => {
      try {
        const stats = await fs.stat(filePath)
        const win = getWindow()
        win?.webContents.send('watcher:file-detected', {
          path: filePath,
          name: path.basename(filePath),
          size: stats.size,
        })
      } catch (err) {
        console.error('watcher add error:', err)
      }
    })
    return { ok: true }
  })

  ipcMain.handle('watcher:stop', async () => stopWatcher())
  ipcMain.handle('watcher:status', () => ({
    running: !!watcher,
    folder: watchedFolder || undefined,
  }))
}

async function stopWatcher() {
  if (watcher) {
    await watcher.close()
    watcher = null
  }
  watchedFolder = null
}
