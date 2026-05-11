'use client'

import { useCallback, useRef, useState } from 'react'
import { ecmApi } from '@/lib/ecm-api'

export type UploadStatus = 'queued' | 'uploading' | 'done' | 'failed'

export interface UploadJob {
  id: string
  file: File
  name: string
  directoryId: number
  documentTypeId?: number
  tagIds?: number[]
  status: UploadStatus
  progress: number
  serverId?: number
  error?: string
}

const MAX_PARALLEL = 4

function uid() { return Math.random().toString(36).slice(2, 10) }

function readBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onerror = () => reject(reader.error)
    reader.onload = () => {
      const r = reader.result as string
      const b64 = r.includes(',') ? r.split(',')[1] : r
      resolve(b64)
    }
    reader.readAsDataURL(file)
  })
}

export function useUploadQueue() {
  const [jobs, setJobs] = useState<UploadJob[]>([])
  const jobsRef = useRef<UploadJob[]>([])
  const runningRef = useRef(0)

  // mantém ref atualizada
  jobsRef.current = jobs

  const updateJob = useCallback((id: string, patch: Partial<UploadJob>) => {
    setJobs((prev) => prev.map((j) => (j.id === id ? { ...j, ...patch } : j)))
  }, [])

  const runJob = useCallback(async (job: UploadJob) => {
    runningRef.current++
    updateJob(job.id, { status: 'uploading', progress: 5 })
    try {
      const contentBase64 = await readBase64(job.file)
      updateJob(job.id, { progress: 60 })
      const serverId = await ecmApi.uploadFile({
        name: job.name,
        directoryId: job.directoryId,
        contentBase64,
        documentTypeId: job.documentTypeId,
        tagIds: job.tagIds,
      })
      updateJob(job.id, { status: 'done', progress: 100, serverId })
    } catch (e: any) {
      updateJob(job.id, { status: 'failed', error: e?.message || 'Falha' })
    } finally {
      runningRef.current--
      // dispara próximo da fila
      setTimeout(tick, 0)
    }
  }, [updateJob])

  const tick = useCallback(() => {
    while (runningRef.current < MAX_PARALLEL) {
      const next = jobsRef.current.find((j) => j.status === 'queued')
      if (!next) break
      // marca como uploading imediatamente pra evitar dupla pega
      jobsRef.current = jobsRef.current.map((j) =>
        j.id === next.id ? { ...j, status: 'uploading' as UploadStatus } : j,
      )
      runJob(next)
    }
  }, [runJob])

  const enqueue = useCallback((args: {
    directoryId: number
    tagIds?: number[]
    items: { file: File; documentTypeId?: number; tagIds?: number[] }[]
  }) => {
    const newJobs: UploadJob[] = args.items.map(({ file, documentTypeId, tagIds }) => ({
      id: uid(),
      file,
      name: file.name,
      directoryId: args.directoryId,
      documentTypeId,
      tagIds: tagIds && tagIds.length ? tagIds : args.tagIds,
      status: 'queued',
      progress: 0,
    }))
    setJobs((prev) => {
      const merged = [...prev, ...newJobs]
      jobsRef.current = merged
      return merged
    })
    setTimeout(tick, 0)
    return newJobs.map((j) => j.id)
  }, [tick])

  const remove = useCallback((id: string) => {
    setJobs((prev) => prev.filter((j) => j.id !== id))
  }, [])

  const clearDone = useCallback(() => {
    setJobs((prev) => prev.filter((j) => j.status !== 'done'))
  }, [])

  return { jobs, enqueue, remove, clearDone }
}
