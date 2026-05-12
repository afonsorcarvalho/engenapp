import {
  File as FileGeneric,
  FileText,
  FileSpreadsheet,
  FileImage,
  FileVideo,
  FileAudio,
  FileCode,
  FileArchive,
  Presentation,
  FileType,
  type LucideIcon,
} from 'lucide-react'

export type FileCategory =
  | 'pdf'
  | 'doc'
  | 'sheet'
  | 'slides'
  | 'image'
  | 'video'
  | 'audio'
  | 'archive'
  | 'code'
  | 'text'
  | 'font'
  | 'generic'

export interface FileIconSpec {
  category: FileCategory
  Icon: LucideIcon
  /** classe Tailwind para a cor do ícone */
  colorClass: string
  /** label curto pra UI / a11y */
  label: string
}

/**
 * Tabela mestre. Extensível: adicione novas extensões/mimetypes mapeando para
 * uma `category`. O `category` decide ícone + cor (centralizado).
 */
const CATEGORY_STYLE: Record<FileCategory, Omit<FileIconSpec, 'category'>> = {
  pdf:     { Icon: FileText,        colorClass: 'text-red-400',     label: 'PDF' },
  doc:     { Icon: FileText,        colorClass: 'text-blue-400',    label: 'Documento' },
  sheet:   { Icon: FileSpreadsheet, colorClass: 'text-emerald-400', label: 'Planilha' },
  slides:  { Icon: Presentation,    colorClass: 'text-orange-400',  label: 'Apresentação' },
  image:   { Icon: FileImage,       colorClass: 'text-violet-400',  label: 'Imagem' },
  video:   { Icon: FileVideo,       colorClass: 'text-pink-400',    label: 'Vídeo' },
  audio:   { Icon: FileAudio,       colorClass: 'text-fuchsia-400', label: 'Áudio' },
  archive: { Icon: FileArchive,     colorClass: 'text-amber-400',   label: 'Arquivo' },
  code:    { Icon: FileCode,        colorClass: 'text-cyan-400',    label: 'Código' },
  text:    { Icon: FileText,        colorClass: 'text-ink-muted',   label: 'Texto' },
  font:    { Icon: FileType,        colorClass: 'text-purple-400',  label: 'Fonte' },
  generic: { Icon: FileGeneric,     colorClass: 'text-ink-muted',   label: 'Arquivo' },
}

const EXT_TO_CATEGORY: Record<string, FileCategory> = {
  pdf: 'pdf',

  doc: 'doc', docx: 'doc', odt: 'doc', rtf: 'doc',
  xls: 'sheet', xlsx: 'sheet', ods: 'sheet', csv: 'sheet', tsv: 'sheet',
  ppt: 'slides', pptx: 'slides', odp: 'slides', key: 'slides',

  png: 'image', jpg: 'image', jpeg: 'image', gif: 'image', webp: 'image',
  bmp: 'image', tif: 'image', tiff: 'image', svg: 'image', heic: 'image',
  avif: 'image', ico: 'image',

  mp4: 'video', mov: 'video', webm: 'video', mkv: 'video', avi: 'video',
  wmv: 'video', flv: 'video', m4v: 'video', '3gp': 'video',

  mp3: 'audio', wav: 'audio', ogg: 'audio', flac: 'audio', aac: 'audio',
  m4a: 'audio', opus: 'audio',

  zip: 'archive', rar: 'archive', '7z': 'archive', tar: 'archive', gz: 'archive',
  bz2: 'archive', xz: 'archive',

  js: 'code', mjs: 'code', ts: 'code', tsx: 'code', jsx: 'code', json: 'code',
  py: 'code', rb: 'code', go: 'code', rs: 'code', java: 'code', kt: 'code',
  c: 'code', cpp: 'code', h: 'code', cs: 'code', php: 'code', sh: 'code',
  yml: 'code', yaml: 'code', xml: 'code', html: 'code', css: 'code',
  scss: 'code', sql: 'code',

  txt: 'text', md: 'text', log: 'text',

  ttf: 'font', otf: 'font', woff: 'font', woff2: 'font',
}

const MIME_TO_CATEGORY: { test: (m: string) => boolean; category: FileCategory }[] = [
  { test: (m) => m === 'application/pdf', category: 'pdf' },
  { test: (m) => m.startsWith('image/'), category: 'image' },
  { test: (m) => m.startsWith('video/'), category: 'video' },
  { test: (m) => m.startsWith('audio/'), category: 'audio' },
  { test: (m) => m.startsWith('font/') || m === 'application/font-woff', category: 'font' },
  { test: (m) => m.includes('spreadsheet') || m.includes('excel'), category: 'sheet' },
  { test: (m) => m.includes('presentation') || m.includes('powerpoint'), category: 'slides' },
  { test: (m) => m.includes('word') || m.includes('document'), category: 'doc' },
  { test: (m) => m.includes('zip') || m.includes('compressed') || m.includes('tar'), category: 'archive' },
  { test: (m) => m.startsWith('text/'), category: 'text' },
]

function extOf(name: string | undefined): string | null {
  if (!name) return null
  const idx = name.lastIndexOf('.')
  if (idx < 0 || idx === name.length - 1) return null
  return name.slice(idx + 1).toLowerCase()
}

export function getFileIcon(mimetype?: string, name?: string): FileIconSpec {
  const ext = extOf(name)
  if (ext && EXT_TO_CATEGORY[ext]) {
    const cat = EXT_TO_CATEGORY[ext]
    return { category: cat, ...CATEGORY_STYLE[cat] }
  }
  if (mimetype) {
    for (const rule of MIME_TO_CATEGORY) {
      if (rule.test(mimetype)) {
        return { category: rule.category, ...CATEGORY_STYLE[rule.category] }
      }
    }
  }
  return { category: 'generic', ...CATEGORY_STYLE.generic }
}

export function isImage(mimetype?: string, name?: string): boolean {
  return getFileIcon(mimetype, name).category === 'image'
}
