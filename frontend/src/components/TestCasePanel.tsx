import { useState, useEffect } from 'react'
import type { Submission, TestCaseSummary, RunCustomResponse } from '../api/client'
import type { LiveProgress } from '../hooks/useWebSocket'

interface TestCasePanelProps {
  submission: Submission | null
  loading: boolean
  testCases: TestCaseSummary[]
  liveProgress?: LiveProgress
  onRunCustomInput?: (stdin: string) => Promise<void>
  customRunning?: boolean
  customResult?: RunCustomResponse | null
}

export default function TestCasePanel({
  submission,
  loading,
  testCases,
  liveProgress,
  onRunCustomInput,
  customRunning,
  customResult,
}: TestCasePanelProps) {
  const [activeTab, setActiveTab] = useState<number>(0)
  const [panelMode, setPanelMode] = useState<'tests' | 'custom'>('tests')
  const [customStdin, setCustomStdin] = useState<string>('')

  // Reset active tab on new submission
  useEffect(() => {
    if (submission) {
      setActiveTab(0)
    }
  }, [submission])

  // If liveProgress is streaming
  const isExecuting = loading || (submission && (submission.status === 'queued' || submission.status === 'running' || submission.status === 'compiling'))
  const statusMessage = liveProgress?.message || (submission?.status === 'compiling' ? 'Compiling in sandbox…' : submission?.status === 'running' ? 'Running test cases…' : 'Queued in worker…')
  const progressPercent = liveProgress && liveProgress.totalCases > 0
    ? Math.round((liveProgress.currentCase / liveProgress.totalCases) * 100)
    : 0

  return (
    <div className="flex flex-col bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-900 rounded-b font-sans h-full min-h-[260px] overflow-hidden transition-colors">
      {/* Top mode switcher: Test Results vs Custom Input */}
      <div className="flex items-center justify-between px-3 py-2 bg-zinc-100 dark:bg-zinc-900/60 border-b border-zinc-200 dark:border-zinc-800">
        <div className="flex items-center gap-1">
          <button
            onClick={() => setPanelMode('tests')}
            className={`px-3 py-1 text-xs font-semibold rounded-md transition-colors ${
              panelMode === 'tests'
                ? 'bg-white dark:bg-zinc-800 text-orange-600 dark:text-orange-400 shadow-sm'
                : 'text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200'
            }`}
          >
            ⚡ Test Results
          </button>
          <button
            onClick={() => setPanelMode('custom')}
            className={`px-3 py-1 text-xs font-semibold rounded-md transition-colors ${
              panelMode === 'custom'
                ? 'bg-white dark:bg-zinc-800 text-orange-600 dark:text-orange-400 shadow-sm'
                : 'text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200'
            }`}
          >
            ⌨ Custom Input
          </button>
        </div>

        {isExecuting && (
          <div className="flex items-center gap-2 text-xs text-orange-500 font-medium">
            <span className="w-2 h-2 rounded-full bg-orange-500 animate-ping" />
            <span>{statusMessage}</span>
          </div>
        )}
      </div>

      {panelMode === 'custom' ? (
        /* Custom Input Panel */
        <div className="p-4 flex-1 flex flex-col gap-3 overflow-y-auto">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
              Provide Standard Input (stdin)
            </span>
            <button
              onClick={() => onRunCustomInput?.(customStdin)}
              disabled={customRunning}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-orange-600 hover:bg-orange-500 disabled:opacity-50 text-white rounded text-xs font-semibold transition-colors shadow-sm"
            >
              {customRunning ? (
                <>
                  <div className="w-3 h-3 rounded-full border-2 border-white/20 border-t-white animate-spin" />
                  <span>Running…</span>
                </>
              ) : (
                <>
                  <span>▶</span>
                  <span>Run with Custom Input</span>
                </>
              )}
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-1">
            <div className="flex flex-col gap-1.5">
              <label className="text-[11px] font-medium text-zinc-400">Standard Input (stdin):</label>
              <textarea
                value={customStdin}
                onChange={(e) => setCustomStdin(e.target.value)}
                placeholder="Type your custom input here... (e.g. 4\n2 7 11 15\n9)"
                className="w-full flex-1 min-h-[140px] p-3 rounded font-mono text-xs bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-800 dark:text-zinc-200 focus:outline-none focus:ring-1 focus:ring-orange-500 resize-none"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <div className="flex items-center justify-between">
                <label className="text-[11px] font-medium text-zinc-400">Execution Output (stdout / stderr):</label>
                {customResult?.execution_time_ms !== null && customResult?.execution_time_ms !== undefined && (
                  <span className="text-[11px] font-mono text-zinc-500">{customResult.execution_time_ms}ms</span>
                )}
              </div>
              <pre className="w-full flex-1 min-h-[140px] p-3 rounded font-mono text-xs bg-zinc-900 border border-zinc-800 text-zinc-200 overflow-auto whitespace-pre-wrap leading-relaxed">
                {customRunning ? (
                  <span className="text-orange-400 animate-pulse">Executing code in Docker sandbox with custom input…</span>
                ) : customResult ? (
                  customResult.stderr ? (
                    <span className="text-red-400">{customResult.stderr}</span>
                  ) : (
                    customResult.stdout || <span className="text-zinc-500">(Program produced no output)</span>
                  )
                ) : (
                  <span className="text-zinc-500">Click "Run with Custom Input" to execute your solution with the provided stdin above.</span>
                )}
              </pre>
            </div>
          </div>
        </div>
      ) : (
        /* Test Cases Mode */
        <>
          {isExecuting ? (
            <div className="flex flex-col items-center justify-center h-full min-h-[200px] text-zinc-650 dark:text-zinc-400 gap-4 bg-white dark:bg-zinc-950 p-6">
              <div className="relative w-12 h-12 flex items-center justify-center">
                <div className="absolute inset-0 rounded-full border-4 border-orange-500/10" />
                <div className="absolute inset-0 rounded-full border-4 border-t-orange-500 animate-spin" />
              </div>
              <div className="flex flex-col items-center gap-1.5 max-w-sm w-full">
                <span className="text-sm font-semibold text-orange-600 dark:text-orange-400 animate-pulse">
                  {statusMessage}
                </span>
                {liveProgress && liveProgress.totalCases > 0 && (
                  <div className="w-full bg-zinc-200 dark:bg-zinc-800 h-2 rounded-full overflow-hidden mt-1">
                    <div
                      className="bg-orange-500 h-full transition-all duration-300"
                      style={{ width: `${progressPercent}%` }}
                    />
                  </div>
                )}
                {liveProgress && liveProgress.totalCases > 0 && (
                  <span className="text-xs text-zinc-500">
                    Test case {liveProgress.currentCase} of {liveProgress.totalCases} ({progressPercent}%)
                  </span>
                )}
              </div>
            </div>
          ) : !submission ? (
            <div className="flex flex-col items-center justify-center h-full min-h-[200px] text-zinc-500 bg-white dark:bg-zinc-950 p-6 text-center">
              <svg className="w-8 h-8 text-zinc-400 dark:text-zinc-600 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-sm">
                Click <span className="text-orange-600 dark:text-orange-400 font-semibold">▶ Run</span> to test against public cases, or <span className="text-orange-600 dark:text-orange-500 font-semibold">✓ Submit</span> to verify all cases.
              </p>
            </div>
          ) : submission.status === 'compile_error' ? (
            <div className="p-4 bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-900 rounded-b font-mono text-xs flex flex-col gap-2 min-h-[200px]">
              <div className="flex items-center gap-2 text-red-500 dark:text-red-400 font-semibold">
                <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
                <span>Compilation Error</span>
              </div>
              <pre className="bg-red-500/5 border border-red-500/10 text-red-700 dark:text-red-300 rounded p-4 overflow-x-auto whitespace-pre-wrap leading-relaxed max-h-[300px]">
                {submission.results_json && submission.results_json.length > 0
                  ? submission.results_json[0].error
                  : "Syntax or compilation error. Please check your types, syntax, and class definitions."}
              </pre>
            </div>
          ) : submission.status === 'error' ? (
            <div className="p-4 bg-white dark:bg-zinc-950 font-sans text-xs flex flex-col gap-2 min-h-[200px]">
              <div className="flex items-center gap-2 text-red-500 font-semibold">
                <span>System Error</span>
              </div>
              <p className="text-zinc-600 dark:text-zinc-400">
                An unexpected error occurred during execution. Please try again.
              </p>
            </div>
          ) : (
            <>
              {/* Panel Header */}
              <div className="flex items-center justify-between px-4 py-2.5 bg-zinc-50 dark:bg-zinc-900/40 border-b border-zinc-200 dark:border-zinc-900">
                <div className="flex items-center gap-3">
                  <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Evaluation</span>
                  {submission.status === 'completed' ? (
                    submission.score === 100 ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-green-500/10 text-green-600 dark:text-green-400 border border-green-500/20">
                        Accepted (100%)
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-red-500/10 text-red-650 dark:text-red-400 border border-red-500/20">
                        Wrong Answer ({submission.score ?? 0}%)
                      </span>
                    )
                  ) : submission.status === 'timeout' ? (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border border-yellow-500/20">
                      Time Limit Exceeded
                    </span>
                  ) : null}
                </div>
                <div className="text-xs text-zinc-500 dark:text-zinc-400 flex items-center gap-3">
                  <span>
                    Passed: <strong className="text-zinc-900 dark:text-white">{submission.passed_cases}/{submission.total_cases}</strong>
                  </span>
                  {submission.execution_time_ms !== null && (
                    <span className="font-mono text-zinc-400">({submission.execution_time_ms}ms)</span>
                  )}
                </div>
              </div>

              {/* Test Case Tabs */}
              <div className="flex border-b border-zinc-200 dark:border-zinc-900/80 bg-zinc-50/50 dark:bg-zinc-900/10 px-2 overflow-x-auto">
                {(submission.results_json || []).map((res, idx) => {
                  const isPassed = res.passed
                  const isVisible = res.is_visible
                  const isActive = idx === activeTab
                  const weight = res.weight ?? testCases[idx]?.weight

                  return (
                    <button
                      key={res.test_case_id || idx}
                      onClick={() => setActiveTab(idx)}
                      className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium border-b-2 transition-all whitespace-nowrap outline-none
                        ${isActive
                          ? 'border-orange-500 text-zinc-900 dark:text-white bg-zinc-100/60 dark:bg-zinc-900/40'
                          : 'border-transparent text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 hover:dark:text-zinc-200'
                        }`}
                    >
                      <span className={`w-1.5 h-1.5 rounded-full ${isPassed ? 'bg-green-500' : 'bg-red-500'}`} />
                      <span>Case {idx + 1}</span>
                      {weight && weight > 1 && (
                        <span className="text-[10px] text-zinc-400">({weight}pts)</span>
                      )}
                      {!isVisible && (
                        <svg className="w-3 h-3 text-zinc-400 dark:text-zinc-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                        </svg>
                      )}
                    </button>
                  )
                })}
              </div>

              {/* Active Test Case Content */}
              <div className="p-4 flex-1 overflow-y-auto min-h-0 bg-white dark:bg-zinc-950 text-xs text-zinc-800 dark:text-zinc-300">
                {submission.results_json && submission.results_json[activeTab] ? (
                  (() => {
                    const activeResult = submission.results_json[activeTab]
                    const correspondingTestCase = testCases.find(tc => tc.id === activeResult?.test_case_id) || testCases[activeTab]
                    return (
                      <div className="flex flex-col gap-4">
                        <div className="flex items-center gap-2">
                          <span className="text-zinc-400">Result:</span>
                          <span className={`font-semibold ${activeResult.passed ? 'text-green-600 dark:text-green-400' : 'text-red-650 dark:text-red-400'}`}>
                            {activeResult.passed ? 'Passed' : activeResult.error === 'Time Limit Exceeded' ? 'Time Limit Exceeded' : 'Failed'}
                          </span>
                          {activeResult.execution_time_ms !== null && (
                            <span className="text-zinc-400 font-mono">({activeResult.execution_time_ms}ms)</span>
                          )}
                          {activeResult.weight && (
                            <span className="text-orange-500 text-xs font-semibold ml-2">Weight: {activeResult.weight} pts</span>
                          )}
                        </div>

                        {!activeResult.passed && activeResult.error && (
                          <div className="flex flex-col gap-1.5">
                            <span className="text-zinc-400 font-medium">Error Details:</span>
                            <pre className="bg-red-500/5 border border-red-500/10 text-red-650 dark:text-red-300 rounded p-3 font-mono whitespace-pre-wrap leading-relaxed">
                              {activeResult.error}
                            </pre>
                          </div>
                        )}

                        {activeResult.is_visible ? (
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div className="flex flex-col gap-1.5">
                              <span className="text-zinc-400 font-medium">Input:</span>
                              <pre className="bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded p-3 font-mono text-zinc-800 dark:text-zinc-300 overflow-x-auto min-h-[50px]">
                                {correspondingTestCase?.input_data || "N/A"}
                              </pre>
                            </div>

                            <div className="flex flex-col gap-1.5">
                              <span className="text-zinc-400 font-medium">Expected Output:</span>
                              <pre className="bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded p-3 font-mono text-zinc-800 dark:text-zinc-300 overflow-x-auto min-h-[50px]">
                                {activeResult.expected_output || correspondingTestCase?.expected_output || "N/A"}
                              </pre>
                            </div>

                            <div className="flex flex-col gap-1.5">
                              <span className="text-zinc-400 font-medium">Your Output:</span>
                              <pre className={`border rounded p-3 font-mono overflow-x-auto min-h-[50px] ${
                                activeResult.passed
                                  ? 'bg-green-500/5 border-green-500/20 text-green-600 dark:text-green-300'
                                  : 'bg-red-500/5 border-red-500/20 text-red-600 dark:text-red-300'
                              }`}>
                                {activeResult.actual_output !== null ? activeResult.actual_output : "(no output)"}
                              </pre>
                            </div>
                          </div>
                        ) : (
                          <div className="flex flex-col items-center justify-center p-6 bg-zinc-50 dark:bg-zinc-900/20 border border-zinc-200 dark:border-zinc-900 rounded text-center">
                            <svg className="w-6 h-6 text-zinc-400 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                            </svg>
                            <span className="font-semibold text-zinc-800 dark:text-zinc-300 mb-1">Hidden Test Case</span>
                            <p className="text-zinc-500 max-w-[320px]">
                              This test case is hidden to ensure algorithmic generalization.
                            </p>
                          </div>
                        )}
                      </div>
                    )
                  })()
                ) : (
                  <p className="text-zinc-500">Select a test case tab to view execution details.</p>
                )}
              </div>
            </>
          )}
        </>
      )}
    </div>
  )
}
