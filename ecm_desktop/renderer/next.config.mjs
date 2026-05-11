/** @type {import('next').NextConfig} */
// ELECTRON_EXPORT=1 => build estático (sem API routes) para empacotar no Electron prod.
// Sem essa flag, Next.js roda em modo SSR/dev normal com /api/odoo proxy.
const isElectronExport = process.env.ELECTRON_EXPORT === '1'

const nextConfig = {
  ...(isElectronExport ? { output: 'export', trailingSlash: true, assetPrefix: './' } : {}),
  images: { unoptimized: true },
}

export default nextConfig
