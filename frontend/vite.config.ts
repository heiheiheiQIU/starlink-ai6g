import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 开发与预览共用：把 /runs 请求转发到本机实验服务，规避浏览器跨域限制。
// 生产/换机验收时后端若加了 CORS，可改用 VITE_API_BASE_URL 直连。
const backendProxy = {
  '/runs': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
  },
}

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: backendProxy,
  },
  preview: {
    proxy: backendProxy,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
    css: true,
  },
})
