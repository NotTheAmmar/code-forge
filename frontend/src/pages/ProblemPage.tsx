import { useEffect, useState, useRef, useCallback } from 'react'
import { useParams, Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels'
import {
  getProblem,
  runCode,
  submitCode,
  getSubmission,
  getSubmissionHistory,
  getLabSession,
  ProblemDetail,
  Submission,
  SubmissionSummary,
  LabSessionDetail,
  Language,
} from '../api/client'
import ProblemDescription from '../components/ProblemDescription'
import CodeEditor from '../components/CodeEditor'
import TestCasePanel from '../components/TestCasePanel'
import { useTheme } from '../context/ThemeContext'
import { useAuth } from '../context/AuthContext'

// ── Badge Toast ───────────────────────────────────────────────────────────────

function BadgeToast({ count, onClose }: { count: number; onClose: () => void }) {
  useEffect(() => {
    const t = setTimeout(onClose, 5000)
    return () => clearTimeout(t)
  }, [onClose])

  return (
    <div className="fixed bottom-6 right-6 z-50 flex items-center gap-3 bg-zinc-900 border border-orange-500/30 shadow-2xl shadow-orange-500/10 rounded-xl px-5 py-4 animate-in slide-in-from-bottom-4 fade-in duration-300">
      <div className="text-2xl">🏅</div>
      <div>
        <p className="text-white font-semibold text-sm">Badge Earned!</p>
        <p className="text-zinc-400 text-xs">You now have {count} badge{count !== 1 ? 's' : ''} in this lab session</p>
      </div>
      <button onClick={onClose} className="ml-2 text-zinc-500 hover:text-zinc-300 transition-colors text-lg leading-none">×</button>
    </div>
  )
}

// ── Submission History Panel ──────────────────────────────────────────────────

function HistoryPanel({ history, onSelect }: { history: SubmissionSummary[]; onSelect: (id: string) => void }) {
  const statusColor: Record<string, string> = {
    completed: 'text-green-500',
    compile_error: 'text-red-400',
    timeout: 'text-yellow-400',
    error: 'text-red-400',
    running: 'text-blue-400',
    queued: 'text-zinc-400',
  }

  if (history.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-2 text-zinc-500 text-sm">
        <svg className="w-8 h-8 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
        <span>No submissions yet</span>
      </div>
    )
  }

  return (
    <div className="overflow-y-auto h-full">
      <table className="w-full text-xs">
        <thead className="sticky top-0 bg-zinc-50 dark:bg-zinc-900/80 border-b border-zinc-200 dark:border-zinc-800">
          <tr className="text-zinc-500 dark:text-zinc-400 uppercase tracking-wider text-[10px]">
            <th className="px-4 py-2 text-left font-semibold">Status</th>
            <th className="px-4 py-2 text-left font-semibold">Score</th>
            <th className="px-4 py-2 text-left font-semibold">Type</th>
            <th className="px-4 py-2 text-left font-semibold">Lang</th>
            <th className="px-4 py-2 text-left font-semibold">When</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-200/50 dark:divide-zinc-800/40">
          {history.map((s) => (
            <tr
              key={s.id}
              onClick={() => onSelect(s.id)}
              className="hover:bg-zinc-50 dark:hover:bg-zinc-800/40 cursor-pointer transition-colors group"
            >
              <td className={`px-4 py-2.5 font-semibold ${statusColor[s.status] ?? 'text-zinc-400'}`}>
                <div className="flex items-center gap-1.5">
                  {s.is_best && <span className="text-orange-400" title="Best submission">★</span>}
                  <span className="capitalize">{s.status.replace('_', ' ')}</span>
                </div>
              </td>
              <td className="px-4 py-2.5 text-zinc-700 dark:text-zinc-300 font-mono">
                {s.score !== null ? `${s.score}%` : '—'}
              </td>
              <td className="px-4 py-2.5 text-zinc-500 dark:text-zinc-400">
                {s.is_full_submit ? 'Submit' : 'Run'}
              </td>
              <td className="px-4 py-2.5 text-zinc-500 dark:text-zinc-400 font-mono uppercase">
                {s.language}
              </td>
              <td className="px-4 py-2.5 text-zinc-400 dark:text-zinc-500">
                {new Date(s.submitted_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Main ProblemPage ──────────────────────────────────────────────────────────

type RightTab = 'editor' | 'history'

export default function ProblemPage() {
  const { slug } = useParams<{ slug: string }>()
  const [searchParams] = useSearchParams()
  const labId = searchParams.get('lab')
  const navigate = useNavigate()
  const [problem, setProblem] = useState<ProblemDetail | null>(null)
  const [code, setCode] = useState<string>('')
  const [language, setLanguage] = useState<Language>('java')
  const [submission, setSubmission] = useState<Submission | null>(null)
  const [history, setHistory] = useState<SubmissionSummary[]>([])
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [rightTab, setRightTab] = useState<RightTab>('editor')
  const [badgeToast, setBadgeToast] = useState<{ count: number } | null>(null)
  const [labSession, setLabSession] = useState<LabSessionDetail | null>(null)
  const [labTimeLeft, setLabTimeLeft] = useState<string>('')
  const pollIntervalRef = useRef<number | null>(null)
  const { theme, toggleTheme } = useTheme()
  const { user, logout } = useAuth()

  // Load lab session if labId is present
  useEffect(() => {
    if (!labId) return
    getLabSession(labId).then(setLabSession).catch(() => {})
  }, [labId])

  // Countdown timer for active lab session
  useEffect(() => {
    if (!labSession) return
    const tick = () => {
      const end = new Date(labSession.ends_at).getTime()
      const diff = end - Date.now()
      if (diff <= 0) {
        setLabTimeLeft('Ended')
        return
      }
      const h = Math.floor(diff / 3600000)
      const m = Math.floor((diff % 3600000) / 60000)
      const s = Math.floor((diff % 60000) / 1000)
      setLabTimeLeft(`${h}h ${m}m ${s}s`)
    }
    tick()
    const iv = setInterval(tick, 1000)
    return () => clearInterval(iv)
  }, [labSession])

  // Load problem on mount
  useEffect(() => {
    if (!slug) return
    setLoading(true)
    getProblem(slug)
      .then((data) => {
        setProblem(data)
        setCode(data.starter_code_java)
        setLoading(false)
      })
      .catch((err) => {
        console.error(err)
        setError('Failed to load problem details. Please check the backend connection.')
        setLoading(false)
      })

    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)
    }
  }, [slug])

  // Refresh submission history whenever a submission completes
  const refreshHistory = useCallback(() => {
    if (!slug) return
    getSubmissionHistory(slug).then(setHistory).catch(() => {})
  }, [slug])

  // Update starter code when language changes
  useEffect(() => {
    if (!problem) return
    if (language === 'python') {
      setCode(problem.starter_code_python ?? '# Your solution here\n')
    } else {
      setCode(problem.starter_code_java)
    }
  }, [language, problem])

  const startPolling = (submissionId: string, isSubmit: boolean) => {
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)
    setLoading(true)
    pollIntervalRef.current = window.setInterval(() => {
      getSubmission(submissionId)
        .then((sub) => {
          setSubmission(sub)
          if (sub.status !== 'queued' && sub.status !== 'running') {
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current)
              pollIntervalRef.current = null
            }
            setLoading(false)

            // Mark as solved in localStorage
            if (isSubmit && sub.status === 'completed' && sub.score === 100) {
              localStorage.setItem(`solved_${slug}`, 'true')
            }

            // Show badge toast
            if (sub.badge_awarded && sub.new_badge_count !== null) {
              setBadgeToast({ count: sub.new_badge_count })
            }

            refreshHistory()
          }
        })
        .catch((err) => {
          console.error(err)
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current)
            pollIntervalRef.current = null
          }
          setLoading(false)
        })
    }, 1000)
  }

  const handleRun = () => {
    if (!slug || !code) return
    setSubmission(null)
    setLoading(true)
    runCode(slug, code, language)
      .then((res) => startPolling(res.submission_id, false))
      .catch((err) => { console.error(err); setLoading(false) })
  }

  const handleSubmit = () => {
    if (!slug || !code) return
    setSubmission(null)
    setLoading(true)
    submitCode(slug, code, language, labId ?? undefined)
      .then((res) => startPolling(res.submission_id, true))
      .catch((err) => { console.error(err); setLoading(false) })
  }

  const handleHistorySelect = (id: string) => {
    setLoading(true)
    getSubmission(id)
      .then((sub) => {
        setSubmission(sub)
        setRightTab('editor')
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="h-screen w-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 flex flex-col overflow-hidden font-sans transition-colors duration-200">
      {/* Student Lab Mode Banner */}
      {labSession && (
        <div className="bg-gradient-to-r from-orange-500 via-amber-500 to-orange-600 text-white px-5 py-2 flex items-center justify-between text-xs font-medium shrink-0 shadow-sm animate-in slide-in-from-top duration-300">
          <div className="flex items-center gap-2.5">
            <span className="w-2 h-2 rounded-full bg-white animate-pulse" />
            <span className="font-bold tracking-wider uppercase text-[10px] bg-black/20 px-2 py-0.5 rounded">Lab Mode</span>
            <span className="font-semibold">{labSession.title}</span>
            <span className="opacity-80 hidden sm:inline">({labSession.topic})</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-mono bg-black/20 px-2 py-0.5 rounded text-[11px] font-semibold">{labTimeLeft}</span>
            <Link
              to={`/labs/${labId}`}
              className="text-white hover:text-orange-100 underline decoration-white/60 text-[11px] font-semibold transition"
            >
              Lab Overview →
            </Link>
          </div>
        </div>
      )}

      {/* Header */}
      <header className="h-14 border-b border-zinc-200 dark:border-zinc-900 bg-white dark:bg-zinc-950 flex items-center justify-between px-6 shrink-0 transition-colors">
        <div className="flex items-center gap-4">
          <Link
            to={labId ? `/labs/${labId}` : "/"}
            className="flex items-center gap-1.5 text-zinc-500 dark:text-zinc-400 hover:text-zinc-950 dark:hover:text-white transition-colors text-xs font-semibold uppercase tracking-wider"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            {labId ? 'Back to Lab' : 'Problems'}
          </Link>
          <div className="h-4 w-[1px] bg-zinc-200 dark:bg-zinc-800" />
          <span className="font-bold text-sm tracking-tight text-zinc-900 dark:text-white">{problem?.title || 'Loading...'}</span>
        </div>

        <div className="flex items-center gap-3">
          {/* User chip */}
          {user && (
            <div className="hidden sm:flex items-center gap-2 text-xs text-zinc-500 dark:text-zinc-400">
              <div className="w-6 h-6 rounded-full bg-orange-500/10 border border-orange-500/20 flex items-center justify-center font-bold text-orange-600 dark:text-orange-400 text-[10px]">
                {user.name.charAt(0).toUpperCase()}
              </div>
              <span>{user.name}</span>
            </div>
          )}

          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            className="p-1.5 rounded-lg bg-zinc-100 dark:bg-zinc-900 text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white border border-zinc-200 dark:border-zinc-805 transition-colors"
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

          {/* Logout */}
          <button
            onClick={handleLogout}
            className="text-xs text-zinc-500 dark:text-zinc-400 hover:text-red-500 dark:hover:text-red-400 transition-colors font-medium"
          >
            Sign out
          </button>
        </div>
      </header>

      {/* Split Pane Workspace */}
      <div className="flex-1 min-h-0 relative bg-zinc-50 dark:bg-zinc-950">
        {error ? (
          <div className="absolute inset-0 flex items-center justify-center p-6 text-center">
            <div className="max-w-md bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-6 flex flex-col gap-4 shadow-md dark:shadow-none">
              <h2 className="text-red-500 dark:text-red-400 font-bold text-lg">Error</h2>
              <p className="text-zinc-600 dark:text-zinc-400 text-sm">{error}</p>
              <Link
                to="/"
                className="bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 border border-zinc-200 dark:border-zinc-700 text-zinc-850 dark:text-white font-medium px-4 py-2 rounded text-sm transition-colors"
              >
                Back to Dashboard
              </Link>
            </div>
          </div>
        ) : !problem ? (
          <div className="absolute inset-0 flex items-center justify-center gap-3">
            <div className="w-8 h-8 rounded-full border-4 border-orange-500/10 border-t-orange-500 animate-spin" />
            <span className="text-zinc-500 text-sm font-medium">Loading workspace…</span>
          </div>
        ) : (
          <PanelGroup direction="horizontal">
            {/* Left Pane - Description */}
            <Panel defaultSize={42} minSize={25} className="bg-white dark:bg-zinc-950">
              <ProblemDescription
                title={problem.title}
                difficulty={problem.difficulty}
                description={problem.description}
              />
            </Panel>

            {/* Resize handle vertical */}
            <PanelResizeHandle className="w-1.5 hover:w-2 bg-zinc-200 dark:bg-zinc-900 hover:bg-orange-500/40 active:bg-orange-500 transition-all cursor-col-resize shrink-0" />

            {/* Right Pane - Editor + Results */}
            <Panel defaultSize={58} minSize={30}>
              <PanelGroup direction="vertical">
                {/* Monaco Editor Pane */}
                <Panel defaultSize={60} minSize={30} className="flex flex-col bg-white dark:bg-zinc-950">
                  {/* Editor Header Toolbar */}
                  <div className="h-10 bg-zinc-50 dark:bg-zinc-900/40 border-b border-zinc-200 dark:border-zinc-900 flex items-center justify-between px-4 shrink-0 gap-3">
                    {/* File name */}
                    <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider font-mono shrink-0">
                      {language === 'java' ? 'Solution.java' : 'solution.py'}
                    </span>

                    {/* Tabs: Editor / History */}
                    <div className="flex items-center bg-zinc-100 dark:bg-zinc-800 rounded-md p-0.5 gap-0.5">
                      {(['editor', 'history'] as RightTab[]).map((tab) => (
                        <button
                          key={tab}
                          onClick={() => {
                            setRightTab(tab)
                            if (tab === 'history') refreshHistory()
                          }}
                          className={`px-2.5 py-1 rounded text-[10px] font-semibold uppercase tracking-wider transition-all capitalize ${
                            rightTab === tab
                              ? 'bg-white dark:bg-zinc-700 text-zinc-900 dark:text-white shadow-sm'
                              : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200'
                          }`}
                        >
                          {tab}
                        </button>
                      ))}
                    </div>

                    {/* Language selector */}
                    <div className="flex items-center gap-1.5 shrink-0">
                      {(['java', 'python'] as Language[]).map((lang) => (
                        <button
                          key={lang}
                          onClick={() => setLanguage(lang)}
                          className={`text-[10px] px-2 py-0.5 rounded font-mono border transition-all uppercase ${
                            language === lang
                              ? 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/25'
                              : 'text-zinc-400 dark:text-zinc-500 border-zinc-200 dark:border-zinc-700 hover:border-zinc-300 dark:hover:border-zinc-600'
                          }`}
                        >
                          {lang === 'java' ? 'Java 21' : 'Python 3'}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Editor or History */}
                  <div className="flex-1 min-h-0 relative">
                    {rightTab === 'editor' ? (
                      <CodeEditor value={code} onChange={setCode} language={language === 'java' ? 'java' : 'python'} />
                    ) : (
                      <div className="absolute inset-0 bg-white dark:bg-zinc-950">
                        <HistoryPanel history={history} onSelect={handleHistorySelect} />
                      </div>
                    )}
                  </div>

                  {/* Action Buttons Toolbar at bottom of Editor */}
                  <div className="h-14 border-t border-zinc-200 dark:border-zinc-900 bg-zinc-50/50 dark:bg-zinc-950/60 px-4 flex items-center justify-end gap-3 shrink-0">
                    <button
                      onClick={handleRun}
                      disabled={loading}
                      className="inline-flex items-center gap-1.5 px-4 py-2 border border-zinc-300 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-900 hover:border-zinc-450 dark:hover:border-zinc-700 text-zinc-700 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-white rounded text-xs font-semibold tracking-wider uppercase transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M8 5v14l11-7z" />
                      </svg>
                      Run
                    </button>
                    <button
                      onClick={handleSubmit}
                      disabled={loading}
                      className="inline-flex items-center gap-1.5 px-5 py-2 bg-orange-500 hover:bg-orange-600 text-white rounded text-xs font-semibold tracking-wider uppercase transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-orange-500/5 hover:shadow-orange-500/10"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      Submit
                    </button>
                  </div>
                </Panel>

                {/* Resize handle horizontal */}
                <PanelResizeHandle className="h-1.5 hover:h-2 bg-zinc-200 dark:bg-zinc-900 hover:bg-orange-500/40 active:bg-orange-500 transition-all cursor-row-resize shrink-0" />

                {/* Test Results Pane */}
                <Panel defaultSize={40} minSize={20} className="bg-white dark:bg-zinc-950">
                  <TestCasePanel
                    submission={submission}
                    loading={loading && !!pollIntervalRef.current}
                    testCases={problem.test_cases}
                  />
                </Panel>
              </PanelGroup>
            </Panel>
          </PanelGroup>
        )}
      </div>

      {/* Badge Toast */}
      {badgeToast && (
        <BadgeToast count={badgeToast.count} onClose={() => setBadgeToast(null)} />
      )}
    </div>
  )
}
