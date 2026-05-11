import { odoo } from './odoo-client'

function uuidv4(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return (crypto as any).randomUUID()
  }
  // fallback
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

export interface EcmDirectory {
  id: number
  name: string
  parent_id: [number, string] | false
  is_root_directory: boolean
  count_files: number
}

export interface EcmFileSummary {
  id: number
  name: string
  display_name?: string
  mimetype?: string
  size?: number
  create_date?: string
  write_date?: string
  directory_id: [number, string] | false
  document_type_id?: [number, string] | false
  confidentiality?: 'public' | 'internal' | 'restricted' | 'confidential'
  expiration_date?: string | false
  expiration_status?: string
  ocr_state?: string
  approval_state?: string
  can_download?: boolean
}

export interface EcmDocumentType {
  id: number
  name: string
  code: string
  default_confidentiality: string
  requires_approval: boolean
  ocr_enabled: boolean
}

const FILE_FIELDS: (keyof EcmFileSummary)[] = [
  'id', 'name', 'mimetype', 'create_date', 'write_date', 'directory_id',
  'document_type_id', 'confidentiality', 'expiration_date', 'expiration_status',
  'ocr_state', 'approval_state', 'can_download',
]

export const ecmApi = {
  // ---- Directories ----
  async listDirectories(): Promise<EcmDirectory[]> {
    return odoo.callKw<EcmDirectory[]>('dms.directory', 'search_read', [
      [],
      ['id', 'name', 'parent_id', 'is_root_directory', 'count_files'],
    ], { order: 'name' })
  },

  async createDirectory(name: string, parent_id?: number): Promise<number> {
    const vals: Record<string, unknown> = { name }
    if (parent_id) vals.parent_id = parent_id
    else vals.is_root_directory = true
    const id = await odoo.callKw<number>('dms.directory', 'create', [vals])
    return id
  },

  // ---- Files ----
  async listFiles(directoryId?: number, limit = 200): Promise<EcmFileSummary[]> {
    const domain: unknown[] = []
    if (directoryId) domain.push(['directory_id', '=', directoryId])
    return odoo.callKw<EcmFileSummary[]>('dms.file', 'search_read', [
      domain, FILE_FIELDS as unknown as string[],
    ], { limit, order: 'write_date desc' })
  },

  async searchFiles(
    query: string,
    opts: { limit?: number; withOcrText?: boolean } = {},
  ): Promise<(EcmFileSummary & { ocr_text?: string })[]> {
    const limit = opts.limit ?? 50
    // backend já busca name OR ocr_text via _name_search (afr_ecm)
    const ids = await odoo.callKw<[number, string][]>('dms.file', 'name_search', [], {
      name: query, args: [], limit,
    })
    if (!ids.length) return []
    const fields = [...FILE_FIELDS] as string[]
    if (opts.withOcrText) fields.push('ocr_text')
    return odoo.callKw<(EcmFileSummary & { ocr_text?: string })[]>('dms.file', 'read', [
      ids.map((p) => p[0]), fields,
    ])
  },

  async readFile(id: number, fields?: string[]): Promise<EcmFileSummary & { ocr_text?: string }> {
    const f = fields || [...FILE_FIELDS, 'ocr_text']
    const rows = await odoo.callKw<any[]>('dms.file', 'read', [[id], f])
    return rows[0]
  },

  async uploadFile(args: {
    name: string
    directoryId: number
    contentBase64: string
    documentTypeId?: number
  }): Promise<number> {
    const vals: Record<string, unknown> = {
      name: args.name,
      directory_id: args.directoryId,
      content: args.contentBase64,
    }
    if (args.documentTypeId) vals.document_type_id = args.documentTypeId
    return odoo.callKw<number>('dms.file', 'create', [vals])
  },

  fileDownloadUrl(id: number, download = true): string {
    return `${odoo.getBaseUrl()}/web/content?model=dms.file&id=${id}&field=content&download=${download}`
  },

  /** Garante access_token no dms.file e retorna URL pública. */
  async getShareUrl(id: number): Promise<string> {
    const rows = await odoo.callKw<{ access_token: string | false }[]>('dms.file', 'read', [
      [id], ['access_token'],
    ])
    let token = rows[0]?.access_token || ''
    if (!token) {
      token = uuidv4()
      await odoo.callKw('dms.file', 'write', [[id], { access_token: token }])
    }
    const cfg = await odoo.callKw<{ value: string }[]>('ir.config_parameter', 'search_read', [
      [['key', '=', 'web.base.url']], ['value'],
    ], { limit: 1 })
    const base = cfg[0]?.value || odoo.getBaseUrl()
    const info = await odoo.sessionInfo()
    const db = (info as any)?.db || ''
    const dbParam = db ? `?db=${encodeURIComponent(db)}` : ''
    return `${base.replace(/\/+$/, '')}/ecm/share/${id}/${token}${dbParam}`
  },

  // ---- Company ----
  async getCurrentCompany(): Promise<{ id: number; name: string; logo: string | null }> {
    const info = await odoo.sessionInfo()
    const cid = (info as any)?.user_companies?.current_company || (info as any)?.company_id || 1
    const rows = await odoo.callKw<{ id: number; name: string; logo: string | false }[]>(
      'res.company', 'read', [[cid], ['id', 'name', 'logo']],
    )
    const r = rows[0]
    return { id: r.id, name: r.name, logo: r.logo ? (r.logo as string) : null }
  },

  // ---- Document Types ----
  async listDocumentTypes(): Promise<EcmDocumentType[]> {
    return odoo.callKw<EcmDocumentType[]>('afr.ecm.document.type', 'search_read', [
      [['active', '=', true]],
      ['id', 'name', 'code', 'default_confidentiality', 'requires_approval', 'ocr_enabled'],
    ], { order: 'sequence, name' })
  },
}
