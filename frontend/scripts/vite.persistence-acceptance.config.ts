import { resolve } from 'node:path'
import { defineConfig } from 'vite'

export default defineConfig({
  resolve: { alias: { '@': resolve(import.meta.dirname, '../src') } },
  build: {
    outDir: '.c21-persistence-dist',
    emptyOutDir: true,
    rollupOptions: {
      input: resolve(import.meta.dirname, 'browser-persistence-harness.html'),
      output: {
        entryFileNames: 'browser-persistence-acceptance.js',
        chunkFileNames: 'chunks/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash][extname]',
      },
    },
  },
})
