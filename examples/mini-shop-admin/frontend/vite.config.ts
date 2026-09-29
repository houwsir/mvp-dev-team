import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 本项目刻意保持「零额外依赖」：不引入任何 UI 库 / 状态管理 / 测试框架，
// 因此这里只保留 Vite 自身的配置，不写 `test`（那是 Vitest 的字段，
// 在 vite 的 UserConfig 类型里不存在，`tsc -b` 会直接报错）。
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
