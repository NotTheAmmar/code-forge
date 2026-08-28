import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getProblems, ProblemSummary } from '../api/client'
import { useTheme } from '../context/ThemeContext'

export default function ProblemListPage() {
  const [problems, setProblems] = useState<ProblemSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [solvedCount, setSolvedCount] = useState(0)
  const { theme, toggleTheme } = useTheme()

  useEffect(() => {
    getProblems()
      .then((data) => {
        setProblems(data)
        setLoading(false)
      })
      .catch((err) => {
        console.error(err)
        setLoading(false)
      })

    // Read solved counts from localStorage
    let count = 0
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)
      if (key && key.startsWith('solved_')) {
        if (localStorage.getItem(key) === 'true') {
          count++
        }
      }
    }
    setSolvedCount(count)
  }, [])

  const isSolved = (slug: string) => {
    return localStorage.getItem(`solved_${slug}`) === 'true'
  }

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 font-sans flex flex-col transition-colors duration-200">
      {/* Header / Navbar */}
      <header className="border-b border-zinc-200 dark:border-zinc-900 bg-white/80 dark:bg-zinc-900/20 backdrop-blur sticky top-0 z-50 px-6 py-4 flex items-center justify-between transition-colors">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded bg-gradient-to-tr from-orange-600 to-orange-400 flex items-center justify-center font-bold text-white shadow-lg shadow-orange-500/10">
            CF
          </div>
          <div>
            <span className="font-bold text-lg text-zinc-900 dark:text-white tracking-tight">CodeForge</span>
            <span className="text-zinc-500 text-xs ml-1 font-mono">v0.1.0</span>
          </div>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <a
            href="https://github.com"
            target="_blank"
            rel="noreferrer"
            className="text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white transition-colors"
          >
            GitHub
          </a>
          <button
            onClick={toggleTheme}
            className="p-1.5 rounded-lg bg-zinc-100 dark:bg-zinc-900 text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white border border-zinc-200 dark:border-zinc-800 transition-colors"
            aria-label="Toggle Theme"
          >
            {theme === 'dark' ? (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m0-12.728l.707.707m12.728 12.728l.707.707M12 8a4 4 0 100 8 4 4 0 000-8z" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
              </svg>
            )}
          </button>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-5xl w-full mx-auto px-6 py-10 flex flex-col gap-8">
        {/* Intro Hero Section */}
        <div className="flex flex-col gap-2">
          <h1 className="text-3xl font-extrabold text-zinc-900 dark:text-white tracking-tight md:text-4xl">
            Striver's A2Z Sheet Practice
          </h1>
          <p className="text-zinc-600 dark:text-zinc-400 text-sm md:text-base max-w-2xl leading-relaxed">
            Write, compile, and run Java code directly in your browser. Every submission is executed inside an ephemeral Docker container sandbox. Get started by picking a challenge below.
          </p>
        </div>

        {/* Statistics & Progress */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800/80 rounded-xl p-5 flex flex-col gap-3 relative overflow-hidden shadow-sm dark:shadow-none">
            <div className="absolute right-0 top-0 w-24 h-24 bg-orange-500/5 rounded-full blur-xl"></div>
            <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Overall Progress</span>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-zinc-900 dark:text-white">{solvedCount}</span>
              <span className="text-zinc-500 dark:text-zinc-400 text-sm">/ {problems.length || 3} solved</span>
            </div>
            {/* Progress bar */}
            <div className="w-full bg-zinc-100 dark:bg-zinc-800 h-2 rounded-full overflow-hidden">
              <div
                className="bg-orange-500 h-full rounded-full transition-all duration-500"
                style={{
                  width: `${problems.length > 0 ? (solvedCount / problems.length) * 100 : 0}%`,
                }}
              ></div>
            </div>
          </div>

          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800/80 rounded-xl p-5 flex flex-col gap-2 shadow-sm dark:shadow-none">
            <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Active Language</span>
            <div className="flex items-center gap-2 mt-1">
              <div className="w-6 h-6 rounded bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-xs font-semibold text-orange-600 dark:text-orange-400 font-mono border border-zinc-200/50 dark:border-transparent">
                J
              </div>
              <span className="text-zinc-800 dark:text-white font-medium text-sm">Java 21</span>
            </div>
            <span className="text-zinc-500 dark:text-zinc-400 text-xs mt-1">C++ and Python coming in Phase 2</span>
          </div>

          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800/80 rounded-xl p-5 flex flex-col gap-2 shadow-sm dark:shadow-none">
            <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Sandbox Engine</span>
            <div className="flex items-center gap-2 mt-1">
              <div className="w-2.5 h-2.5 rounded-full bg-green-500 animate-pulse"></div>
              <span className="text-zinc-850 dark:text-white font-medium text-sm">Active & Secure</span>
            </div>
            <span className="text-zinc-500 dark:text-zinc-400 text-xs mt-1">Cgroups + Capabilities limits active</span>
          </div>
        </div>

        {/* Problems List Table */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800/80 rounded-xl overflow-hidden shadow-sm dark:shadow-xl">
          <div className="px-6 py-4 border-b border-zinc-200 dark:border-zinc-800/80 bg-zinc-50/50 dark:bg-zinc-900/60 flex items-center justify-between">
            <h2 className="font-bold text-zinc-900 dark:text-white">Problem Set</h2>
            <span className="text-xs bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400 px-2 py-0.5 rounded-full font-medium">
              {problems.length} Available
            </span>
          </div>

          {loading ? (
            <div className="flex flex-col items-center justify-center p-20 gap-3">
              <div className="w-8 h-8 rounded-full border-4 border-orange-500/10 border-t-orange-500 animate-spin"></div>
              <span className="text-zinc-550 dark:text-zinc-500 text-sm font-medium">Loading problems…</span>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-zinc-200 dark:border-zinc-800/60 text-xs font-semibold text-zinc-500 dark:text-zinc-400 bg-zinc-50/85 dark:bg-zinc-900/20 uppercase tracking-wider">
                    <th className="px-6 py-3.5 w-[80px] text-center">Status</th>
                    <th className="px-6 py-3.5">Problem Title</th>
                    <th className="px-6 py-3.5 w-[140px]">Difficulty</th>
                    <th className="px-6 py-3.5 w-[140px]">Language</th>
                    <th className="px-6 py-3.5 w-[120px] text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-200/60 dark:divide-zinc-800/40 text-sm">
                  {problems.map((problem) => {
                    const solved = isSolved(problem.slug)
                    return (
                      <tr
                        key={problem.id}
                        className="hover:bg-zinc-50 dark:hover:bg-zinc-850/30 transition-colors group"
                      >
                        <td className="px-6 py-4 text-center">
                          {solved ? (
                            <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-green-500/10 text-green-600 dark:text-green-400 border border-green-500/20">
                              ✓
                            </span>
                          ) : (
                            <span className="text-zinc-400 dark:text-zinc-600 font-light">—</span>
                          )}
                        </td>
                        <td className="px-6 py-4">
                          <Link
                            to={`/problems/${problem.slug}`}
                            className="font-semibold text-zinc-800 dark:text-white group-hover:text-orange-600 dark:group-hover:text-orange-400 transition-colors"
                          >
                            {problem.title}
                          </Link>
                        </td>
                        <td className="px-6 py-4">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium uppercase border
                              ${
                                problem.difficulty === 'easy'
                                  ? 'bg-green-500/5 text-green-600 dark:text-green-400 border-green-500/15'
                                  : problem.difficulty === 'medium'
                                    ? 'bg-yellow-500/5 text-yellow-600 dark:text-yellow-400 border-yellow-500/15'
                                    : 'bg-red-500/5 text-red-600 dark:text-red-400 border-red-500/15'
                              }`}
                          >
                            {problem.difficulty}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-zinc-500 dark:text-zinc-400 font-mono text-xs">Java</td>
                        <td className="px-6 py-4 text-right">
                          <Link
                            to={`/problems/${problem.slug}`}
                            className="inline-flex items-center justify-center bg-orange-500 hover:bg-orange-600 text-white font-semibold text-xs px-3.5 py-1.5 rounded transition-all shadow-md hover:shadow-orange-500/10"
                          >
                            Solve
                          </Link>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
