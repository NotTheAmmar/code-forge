import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { getProblems, createLabSession, ProblemSummary } from '../api/client'

interface SelectedProblem {
  problem_id: string
  is_mandatory: boolean
}

export default function LabCreatePage() {
  const { courseId } = useParams<{ courseId: string }>()
  const navigate = useNavigate()

  const [problems, setProblems] = useState<ProblemSummary[]>([])
  const [title, setTitle] = useState('')
  const [topic, setTopic] = useState('')
  const [startsAt, setStartsAt] = useState('')
  const [endsAt, setEndsAt] = useState('')
  const [selected, setSelected] = useState<SelectedProblem[]>([])
  const [creating, setCreating] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getProblems()
      .then(setProblems)
      .catch(() => {})
      .finally(() => setLoading(false))

    // Default times: now → +2 hours
    const now = new Date()
    const later = new Date(now.getTime() + 2 * 3600000)
    setStartsAt(toLocalISO(now))
    setEndsAt(toLocalISO(later))
  }, [])

  const toLocalISO = (d: Date) => {
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
  }

  const toggleProblem = (pid: string) => {
    setSelected((prev) => {
      const exists = prev.find((s) => s.problem_id === pid)
      if (exists) return prev.filter((s) => s.problem_id !== pid)
      return [...prev, { problem_id: pid, is_mandatory: false }]
    })
  }

  const toggleMandatory = (pid: string) => {
    setSelected((prev) => prev.map((s) => s.problem_id === pid ? { ...s, is_mandatory: !s.is_mandatory } : s))
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!courseId || selected.length === 0) return
    setCreating(true)
    try {
      const lab = await createLabSession(courseId, {
        title,
        topic,
        starts_at: new Date(startsAt).toISOString(),
        ends_at: new Date(endsAt).toISOString(),
        problem_ids: selected,
      })
      navigate(`/labs/${lab.id}/dashboard`)
    } catch {
      /* fallback already handled in client */
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 font-sans flex flex-col transition-colors duration-200">
      <main className="flex-1 max-w-3xl w-full mx-auto px-6 py-8 flex flex-col gap-6">
        <div>
          <Link
            to={courseId ? `/courses/${courseId}?tab=labs` : '/'}
            className="inline-flex items-center gap-1.5 text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-white text-xs font-semibold uppercase tracking-wider transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            <span>Back to Course</span>
          </Link>
        </div>
        <form onSubmit={handleCreate} className="flex flex-col gap-6">
          {/* Basic info */}
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 flex flex-col gap-5">
            <h2 className="font-bold text-lg text-zinc-900 dark:text-white">Session Details</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Title</label>
                <input type="text" value={title} onChange={(e) => setTitle(e.target.value)} required placeholder="e.g. Lab 3: Linked Lists"
                  className="bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg px-4 py-2.5 text-sm text-zinc-900 dark:text-white placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500 transition"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Topic</label>
                <input type="text" value={topic} onChange={(e) => setTopic(e.target.value)} required placeholder="e.g. Linked Lists"
                  className="bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg px-4 py-2.5 text-sm text-zinc-900 dark:text-white placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500 transition"
                />
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Starts At</label>
                <input type="datetime-local" value={startsAt} onChange={(e) => setStartsAt(e.target.value)} required
                  className="bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg px-4 py-2.5 text-sm text-zinc-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500 transition"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Ends At</label>
                <input type="datetime-local" value={endsAt} onChange={(e) => setEndsAt(e.target.value)} required
                  className="bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg px-4 py-2.5 text-sm text-zinc-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500 transition"
                />
              </div>
            </div>
          </div>

          {/* Problem selector */}
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <h2 className="font-bold text-lg text-zinc-900 dark:text-white">Select Problems</h2>
              <span className="text-xs text-zinc-500 dark:text-zinc-400">{selected.length} selected · {selected.filter((s) => s.is_mandatory).length} mandatory</span>
            </div>

            {loading ? (
              <div className="flex items-center justify-center py-8">
                <div className="w-6 h-6 rounded-full border-3 border-orange-500/10 border-t-orange-500 animate-spin" />
              </div>
            ) : (
              <div className="divide-y divide-zinc-100 dark:divide-zinc-800/50 -mx-6">
                {problems.map((p) => {
                  const sel = selected.find((s) => s.problem_id === p.id)
                  return (
                    <div key={p.id} className="flex items-center justify-between px-6 py-3 hover:bg-zinc-50 dark:hover:bg-zinc-800/30 transition-colors">
                      <label className="flex items-center gap-3 cursor-pointer flex-1">
                        <input
                          type="checkbox"
                          checked={!!sel}
                          onChange={() => toggleProblem(p.id)}
                          className="w-4 h-4 rounded border-zinc-300 dark:border-zinc-600 text-orange-500 focus:ring-orange-500"
                        />
                        <div>
                          <span className="font-medium text-zinc-800 dark:text-white text-sm">{p.title}</span>
                          <span className={`ml-2 text-[10px] px-1.5 py-0.5 rounded font-semibold uppercase border ${
                            p.difficulty === 'easy' ? 'text-green-500 border-green-500/20 bg-green-500/5'
                            : p.difficulty === 'medium' ? 'text-yellow-500 border-yellow-500/20 bg-yellow-500/5'
                            : 'text-red-500 border-red-500/20 bg-red-500/5'
                          }`}>{p.difficulty}</span>
                        </div>
                      </label>
                      {sel && (
                        <button
                          type="button"
                          onClick={() => toggleMandatory(p.id)}
                          className={`text-[10px] px-2 py-1 rounded font-bold uppercase border transition-all ${
                            sel.is_mandatory
                              ? 'bg-red-500/10 text-red-500 border-red-500/20'
                              : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-500 border-zinc-200 dark:border-zinc-700'
                          }`}
                        >
                          {sel.is_mandatory ? '★ Mandatory' : 'Extra (badge)'}
                        </button>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Submit */}
          <div className="flex items-center justify-end gap-3">
            <Link to={`/courses/${courseId}`} className="px-5 py-2.5 rounded-lg border border-zinc-200 dark:border-zinc-700 text-zinc-600 dark:text-zinc-400 font-medium text-sm hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors">
              Cancel
            </Link>
            <button
              type="submit"
              disabled={creating || selected.length === 0 || !title || !topic}
              className="px-6 py-2.5 bg-orange-500 hover:bg-orange-600 text-white rounded-lg font-semibold text-sm shadow-lg shadow-orange-500/20 disabled:opacity-50 transition-all"
            >
              {creating ? 'Creating…' : 'Create Lab Session'}
            </button>
          </div>
        </form>
      </main>
    </div>
  )
}
