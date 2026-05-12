'use client'

import { useMemo, useState } from 'react'
import { ChevronRight, Folder, FolderOpen, FolderPlus, Pencil, Trash2 } from 'lucide-react'
import clsx from 'clsx'
import type { EcmDirectory } from '@/lib/ecm-api'

interface Props {
  directories: EcmDirectory[]
  currentId: number | null
  onSelect: (id: number | null) => void
  onNewFolder?: (parentId: number | null) => void
  onRename?: (dir: EcmDirectory) => void
  onDelete?: (dir: EcmDirectory) => void
  /** chamado quando arquivo é solto numa pasta (id, targetDirId) */
  onDropFile?: (fileId: number, targetDirId: number) => void
  /** chamado quando pasta é solta noutra (sourceId, targetDirId) */
  onDropDirectory?: (sourceId: number, targetDirId: number) => void
}

interface TreeNode extends EcmDirectory {
  children: TreeNode[]
}

function buildTree(dirs: EcmDirectory[]): TreeNode[] {
  const map = new Map<number, TreeNode>()
  dirs.forEach((d) => map.set(d.id, { ...d, children: [] }))
  const roots: TreeNode[] = []
  map.forEach((node) => {
    const parentId = node.parent_id ? node.parent_id[0] : null
    if (parentId && map.has(parentId)) map.get(parentId)!.children.push(node)
    else roots.push(node)
  })
  const sort = (nodes: TreeNode[]) => {
    nodes.sort((a, b) => a.name.localeCompare(b.name))
    nodes.forEach((n) => sort(n.children))
  }
  sort(roots)
  return roots
}

export function FolderTree({
  directories, currentId, onSelect, onNewFolder, onRename, onDelete,
  onDropFile, onDropDirectory,
}: Props) {
  const tree = useMemo(() => buildTree(directories), [directories])

  // mapa id → set de descendentes (pra impedir drop em descendente próprio)
  const descendantsOf = useMemo(() => {
    const m = new Map<number, Set<number>>()
    const walk = (n: TreeNode, acc: Set<number>) => {
      acc.add(n.id)
      n.children.forEach((c) => walk(c, acc))
    }
    function collect(roots: TreeNode[]) {
      roots.forEach((root) => {
        const s = new Set<number>()
        walk(root, s)
        m.set(root.id, s)
        collect(root.children)
      })
    }
    collect(tree)
    return m
  }, [tree])

  return (
    <div className="text-sm">
      <div className="group flex items-center pr-1 rounded-md hover:bg-bg-muted">
        <button
          onClick={() => onSelect(null)}
          className={clsx(
            'flex-1 text-left px-2 py-1.5 rounded-md flex items-center gap-2',
            currentId === null && 'text-accent',
          )}
        >
          <Folder size={16} />
          <span>Todos</span>
        </button>
        {onNewFolder && (
          <button
            onClick={(e) => { e.stopPropagation(); onNewFolder(null) }}
            className="opacity-0 group-hover:opacity-100 transition p-1 rounded text-ink-dim hover:text-accent"
            title="Nova pasta raiz"
          >
            <FolderPlus size={14} />
          </button>
        )}
      </div>
      {tree.map((n) => (
        <TreeRow
          key={n.id} node={n} depth={0}
          currentId={currentId} onSelect={onSelect}
          onNewFolder={onNewFolder} onRename={onRename} onDelete={onDelete}
          onDropFile={onDropFile} onDropDirectory={onDropDirectory}
          descendantsOf={descendantsOf}
        />
      ))}
    </div>
  )
}

function TreeRow({
  node, depth, currentId, onSelect, onNewFolder, onRename, onDelete,
  onDropFile, onDropDirectory, descendantsOf,
}: {
  node: TreeNode; depth: number;
  currentId: number | null;
  onSelect: (id: number) => void;
  onNewFolder?: (parentId: number | null) => void;
  onRename?: (dir: EcmDirectory) => void;
  onDelete?: (dir: EcmDirectory) => void;
  onDropFile?: (fileId: number, targetDirId: number) => void;
  onDropDirectory?: (sourceId: number, targetDirId: number) => void;
  descendantsOf?: Map<number, Set<number>>;
}) {
  const [open, setOpen] = useState(depth === 0)
  const [dragOver, setDragOver] = useState(false)
  const hasChildren = node.children.length > 0
  const active = currentId === node.id

  const draggable = !!onDropDirectory
  const acceptDrop = !!(onDropFile || onDropDirectory)

  function handleDragStart(e: React.DragEvent) {
    if (!draggable) return
    e.dataTransfer.setData('application/x-ecm-dir', String(node.id))
    e.dataTransfer.effectAllowed = 'move'
  }

  function handleDragOver(e: React.DragEvent) {
    if (!acceptDrop) return
    const hasFile = e.dataTransfer.types.includes('application/x-ecm-file')
    const hasDir = e.dataTransfer.types.includes('application/x-ecm-dir')
    if (!hasFile && !hasDir) return
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    if (!dragOver) setDragOver(true)
  }

  function handleDragLeave() {
    if (dragOver) setDragOver(false)
  }

  function handleDrop(e: React.DragEvent) {
    setDragOver(false)
    const fileData = e.dataTransfer.getData('application/x-ecm-file')
    if (fileData && onDropFile) {
      e.preventDefault()
      const fid = Number(fileData)
      if (Number.isFinite(fid)) onDropFile(fid, node.id)
      return
    }
    const dirData = e.dataTransfer.getData('application/x-ecm-dir')
    if (dirData && onDropDirectory) {
      e.preventDefault()
      const sid = Number(dirData)
      if (!Number.isFinite(sid) || sid === node.id) return
      // bloqueia drop em descendente próprio (ciclo)
      const descs = descendantsOf?.get(sid)
      if (descs && descs.has(node.id)) return
      onDropDirectory(sid, node.id)
      return
    }
  }

  return (
    <div>
      <div
        draggable={draggable}
        onDragStart={handleDragStart}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={clsx(
          'group flex items-center gap-1 py-1 pr-1 rounded-md hover:bg-bg-muted cursor-pointer',
          active && 'bg-bg-muted text-accent',
          dragOver && 'ring-2 ring-accent/60 bg-accent/10',
        )}
        style={{ paddingLeft: 8 + depth * 14 }}
      >
        <button
          onClick={(e) => { e.stopPropagation(); setOpen((o) => !o) }}
          className={clsx(
            'w-5 h-5 grid place-items-center text-ink-dim hover:text-ink',
            !hasChildren && 'invisible',
          )}
        >
          <ChevronRight size={14} className={clsx('transition-transform', open && 'rotate-90')} />
        </button>
        <button
          onClick={() => onSelect(node.id)}
          onDoubleClick={() => onRename?.(node)}
          className="flex-1 text-left flex items-center gap-2 min-w-0"
        >
          {open && hasChildren ? <FolderOpen size={15} /> : <Folder size={15} />}
          <span className="truncate">{node.name}</span>
          {typeof node.count_files === 'number' && node.count_files > 0 && (
            <span className="ml-auto text-[10px] text-ink-dim">{node.count_files}</span>
          )}
        </button>
        {onRename && (
          <button
            onClick={(e) => { e.stopPropagation(); onRename(node) }}
            className="opacity-0 group-hover:opacity-100 transition p-1 rounded text-ink-dim hover:text-accent"
            title="Renomear (F2)"
          >
            <Pencil size={12} />
          </button>
        )}
        {onNewFolder && (
          <button
            onClick={(e) => { e.stopPropagation(); onNewFolder(node.id) }}
            className="opacity-0 group-hover:opacity-100 transition p-1 rounded text-ink-dim hover:text-accent"
            title="Nova subpasta"
          >
            <FolderPlus size={13} />
          </button>
        )}
        {onDelete && (
          <button
            onClick={(e) => { e.stopPropagation(); onDelete(node) }}
            className="opacity-0 group-hover:opacity-100 transition p-1 rounded text-ink-dim hover:text-red-400"
            title="Excluir pasta (Shift+Del)"
          >
            <Trash2 size={12} />
          </button>
        )}
      </div>
      {open && hasChildren && (
        <div>
          {node.children.map((c) => (
            <TreeRow
              key={c.id} node={c} depth={depth + 1}
              currentId={currentId} onSelect={onSelect}
              onNewFolder={onNewFolder} onRename={onRename} onDelete={onDelete}
              onDropFile={onDropFile} onDropDirectory={onDropDirectory}
              descendantsOf={descendantsOf}
            />
          ))}
        </div>
      )}
    </div>
  )
}
