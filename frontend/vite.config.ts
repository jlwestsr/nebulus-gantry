import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    allowedHosts: ['nebulus', 'nebulus.local'],
    proxy: {
      '/api': 'http://172.17.0.1:8000',
    },
  },
})
