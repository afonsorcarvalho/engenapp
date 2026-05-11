import { create } from 'zustand'

interface EcmState {
  currentDirectoryId: number | null
  selectedFileId: number | null
  setCurrentDirectory(id: number | null): void
  selectFile(id: number | null): void
}

export const useEcmStore = create<EcmState>((set) => ({
  currentDirectoryId: null,
  selectedFileId: null,
  setCurrentDirectory: (id) => set({ currentDirectoryId: id, selectedFileId: null }),
  selectFile: (id) => set({ selectedFileId: id }),
}))
