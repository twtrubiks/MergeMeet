import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5173,
    watch: {
      // 使用輪詢模式監視文件變化（適用於 Docker、WSL 等環境）
      // 在正常環境下可能不需要，會增加 CPU 使用率
      // 可透過環境變數 VITE_USE_POLLING=false 關閉
      usePolling: process.env.VITE_USE_POLLING !== 'false',
      interval: 1000
    },
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true
      }
    }
  }
})
