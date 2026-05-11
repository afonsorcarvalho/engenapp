import { app, BrowserWindow, ipcMain, shell, dialog, Notification, Tray, Menu, nativeImage } from 'electron'
import path from 'node:path'
import { registerWatcherIpc } from './services/watcher'
import { registerCredentialsIpc } from './services/credentials'

const isDev = process.env.NODE_ENV === 'development'
const RENDERER_DEV_URL = 'http://localhost:3000'

let mainWindow: BrowserWindow | null = null
let tray: Tray | null = null

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 1024,
    minHeight: 600,
    backgroundColor: '#0b0d12',
    show: false,
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })

  if (isDev) {
    mainWindow.loadURL(RENDERER_DEV_URL)
    mainWindow.webContents.openDevTools({ mode: 'detach' })
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'renderer', 'out', 'index.html'))
  }

  mainWindow.once('ready-to-show', () => mainWindow?.show())

  mainWindow.on('closed', () => { mainWindow = null })

  // links externos abrem no browser default
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })
}

function createTray() {
  const iconPath = path.join(__dirname, '..', 'resources', 'tray-icon.png')
  try {
    const icon = nativeImage.createFromPath(iconPath)
    tray = new Tray(icon.isEmpty() ? nativeImage.createEmpty() : icon)
  } catch {
    tray = new Tray(nativeImage.createEmpty())
  }
  tray.setToolTip('ECM Desktop')
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: 'Abrir', click: () => mainWindow?.show() },
    { type: 'separator' },
    { label: 'Sair', click: () => { app.quit() } },
  ]))
  tray.on('click', () => mainWindow?.show())
}

app.whenReady().then(() => {
  registerCredentialsIpc()
  registerWatcherIpc(() => mainWindow)

  ipcMain.handle('app:version', () => app.getVersion())
  ipcMain.handle('app:openExternal', async (_e, url: string) => {
    await shell.openExternal(url)
  })
  ipcMain.handle('app:notify', async (_e, opts: { title: string; body?: string }) => {
    new Notification({ title: opts.title, body: opts.body }).show()
  })
  ipcMain.handle('app:pickFolder', async () => {
    const r = await dialog.showOpenDialog({ properties: ['openDirectory', 'createDirectory'] })
    return r.canceled ? null : r.filePaths[0]
  })

  createMainWindow()
  createTray()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createMainWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
