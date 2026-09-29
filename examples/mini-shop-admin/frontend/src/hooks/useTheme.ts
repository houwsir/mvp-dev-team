import { useEffect, useState } from 'react'

type Theme = 'light' | 'dark'
const storageKey = 'mini-shop-admin-theme'

function initialTheme(): Theme {
  const saved = localStorage.getItem(storageKey)
  if (saved === 'light' || saved === 'dark') return saved
  return window.matchMedia('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light'
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(initialTheme)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem(storageKey, theme)
  }, [theme])

  return {
    theme,
    toggleTheme: () => setTheme((value) => (value === 'light' ? 'dark' : 'light')),
  }
}
