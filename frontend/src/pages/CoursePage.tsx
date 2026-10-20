import { useEffect, useState } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { getCourse, getCourseProblems, getCourseLabs, CourseResponse, ProblemSummary, LabSession } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'

type Tab = 'problems' | 'labs' | 'gradebook'

export default function CoursePage() {
  const { id } = useParams<{ id: string }>()
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const navigate = useNavigate()

  const [course, setCourse] = useState<CourseResponse | null>(null)
  const [problems, setProblems] = useState<ProblemSummary[]>([])
  const [labs, setLabs] = useState<LabSession[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<Tab>('problems')
  const [showCode, setShowCode] = useState(false)

  const isInstructor = user?.role === 'instructor'

  useEffect(() => {
    if (!id) return
    Promise.all([getCourse(id), getCourseProblems(id), getCourseLabs(id)])
      .then(([c, p, l]) => { setCourse(c); setProblems(p); setLabs(l) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [id])

  const isSolved = (slug: string) => localStorage.getItem(`solved_${slug}`) === 'true'

  const activeLabs = labs.filter((l) => l.is_active)
  const pastLabs = labs.filter((l) => !l.is_active)

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex items-center justify-center gap-3">
        <div className="w-8 h-8 rounded-full border-4 border-orange-500/10 border-t-orange-500 animate-spin" />
        <span className="text-zinc-500 text-sm font-medium">Loading course…</span>
      </div>
    )
  }

  if (!course) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex items-center justify-center">
        <div className="text-center">
          <p className="text-zinc-500 mb-4">Course not found.</p>
          <Link to="/" className="text-orange-500 hover:text-orange-600 font-medium text-sm">← Back to Courses</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 font-sans flex flex-col transition-colors duration-200">
      {/* Header */}
      <header className="border-b border-zinc-200 dark:border-zinc-900 bg-white/80 dark:bg-zinc-900/20 backdrop-blur sticky top-0 z-50 px-6 py-4 flex items-center justify-between transition-colors">
        <div className="flex items-center gap-3">
          <Link to="/" className="flex items-center gap-1.5 text-zinc-500 dark:text-zinc-400 hover:text-orange-500 dark:hover:text-orange-400 text-xs font-semibold uppercase tracking-wider transition-colors">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
            Courses
          </Link>
          <div className="h-4 w-[1px] bg-zinc-200 dark:bg-zinc-800" />
          <span className="font-bold text-sm text-zinc-900 dark:text-white tracking-tight">{course.title}</span>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={toggleTheme} className="p-1.5 rounded-lg bg-zinc-100 dark:bg-zinc-900 text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white border border-zinc-200 dark:border-zinc-800 transition-colors">
            {theme === 'dark' ? (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m0-12.728l.707.707m12.728 12.728l.707.707M12 8a4 4 0 100 8 4 4 0 000-8z" /></svg>
            ) : (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" /></svg>
            )}
          </button>
          <button onClick={() => { logout(); navigate('/login') }} className="text-xs text-zinc-500 dark:text-zinc-400 hover:text-red-500 transition-colors font-medium">Sign out</button>
        </div>
      </header>

      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8 flex flex-col gap-6">
        {/* Course header card */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-bl from-orange-500/5 to-transparent rounded-full -translate-y-1/2 translate-x-1/4" />
          <div className="relative">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-2xl font-extrabold text-zinc-900 dark:text-white tracking-tight">{course.title}</h1>
              {isInstructor && (
                <button onClick={() => setShowCode(!showCode)} className="text-xs px-2 py-1 rounded-md bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-zinc-500 dark:text-zinc-400 hover:text-orange-500 font-mono transition-colors">
                  {showCode ? course.join_code : '••••••'}
                </button>
              )}
            </div>
            <p className="text-zinc-500 dark:text-zinc-400 text-sm max-w-2xl">{course.description}</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-1 bg-zinc-100 dark:bg-zinc-900 rounded-lg p-1 self-start border border-zinc-200 dark:border-zinc-800">
          {(['problems', 'labs', ...(isInstructor ? ['gradebook'] : [])] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 rounded-md text-sm font-semibold capitalize transition-all ${
                tab === t
                  ? 'bg-white dark:bg-zinc-800 text-zinc-900 dark:text-white shadow-sm'
                  : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200'
              }`}
            >
              {t === 'labs' ? 'Lab Sessions' : t}
            </button>
          ))}
        </div>

        {/* ── Problems Tab ── */}
        {tab === 'problems' && (
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden shadow-sm">
            <div className="px-6 py-4 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
              <h2 className="font-bold text-zinc-900 dark:text-white">Problems</h2>
              <span className="text-xs bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400 px-2 py-0.5 rounded-full">{problems.length} total</span>
            </div>
            <div className="divide-y divide-zinc-100 dark:divide-zinc-800/50">
              {problems.map((p) => {
                const solved = isSolved(p.slug)
                return (
                  <Link key={p.id} to={`/problems/${p.slug}`} className="flex items-center justify-between px-6 py-4 hover:bg-zinc-50 dark:hover:bg-zinc-800/30 transition-colors group">
                    <div className="flex items-center gap-4">
                      <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold border ${solved ? 'bg-green-500/10 border-green-500/20 text-green-500' : 'border-zinc-200 dark:border-zinc-700 text-zinc-400'}`}>
                        {solved ? '✓' : '·'}
                      </span>
                      <div>
                        <span className="font-semibold text-zinc-800 dark:text-white group-hover:text-orange-500 transition-colors">{p.title}</span>
                        <span className={`ml-3 text-xs px-2 py-0.5 rounded font-medium uppercase border ${
                          p.difficulty === 'easy' ? 'text-green-500 border-green-500/20 bg-green-500/5'
                          : p.difficulty === 'medium' ? 'text-yellow-500 border-yellow-500/20 bg-yellow-500/5'
                          : 'text-red-500 border-red-500/20 bg-red-500/5'
                        }`}>{p.difficulty}</span>
                      </div>
                    </div>
                    <svg className="w-4 h-4 text-zinc-400 group-hover:text-orange-500 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
                  </Link>
                )
              })}
            </div>
          </div>
        )}

        {/* ── Labs Tab ── */}
        {tab === 'labs' && (
          <div className="flex flex-col gap-5">
            {isInstructor && (
              <Link
                to={`/courses/${id}/labs/create`}
                className="inline-flex items-center gap-1.5 self-start px-4 py-2.5 bg-orange-500 hover:bg-orange-600 text-white rounded-lg text-sm font-semibold transition-all shadow-lg shadow-orange-500/20"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                Create Lab Session
              </Link>
            )}

            {/* Active labs */}
            {activeLabs.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-green-500 uppercase tracking-wider mb-3 flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" /> Active Labs
                </h3>
                <div className="grid gap-3">
                  {activeLabs.map((lab) => (
                    <Link key={lab.id} to={isInstructor ? `/labs/${lab.id}/dashboard` : `/labs/${lab.id}`}
                      className="bg-white dark:bg-zinc-900 border border-green-500/20 rounded-xl p-5 flex items-center justify-between hover:shadow-lg hover:border-green-500/40 transition-all group"
                    >
                      <div>
                        <h4 className="font-bold text-zinc-900 dark:text-white group-hover:text-green-500 transition-colors">{lab.title}</h4>
                        <p className="text-zinc-500 dark:text-zinc-400 text-sm mt-0.5">{lab.topic} · {lab.problem_count} problems · {lab.mandatory_count} mandatory</p>
                        <p className="text-xs text-zinc-400 mt-1">Ends {new Date(lab.ends_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
                      </div>
                      <div className="px-3 py-1.5 rounded-full bg-green-500/10 text-green-500 text-xs font-semibold border border-green-500/20">
                        LIVE
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            )}

            {/* Past labs */}
            {pastLabs.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-3">Past Labs</h3>
                <div className="grid gap-3">
                  {pastLabs.map((lab) => (
                    <Link key={lab.id} to={isInstructor ? `/labs/${lab.id}/dashboard` : `/labs/${lab.id}`}
                      className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5 flex items-center justify-between hover:shadow-md transition-all group"
                    >
                      <div>
                        <h4 className="font-semibold text-zinc-700 dark:text-zinc-300 group-hover:text-orange-500 transition-colors">{lab.title}</h4>
                        <p className="text-zinc-500 dark:text-zinc-400 text-sm mt-0.5">{lab.topic} · {lab.problem_count} problems</p>
                        <p className="text-xs text-zinc-400 mt-1">{new Date(lab.starts_at).toLocaleDateString()}</p>
                      </div>
                      <span className="text-xs text-zinc-400 dark:text-zinc-600">Ended</span>
                    </Link>
                  ))}
                </div>
              </div>
            )}

            {labs.length === 0 && (
              <div className="text-center py-16 text-zinc-500 dark:text-zinc-400 text-sm">
                No lab sessions yet.{isInstructor && ' Create one to get started!'}
              </div>
            )}
          </div>
        )}

        {/* ── Gradebook Tab ── */}
        {tab === 'gradebook' && isInstructor && (
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-6 text-center">
            <Link
              to={`/courses/${id}/gradebook`}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-orange-500 hover:bg-orange-600 text-white rounded-lg font-semibold text-sm shadow-lg shadow-orange-500/20 transition-all"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
              Open Full Gradebook
            </Link>
          </div>
        )}
      </main>
    </div>
  )
}
