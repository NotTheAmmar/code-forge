import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  getCourseAnalytics,
  CourseAnalytics,
  getCourse,
  CourseResponse,
} from '../api/client'
import Navbar from '../components/Navbar'

export default function AnalyticsPage() {
  const { courseId } = useParams<{ courseId: string }>()

  const [course, setCourse] = useState<CourseResponse | null>(null)
  const [analytics, setAnalytics] = useState<CourseAnalytics | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!courseId) return
    setLoading(true)

    Promise.all([
      getCourse(courseId),
      getCourseAnalytics(courseId),
    ])
      .then(([cData, aData]) => {
        setCourse(cData)
        setAnalytics(aData)
        setLoading(false)
      })
      .catch((err) => {
        console.error(err)
        setError('Failed to load course analytics.')
        setLoading(false)
      })
  }, [courseId])

  const summary = analytics?.summary || {
    total_students: 0,
    total_submissions: 0,
    average_pass_rate: 0,
    active_students_7d: 0,
  }

  const problemPassRates = analytics?.problem_pass_rates || []
  const errorDistribution = analytics?.common_error_distribution || []
  const submissionTrends = analytics?.submission_trends || []

  const totalErrors = errorDistribution.reduce((acc, curr) => acc + curr.count, 0) || 1
  const maxTrend = Math.max(...submissionTrends.map((t) => t.count), 1)

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 flex flex-col font-sans transition-colors">
      {/* Header */}
      <Navbar
        customTitle={course?.title ? `${course.title} (Analytics)` : 'Course Analytics'}
        backTo={courseId ? `/courses/${courseId}?tab=analytics` : '/'}
        backLabel="Course"
      />

      {/* Main Content */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 gap-3">
            <div className="w-8 h-8 rounded-full border-4 border-orange-500/10 border-t-orange-500 animate-spin" />
            <span className="text-zinc-500 text-sm">Aggregating algorithmic performance metrics…</span>
          </div>
        ) : error || !analytics ? (
          <div className="p-6 bg-red-500/10 border border-red-500/20 rounded-xl text-center text-red-500 font-semibold">
            {error || 'No analytics data available.'}
          </div>
        ) : (
          <div className="flex flex-col gap-8">
            {/* KPI Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-5 shadow-sm">
                <span className="text-xs text-zinc-500 uppercase tracking-wider font-semibold block mb-1">
                  Total Students
                </span>
                <span className="text-2xl font-black font-mono text-zinc-900 dark:text-white">
                  {summary.total_students}
                </span>
                <span className="text-[11px] text-zinc-400 mt-1 block">Active in course</span>
              </div>

              <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-5 shadow-sm">
                <span className="text-xs text-zinc-500 uppercase tracking-wider font-semibold block mb-1">
                  Total Submissions
                </span>
                <span className="text-2xl font-black font-mono text-zinc-900 dark:text-white">
                  {summary.total_submissions}
                </span>
                <span className="text-[11px] text-zinc-400 mt-1 block">Runs & full submits</span>
              </div>

              <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-5 shadow-sm">
                <span className="text-xs text-zinc-500 uppercase tracking-wider font-semibold block mb-1">
                  Class Pass Rate
                </span>
                <span className="text-2xl font-black font-mono text-orange-600 dark:text-orange-400">
                  {summary.average_pass_rate}%
                </span>
                <span className="text-[11px] text-green-500 mt-1 block font-medium">Class-wide average</span>
              </div>

              <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-5 shadow-sm">
                <span className="text-xs text-zinc-500 uppercase tracking-wider font-semibold block mb-1">
                  Active (7 Days)
                </span>
                <span className="text-2xl font-black font-mono text-zinc-900 dark:text-white">
                  {summary.active_students_7d}
                </span>
                <span className="text-[11px] text-zinc-400 mt-1 block">Students coding this week</span>
              </div>
            </div>

            {/* Problem Pass Rates Bar Chart */}
            <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 shadow-sm flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-base font-bold text-zinc-900 dark:text-white">
                    Problem Pass Rates (%)
                  </h2>
                  <p className="text-xs text-zinc-500">
                    Percentage of students who achieved 100% accepted score on each problem.
                  </p>
                </div>
              </div>

              <div className="flex flex-col gap-4 pt-2">
                {problemPassRates.map((prob) => {
                  const passPercent = Math.round(prob.pass_rate)

                  return (
                    <div key={prob.problem_id} className="flex flex-col gap-1.5">
                      <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-zinc-900 dark:text-white">{prob.title}</span>
                          <span className="text-[10px] uppercase font-semibold text-zinc-400 px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800">
                            {prob.difficulty}
                          </span>
                          <span className="text-zinc-400 text-[11px]">
                            ({prob.submissions_count} submissions)
                          </span>
                        </div>
                        <span className="font-mono font-bold text-orange-600 dark:text-orange-400">
                          {prob.pass_rate}%
                        </span>
                      </div>

                      <div className="w-full bg-zinc-100 dark:bg-zinc-800 h-3 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${
                            passPercent >= 80
                              ? 'bg-green-500'
                              : passPercent >= 50
                              ? 'bg-orange-500'
                              : 'bg-red-500'
                          }`}
                          style={{ width: `${passPercent}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Split Row: Submission Trends & Error Distribution */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Submission Volume Trends (7 Days) */}
              <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 shadow-sm flex flex-col gap-4">
                <div>
                  <h2 className="text-base font-bold text-zinc-900 dark:text-white">
                    Submission Volume (Last 7 Days)
                  </h2>
                  <p className="text-xs text-zinc-500">
                    Daily student coding activity across the course.
                  </p>
                </div>

                <div className="h-48 flex items-end justify-between gap-3 pt-6 pb-2 px-2 border-b border-zinc-200 dark:border-zinc-800">
                  {submissionTrends.map((t) => {
                    const heightPercent = Math.max(12, Math.round((t.count / maxTrend) * 100))

                    return (
                      <div key={t.date} className="flex-1 flex flex-col items-center gap-2 h-full justify-end group">
                        <span className="text-[10px] font-mono font-bold text-orange-500 opacity-0 group-hover:opacity-100 transition-opacity">
                          {t.count}
                        </span>
                        <div
                          className="w-full max-w-[32px] bg-gradient-to-t from-orange-600 to-orange-400 rounded-t-lg transition-all group-hover:brightness-110"
                          style={{ height: `${heightPercent}%` }}
                        />
                        <span className="text-[10px] text-zinc-400 font-medium whitespace-nowrap">
                          {t.date}
                        </span>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* Error Distribution Breakdown */}
              <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 shadow-sm flex flex-col gap-4">
                <div>
                  <h2 className="text-base font-bold text-zinc-900 dark:text-white">
                    Common Error Distribution
                  </h2>
                  <p className="text-xs text-zinc-500">
                    Breakdown of algorithmic compilation, logic, and runtime failures.
                  </p>
                </div>

                <div className="flex flex-col gap-3 pt-2">
                  {errorDistribution.map((err) => {
                    const percent = Math.round((err.count / totalErrors) * 100)
                    const label = err.error_type.replace('_', ' ')

                    const color =
                      err.error_type === 'wrong_answer'
                        ? 'bg-red-500'
                        : err.error_type === 'compile_error'
                        ? 'bg-amber-500'
                        : err.error_type === 'runtime_error'
                        ? 'bg-purple-500'
                        : 'bg-blue-500'

                    return (
                      <div key={err.error_type} className="flex flex-col gap-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="capitalize font-semibold text-zinc-700 dark:text-zinc-300">
                            {label}
                          </span>
                          <span className="font-mono text-zinc-500">
                            {err.count} incidents ({percent}%)
                          </span>
                        </div>
                        <div className="w-full bg-zinc-100 dark:bg-zinc-800 h-2.5 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${color}`}
                            style={{ width: `${percent}%` }}
                          />
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
