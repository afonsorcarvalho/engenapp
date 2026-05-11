import { odoo } from './odoo-client'

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
  'ocr_state', 'approval_state',
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

  async searchFiles(query: string, limit = 50): Promise<EcmFileSummary[]> {
    // backend já busca name OR ocr_text via _name_search (afr_ecm)
    const ids = await odoo.callKw<[number, string][]>('dms.file', 'name_search', [], {
      name: query, args: [], limit,
    })
    if (!ids.length) return []
    return odoo.callKw<EcmFileSummary[]>('dms.file', 'read', [
      ids.map((p) => p[0]), FILE_FIELDS as unknown as string[],
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

  // ---- Document Types ----
  async listDocumentTypes(): Promise<EcmDocumentType[]> {
    return odoo.callKw<EcmDocumentType[]>('afr.ecm.document.type', 'search_read', [
      [['active', '=', true]],
      ['id', 'name', 'code', 'default_confidentiality', 'requires_approval', 'ocr_enabled'],
    ], { order: 'sequence, name' })
  },
}
