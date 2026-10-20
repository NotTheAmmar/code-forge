import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getCourses, joinCourse, createCourse, CourseResponse } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'

export default function CourseListPage() {
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const navigate = useNavigate()

  const [courses, setCourses] = useState<CourseResponse[]>([])
  const [loading, setLoading] = useState(true)

  // Join modal state
  const [showJoin, setShowJoin] = useState(false)
  const [joinCode, setJoinCode] = useState('')
  const [joinError, setJoinError] = useState<string | null>(null)
  const [joining, setJoining] = useState(false)

  // Create modal state
  const [showCreate, setShowCreate] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    getCourses()
      .then(setCourses)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleJoin = async (e: React.FormEvent) => {
    e.preventDefault()
    setJoinError(null)
    setJoining(true)
    try {
      const course = await joinCourse(joinCode.trim())
      setCourses((prev) => (prev.find((c) => c.id === course.id) ? prev : [...prev, course]))
      setShowJoin(false)
      setJoinCode('')
      navigate(`/courses/${course.id}`)
    } catch {
      setJoinError('Invalid join code. Please check and try again.')
    } finally {
      setJoining(false)
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreating(true)
    try {
      const course = await createCourse({ title: newTitle, description: newDesc })
      setCourses((prev) => [...prev, course])
      setShowCreate(false)
      setNewTitle('')
      setNewDesc('')
      navigate(`/courses/${course.id}`)
    } catch {
      /* ignore */
    } finally {
      setCreating(false)
    }
  }

  const isInstructor = user?.role === 'instructor'
  const courseColors = [
    'from-orange-500 to-amber-500',
    'from-violet-500 to-purple-500',
    'from-cyan-500 to-blue-500',
    'from-emerald-500 to-teal-500',
    'from-rose-500 to-pink-500',
    'from-indigo-500 to-sky-500',
  ]

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 font-sans flex flex-col transition-colors duration-200">
      {/* ── Header ─────────────────────────────────────── */}
      <header className="border-b border-zinc-200 dark:border-zinc-900 bg-white/80 dark:bg-zinc-900/20 backdrop-blur sticky top-0 z-50 px-6 py-4 flex items-center justify-between transition-colors">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded bg-gradient-to-tr from-orange-600 to-orange-400 flex items-center justify-center font-bold text-white shadow-lg shadow-orange-500/10">
            CF
          </div>
          <div>
            <span className="font-bold text-lg text-zinc-900 dark:text-white tracking-tight">CodeForge</span>
            <span className="text-zinc-500 text-xs ml-1 font-mono">v0.2.0</span>
          </div>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <Link
            to="/practice"
            className="text-zinc-500 dark:text-zinc-400 hover:text-orange-500 dark:hover:text-orange-400 text-xs font-semibold uppercase tracking-wider transition-colors"
          >
            Practice
          </Link>
          {user && (
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-full bg-orange-500/10 border border-orange-500/20 flex items-center justify-center text-xs font-bold text-orange-600 dark:text-orange-400">
                {user.name.charAt(0).toUpperCase()}
              </div>
              <span className="text-zinc-600 dark:text-zinc-400 text-xs font-medium hidden sm:block">{user.name}</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400 font-mono uppercase border border-zinc-200 dark:border-zinc-700 hidden sm:inline">
                {user.role}
              </span>
            </div>
          )}
          <button
            onClick={toggleTheme}
            className="p-1.5 rounded-lg bg-zinc-100 dark:bg-zinc-900 text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white border border-zinc-200 dark:border-zinc-800 transition-colors"
            aria-label="Toggle Theme"
          >
            {theme === 'dark' ? (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m0-12.728l.707.707m12.728 12.728l.707.707M12 8a4 4 0 100 8 4 4 0 000-8z" /></svg>
            ) : (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" /></svg>
            )}
          </button>
          <button onClick={() => { logout(); navigate('/login') }} className="text-zinc-500 dark:text-zinc-400 hover:text-red-600 dark:hover:text-red-400 transition-colors text-xs font-medium">
            Sign out
          </button>
        </div>
      </header>

      {/* ── Main ───────────────────────────────────────── */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-10 flex flex-col gap-8">
        {/* Hero */}
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-extrabold text-zinc-900 dark:text-white tracking-tight md:text-4xl">
              My Courses
            </h1>
            <p className="text-zinc-600 dark:text-zinc-400 text-sm mt-1">
              {isInstructor ? 'Manage your courses, lab sessions, and student progress.' : 'Join a course to start solving problems and earning badges.'}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setShowJoin(true)}
              className="inline-flex items-center gap-1.5 px-4 py-2.5 border border-zinc-300 dark:border-zinc-700 hover:border-orange-500/50 bg-white dark:bg-zinc-900 text-zinc-700 dark:text-zinc-300 rounded-lg text-sm font-semibold transition-all hover:shadow-md"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" /></svg>
              Join Course
            </button>
            {isInstructor && (
              <button
                onClick={() => setShowCreate(true)}
                className="inline-flex items-center gap-1.5 px-4 py-2.5 bg-orange-500 hover:bg-orange-600 text-white rounded-lg text-sm font-semibold transition-all shadow-lg shadow-orange-500/20"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                Create Course
              </button>
            )}
          </div>
        </div>

        {/* Course Grid */}
        {loading ? (
          <div className="flex items-center justify-center py-20 gap-3">
            <div className="w-8 h-8 rounded-full border-4 border-orange-500/10 border-t-orange-500 animate-spin" />
            <span className="text-zinc-500 text-sm font-medium">Loading courses…</span>
          </div>
        ) : courses.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 gap-4 text-center">
            <div className="w-16 h-16 rounded-2xl bg-zinc-100 dark:bg-zinc-900 flex items-center justify-center text-zinc-300 dark:text-zinc-700">
              <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>
            </div>
            <p className="text-zinc-500 dark:text-zinc-400 text-sm">No courses yet. Join one using a code or create your own!</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {courses.map((course, i) => (
              <Link
                key={course.id}
                to={`/courses/${course.id}`}
                className="group relative bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl overflow-hidden shadow-sm hover:shadow-xl dark:hover:shadow-zinc-950/80 transition-all duration-300 hover:-translate-y-0.5"
              >
                {/* Gradient banner */}
                <div className={`h-24 bg-gradient-to-br ${courseColors[i % courseColors.length]} relative overflow-hidden`}>
                  <div className="absolute inset-0 bg-black/5" />
                  <div className="absolute bottom-3 left-4 text-white/90 text-xs font-mono tracking-wider uppercase">
                    {course.join_code}
                  </div>
                </div>
                <div className="p-5">
                  <h3 className="font-bold text-zinc-900 dark:text-white group-hover:text-orange-600 dark:group-hover:text-orange-400 transition-colors text-lg">
                    {course.title}
                  </h3>
                  <p className="text-zinc-500 dark:text-zinc-400 text-sm mt-1 line-clamp-2 leading-relaxed">
                    {course.description}
                  </p>
                  <div className="flex items-center gap-2 mt-4 text-xs text-zinc-400 dark:text-zinc-600">
                    <span>{course.instructor_name ?? 'Instructor'}</span>
                    <span>·</span>
                    <span>{new Date(course.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>

      {/* ── Join Modal ─────────────────────────────────── */}
      {showJoin && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm animate-fade-in" onClick={() => setShowJoin(false)}>
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-2xl w-full max-w-md mx-4 p-6 animate-scale-in" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-bold text-zinc-900 dark:text-white mb-1">Join a Course</h2>
            <p className="text-zinc-500 dark:text-zinc-400 text-sm mb-5">Enter the join code provided by your instructor.</p>
            <form onSubmit={handleJoin} className="flex flex-col gap-4">
              <input
                id="join-code-input"
                type="text"
                value={joinCode}
                onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
                placeholder="e.g. DSA2024"
                required
                className="w-full bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg px-4 py-3 text-center text-lg font-mono font-bold tracking-[0.3em] text-zinc-900 dark:text-white placeholder-zinc-400 dark:placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500 transition uppercase"
              />
              {joinError && (
                <p className="bg-red-500/5 border border-red-500/20 text-red-500 text-sm rounded-lg px-4 py-2">{joinError}</p>
              )}
              <div className="flex gap-2">
                <button type="button" onClick={() => setShowJoin(false)} className="flex-1 py-2.5 rounded-lg border border-zinc-200 dark:border-zinc-700 text-zinc-600 dark:text-zinc-400 font-medium text-sm hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors">
                  Cancel
                </button>
                <button type="submit" disabled={joining || !joinCode.trim()} className="flex-1 py-2.5 rounded-lg bg-orange-500 hover:bg-orange-600 text-white font-semibold text-sm shadow-lg shadow-orange-500/20 disabled:opacity-50 transition-all">
                  {joining ? 'Joining…' : 'Join'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Create Modal ───────────────────────────────── */}
      {showCreate && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm animate-fade-in" onClick={() => setShowCreate(false)}>
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-2xl w-full max-w-md mx-4 p-6 animate-scale-in" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-bold text-zinc-900 dark:text-white mb-4">Create Course</h2>
            <form onSubmit={handleCreate} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Course Title</label>
                <input type="text" value={newTitle} onChange={(e) => setNewTitle(e.target.value)} required placeholder="e.g. Data Structures & Algorithms"
                  className="w-full bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg px-4 py-2.5 text-sm text-zinc-900 dark:text-white placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500 transition"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Description</label>
                <textarea value={newDesc} onChange={(e) => setNewDesc(e.target.value)} required rows={3} placeholder="Brief description of the course…"
                  className="w-full bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg px-4 py-2.5 text-sm text-zinc-900 dark:text-white placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500 transition resize-none"
                />
              </div>
              <div className="flex gap-2">
                <button type="button" onClick={() => setShowCreate(false)} className="flex-1 py-2.5 rounded-lg border border-zinc-200 dark:border-zinc-700 text-zinc-600 dark:text-zinc-400 font-medium text-sm hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors">
                  Cancel
                </button>
                <button type="submit" disabled={creating} className="flex-1 py-2.5 rounded-lg bg-orange-500 hover:bg-orange-600 text-white font-semibold text-sm shadow-lg shadow-orange-500/20 disabled:opacity-50 transition-all">
                  {creating ? 'Creating…' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
