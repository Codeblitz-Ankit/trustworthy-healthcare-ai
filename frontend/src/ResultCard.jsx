import { AlertOctagon, Check, ExternalLink, ShieldCheck, TriangleAlert } from 'lucide-react'

const statusPresentation = {
  verified: {
    title: 'Verified',
    Icon: ShieldCheck,
    accent: 'text-clinical-green',
    badge: 'border-clinical-green/25 bg-clinical-green/10 text-clinical-green',
  },
  partially_verified: {
    title: 'Partially Verified',
    Icon: TriangleAlert,
    accent: 'text-clinical-amber',
    badge: 'border-clinical-amber/25 bg-clinical-amber/10 text-clinical-amber',
  },
  not_verified: {
    title: 'Withheld for Safety',
    Icon: AlertOctagon,
    accent: 'text-clinical-red',
    badge: 'border-clinical-red/25 bg-clinical-red/10 text-clinical-red',
  },
}

function ResultCard({ result }) {
  const status = statusPresentation[result?.status] ?? statusPresentation.not_verified
  const { Icon } = status
  const sources = Array.isArray(result?.sources) ? result.sources : []
  const reviewRequired = Boolean(result?.review_required)

  return (
    <section aria-live="polite" aria-labelledby="result-title" className="mt-6 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900/70">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-4 py-4 dark:border-zinc-800 sm:px-6">
        <div className="flex items-center gap-3">
          <span className={`flex h-9 w-9 items-center justify-center rounded-md border ${status.badge}`}><Icon size={19} aria-hidden="true" /></span>
          <div>
            <p className="text-xs text-slate-500 dark:text-zinc-400">Verification result</p>
            <h2 id="result-title" className="text-base font-semibold text-slate-900 dark:text-white">{status.title}</h2>
          </div>
        </div>
        {result?.status === 'verified' && (
          <span className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs font-medium ${status.badge}`}><Check size={13} aria-hidden="true" /> Evidence supported</span>
        )}
      </div>

      <div className="px-4 py-5 sm:px-6 sm:py-6">
        <p className="whitespace-pre-wrap text-sm leading-7 text-slate-700 dark:text-zinc-300">{result?.content || 'No explanation was returned for this result.'}</p>
        {result?.status === 'verified' && sources.length > 0 && (
          <div className="mt-6 border-t border-slate-200 pt-4 dark:border-zinc-800">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-zinc-400">Sources</h3>
            <ul className="mt-3 space-y-2">
              {sources.map((source, index) => {
                const label = typeof source === 'string' ? source : source?.title || source?.name || 'Reference source'
                const href = typeof source === 'object' && source ? source.url || source.href : null
                return (
                  <li key={`${label}-${index}`} className="flex items-start gap-2 text-sm text-slate-600 dark:text-zinc-400">
                    <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-clinical-green" />
                    {href ? <a href={href} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 underline decoration-slate-300 underline-offset-2 hover:text-slate-900 dark:decoration-zinc-600 dark:hover:text-white">{label}<ExternalLink size={12} aria-hidden="true" /></a> : <span>{label}</span>}
                  </li>
                )
              })}
            </ul>
          </div>
        )}
        {result?.status !== 'verified' && (
          <p className="mt-5 border-t border-slate-200 pt-4 text-xs leading-5 text-slate-500 dark:border-zinc-800 dark:text-zinc-500">If this concerns a personal health decision, consult a qualified healthcare professional.</p>
        )}
      </div>

      {reviewRequired && (
        <div
          role="alert"
          aria-live="assertive"
          className="flex items-center gap-2 border-t border-orange-200 bg-orange-50 px-4 py-3 text-sm font-medium text-orange-800 dark:border-orange-900/40 dark:bg-orange-950/30 dark:text-orange-300 sm:px-6"
        >
          <span aria-hidden="true" className="text-base">⚠️</span>
          <span>Escalated to Clinician Review</span>
        </div>
      )}
    </section>
  )
}

export default ResultCard
