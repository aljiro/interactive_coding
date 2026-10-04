import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// In development the API runs separately (see README "Development"); requests to /api are
// proxied so the browser only ever talks to one origin, exactly as in production.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: process.env.VITE_API_PROXY ?? 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: { outDir: 'dist', sourcemap: false },
});
