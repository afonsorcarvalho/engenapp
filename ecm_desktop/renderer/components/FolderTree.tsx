'use client'

import { useMemo, useState } from 'react'
import { ChevronRight, Folder, FolderOpen } from 'lucide-react'
import clsx from 'clsx'
import type { EcmDirectory } from '@/lib/ecm-api'

interface Props {
  directories: EcmDirectory[]
  currentId: number | null
  onSelect: (id: number | null) => void
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

export function FolderTree({ directories, currentId, onSelect }: Props) {
  const tree = useMemo(() => buildTree(directories), [directories])

  return (
    <div className="text-sm">
      <button
        onClick={() => onSelect(null)}
        className={clsx(
          'w-full text-left px-2 py-1.5 rounded-md flex items-center gap-2 hover:bg-bg-muted',
          currentId === null && 'bg-bg-muted text-accent',
        )}
      >
        <Folder size={16} />
        <span>Todos</span>
      </button>
      {tree.map((n) => (
        <TreeRow key={n.id} node={n} depth={0} currentId={currentId} onSelect={onSelect} />
      ))}
    </div>
  )
}

function TreeRow({
  node, depth, currentId, onSelect,
}: { node: TreeNode; depth: number; currentId: number | null; onSelect: (id: number) => void }) {
  const [open, setOpen] = useState(depth === 0)
  const hasChildren = node.children.length > 0
  const active = currentId === node.id

  return (
    <div>
      <div
        className={clsx(
          'group flex items-center gap-1 py-1 pr-2 rounded-md hover:bg-bg-muted cursor-pointer',
          active && 'bg-bg-muted text-accent',
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
          className="flex-1 text-left flex items-center gap-2 min-w-0"
        >
          {open && hasChildren ? <FolderOpen size={15} /> : <Folder size={15} />}
          <span className="truncate">{node.name}</span>
          {typeof node.count_files === 'number' && node.count_files > 0 && (
            <span className="ml-auto text-[10px] text-ink-dim">{node.count_files}</span>
          )}
        </button>
      </div>
      {open && hasChildren && (
        <div>
          {node.children.map((c) => (
            <TreeRow key={c.id} node={c} depth={depth + 1} currentId={currentId} onSelect={onSelect} />
          ))}
        </div>
      )}
    </div>
  )
}
