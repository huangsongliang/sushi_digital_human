import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },
  build: {
    // 启用代码分割
    rollupOptions: {
      output: {
        // 手动分包
        manualChunks: {
          'vendor': ['vue', 'vue-router', 'pinia', 'axios'],
          'editor': ['@vueuse/core']
        }
      }
    },
    // 启用压缩（esbuild 内置，无需额外依赖）
    minify: 'esbuild',
    esbuild: {
      drop: ['console', 'debugger'],
    }
  }
})
