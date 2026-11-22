import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getLabSession, getMyLabProgress, LabSessionDetail, MyLabProgress } from '../api/client'
import Navbar from '../components/Navbar'

export default function StudentLabPage() {
  const { id } = useParams<{ id: string }>()

  const [lab, setLab] = useState<LabSessionDetail | null>(null)
  const [progress, setProgress] = useState<MyLabProgress | null>(null)
  const [loading, setLoading] = useState(true)
  const [timeLeft, setTimeLeft] = useState('')

  useEffect(() => {
    if (!id) return
    Promise.all([getLabSession(id), getMyLabProgress(id)])
      .then(([l, p]) => { setLab(l); setProgress(p) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [id])

  // Countdown timer
  useEffect(() => {
    if (!lab) return
    const tick = () => {
      const end = new Date(lab.ends_at).getTime()
      const now = Date.now()
      const diff = end - now
      if (diff <= 0) { setTimeLeft('Ended'); return }
      const h = Math.floor(diff / 3600000)
      const m = Math.floor((diff % 3600000) / 60000)
      const s = Math.floor((diff % 60000) / 1000)
      setTimeLeft(`${h}h ${m}m ${s}s`)
    }
    tick()
    const iv = setInterval(tick, 1000)
    return () => clearInterval(iv)
  }, [lab])

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex items-center justify-center gap-3">
        <div className="w-8 h-8 rounded-full border-4 border-orange-500/10 border-t-orange-500 animate-spin" />
      </div>
    )
  }

  if (!lab || !progress) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex items-center justify-center">
        <p className="text-zinc-500">Lab session not found.</p>
      </div>
    )
  }

  const totalProblems = progress.problems.length
  const solvedCount = progress.problems.filter((p) => p.is_solved).length
  const progressPct = totalProblems > 0 ? Math.round((solvedCount / totalProblems) * 100) : 0

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 font-sans flex flex-col transition-colors duration-200">
      {/* Lab Mode Banner */}
      <div className="bg-gradient-to-r from-orange-500 to-amber-500 text-white px-6 py-3 flex items-center justify-between text-sm font-medium">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-white animate-pulse" />
          <span className="font-bold">LAB MODE</span>
          <span className="opacity-80">— {lab.title}</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="font-mono text-xs bg-white/20 rounded px-2 py-0.5">{timeLeft}</span>
          <span className="text-xs opacity-80">🏅 {progress.badges_earned} badges</span>
        </div>
      </div>

      {/* Header */}
      <Navbar
        customTitle={lab.title}
        backTo={`/courses/${lab.course_id}`}
        backLabel="Course"
      />

      <main className="flex-1 max-w-4xl w-full mx-auto px-6 py-8 flex flex-col gap-6">
        {/* Progress Overview */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-xl font-extrabold text-zinc-900 dark:text-white">{lab.title}</h1>
              <p className="text-zinc-500 dark:text-zinc-400 text-sm mt-0.5">Topic: {lab.topic}</p>
            </div>
            <div className="flex items-center gap-4 text-sm">
              <div className="text-center">
                <p className="text-2xl font-bold text-zinc-900 dark:text-white">{progress.mandatory_solved}/{progress.mandatory_total}</p>
                <p className="text-xs text-zinc-500">Mandatory</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-orange-500">🏅 {progress.badges_earned}</p>
                <p className="text-xs text-zinc-500">Badges</p>
              </div>
            </div>
          </div>

          {/* Progress bar */}
          <div className="mb-2 flex items-center justify-between text-xs text-zinc-500 dark:text-zinc-400">
            <span>Overall Progress</span>
            <span className="font-mono">{solvedCount}/{totalProblems} solved ({progressPct}%)</span>
          </div>
          <div className="w-full h-3 bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-orange-500 to-amber-500 transition-all duration-700"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>

        {/* Problem list */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden">
          <div className="px-6 py-4 border-b border-zinc-200 dark:border-zinc-800">
            <h2 className="font-bold text-zinc-900 dark:text-white">Problems</h2>
          </div>
          <div className="divide-y divide-zinc-100 dark:divide-zinc-800/50">
            {progress.problems.map((p) => (
              <Link
                key={p.problem_id}
                to={`/problems/${p.problem_slug}?lab=${lab.id}`}
                className="flex items-center justify-between px-6 py-4 hover:bg-zinc-50 dark:hover:bg-zinc-800/30 transition-colors group"
              >
                <div className="flex items-center gap-4">
                  <span className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border ${
                    p.is_solved
                      ? 'bg-green-500/10 border-green-500/20 text-green-500'
                      : 'border-zinc-200 dark:border-zinc-700 text-zinc-400'
                  }`}>
                    {p.is_solved ? '✓' : '·'}
                  </span>
                  <div>
                    <span className="font-semibold text-zinc-800 dark:text-white group-hover:text-orange-500 transition-colors">{p.problem_title}</span>
                    <div className="flex items-center gap-2 mt-0.5">
                      {p.is_mandatory ? (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/10 text-red-500 border border-red-500/20 font-bold uppercase">Required</span>
                      ) : (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-500 border border-zinc-200 dark:border-zinc-700 font-semibold uppercase">Extra (+🏅)</span>
                      )}
                      {p.best_score !== null && (
                        <span className="text-[10px] text-zinc-400 font-mono">Best: {p.best_score}%</span>
                      )}
                    </div>
                  </div>
                </div>
                <svg className="w-4 h-4 text-zinc-400 group-hover:text-orange-500 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </Link>
            ))}
          </div>
        </div>
      </main>
    </div>
  )
}
