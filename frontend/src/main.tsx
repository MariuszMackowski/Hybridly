import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { setCalendarTimezone } from './features/history/weeks'
import './styles/theme.css'

const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 30_000, retry: 1 } } })

/** Pick up the server's calendar timezone, then render (offline: render with the device timezone). */
async function start() {
  try {
    const health = await fetch('/api/health').then((r) => r.json())
    if (health.timezone) setCalendarTimezone(health.timezone)
  } catch {
    // keep the device timezone
  }
  render()
}

const render = () => createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)

start()
