import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      '/webhooks': 'http://localhost:8000',
      '/cases': 'http://localhost:8000',
      '/metrics': 'http://localhost:8000',
      '/demo': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
});
