/**
 * TestCasePanel — renders submission results.
 * Developer B: implement in Phase B2.
 *
 * TODO:
 * - Visible test cases: show input, expected output, actual output, ✅/❌
 * - Hidden test cases: show only pass/fail, no details
 * - Overall score: "3/5 test cases passed (60%)"
 * - Compile error: red block with javac output
 * - Runtime error: show stderr for that test case
 * - Timeout: show "⏱️ Time Limit Exceeded"
 */

import type { Submission } from '../api/client'

interface TestCasePanelProps {
  submission: Submission | null
  loading: boolean
}

export default function TestCasePanel({ submission, loading }: TestCasePanelProps) {
  if (loading) {
    return (
      <div className="flex items-center gap-2 text-gray-400 p-4">
        <span className="animate-pulse">●</span>
        Running…
      </div>
    )
  }

  if (!submission) {
    return (
      <p className="text-gray-500 p-4 text-sm">
        Click ▶ Run to execute your code against visible test cases.
      </p>
    )
  }

  // TODO Phase B2: render full results
  return (
    <div className="p-4 text-sm">
      <p className="text-gray-400">
        Status: <span className="text-white font-mono">{submission.status}</span>
      </p>
    </div>
  )
}
