import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  getExamResults,
  ExamResultsDashboard,
  ExamStudentResult,
} from '../api/client'
import { useAuth } from '../context/AuthContext'
import Navbar from '../components/Navbar'

export default function ExamResultsPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [results, setResults] = useState<ExamResultsDashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedStudentId, setExpandedStudentId] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    // If student, route to student-specific exam outcome
    if (user?.role === 'student') {
      navigate(`/exams/${id}/my-result`, { replace: true })
      return
    }

    setLoading(true)
    getExamResults(id)
      .then((data) => {
        setResults(data)
        setLoading(false)
      })
      .catch((err) => {
        console.error(err)
        setError('Failed to load exam results.')
        setLoading(false)
      })
  }, [id, user, navigate])

  const toggleExpand = (userId: string) => {
    setExpandedStudentId((prev) => (prev === userId ? null : userId))
  }

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 flex flex-col font-sans transition-colors">
      {/* Header */}
      <Navbar
        customTitle={results?.title ? `${results.title} (Results & Audit)` : 'Exam Audit'}
        backTo={results?.course_id ? `/courses/${results.course_id}?tab=exams` : '/'}
        backLabel="Course"
      />

      {/* Main Content */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 gap-3">
            <div className="w-8 h-8 rounded-full border-4 border-orange-500/10 border-t-orange-500 animate-spin" />
            <span className="text-zinc-500 text-sm">Aggregating proctoring results…</span>
          </div>
        ) : error || !results ? (
          <div className="p-6 bg-red-500/10 border border-red-500/20 rounded-xl text-center text-red-500 font-semibold">
            {error || 'No results available'}
          </div>
        ) : (
          <div className="flex flex-col gap-6">
            {/* Top KPI Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-5 shadow-sm">
                <span className="text-xs text-zinc-500 uppercase tracking-wider font-semibold block mb-1">
                  Total Enrolled
                </span>
                <span className="text-2xl font-black font-mono text-zinc-900 dark:text-white">
                  {results.total_enrolled}
                </span>
              </div>

              <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-5 shadow-sm">
                <span className="text-xs text-zinc-500 uppercase tracking-wider font-semibold block mb-1">
                  Submissions
                </span>
                <span className="text-2xl font-black font-mono text-zinc-900 dark:text-white">
                  {results.submissions_count}
                </span>
              </div>

              <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-5 shadow-sm">
                <span className="text-xs text-zinc-500 uppercase tracking-wider font-semibold block mb-1">
                  Average Score
                </span>
                <span className="text-2xl font-black font-mono text-orange-600 dark:text-orange-400">
                  {results.average_score}%
                </span>
              </div>

              <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-5 shadow-sm">
                <span className="text-xs text-zinc-500 uppercase tracking-wider font-semibold block mb-1">
                  Flagged Sessions
                </span>
                <span className="text-2xl font-black font-mono text-red-500">
                  {results.students.filter((s) => s.violation_count >= 3).length}
                </span>
              </div>
            </div>

            {/* Students Table */}
            <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm overflow-hidden">
              <div className="p-4 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
                <h2 className="text-sm font-bold uppercase tracking-wider text-zinc-700 dark:text-zinc-300">
                  Student Assessment Submissions & Integrity Logs
                </h2>
                <span className="text-xs text-zinc-400">
                  Click student row to inspect anti-cheat violations log
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead className="bg-zinc-50 dark:bg-zinc-950/80 border-b border-zinc-200 dark:border-zinc-800 text-zinc-500 font-semibold uppercase tracking-wider text-[10px]">
                    <tr>
                      <th className="px-5 py-3">Student</th>
                      <th className="px-5 py-3">Status</th>
                      <th className="px-5 py-3">Score</th>
                      <th className="px-5 py-3">Violations</th>
                      <th className="px-5 py-3">Submitted At</th>
                      <th className="px-5 py-3 text-right">Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
                    {results.students.map((student: ExamStudentResult) => {
                      const isExpanded = expandedStudentId === student.user_id
                      const violColor =
                        student.violation_count === 0
                          ? 'bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20'
                          : student.violation_count <= 2
                          ? 'bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border-yellow-500/20'
                          : 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20 font-bold'

                      return (
                        <tr
                          key={student.user_id}
                          onClick={() => toggleExpand(student.user_id)}
                          className="hover:bg-zinc-50 dark:hover:bg-zinc-800/40 cursor-pointer transition"
                        >
                          <td className="px-5 py-3.5">
                            <div className="flex flex-col">
                              <span className="font-bold text-zinc-900 dark:text-white">
                                {student.name}
                              </span>
                              <span className="text-[11px] text-zinc-400 font-mono">
                                {student.email}
                              </span>
                            </div>
                          </td>

                          <td className="px-5 py-3.5">
                            <span className="capitalize px-2 py-0.5 rounded text-[10px] font-semibold bg-zinc-100 dark:bg-zinc-800">
                              {student.status}
                            </span>
                            {student.is_auto_submitted && (
                              <span className="ml-1 text-[10px] text-zinc-400" title="Auto-submitted on timer expiration">
                                (auto)
                              </span>
                            )}
                          </td>

                          <td className="px-5 py-3.5 font-mono font-bold text-sm text-zinc-900 dark:text-white">
                            {student.total_score !== null ? `${student.total_score} pts` : '—'}
                          </td>

                          <td className="px-5 py-3.5">
                            <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold border ${violColor}`}>
                              {student.violation_count === 0
                                ? '✓ Clean'
                                : `${student.violation_count} Violation${student.violation_count > 1 ? 's' : ''}`}
                            </span>
                          </td>

                          <td className="px-5 py-3.5 text-zinc-400">
                            {student.submitted_at
                              ? new Date(student.submitted_at).toLocaleTimeString([], {
                                  hour: '2-digit',
                                  minute: '2-digit',
                                })
                              : 'In Progress'}
                          </td>

                          <td className="px-5 py-3.5 text-right font-medium text-orange-600 dark:text-orange-400">
                            {isExpanded ? '▲ Hide' : '▼ Expand'}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Expanded Violation Details Log */}
            {expandedStudentId && (
              (() => {
                const student = results.students.find((s) => s.user_id === expandedStudentId)
                if (!student) return null

                return (
                  <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 shadow-sm flex flex-col gap-4 animate-in fade-in duration-200">
                    <div className="flex items-center justify-between border-b border-zinc-200 dark:border-zinc-800 pb-3">
                      <div>
                        <h3 className="font-bold text-sm text-zinc-900 dark:text-white">
                          Integrity Audit Log: {student.name}
                        </h3>
                        <span className="text-xs text-zinc-400">
                          Total recorded incidents: {student.violation_count}
                        </span>
                      </div>
                      <button
                        onClick={() => setExpandedStudentId(null)}
                        className="text-xs text-zinc-400 hover:text-zinc-200"
                      >
                        ✕ Close
                      </button>
                    </div>

                    {student.violations.length === 0 ? (
                      <p className="text-xs text-green-500 font-medium py-2">
                        ✓ No integrity violations recorded during this exam session.
                      </p>
                    ) : (
                      <div className="flex flex-col gap-2">
                        {student.violations.map((v, i) => (
                          <div
                            key={i}
                            className="p-3 bg-red-500/5 border border-red-500/20 rounded-xl flex items-center justify-between text-xs"
                          >
                            <div className="flex items-center gap-3">
                              <span className="text-red-500 font-bold uppercase font-mono text-[10px] px-2 py-0.5 bg-red-500/10 rounded">
                                {v.violation_type.replace('_', ' ')}
                              </span>
                              <span className="text-zinc-700 dark:text-zinc-300 font-medium">
                                {v.details || 'Integrity violation event'}
                              </span>
                            </div>
                            <span className="text-zinc-400 font-mono text-[11px]">
                              {new Date(v.occurred_at).toLocaleTimeString()}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })()
            )}
          </div>
        )}
      </main>
    </div>
  )
}
