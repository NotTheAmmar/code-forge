import { useEffect, useState, useCallback, useRef } from 'react'
import { useParams, Link, useSearchParams } from 'react-router-dom'
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels'
import {
  getProblem,
  runCode,
  submitCode,
  getSubmission,
  getSubmissionHistory,
  getLabSession,
  runCustomInput,
  ProblemDetail,
  Submission,
  SubmissionSummary,
  LabSessionDetail,
  Language,
  RunCustomResponse,
} from '../api/client'
import ProblemDescription from '../components/ProblemDescription'
import AITutorPanel from '../components/AITutorPanel'
import CodeEditor, { KeybindingMode } from '../components/CodeEditor'
import TestCasePanel from '../components/TestCasePanel'
import Navbar from '../components/Navbar'
import { useWebSocket } from '../hooks/useWebSocket'

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
  const courseIdParam = searchParams.get('courseId')
  const moduleId = searchParams.get('moduleId')

  const [problem, setProblem] = useState<ProblemDetail | null>(null)
  const [code, setCode] = useState<string>('')
  const [language, setLanguage] = useState<Language>('python')
  const [keybindingMode, setKeybindingMode] = useState<KeybindingMode>('vscode')
  const [draftSaved, setDraftSaved] = useState<boolean>(false)

  const [history, setHistory] = useState<SubmissionSummary[]>([])
  const [pageLoading, setPageLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [rightTab, setRightTab] = useState<RightTab>('editor')
  const [leftTab, setLeftTab] = useState<'description' | 'ai-tutor'>('description')
  const [badgeToast, setBadgeToast] = useState<{ count: number } | null>(null)
  const [labSession, setLabSession] = useState<LabSessionDetail | null>(null)
  const [labTimeLeft, setLabTimeLeft] = useState<string>('')

  // Custom Input State
  const [customRunning, setCustomRunning] = useState<boolean>(false)
  const [customResult, setCustomResult] = useState<RunCustomResponse | null>(null)

  // Real-Time WebSocket Hook
  const {
    submission: wsSubmission,
    loading: wsLoading,
    progress: liveProgress,
    startTracking,
  } = useWebSocket()

  const [selectedHistoricalSub, setSelectedHistoricalSub] = useState<Submission | null>(null)
  const currentSubmission = selectedHistoricalSub || wsSubmission

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

  // Helper to get default starter code for language
  const getStarterCode = useCallback((prob: ProblemDetail, lang: Language): string => {
    switch (lang) {
      case 'python':
        return prob.starter_code_python ?? `import sys\n\ndef main():\n    # Your solution here\n    pass\n\nif __name__ == '__main__':\n    main()`
      case 'c':
        return prob.starter_code_c ?? `#include <stdio.h>\n\nint main() {\n    // Your solution here\n    return 0;\n}`
      case 'cpp':
        return prob.starter_code_cpp ?? `#include <iostream>\nusing namespace std;\n\nint main() {\n    // Your solution here\n    return 0;\n}`
      case 'java':
      default:
        return prob.starter_code_java ?? `import java.util.Scanner;\n\npublic class Solution {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        // Your code here\n    }\n}`
    }
  }, [])

  // Load problem on mount
  useEffect(() => {
    if (!slug) return
    setPageLoading(true)
    getProblem(slug)
      .then((data) => {
        setProblem(data)
        // Check for saved draft
        const draftKey = `cf_draft_${slug}_${language}`
        const savedDraft = localStorage.getItem(draftKey)
        if (savedDraft) {
          setCode(savedDraft)
          setDraftSaved(true)
        } else {
          setCode(getStarterCode(data, language))
        }
        setPageLoading(false)
      })
      .catch((err) => {
        console.error(err)
        setError('Failed to load problem details. Please check connection.')
        setPageLoading(false)
      })
  }, [slug, language, getStarterCode])

  // Auto-save draft on code changes (debounced)
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const handleCodeChange = (newCode: string) => {
    setCode(newCode)
    setDraftSaved(false)
    if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current)
    saveTimeoutRef.current = setTimeout(() => {
      if (slug) {
        localStorage.setItem(`cf_draft_${slug}_${language}`, newCode)
        setDraftSaved(true)
      }
    }, 600)
  }

  // Refresh submission history whenever a submission completes
  const refreshHistory = useCallback(() => {
    if (!slug) return
    getSubmissionHistory(slug).then(setHistory).catch(() => {})
  }, [slug])

  // Handle language switch
  const handleLanguageChange = (newLang: Language) => {
    if (newLang === language) return
    setLanguage(newLang)
    if (!problem) return
    const draftKey = `cf_draft_${slug}_${newLang}`
    const savedDraft = localStorage.getItem(draftKey)
    if (savedDraft) {
      setCode(savedDraft)
      setDraftSaved(true)
    } else {
      setCode(getStarterCode(problem, newLang))
      setDraftSaved(false)
    }
  }

  // Check badges when wsSubmission completes
  useEffect(() => {
    if (wsSubmission?.status === 'completed') {
      if (wsSubmission.score === 100 && slug) {
        localStorage.setItem(`solved_${slug}`, 'true')
      }
      if (wsSubmission.badge_awarded && wsSubmission.new_badge_count !== null) {
        setBadgeToast({ count: wsSubmission.new_badge_count })
      }
      refreshHistory()
    }
  }, [wsSubmission, slug, refreshHistory])

  // Execution triggers using WebSocket
  const handleRun = () => {
    if (!slug || !code) return
    setSelectedHistoricalSub(null)
    runCode(slug, code, language)
      .then((res) => startTracking(res.submission_id))
      .catch((err) => console.error(err))
  }

  const handleSubmit = () => {
    if (!slug || !code) return
    setSelectedHistoricalSub(null)
    submitCode(slug, code, language, labId ?? undefined)
      .then((res) => startTracking(res.submission_id))
      .catch((err) => console.error(err))
  }

  const handleCustomInputRun = async (stdin: string) => {
    if (!slug || !code) return
    setCustomRunning(true)
    setCustomResult(null)
    try {
      const res = await runCustomInput(slug, code, language, stdin)
      setCustomResult(res)
    } catch (err) {
      console.error(err)
    } finally {
      setCustomRunning(false)
    }
  }

  const handleHistorySelect = (id: string) => {
    getSubmission(id)
      .then((sub) => {
        setSelectedHistoricalSub(sub)
        setRightTab('editor')
      })
      .catch(() => {})
  }

  const filenameMap: Record<Language, string> = {
    java: 'Solution.java',
    python: 'solution.py',
    c: 'solution.c',
    cpp: 'solution.cpp',
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
      <Navbar
        customTitle={problem?.title || 'Loading...'}
        backTo={
          labId
            ? `/labs/${labId}`
            : moduleId
            ? `/modules/${moduleId}`
            : courseIdParam || problem?.course_id
            ? `/courses/${courseIdParam || problem?.course_id}?tab=problems`
            : '/'
        }
        backLabel={
          labId
            ? 'Lab'
            : moduleId
            ? 'Module'
            : courseIdParam || problem?.course_id
            ? 'Course'
            : 'Courses'
        }
      />

      {/* Split Pane Workspace */}
      <div className="flex-1 min-h-0 relative bg-zinc-50 dark:bg-zinc-950">
        {error ? (
          <div className="absolute inset-0 flex items-center justify-center p-6 text-center">
            <div className="max-w-md bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-6 flex flex-col gap-4 shadow-md">
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
        ) : !problem || pageLoading ? (
          <div className="absolute inset-0 flex items-center justify-center gap-3">
            <div className="w-8 h-8 rounded-full border-4 border-orange-500/10 border-t-orange-500 animate-spin" />
            <span className="text-zinc-500 text-sm font-medium">Loading workspace…</span>
          </div>
        ) : (
          <PanelGroup direction="horizontal">
            {/* Left Pane - Description or AI Tutor */}
            <Panel defaultSize={42} minSize={25} className="flex flex-col bg-white dark:bg-zinc-950 border-r border-zinc-200 dark:border-zinc-800">
              <div className="h-10 bg-zinc-50 dark:bg-zinc-900/40 border-b border-zinc-200 dark:border-zinc-900 flex items-center justify-between px-4 shrink-0">
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setLeftTab('description')}
                    className={`px-3 py-1 rounded text-xs font-semibold uppercase tracking-wider transition-all ${
                      leftTab === 'description'
                        ? 'bg-white dark:bg-zinc-800 text-zinc-900 dark:text-white shadow-sm border border-zinc-200 dark:border-zinc-700'
                        : 'text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200'
                    }`}
                  >
                    📖 Problem
                  </button>
                  <button
                    onClick={() => setLeftTab('ai-tutor')}
                    className={`flex items-center gap-1 px-3 py-1 rounded text-xs font-semibold uppercase tracking-wider transition-all ${
                      leftTab === 'ai-tutor'
                        ? 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border border-orange-500/30 shadow-sm'
                        : 'text-zinc-500 hover:text-orange-600 dark:hover:text-orange-400'
                    }`}
                  >
                    <span>✨ AI Tutor</span>
                  </button>
                </div>
              </div>

              <div className="flex-1 min-h-0 overflow-hidden">
                {leftTab === 'description' ? (
                  <ProblemDescription
                    title={problem.title}
                    difficulty={problem.difficulty}
                    description={problem.description}
                  />
                ) : (
                  <AITutorPanel
                    problemSlug={problem.slug}
                    problemTitle={problem.title}
                    currentCode={code}
                    currentLanguage={language}
                  />
                )}
              </div>
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
                    {/* File name & Auto-save pill */}
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider font-mono">
                        {filenameMap[language]}
                      </span>
                      {draftSaved && (
                        <span className="text-[10px] text-green-500 flex items-center gap-1 font-sans">
                          <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                          Saved
                        </span>
                      )}
                    </div>

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

                    {/* Keybinding Selector & Language selector */}
                    <div className="flex items-center gap-2 shrink-0">
                      {/* Keybindings */}
                      <select
                        value={keybindingMode}
                        onChange={(e) => setKeybindingMode(e.target.value as KeybindingMode)}
                        aria-label="Editor Keybindings"
                        className="text-[10px] bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded px-1.5 py-0.5 text-zinc-600 dark:text-zinc-300 focus:outline-none"
                      >
                        <option value="vscode">VS Code</option>
                        <option value="vim">Vim</option>
                        <option value="emacs">Emacs</option>
                      </select>

                      {/* Languages: Java, Python, C, C++ */}
                      <div className="flex items-center gap-1">
                        {(['python', 'java', 'c', 'cpp'] as Language[]).map((lang) => (
                          <button
                            key={lang}
                            onClick={() => handleLanguageChange(lang)}
                            className={`text-[10px] px-2 py-0.5 rounded font-mono border transition-all uppercase ${
                              language === lang
                                ? 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/30 font-bold'
                                : 'text-zinc-400 dark:text-zinc-500 border-zinc-200 dark:border-zinc-800 hover:border-zinc-400'
                            }`}
                          >
                            {lang === 'cpp' ? 'C++' : lang}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Editor or History */}
                  <div className="flex-1 min-h-0 relative">
                    {rightTab === 'editor' ? (
                      <CodeEditor
                        value={code}
                        onChange={handleCodeChange}
                        language={language}
                        keybindingMode={keybindingMode}
                      />
                    ) : (
                      <div className="absolute inset-0 bg-white dark:bg-zinc-950">
                        <HistoryPanel history={history} onSelect={handleHistorySelect} />
                      </div>
                    )}
                  </div>

                  {/* Action Buttons Toolbar at bottom of Editor */}
                  <div className="h-14 border-t border-zinc-200 dark:border-zinc-900 bg-zinc-50/50 dark:bg-zinc-950/60 px-4 flex items-center justify-between shrink-0">
                    <div className="text-[11px] text-zinc-400 flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-green-500" />
                      <span>Ready in Docker Sandbox ({language.toUpperCase()})</span>
                    </div>

                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => setLeftTab('ai-tutor')}
                        className="inline-flex items-center gap-1.5 px-3 py-2 border border-orange-500/20 hover:border-orange-500/50 bg-orange-500/5 hover:bg-orange-500/10 text-orange-600 dark:text-orange-400 rounded text-xs font-semibold tracking-wider uppercase transition-all shadow-sm"
                        title="Ask Socratic AI Tutor for conceptual help"
                      >
                        <span>✨ AI Tutor</span>
                      </button>
                      <button
                        onClick={handleRun}
                        disabled={wsLoading}
                        className="inline-flex items-center gap-1.5 px-4 py-2 border border-zinc-300 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-900 hover:border-zinc-400 dark:hover:border-zinc-700 text-zinc-700 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-white rounded text-xs font-semibold tracking-wider uppercase transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
                      >
                        <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M8 5v14l11-7z" />
                        </svg>
                        Run
                      </button>
                      <button
                        onClick={handleSubmit}
                        disabled={wsLoading}
                        className="inline-flex items-center gap-1.5 px-5 py-2 bg-orange-600 hover:bg-orange-500 text-white rounded text-xs font-semibold tracking-wider uppercase transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-orange-500/10"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        Submit
                      </button>
                    </div>
                  </div>
                </Panel>

                {/* Resize handle horizontal */}
                <PanelResizeHandle className="h-1.5 hover:h-2 bg-zinc-200 dark:bg-zinc-900 hover:bg-orange-500/40 active:bg-orange-500 transition-all cursor-row-resize shrink-0" />

                {/* Test Results & Custom Input Pane */}
                <Panel defaultSize={40} minSize={20} className="bg-white dark:bg-zinc-950">
                  <TestCasePanel
                    submission={currentSubmission}
                    loading={wsLoading}
                    testCases={problem.test_cases}
                    liveProgress={liveProgress}
                    onRunCustomInput={handleCustomInputRun}
                    customRunning={customRunning}
                    customResult={customResult}
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
