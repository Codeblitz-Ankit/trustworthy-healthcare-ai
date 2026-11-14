import { useState } from 'react'
import { ArrowUpRight, CircleAlert, ShieldCheck, Stethoscope, TriangleAlert } from 'lucide-react'
import ResultCard from './ResultCard.jsx'
import SearchBar from './SearchBar.jsx'
import ThemeToggle from './ThemeToggle.jsx'

const API_URL = 'http://127.0.0.1:8000/verify'

function App() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  async function handleVerify(event) {
    event.preventDefault()
    const cleanedQuery = query.trim()
    if (!cleanedQuery || loading) return

    setLoading(true)
    setError('')
    setResult(null)
    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: cleanedQuery }),
      })
      if (!response.ok) {
        const detail = await response.text()
        throw new Error(detail || `Request failed (${response.status})`)
      }
      setResult(await response.json())
    } catch (err) {
      setError(err instanceof TypeError
        ? 'Unable to reach the verification service. Check that the API is running and try again.'
        : err.message || 'Something went wrong while verifying this query.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900 transition-colors dark:bg-zinc-950 dark:text-zinc-100">
      <header className="border-b border-slate-200 bg-white/90 dark:border-zinc-800 dark:bg-zinc-950/90">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <a href="#main" className="flex items-center gap-3 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-clinical-green">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-slate-50 text-clinical-green dark:border-zinc-700 dark:bg-zinc-900">
              <Stethoscope aria-hidden="true" size={20} strokeWidth={1.8} />
            </span>
            <span>
              <span className="block text-sm font-semibold tracking-tight">Clinical AI Verifier</span>
              <span className="hidden text-xs text-slate-500 dark:text-zinc-400 sm:block">Evidence-aware health information</span>
            </span>
          </a>
          <ThemeToggle />
        </div>
      </header>

      <main id="main" className="mx-auto max-w-4xl px-4 pb-16 pt-10 sm:px-6 sm:pt-14 lg:px-8">
        <div className="mb-8 max-w-2xl">
          <div className="mb-3 inline-flex items-center gap-2 rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-600 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300">
            <ShieldCheck size={14} className="text-clinical-green" aria-hidden="true" />
            Clinical information, checked against sources
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-950 dark:text-white sm:text-3xl">Verify a health-related answer</h1>
          <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-zinc-400 sm:text-base">
            Submit a medical claim or question to review its grounding and safety.
          </p>
        </div>

        <section aria-label="Medical query verification" className="rounded-lg border border-slate-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900/70">
          <div className="border-b border-slate-200 px-4 py-4 dark:border-zinc-800 sm:px-6">
            <h2 className="text-sm font-semibold text-slate-900 dark:text-zinc-100">Your query</h2>
            <p className="mt-1 text-xs text-slate-500 dark:text-zinc-400">Avoid including names or other personal identifying information.</p>
          </div>
          <div className="p-4 sm:p-6">
            <SearchBar query={query} onQueryChange={setQuery} onSubmit={handleVerify} loading={loading} />
            {loading && (
              <div role="status" className="mt-5 flex items-center gap-3 rounded-md border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600 dark:border-zinc-800 dark:bg-zinc-950 dark:text-zinc-300">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-clinical-green dark:border-zinc-700 dark:border-t-clinical-green" />
                Reviewing the query against available evidence…
              </div>
            )}
            {error && (
              <div role="alert" className="mt-5 flex gap-3 rounded-md border border-clinical-red/30 bg-clinical-red/5 p-4 text-sm text-slate-700 dark:text-zinc-200">
                <CircleAlert size={18} className="mt-0.5 shrink-0 text-clinical-red" aria-hidden="true" />
                <div><p className="font-medium">Verification could not be completed</p><p className="mt-1 text-slate-600 dark:text-zinc-400">{error}</p></div>
              </div>
            )}
          </div>
        </section>

        {result && <ResultCard result={result} />}

        {!result && !loading && !error && (
          <div className="mt-6 flex items-start gap-3 rounded-lg border border-slate-200 bg-white/70 px-4 py-4 text-sm dark:border-zinc-800 dark:bg-zinc-900/40">
            <TriangleAlert size={17} className="mt-0.5 shrink-0 text-clinical-amber" aria-hidden="true" />
            <p className="leading-6 text-slate-600 dark:text-zinc-400">This tool supports review of health information and does not replace advice from a qualified healthcare professional.</p>
          </div>
        )}

        <footer className="mt-10 flex flex-col gap-2 border-t border-slate-200 pt-5 text-xs text-slate-500 dark:border-zinc-800 dark:text-zinc-500 sm:flex-row sm:items-center sm:justify-between">
          <span>Clinical AI Verifier <span aria-hidden="true">·</span> Evidence review</span>
          <a href="https://www.fda.gov/drugs" target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 hover:text-slate-700 dark:hover:text-zinc-300">Learn about medicine safety <ArrowUpRight size={12} aria-hidden="true" /></a>
        </footer>
      </main>
    </div>
  )
}

export default App
