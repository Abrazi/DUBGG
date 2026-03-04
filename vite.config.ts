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
  },
});
