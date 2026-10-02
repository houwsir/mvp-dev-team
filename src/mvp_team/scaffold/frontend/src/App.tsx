import { Route, Routes } from 'react-router-dom'

/**
 * 应用根组件（骨架兜底版本）。
 * 前端工程师应按 PRD 的页面清单替换本文件，注册真实路由。
 */
export default function App() {
  return (
    <div style={{ padding: 24 }}>
      <h1>MVP 应用骨架已就绪</h1>
      <p>页面组件尚未生成。请按 PRD 补全 src/pages 下的页面并在此注册路由。</p>
      <Routes>
        <Route path="*" element={<p>暂无路由</p>} />
      </Routes>
    </div>
  )
}
