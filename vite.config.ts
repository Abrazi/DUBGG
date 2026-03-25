import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: '/',
  build: {
    outDir: 'dist',          // PowerShell script renames this to frontend_dist/
    emptyOutDir: true,
  },
  server: {
    port: 3000,
    proxy: {
      // Forward all API calls to the backend running on :8500
      '/generators': 'http://localhost:8500',
      '/loadbanks':  'http://localhost:8500',
      '/switchgears': 'http://localhost:8500',
      '/admin':      'http://localhost:8500',
    },
  },
});
