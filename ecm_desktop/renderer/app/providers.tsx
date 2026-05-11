'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'
import { Toaster } from 'react-hot-toast'

export function Providers({ children }: { children: React.ReactNode }) {
  const [qc] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false },
        },
      }),
  )
  return (
    <QueryClientProvider client={qc}>
      {children}
      <Toaster position="bottom-right" toastOptions={{ style: { background: '#1a1f2b', color: '#f1f3f8' } }} />
    </QueryClientProvider>
  )
}
