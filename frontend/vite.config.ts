import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  server: {
    // Dev only: reuse the running `web` container for the API.
    proxy: { '/api': 'http://localhost:8080' },
  },
  // Fixed timezone so date tests do not depend on the machine running them.
  test: { env: { TZ: 'Europe/Warsaw' } },
})
