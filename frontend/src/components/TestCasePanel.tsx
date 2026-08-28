import { useState, useEffect } from 'react'
import type { Submission, TestCaseSummary } from '../api/client'

interface TestCasePanelProps {
  submission: Submission | null
  loading: boolean
  testCases: TestCaseSummary[]
}

export default function TestCasePanel({ submission, loading, testCases }: TestCasePanelProps) {
  const [activeTab, setActiveTab] = useState<number>(0)

  // Reset active tab on new submission
  useEffect(() => {
    if (submission) {
      setActiveTab(0)
    }
  }, [submission])

  if (loading || (submission && (submission.status === 'queued' || submission.status === 'running'))) {
    const statusText = submission?.status === 'running' ? 'Running test cases…' : 'Queued…'
    return (
      <div className="flex flex-col items-center justify-center h-full min-h-[200px] text-zinc-650 dark:text-zinc-400 gap-3 bg-white dark:bg-zinc-950 font-sans border border-zinc-200 dark:border-zinc-900 rounded-b">
        <div className="relative w-10 h-10 flex items-center justify-center">
          <div className="absolute inset-0 rounded-full border-4 border-orange-500/10"></div>
          <div className="absolute inset-0 rounded-full border-4 border-t-orange-500 animate-spin"></div>
        </div>
        <span className="text-sm font-medium animate-pulse text-orange-600 dark:text-orange-400">{statusText}</span>
      </div>
    )
  }

  if (!submission) {
    return (
      <div className="flex flex-col items-center justify-center h-full min-h-[200px] text-zinc-500 bg-white dark:bg-zinc-950 font-sans border border-zinc-200 dark:border-zinc-900 rounded-b p-6 text-center">
        <svg className="w-8 h-8 text-zinc-400 dark:text-zinc-600 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <p className="text-sm">Click <span className="text-orange-600 dark:text-orange-400 font-semibold">▶ Run</span> to test against visible cases, or <span className="text-orange-600 dark:text-orange-500 font-semibold">✓ Submit</span> to verify all cases.</p>
      </div>
    )
  }

  // Handle compilation errors
  if (submission.status === 'compile_error') {
    return (
      <div className="p-4 bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-900 rounded-b font-mono text-xs flex flex-col gap-2 min-h-[200px]">
        <div className="flex items-center gap-2 text-red-500 dark:text-red-400 font-semibold">
          <span className="w-2 h-2 rounded-full bg-red-500 animate-ping"></span>
          <span>Compilation Error</span>
        </div>
        <pre className="bg-red-500/5 border border-red-500/10 text-red-700 dark:text-red-300 rounded p-4 overflow-x-auto whitespace-pre-wrap leading-relaxed max-h-[300px]">
          {submission.results_json && submission.results_json.length > 0 
            ? submission.results_json[0].error 
            : "No output. Please check your syntax, imports, and ensure the class is named 'Solution'."}
        </pre>
      </div>
    )
  }

  // Handle system error
  if (submission.status === 'error') {
    return (
      <div className="p-4 bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-900 rounded-b font-sans text-xs flex flex-col gap-2 min-h-[200px]">
        <div className="flex items-center gap-2 text-red-500 font-semibold">
          <span>System Error</span>
        </div>
        <p className="text-zinc-600 dark:text-zinc-400">An unexpected system error occurred during execution. Please try again.</p>
      </div>
    )
  }

  const results = submission.results_json || []

  // If there are no results yet
  if (results.length === 0) {
    return (
      <div className="flex items-center justify-center h-full min-h-[200px] text-zinc-500 bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-900 rounded-b">
        No execution details available.
      </div>
    )
  }

  const activeResult = results[activeTab]
  const correspondingTestCase = testCases.find(tc => tc.id === activeResult?.test_case_id) || testCases[activeTab]

  return (
    <div className="flex flex-col bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-900 rounded-b font-sans h-full min-h-[240px] overflow-hidden transition-colors">
      {/* Panel Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-zinc-50 dark:bg-zinc-900/40 border-b border-zinc-200 dark:border-zinc-900">
        <div className="flex items-center gap-3">
          <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Test Results</span>
          {submission.status === 'completed' ? (
            submission.score === 100 ? (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-green-500/10 text-green-600 dark:text-green-400 border border-green-500/20">
                Accepted
              </span>
            ) : (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-red-500/10 text-red-650 dark:text-red-400 border border-red-500/20">
                Wrong Answer
              </span>
            )
          ) : submission.status === 'timeout' ? (
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border border-yellow-500/20">
              Time Limit Exceeded
            </span>
          ) : null}
        </div>
        <div className="text-xs text-zinc-500 dark:text-zinc-400">
          Passed: <span className="font-semibold text-zinc-900 dark:text-white">{submission.passed_cases}/{submission.total_cases}</span>
          {submission.execution_time_ms !== null && (
            <span className="ml-3 font-mono">({submission.execution_time_ms}ms)</span>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-zinc-200 dark:border-zinc-900/80 bg-zinc-50/50 dark:bg-zinc-900/10 px-2 overflow-x-auto">
        {results.map((res, idx) => {
          const isPassed = res.passed
          const isVisible = res.is_visible
          const isActive = idx === activeTab

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
              <span className={`w-1.5 h-1.5 rounded-full ${isPassed ? 'bg-green-500' : 'bg-red-500'}`}></span>
              <span>Case {idx + 1}</span>
              {!isVisible && (
                <svg className="w-3 h-3 text-zinc-400 dark:text-zinc-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              )}
            </button>
          )
        })}
      </div>

      {/* Active Tab Content */}
      <div className="p-4 flex-1 overflow-y-auto min-h-0 bg-white dark:bg-zinc-950 text-xs text-zinc-800 dark:text-zinc-300">
        {activeResult ? (
          <div className="flex flex-col gap-4">
            {/* Status Message */}
            <div className="flex items-center gap-2">
              <span className="text-zinc-400 dark:text-zinc-550">Result:</span>
              <span className={`font-semibold ${activeResult.passed ? 'text-green-600 dark:text-green-400' : 'text-red-650 dark:text-red-400'}`}>
                {activeResult.passed ? 'Passed' : activeResult.error === 'Time Limit Exceeded' ? 'Time Limit Exceeded' : 'Failed'}
              </span>
              {activeResult.execution_time_ms !== null && (
                <span className="text-zinc-405 dark:text-zinc-500 font-mono">({activeResult.execution_time_ms}ms)</span>
              )}
            </div>

            {/* Error Message if failed */}
            {!activeResult.passed && activeResult.error && (
              <div className="flex flex-col gap-1.5">
                <span className="text-zinc-400 dark:text-zinc-500 font-medium">Error Details:</span>
                <pre className="bg-red-500/5 border border-red-500/10 text-red-650 dark:text-red-300 rounded p-3 font-mono whitespace-pre-wrap leading-relaxed">
                  {activeResult.error}
                </pre>
              </div>
            )}

            {/* If visible, show inputs and outputs */}
            {activeResult.is_visible ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Input */}
                <div className="flex flex-col gap-1.5">
                  <span className="text-zinc-400 dark:text-zinc-500 font-medium">Input:</span>
                  <pre className="bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded p-3 font-mono text-zinc-800 dark:text-zinc-300 overflow-x-auto min-h-[50px]">
                    {correspondingTestCase?.input_data || "N/A"}
                  </pre>
                </div>

                {/* Expected Output */}
                <div className="flex flex-col gap-1.5">
                  <span className="text-zinc-400 dark:text-zinc-500 font-medium">Expected Output:</span>
                  <pre className="bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded p-3 font-mono text-zinc-800 dark:text-zinc-300 overflow-x-auto min-h-[50px]">
                    {activeResult.expected_output || correspondingTestCase?.expected_output || "N/A"}
                  </pre>
                </div>

                {/* Actual Output */}
                <div className="flex flex-col gap-1.5">
                  <span className="text-zinc-400 dark:text-zinc-500 font-medium">Your Output:</span>
                  <pre className={`border rounded p-3 font-mono overflow-x-auto min-h-[50px]
                    ${activeResult.passed 
                      ? 'bg-green-500/5 border-green-500/20 text-green-600 dark:text-green-300' 
                      : 'bg-red-500/5 border-red-500/20 text-red-600 dark:text-red-300'
                    }`}
                  >
                    {activeResult.actual_output !== null ? activeResult.actual_output : "(no output)"}
                  </pre>
                </div>
              </div>
            ) : (
              /* If hidden, show message */
              <div className="flex flex-col items-center justify-center p-6 bg-zinc-50 dark:bg-zinc-900/20 border border-zinc-200 dark:border-zinc-900 rounded text-center">
                <svg className="w-6 h-6 text-zinc-400 dark:text-zinc-655 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
                <span className="font-semibold text-zinc-800 dark:text-zinc-300 mb-1">Hidden Test Case</span>
                <p className="text-zinc-500 max-w-[320px]">This test case is hidden to prevent hard-coded solutions. No inputs or outputs are visible.</p>
              </div>
            )}
          </div>
        ) : (
          <p className="text-zinc-500">Select a test case to view details.</p>
        )}
      </div>
    </div>
  )
}
