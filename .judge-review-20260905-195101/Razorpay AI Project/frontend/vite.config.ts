import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/copilot': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        bypass: (req) => {
          if (req.headers.accept?.includes('application/json')) return undefined;
          const isDocNav = req.headers['sec-fetch-dest'] === 'document' || req.headers['sec-fetch-mode'] === 'navigate';
          if (isDocNav || (req.headers.accept?.includes('text/html') && !req.headers.accept?.includes('application/json'))) {
            return '/index.html';
          }
        },
      },
      '/voice': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        bypass: (req) => {
          if (req.headers.accept?.includes('application/json')) return undefined;
          const isDocNav = req.headers['sec-fetch-dest'] === 'document' || req.headers['sec-fetch-mode'] === 'navigate';
          if (isDocNav || (req.headers.accept?.includes('text/html') && !req.headers.accept?.includes('application/json'))) {
            return '/index.html';
          }
        },
      },
      '/cases': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        bypass: (req) => {
          if (req.headers.accept?.includes('application/json')) return undefined;
          const isDocNav = req.headers['sec-fetch-dest'] === 'document' || req.headers['sec-fetch-mode'] === 'navigate';
          if (isDocNav || (req.headers.accept?.includes('text/html') && !req.headers.accept?.includes('application/json'))) {
            return '/index.html';
          }
        },
      },
      '/admin': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/webhooks': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/metrics': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/demo': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
