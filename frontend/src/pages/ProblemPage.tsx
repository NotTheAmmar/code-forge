import { useEffect, useState, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels'
import { getProblem, runCode, submitCode, getSubmission, ProblemDetail, Submission } from '../api/client'
import ProblemDescription from '../components/ProblemDescription'
import CodeEditor from '../components/CodeEditor'
import TestCasePanel from '../components/TestCasePanel'
import { useTheme } from '../context/ThemeContext'

export default function ProblemPage() {
  const { slug } = useParams<{ slug: string }>()
  const [problem, setProblem] = useState<ProblemDetail | null>(null)
  const [code, setCode] = useState<string>('')
  const [submission, setSubmission] = useState<Submission | null>(null)
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const pollIntervalRef = useRef<number | null>(null)
  const { theme, toggleTheme } = useTheme()

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
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
      }
    }
  }, [slug])

  const startPolling = (submissionId: string, isSubmit: boolean) => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
    }

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

            // If solved with 100%, mark as solved in localStorage
            if (isSubmit && sub.status === 'completed' && sub.score === 100) {
              localStorage.setItem(`solved_${slug}`, 'true')
            }
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
    runCode(slug, code)
      .then((res) => {
        startPolling(res.submission_id, false)
      })
      .catch((err) => {
        console.error(err)
        setLoading(false)
      })
  }

  const handleSubmit = () => {
    if (!slug || !code) return
    setSubmission(null)
    setLoading(true)
    submitCode(slug, code)
      .then((res) => {
        startPolling(res.submission_id, true)
      })
      .catch((err) => {
        console.error(err)
        setLoading(false)
      })
  }

  return (
    <div className="h-screen w-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 flex flex-col overflow-hidden font-sans transition-colors duration-200">
      {/* Header */}
      <header className="h-14 border-b border-zinc-200 dark:border-zinc-900 bg-white dark:bg-zinc-950 flex items-center justify-between px-6 shrink-0 transition-colors">
        <div className="flex items-center gap-4">
          <Link
            to="/"
            className="flex items-center gap-1.5 text-zinc-500 dark:text-zinc-400 hover:text-zinc-950 dark:hover:text-white transition-colors text-xs font-semibold uppercase tracking-wider"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Problems
          </Link>
          <div className="h-4 w-[1px] bg-zinc-200 dark:bg-zinc-800"></div>
          <span className="font-bold text-sm tracking-tight text-zinc-900 dark:text-white">{problem?.title || 'Loading...'}</span>
        </div>
        <div className="flex items-center gap-3">
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
            <div className="w-8 h-8 rounded-full border-4 border-orange-500/10 border-t-orange-500 animate-spin"></div>
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
                  <div className="h-10 bg-zinc-50 dark:bg-zinc-900/40 border-b border-zinc-200 dark:border-zinc-900 flex items-center justify-between px-4 shrink-0">
                    <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider font-mono">Solution.java</span>
                    <span className="text-[10px] bg-orange-500/10 text-orange-600 dark:text-orange-400 border border-orange-500/25 px-2 py-0.5 rounded font-mono">
                      Java 21
                    </span>
                  </div>

                  {/* Editor Container */}
                  <div className="flex-1 min-h-0 relative">
                    <CodeEditor value={code} onChange={setCode} language="java" />
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
    </div>
  )
}
