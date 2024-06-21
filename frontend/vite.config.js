import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  // need to define the bleow to make sure the server uses the right port and host.
  server: {
    port: 5173,
    host: '0.0.0.0'
  }
})
