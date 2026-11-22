import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels'
import { useAuth } from '../context/AuthContext'
import {
  getExamDetail,
  startExamSession,
  submitExamSession,
  logExamViolation,
  runCode,
  submitCode,
  ExamDetail,
  ExamProblem,
  Language,
} from '../api/client'
import CodeEditor from '../components/CodeEditor'
import ProblemDescription from '../components/ProblemDescription'
import TestCasePanel from '../components/TestCasePanel'
import { useWebSocket } from '../hooks/useWebSocket'

export default function ExamPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()

  // Instructors must not take exams; redirect them to results & audit dashboard
  useEffect(() => {
    if (user?.role === 'instructor' && id) {
      navigate(`/exams/${id}/results`, { replace: true })
    }
  }, [user, id, navigate])

  // Exam info & session state
  const [exam, setExam] = useState<ExamDetail | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [isStarted, setIsStarted] = useState<boolean>(false)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  // Problems & Active problem state
  const [problems, setProblems] = useState<ExamProblem[]>([])
  const [activeProblemIndex, setActiveProblemIndex] = useState<number>(0)
  const [codes, setCodes] = useState<Record<string, string>>({})
  const [languages, setLanguages] = useState<Record<string, Language>>({})

  // Countdown timer state
  const [secondsRemaining, setSecondsRemaining] = useState<number>(0)
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false)
  const [confirmSubmitOpen, setConfirmSubmitOpen] = useState<boolean>(false)

  // Anti-cheat state
  const [fullscreenAlert, setFullscreenAlert] = useState<boolean>(false)
  const [violationsCount, setViolationsCount] = useState<number>(0)
  const [tabSwitchesCount, setTabSwitchesCount] = useState<number>(0)
  const [violationToast, setViolationToast] = useState<string | null>(null)

  // Real-time submission hook for testing code within the exam
  const {
    submission,
    loading: wsLoading,
    progress: liveProgress,
    startTracking,
  } = useWebSocket()

  // Fetch exam metadata on load
  useEffect(() => {
    if (!id) return
    setLoading(true)
    getExamDetail(id)
      .then((data) => {
        setExam(data)
        if (data.problems) {
          setProblems(data.problems)
          // Initialize starter codes
          const initialCodes: Record<string, string> = {}
          const initialLangs: Record<string, Language> = {}
          data.problems.forEach((p) => {
            initialCodes[p.id] = p.starter_code_python || `def main():\n    # Solution for ${p.title}\n    pass\n\nif __name__ == '__main__':\n    main()`
            initialLangs[p.id] = 'python'
          })
          setCodes(initialCodes)
          setLanguages(initialLangs)
        }
        setLoading(false)
      })
      .catch((err) => {
        console.error(err)
        setError('Failed to load exam details.')
        setLoading(false)
      })
  }, [id])

  // Timer countdown
  useEffect(() => {
    if (!isStarted || secondsRemaining <= 0) return

    const timer = setInterval(() => {
      setSecondsRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(timer)
          handleAutoSubmit()
          return 0
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(timer)
  }, [isStarted, secondsRemaining])

  // Helper for starter code
  const getProblemStarterCode = (prob: ExamProblem, lang: Language): string => {
    switch (lang) {
      case 'java':
        return prob.starter_code_java || `public class Solution {\n    public static void main(String[] args) {\n        // Code here\n    }\n}`
      case 'c':
        return prob.starter_code_c || `#include <stdio.h>\nint main() {\n    // Code here\n    return 0;\n}`
      case 'cpp':
        return prob.starter_code_cpp || `#include <iostream>\nusing namespace std;\nint main() {\n    // Code here\n    return 0;\n}`
      case 'python':
      default:
        return prob.starter_code_python || `def main():\n    # Code here\n    pass\n\nif __name__ == '__main__':\n    main()`
    }
  }

  // Anti-cheat: Enter fullscreen
  const requestFullscreen = async () => {
    try {
      if (document.documentElement.requestFullscreen) {
        await document.documentElement.requestFullscreen()
      }
      setFullscreenAlert(false)
    } catch (err) {
      console.warn('Fullscreen request blocked or failed:', err)
    }
  }

  // Anti-cheat: Start Exam Session
  const handleStartExam = async () => {
    if (!id) return
    try {
      setLoading(true)
      const session = await startExamSession(id)
      setSessionId(session.session_id)
      setSecondsRemaining(session.remaining_seconds || session.duration_seconds)
      if (session.problems && session.problems.length > 0) {
        setProblems(session.problems)
      }
      setIsStarted(true)
      setLoading(false)

      if (exam?.fullscreen_required) {
        requestFullscreen()
      }
    } catch (err) {
      console.error(err)
      setError('Unable to start exam session. Check your enrollment or time window.')
      setLoading(false)
    }
  }

  // Anti-cheat: Submit Exam
  const handleFinalSubmit = async (isAuto: boolean = false) => {
    if (!id) return
    setIsSubmitting(true)
    try {
      await submitExamSession(id, isAuto)
      if (document.fullscreenElement) {
        document.exitFullscreen().catch(() => {})
      }
      navigate(`/exams/${id}/my-result`)
    } catch (err) {
      console.error(err)
      setIsSubmitting(false)
    }
  }

  const handleAutoSubmit = useCallback(() => {
    handleFinalSubmit(true)
  }, [id])

  // Anti-cheat Event Listeners
  useEffect(() => {
    if (!isStarted || !sessionId) return

    let lastFocusLoss = 0
    const triggerFocusLoss = (details: string) => {
      const now = Date.now()
      if (now - lastFocusLoss < 1000) return
      lastFocusLoss = now

      setTabSwitchesCount((prev) => {
        const newCount = prev + 1
        setViolationsCount((v) => v + 1)
        setViolationToast(`⚠ Focus lost / Desktop switch detected (${newCount} switches)`)

        logExamViolation(sessionId, {
          violation_type: 'tab_switch',
          details: `${details}. Switch #${newCount}`,
        }).catch(() => {})

        setTimeout(() => setViolationToast(null), 4000)
        return newCount
      })
    }

    // 1. Tab switch / visibility loss
    const handleVisibilityChange = () => {
      if (document.hidden) {
        triggerFocusLoss('Visibility hidden (tab switched)')
      }
    }

    // 2. Desktop / workspace switch & window blur (Linux/Wayland, macOS, Windows)
    const handleWindowBlur = () => {
      triggerFocusLoss('Window blur / desktop switch')
    }

    // 3. Screenshot shortcut or PrintScreen key
    const handleKeyDown = (e: KeyboardEvent) => {
      const isPrintScreen = e.key === 'PrintScreen' || e.keyCode === 44
      const isScreenshot =
        (e.key.toLowerCase() === 's' && (e.shiftKey && (e.metaKey || e.ctrlKey))) ||
        (e.metaKey && e.shiftKey && (e.key === '3' || e.key === '4' || e.key === '5'))

      if (isPrintScreen || isScreenshot) {
        e.preventDefault()
        setViolationsCount((v) => v + 1)
        setViolationToast('⚠ Screenshot attempt detected & logged. Assessment integrity monitored.')
        logExamViolation(sessionId, {
          violation_type: 'focus_loss',
          details: `Screenshot attempt detected via ${isPrintScreen ? 'PrintScreen' : 'Shortcut'}`,
        }).catch(() => {})
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText('').catch(() => {})
        }
        setTimeout(() => setViolationToast(null), 4000)
      }
    }

    // 4. Fullscreen exit
    const handleFullscreenChange = () => {
      if (exam?.fullscreen_required && !document.fullscreenElement) {
        setFullscreenAlert(true)
        setViolationsCount((v) => v + 1)
        logExamViolation(sessionId, {
          violation_type: 'fullscreen_exit',
          details: 'User exited fullscreen lockdown mode',
        }).catch(() => {})
      }
    }

    // 5. Right-click context menu blocking
    const handleContextMenu = (e: MouseEvent) => {
      e.preventDefault()
    }

    // 6. Copy-paste blocking
    const handlePaste = (e: ClipboardEvent) => {
      if (exam?.copy_paste_blocked) {
        e.preventDefault()
        setViolationsCount((v) => v + 1)
        setViolationToast('⚠ External copy/paste is blocked during proctored exam.')
        logExamViolation(sessionId, {
          violation_type: 'copy_paste',
          details: 'Blocked paste event in editor',
        }).catch(() => {})
        setTimeout(() => setViolationToast(null), 3000)
      }
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)
    window.addEventListener('blur', handleWindowBlur)
    window.addEventListener('keydown', handleKeyDown)
    document.addEventListener('fullscreenchange', handleFullscreenChange)
    document.addEventListener('contextmenu', handleContextMenu)
    document.addEventListener('paste', handlePaste)

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      window.removeEventListener('blur', handleWindowBlur)
      window.removeEventListener('keydown', handleKeyDown)
      document.removeEventListener('fullscreenchange', handleFullscreenChange)
      document.removeEventListener('contextmenu', handleContextMenu)
      document.removeEventListener('paste', handlePaste)
    }
  }, [isStarted, sessionId, exam])

  // Active Problem
  const currentProblem = problems[activeProblemIndex]
  const currentCode = (currentProblem ? codes[currentProblem.id] : '') || ''
  const currentLanguage = (currentProblem ? languages[currentProblem.id] : 'python') || 'python'

  const handleCodeChange = (newCode: string) => {
    if (!currentProblem) return
    setCodes((prev) => ({ ...prev, [currentProblem.id]: newCode }))
  }

  const handleLanguageChange = (newLang: Language) => {
    if (!currentProblem) return
    setLanguages((prev) => ({ ...prev, [currentProblem.id]: newLang }))
    setCodes((prev) => ({ ...prev, [currentProblem.id]: getProblemStarterCode(currentProblem, newLang) }))
  }

  // Run solution in sandbox for current problem
  const handleRunProblem = () => {
    if (!currentProblem || !currentCode) return
    runCode(currentProblem.slug, currentCode, currentLanguage)
      .then((res) => startTracking(res.submission_id))
      .catch((err) => console.error(err))
  }

  // Submit solution in sandbox for current problem
  const handleSubmitProblem = () => {
    if (!currentProblem || !currentCode) return
    submitCode(currentProblem.slug, currentCode, currentLanguage)
      .then((res) => startTracking(res.submission_id))
      .catch((err) => console.error(err))
  }

  // Formatting remaining time
  const formatTimer = (totalSeconds: number) => {
    const m = Math.floor(totalSeconds / 60)
    const s = totalSeconds % 60
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }

  const isLowTime = secondsRemaining < 300 // < 5 mins

  if (loading && !exam) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center gap-3">
        <div className="w-8 h-8 rounded-full border-4 border-orange-500/10 border-t-orange-500 animate-spin" />
        <span className="text-zinc-500 text-sm">Preparing proctored environment…</span>
      </div>
    )
  }

  if (error || !exam) {
    return (
      <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center p-6 text-center text-white">
        <p className="text-red-400 font-semibold mb-4">{error || 'Exam not found'}</p>
        <button
          onClick={() => navigate('/')}
          className="px-4 py-2 bg-zinc-800 rounded text-xs font-semibold"
        >
          Return to Dashboard
        </button>
      </div>
    )
  }

  // ── Pre-Exam Screen ─────────────────────────────────────────────────────────
  if (!isStarted) {
    return (
      <div className="min-h-screen bg-zinc-950 text-white flex flex-col items-center justify-center p-6">
        <div className="max-w-2xl w-full bg-zinc-900 border border-zinc-800 rounded-3xl p-8 shadow-2xl flex flex-col gap-6">
          <div className="flex items-center gap-3">
            <span className="w-12 h-12 rounded-2xl bg-orange-500/10 border border-orange-500/20 flex items-center justify-center text-2xl">
              🛡️
            </span>
            <div>
              <span className="text-xs uppercase font-bold tracking-wider text-orange-400">
                Proctored Assessment
              </span>
              <h1 className="text-2xl font-black tracking-tight">{exam.title}</h1>
            </div>
          </div>

          {exam.description && (
            <p className="text-sm text-zinc-400 leading-relaxed bg-zinc-950 p-4 rounded-xl border border-zinc-800/80">
              {exam.description}
            </p>
          )}

          {/* Exam Specs */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3 bg-zinc-950 rounded-xl border border-zinc-800 text-center">
              <span className="text-[10px] text-zinc-500 uppercase tracking-wider block">Duration</span>
              <span className="font-bold text-base font-mono">{exam.duration_minutes}m</span>
            </div>
            <div className="p-3 bg-zinc-950 rounded-xl border border-zinc-800 text-center">
              <span className="text-[10px] text-zinc-500 uppercase tracking-wider block">Problems</span>
              <span className="font-bold text-base font-mono">{problems.length}</span>
            </div>
            <div className="p-3 bg-zinc-950 rounded-xl border border-zinc-800 text-center">
              <span className="text-[10px] text-zinc-500 uppercase tracking-wider block">Lockdown</span>
              <span className="font-bold text-base text-green-400">Active</span>
            </div>
            <div className="p-3 bg-zinc-950 rounded-xl border border-zinc-800 text-center">
              <span className="text-[10px] text-zinc-500 uppercase tracking-wider block">Tab Limit</span>
              <span className="font-bold text-base font-mono">{exam.tab_switch_limit} Max</span>
            </div>
          </div>

          {/* Rules & Anti-cheat acknowledgment */}
          <div className="flex flex-col gap-2.5 bg-orange-500/5 border border-orange-500/20 rounded-2xl p-5 text-xs text-zinc-300">
            <p className="font-bold text-orange-400 flex items-center gap-1.5 uppercase tracking-wider">
              <span>⚠</span> Anti-Cheat & Integrity Rules
            </p>
            <ul className="list-disc pl-5 space-y-1 text-zinc-400">
              <li>The exam will enter <strong>full-screen mode</strong>. Exiting fullscreen will be logged as an integrity violation.</li>
              <li>Switching browser tabs or minimizing the window is recorded in real time.</li>
              <li>External clipboard paste is restricted. Code must be written in the editor.</li>
              <li>When the timer expires, all solutions will automatically be submitted.</li>
            </ul>
          </div>

          {/* Action buttons */}
          <div className="flex flex-col sm:flex-row items-center gap-3 w-full">
            <button
              onClick={() => {
                if (exam.course_id) {
                  navigate(`/courses/${exam.course_id}`)
                } else {
                  navigate(-1)
                }
              }}
              className="w-full sm:w-1/3 py-3.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-xl text-xs font-bold uppercase tracking-wider transition border border-zinc-700"
            >
              ← Cancel / Return
            </button>
            <button
              onClick={handleStartExam}
              className="w-full sm:w-2/3 py-3.5 bg-orange-600 hover:bg-orange-500 text-white rounded-xl text-xs font-bold uppercase tracking-wider transition-all shadow-lg shadow-orange-500/20"
            >
              I Understand & Start Proctored Exam →
            </button>
          </div>
        </div>
      </div>
    )
  }

  // ── Active Proctored Exam Environment ───────────────────────────────────────
  return (
    <div className="h-screen w-screen bg-zinc-950 text-white flex flex-col overflow-hidden font-sans select-none">
      {/* Fullscreen Alert Modal */}
      {fullscreenAlert && (
        <div className="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex items-center justify-center p-6">
          <div className="max-w-md w-full bg-zinc-900 border-2 border-red-500/60 rounded-3xl p-6 text-center flex flex-col items-center gap-4 animate-in zoom-in-95 duration-200">
            <div className="w-16 h-16 rounded-full bg-red-500/20 border border-red-500/40 flex items-center justify-center text-3xl animate-bounce">
              ⚠
            </div>
            <h2 className="text-xl font-black text-red-400">Fullscreen Mode Required</h2>
            <p className="text-xs text-zinc-400 leading-relaxed">
              You have exited full-screen lockdown. This event has been logged in your assessment audit record. Re-enter fullscreen immediately to continue the exam.
            </p>
            <button
              onClick={requestFullscreen}
              className="px-6 py-2.5 bg-red-600 hover:bg-red-500 text-white rounded-xl text-xs font-bold uppercase tracking-wider transition"
            >
              Re-enter Fullscreen Lockdown
            </button>
          </div>
        </div>
      )}

      {/* Violation Toast Notification */}
      {violationToast && (
        <div className="fixed top-16 right-6 z-50 bg-red-600 text-white text-xs font-bold px-4 py-2.5 rounded-xl shadow-2xl flex items-center gap-2 animate-in slide-in-from-top-4 duration-200">
          <span>🚨</span>
          <span>{violationToast}</span>
        </div>
      )}

      {/* Top Lockdown Header */}
      <header className="h-14 border-b border-zinc-800 bg-zinc-950 flex items-center justify-between px-6 shrink-0 z-20">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse" />
            <span className="text-xs font-black tracking-widest uppercase bg-red-500/10 text-red-400 border border-red-500/20 px-2 py-0.5 rounded">
              PROCTORED
            </span>
          </div>
          <span className="font-bold text-sm tracking-tight truncate max-w-sm">
            {exam.title}
          </span>
        </div>

        {/* Center: Live Countdown Timer */}
        <div
          className={`flex items-center gap-2 px-4 py-1.5 rounded-xl border font-mono font-bold text-sm transition-all ${
            isLowTime
              ? 'bg-red-500/10 border-red-500/40 text-red-400 animate-pulse'
              : 'bg-zinc-900 border-zinc-800 text-zinc-200'
          }`}
        >
          <svg className="w-4 h-4 text-orange-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{formatTimer(secondsRemaining)}</span>
        </div>

        {/* Right: Anti-cheat Violations Counter & Finish button */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5 text-xs text-zinc-400">
            <span className="text-zinc-500 font-medium">Tab Switches:</span>
            <span
              className={`font-bold font-mono px-2 py-0.5 rounded ${
                tabSwitchesCount >= exam.tab_switch_limit
                  ? 'bg-red-500/20 text-red-400'
                  : tabSwitchesCount > 0
                  ? 'bg-yellow-500/20 text-yellow-400'
                  : 'bg-zinc-900 text-green-400'
              }`}
            >
              {tabSwitchesCount} / {exam.tab_switch_limit}
            </span>
            {violationsCount > 0 && (
              <span className="text-red-400 font-semibold ml-1">
                ({violationsCount} event{violationsCount !== 1 ? 's' : ''})
              </span>
            )}
          </div>

          <button
            onClick={() => setConfirmSubmitOpen(true)}
            className="px-4 py-1.5 bg-orange-600 hover:bg-orange-500 text-white rounded-lg text-xs font-bold tracking-wider uppercase transition shadow-md"
          >
            Submit Exam
          </button>
        </div>
      </header>

      {/* Main Split Problem Workspace */}
      <div className="flex-1 min-h-0 flex flex-col">
        {/* Problems Navigation Strip */}
        <div className="h-10 bg-zinc-900/60 border-b border-zinc-800 px-6 flex items-center gap-2 shrink-0 overflow-x-auto">
          {problems.map((prob, idx) => {
            const isActive = idx === activeProblemIndex
            return (
              <button
                key={prob.id}
                onClick={() => setActiveProblemIndex(idx)}
                className={`flex items-center gap-2 px-3.5 py-1 rounded-md text-xs font-semibold transition-all ${
                  isActive
                    ? 'bg-orange-600 text-white shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60'
                }`}
              >
                <span>Problem {idx + 1}</span>
                <span className="text-[10px] opacity-75">({prob.weight} pts)</span>
              </button>
            )
          })}
        </div>

        {/* Problem Split Workspace */}
        {currentProblem ? (
          <div className="flex-1 min-h-0">
            <PanelGroup direction="horizontal">
              {/* Left Pane - Problem Description */}
              <Panel defaultSize={40} minSize={25} className="bg-zinc-950">
                <ProblemDescription
                  title={`${currentProblem.title} (${currentProblem.weight} pts)`}
                  difficulty={currentProblem.difficulty}
                  description={currentProblem.description}
                />
              </Panel>

              <PanelResizeHandle className="w-1.5 hover:w-2 bg-zinc-900 hover:bg-orange-500/40 active:bg-orange-500 transition-all cursor-col-resize shrink-0" />

              {/* Right Pane - Editor + Test Cases */}
              <Panel defaultSize={60} minSize={30}>
                <PanelGroup direction="vertical">
                  {/* Editor Header Toolbar */}
                  <Panel defaultSize={60} minSize={30} className="flex flex-col bg-zinc-950">
                    <div className="h-10 bg-zinc-900/40 border-b border-zinc-900 flex items-center justify-between px-4 shrink-0">
                      <span className="text-xs font-mono font-semibold text-zinc-400 uppercase">
                        {currentLanguage === 'java'
                          ? 'Solution.java'
                          : currentLanguage === 'c'
                          ? 'solution.c'
                          : currentLanguage === 'cpp'
                          ? 'solution.cpp'
                          : 'solution.py'}
                      </span>

                      {/* Language switcher */}
                      <div className="flex items-center gap-1">
                        {(['python', 'java', 'c', 'cpp'] as Language[]).map((lang) => (
                          <button
                            key={lang}
                            onClick={() => handleLanguageChange(lang)}
                            className={`text-[10px] px-2 py-0.5 rounded font-mono border transition uppercase ${
                              currentLanguage === lang
                                ? 'bg-orange-500/20 text-orange-400 border-orange-500/40 font-bold'
                                : 'text-zinc-500 border-zinc-800 hover:border-zinc-700'
                            }`}
                          >
                            {lang === 'cpp' ? 'C++' : lang}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Monaco Editor */}
                    <div className="flex-1 min-h-0">
                      <CodeEditor
                        value={currentCode}
                        onChange={handleCodeChange}
                        language={currentLanguage}
                      />
                    </div>

                    {/* Run / Submit problem buttons */}
                    <div className="h-12 border-t border-zinc-900 bg-zinc-900/30 px-4 flex items-center justify-end gap-3 shrink-0">
                      <button
                        onClick={handleRunProblem}
                        disabled={wsLoading}
                        className="px-4 py-1.5 border border-zinc-800 hover:border-zinc-700 text-zinc-300 rounded text-xs font-semibold uppercase tracking-wider disabled:opacity-50 transition"
                      >
                        ▶ Run Code
                      </button>
                      <button
                        onClick={handleSubmitProblem}
                        disabled={wsLoading}
                        className="px-5 py-1.5 bg-orange-600 hover:bg-orange-500 text-white rounded text-xs font-bold uppercase tracking-wider disabled:opacity-50 transition shadow"
                      >
                        ✓ Submit Problem
                      </button>
                    </div>
                  </Panel>

                  <PanelResizeHandle className="h-1.5 hover:h-2 bg-zinc-900 hover:bg-orange-500/40 active:bg-orange-500 transition-all cursor-row-resize shrink-0" />

                  {/* Test Cases Panel */}
                  <Panel defaultSize={40} minSize={20} className="bg-zinc-950">
                    <TestCasePanel
                      submission={submission}
                      loading={wsLoading}
                      testCases={[]}
                      liveProgress={liveProgress}
                    />
                  </Panel>
                </PanelGroup>
              </Panel>
            </PanelGroup>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center text-zinc-500">
            No problem loaded.
          </div>
        )}
      </div>

      {/* Confirmation Modal before Submit */}
      {confirmSubmitOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-6">
          <div className="max-w-md w-full bg-zinc-900 border border-zinc-800 rounded-3xl p-6 flex flex-col gap-4 text-center">
            <h3 className="text-lg font-bold text-white">Submit Entire Exam?</h3>
            <p className="text-xs text-zinc-400">
              Are you sure you want to finalize and submit all problems? Once submitted, you cannot resume this exam session.
            </p>
            <div className="flex items-center justify-center gap-3 mt-2">
              <button
                onClick={() => setConfirmSubmitOpen(false)}
                className="px-4 py-2 rounded-xl border border-zinc-800 text-xs font-semibold text-zinc-300 hover:bg-zinc-800 transition"
              >
                Continue Working
              </button>
              <button
                onClick={() => handleFinalSubmit(false)}
                disabled={isSubmitting}
                className="px-5 py-2 rounded-xl bg-orange-600 hover:bg-orange-500 text-white text-xs font-bold uppercase tracking-wider transition shadow-md"
              >
                {isSubmitting ? 'Submitting…' : 'Yes, Submit Exam'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
