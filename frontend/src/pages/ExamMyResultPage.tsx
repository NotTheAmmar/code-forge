import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getMyExamResult, ExamMyResult } from '../api/client'
import Navbar from '../components/Navbar'

export default function ExamMyResultPage() {
  const { id } = useParams<{ id: string }>()

  const [result, setResult] = useState<ExamMyResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    getMyExamResult(id)
      .then((data) => {
        setResult(data)
        setLoading(false)
      })
      .catch((err) => {
        console.error(err)
        setError('Failed to load your exam result.')
        setLoading(false)
      })
  }, [id])

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 flex flex-col font-sans transition-colors">
      {/* Header */}
      <Navbar
        customTitle="Assessment Outcome"
        backTo="/"
        backLabel="Dashboard"
      />

      {/* Main Content */}
      <main className="flex-1 max-w-xl w-full mx-auto px-6 py-12 flex flex-col items-center justify-center">
        {loading ? (
          <div className="flex flex-col items-center justify-center gap-3">
            <div className="w-8 h-8 rounded-full border-4 border-orange-500/10 border-t-orange-500 animate-spin" />
            <span className="text-zinc-500 text-sm">Loading exam results…</span>
          </div>
        ) : error || !result ? (
          <div className="p-6 bg-red-500/10 border border-red-500/20 rounded-xl text-center text-red-500 font-semibold">
            {error || 'No result found'}
          </div>
        ) : (
          <div className="w-full bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-3xl p-8 shadow-xl flex flex-col gap-6 text-center animate-in zoom-in-95 duration-200">
            <div className="w-16 h-16 rounded-3xl bg-green-500/10 border border-green-500/20 text-green-500 flex items-center justify-center text-3xl mx-auto">
              ✓
            </div>

            <div>
              <span className="text-xs uppercase font-bold tracking-wider text-green-600 dark:text-green-400">
                Exam Successfully Submitted
              </span>
              <h1 className="text-2xl font-black text-zinc-900 dark:text-white mt-1">
                Your Assessment Score
              </h1>
              <p className="text-xs text-zinc-500 mt-1">
                Submitted at{' '}
                {new Date(result.submitted_at).toLocaleTimeString([], {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
                {result.is_auto_submitted && ' (auto-submitted upon timer expiration)'}
              </p>
            </div>

            {/* Total Score Display */}
            <div className="p-6 bg-zinc-50 dark:bg-zinc-950 rounded-2xl border border-zinc-200 dark:border-zinc-800 flex flex-col items-center justify-center">
              <span className="text-5xl font-black font-mono text-orange-600 dark:text-orange-400 tracking-tight">
                {result.total_score}
              </span>
              <span className="text-xs uppercase tracking-wider text-zinc-500 font-bold mt-1">
                Total Score
              </span>
            </div>

            {/* Problem Scores Breakdown */}
            <div className="flex flex-col gap-2.5 text-left">
              <span className="text-xs font-bold uppercase tracking-wider text-zinc-500">
                Problem Breakdown
              </span>
              <div className="bg-zinc-50 dark:bg-zinc-950 rounded-xl border border-zinc-200 dark:border-zinc-800 divide-y divide-zinc-200 dark:divide-zinc-800 overflow-hidden">
                {Object.entries(result.problem_scores || {}).map(([probId, score], idx) => (
                  <div key={probId} className="px-4 py-3 flex items-center justify-between text-xs">
                    <span className="font-semibold text-zinc-800 dark:text-zinc-200">
                      Problem {idx + 1}
                    </span>
                    <span className="font-mono font-bold text-zinc-900 dark:text-white">
                      {score} pts
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <Link
              to="/"
              className="w-full py-3 bg-orange-600 hover:bg-orange-500 text-white rounded-xl text-xs font-bold uppercase tracking-wider transition shadow-md"
            >
              Back to Home Dashboard →
            </Link>
          </div>
        )}
      </main>
    </div>
  )
}
