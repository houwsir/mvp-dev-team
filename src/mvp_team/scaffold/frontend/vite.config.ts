import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 说明：
// * 构建脚本是 `tsc --noEmit && vite build`，tsconfig 只检查 src，本文件不参与类型检查；
// * 开发态把 /api 代理到本地后端，前端因此始终使用同源相对路径，无需处理 CORS。
export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
})
