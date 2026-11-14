import { ArrowRight, LoaderCircle } from 'lucide-react'

function SearchBar({ query, onQueryChange, onSubmit, loading }) {
  return (
    <form onSubmit={onSubmit}>
      <label htmlFor="medical-query" className="sr-only">Medical query</label>
      <textarea
        id="medical-query"
        value={query}
        onChange={(event) => onQueryChange(event.target.value)}
        placeholder="For example: Does ibuprofen interact with blood pressure medication?"
        rows={4}
        required
        maxLength={5000}
        disabled={loading}
        className="block w-full resize-y rounded-md border border-slate-300 bg-white px-3.5 py-3 text-sm leading-6 text-slate-900 placeholder:text-slate-400 focus:border-clinical-green focus:outline-none focus:ring-2 focus:ring-clinical-green/20 disabled:cursor-wait disabled:opacity-70 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100 dark:placeholder:text-zinc-600"
      />
      <div className="mt-3 flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs text-slate-500 dark:text-zinc-500">Up to 5,000 characters</p>
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="inline-flex min-h-10 items-center justify-center gap-2 rounded-md bg-slate-800 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-clinical-green focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white dark:focus-visible:ring-offset-zinc-900"
        >
          {loading ? <LoaderCircle size={16} className="animate-spin" aria-hidden="true" /> : <ArrowRight size={16} aria-hidden="true" />}
          {loading ? 'Verifying…' : 'Verify Query'}
        </button>
      </div>
    </form>
  )
}

export default SearchBar
