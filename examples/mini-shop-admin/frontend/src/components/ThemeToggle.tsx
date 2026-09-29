import { useTheme } from '../hooks/useTheme'

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme()
  const dark = theme === 'dark'

  return (
    <button
      className="icon-button"
      type="button"
      onClick={toggleTheme}
      aria-label={dark ? '切换到浅色主题' : '切换到深色主题'}
      title={dark ? '切换到浅色主题' : '切换到深色主题'}
    >
      <span aria-hidden="true">{dark ? '☀' : '☾'}</span>
    </button>
  )
}
