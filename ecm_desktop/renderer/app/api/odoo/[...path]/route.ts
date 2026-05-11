// Proxy Odoo para evitar CORS quando rodando no browser (dev / fallback).
// No Electron, OdooClient faz request direto (sem proxy).
// Header X-Odoo-Target indica a base URL alvo.

import { NextRequest, NextResponse } from 'next/server'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

async function proxy(req: NextRequest, ctx: { params: { path: string[] } }) {
  const target = req.headers.get('x-odoo-target')
  if (!target) {
    return NextResponse.json({ error: 'X-Odoo-Target header missing' }, { status: 400 })
  }
  const targetClean = target.replace(/\/+$/, '')
  const upstreamPath = '/' + ctx.params.path.join('/')
  const url = new URL(req.url)
  const upstream = targetClean + upstreamPath + url.search

  const incomingHeaders = new Headers(req.headers)
  // headers que não devem ir pro upstream
  incomingHeaders.delete('host')
  incomingHeaders.delete('x-odoo-target')
  incomingHeaders.delete('connection')

  const init: RequestInit = {
    method: req.method,
    headers: incomingHeaders,
    redirect: 'manual',
    // @ts-ignore — Node fetch precisa duplex pra body streaming
    duplex: 'half',
  }

  if (!['GET', 'HEAD'].includes(req.method)) {
    init.body = await req.text()
  }

  const upstreamRes = await fetch(upstream, init)

  const resHeaders = new Headers()
  upstreamRes.headers.forEach((v, k) => {
    // não repassa hop-by-hop / encoding
    if (['transfer-encoding', 'content-encoding', 'content-length', 'connection'].includes(k.toLowerCase())) return
    resHeaders.set(k, v)
  })

  const body = await upstreamRes.arrayBuffer()
  return new NextResponse(body, { status: upstreamRes.status, headers: resHeaders })
}

export const GET = proxy
export const POST = proxy
export const PUT = proxy
export const DELETE = proxy
export const PATCH = proxy
