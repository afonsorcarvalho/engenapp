# AFR ECM Desktop

Cliente desktop Electron + Next.js para o afr_ecm (Odoo 16).

## Stack
- Electron 31, electron-builder (NSIS Windows)
- Next.js 14 (App Router, static export), TypeScript, Tailwind, Radix UI
- Zustand (state), React Query (server cache)
- chokidar (watch folder), safeStorage (credenciais criptografadas)

## Dev

```bash
cd renderer && npm install
cd .. && npm install
npm run dev
```

Isto sobe Next.js em `:3000` e Electron aponta pra ele.

## Build .exe

```bash
npm run dist
# resultado em release/AFR ECM Desktop-x.y.z-setup.exe
```

## Estrutura

```
ecm_desktop/
├── electron/        # Electron main (Node)
├── renderer/        # Next.js (UI)
├── resources/       # ícones, assets do app
├── electron-builder.yml
└── package.json
```

## Login

URL Odoo, banco, usuário, senha. "Lembrar" criptografa via `safeStorage` (Win DPAPI / macOS Keychain / Linux libsecret).

## Roadmap

- [x] F4.1.0 Setup base + login
- [ ] F4.1.1 Browser + upload (drag-drop + wizard classificação)
- [ ] F4.1.2 Busca + preview (PDF inline + OCR sidebar)
- [ ] F4.1.3 Watch folder + webcam
- [ ] F4.1.4 Notif OS + tray + auto-update
- [ ] F4.1.5 Polish + build .exe
