import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      '/copilot': 'http://127.0.0.1:8000',
      '/voice': 'http://127.0.0.1:8000',
      '/admin': 'http://127.0.0.1:8000',
      '/webhooks': 'http://127.0.0.1:8000',
      '/cases': 'http://127.0.0.1:8000',
      '/metrics': 'http://127.0.0.1:8000',
      '/demo': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
    },
  },
});

