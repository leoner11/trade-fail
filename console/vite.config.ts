import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/spine': {
        target: 'http://localhost:8101',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/spine/, ''),
      },
      '/glue': {
        target: 'http://localhost:8102',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/glue/, ''),
      },
    },
  },
})
