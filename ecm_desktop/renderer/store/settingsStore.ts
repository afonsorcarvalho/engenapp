import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface SettingsState {
  // Watch folder
  watchedFolder: string
  watchDestinationDirectoryId: number | null
  watchDestinationDirectoryName: string
  watchDefaultDocumentTypeId: number | null
  watchAutoStart: boolean
  watchPostAction: 'move' | 'delete' | 'keep'
  watchProcessedFolder: string

  set: (patch: Partial<SettingsState>) => void
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      watchedFolder: '',
      watchDestinationDirectoryId: null,
      watchDestinationDirectoryName: '',
      watchDefaultDocumentTypeId: null,
      watchAutoStart: false,
      watchPostAction: 'move',
      watchProcessedFolder: '',
      set: (patch) => set(patch),
    }),
    {
      name: 'ecm-settings',
      partialize: (s) => ({
        watchedFolder: s.watchedFolder,
        watchDestinationDirectoryId: s.watchDestinationDirectoryId,
        watchDestinationDirectoryName: s.watchDestinationDirectoryName,
        watchDefaultDocumentTypeId: s.watchDefaultDocumentTypeId,
        watchAutoStart: s.watchAutoStart,
        watchPostAction: s.watchPostAction,
        watchProcessedFolder: s.watchProcessedFolder,
      }),
    },
  ),
)
