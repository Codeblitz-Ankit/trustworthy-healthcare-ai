import { useEffect, useState } from 'react'
import { Moon, Sun } from 'lucide-react'

function ThemeToggle() {
  const [dark, setDark] = useState(() => {
    try {
      return window.localStorage.getItem('clinical-verifier-theme') !== 'light'
    } catch {
      return true
    }
  })

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    try {
      window.localStorage.setItem('clinical-verifier-theme', dark ? 'dark' : 'light')
    } catch {
      // Theme switching still works when storage is unavailable.
    }
  }, [dark])

  return (
    <button
      type="button"
      onClick={() => setDark((current) => !current)}
      aria-label={`Switch to ${dark ? 'light' : 'dark'} mode`}
      title={`Switch to ${dark ? 'light' : 'dark'} mode`}
      className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-clinical-green dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800"
    >
      {dark ? <Sun size={17} aria-hidden="true" /> : <Moon size={17} aria-hidden="true" />}
    </button>
  )
}

export default ThemeToggle
