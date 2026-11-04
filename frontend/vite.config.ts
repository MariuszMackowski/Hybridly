import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    // Dev only: reuse the running `web` container for the API.
    proxy: { '/api': 'http://localhost:8080' },
  },
})
