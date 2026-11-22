import { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import {
  getCourse,
  getCourseModules,
  getCourseModuleProgress,
  CourseResponse,
  LearningModule,
  CourseProgressResponse,
} from '../api/client'
import { useAuth } from '../context/AuthContext'
import Navbar from '../components/Navbar'

export default function LearnPage() {
  const { courseId } = useParams<{ courseId: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [course, setCourse] = useState<CourseResponse | null>(null)
  const [modules, setModules] = useState<LearningModule[]>([])
  const [progress, setProgress] = useState<CourseProgressResponse | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  const isInstructor = user?.role === 'instructor'

  useEffect(() => {
    if (!courseId) return
    setLoading(true)

    Promise.all([
      getCourse(courseId),
      getCourseModules(courseId),
      getCourseModuleProgress(courseId).catch(() => null),
    ])
      .then(([cData, mData, pData]) => {
        setCourse(cData)
        // Sort modules by order_index
        const sorted = [...mData].sort((a, b) => a.order_index - b.order_index)
        setModules(sorted)
        setProgress(pData)
        setLoading(false)
      })
      .catch((err) => {
        console.error(err)
        setError('Failed to load learning modules.')
        setLoading(false)
      })
  }, [courseId])

  // Determine lock state:
  // If instructor, nothing is locked.
  // If student: module 0 is unlocked. Subsequent modules are unlocked if previous module is completed.
  const isModuleUnlocked = (index: number): boolean => {
    if (isInstructor) return true
    if (index === 0) return true
    const prevModule = modules[index - 1]
    return prevModule ? prevModule.is_completed : false
  }

  const completedCount = modules.filter((m) => m.is_completed).length
  const progressPercent = progress?.progress_percentage !== undefined ? Math.round(progress.progress_percentage) : (modules.length > 0 ? Math.round((completedCount / modules.length) * 100) : 0)

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 flex flex-col font-sans transition-colors">
      <Navbar
        customTitle={course?.title ? `${course.title} (Curriculum)` : 'Learning Path'}
        backTo={courseId ? `/courses/${courseId}` : '/'}
        backLabel="Course"
      />

      {/* Main Content */}
      <main className="flex-1 max-w-5xl w-full mx-auto px-6 py-8">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 gap-3">
            <div className="w-8 h-8 rounded-full border-4 border-orange-500/10 border-t-orange-500 animate-spin" />
            <span className="text-zinc-500 text-sm">Loading curriculum modules…</span>
          </div>
        ) : error ? (
          <div className="p-6 bg-red-500/10 border border-red-500/20 rounded-xl text-center">
            <p className="text-red-500 font-semibold">{error}</p>
          </div>
        ) : (
          <div className="flex flex-col gap-8">
            {/* Curriculum Progress Hero Card */}
            <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
              <div className="flex flex-col gap-1.5">
                <h1 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-white">
                  Course Learning Path
                </h1>
                <p className="text-sm text-zinc-500 dark:text-zinc-400">
                  Step-by-step interactive theory, video tutorials, and hands-on coding exercises.
                </p>
              </div>

              <div className="w-full sm:w-64 bg-zinc-50 dark:bg-zinc-950 p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 flex flex-col gap-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-zinc-500 dark:text-zinc-400 font-medium">Curriculum Progress</span>
                  <span className="font-bold text-orange-600 dark:text-orange-400 font-mono">
                    {progressPercent}%
                  </span>
                </div>
                <div className="w-full bg-zinc-200 dark:bg-zinc-800 h-2.5 rounded-full overflow-hidden">
                  <div
                    className="bg-orange-500 h-full transition-all duration-500 rounded-full"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
                <span className="text-[11px] text-zinc-400">
                  {completedCount} of {modules.length} modules completed
                </span>
              </div>
            </div>

            {/* Modules List */}
            <div className="flex flex-col gap-4">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
                Modules ({modules.length})
              </h2>

              {modules.length === 0 ? (
                <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-12 text-center flex flex-col items-center gap-3">
                  <span className="text-3xl">📚</span>
                  <p className="font-semibold text-zinc-800 dark:text-zinc-200">No learning modules yet</p>
                  <p className="text-sm text-zinc-500 max-w-sm">
                    {isInstructor
                      ? 'Create the first learning module with lessons and practice exercises.'
                      : 'The instructor has not published any learning modules yet.'}
                  </p>
                  {isInstructor && (
                    <Link
                      to={`/courses/${courseId}/modules/create`}
                      className="mt-2 px-4 py-2 bg-orange-600 hover:bg-orange-500 text-white rounded text-xs font-semibold"
                    >
                      Create First Module
                    </Link>
                  )}
                </div>
              ) : (
                modules.map((mod, idx) => {
                  const unlocked = isModuleUnlocked(idx)
                  const isCompleted = mod.is_completed

                  return (
                    <div
                      key={mod.id}
                      className={`relative bg-white dark:bg-zinc-900 border rounded-xl p-5 transition-all shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4 ${
                        unlocked
                          ? 'border-zinc-200 dark:border-zinc-800 hover:border-orange-500/40'
                          : 'border-zinc-200/50 dark:border-zinc-800/40 opacity-60 bg-zinc-50/50 dark:bg-zinc-950/40'
                      }`}
                    >
                      <div className="flex items-start gap-4">
                        {/* Status Icon */}
                        <div
                          className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 font-bold text-sm ${
                            isCompleted
                              ? 'bg-green-500/10 text-green-500 border border-green-500/20'
                              : unlocked
                              ? 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border border-orange-500/20'
                              : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-400'
                          }`}
                        >
                          {isCompleted ? '✓' : unlocked ? idx + 1 : '🔒'}
                        </div>

                        <div className="flex flex-col gap-1">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-semibold text-orange-600 dark:text-orange-400">
                              Module {mod.order_index}
                            </span>
                            {isCompleted && (
                              <span className="text-[10px] bg-green-500/10 text-green-600 dark:text-green-400 px-2 py-0.5 rounded-full font-semibold border border-green-500/20">
                                Completed
                              </span>
                            )}
                            {!mod.is_published && (
                              <span className="text-[10px] bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 px-2 py-0.5 rounded-full font-semibold">
                                Draft
                              </span>
                            )}
                          </div>
                          <h3 className="font-bold text-base text-zinc-900 dark:text-white">
                            {mod.title}
                          </h3>
                          {mod.description && (
                            <p className="text-xs text-zinc-500 dark:text-zinc-400 line-clamp-2">
                              {mod.description}
                            </p>
                          )}
                          <div className="flex items-center gap-3 text-xs text-zinc-400 mt-1">
                            <span>📖 {mod.content_count} lessons & exercises</span>
                          </div>
                        </div>
                      </div>

                      {/* Action Button */}
                      <div className="shrink-0 w-full md:w-auto flex items-center justify-end">
                        {unlocked ? (
                          <button
                            onClick={() => navigate(`/modules/${mod.id}`)}
                            className="w-full md:w-auto px-4 py-2 bg-orange-600 hover:bg-orange-500 text-white rounded-lg text-xs font-semibold transition-all shadow-sm"
                          >
                            {isCompleted ? 'Review Module' : 'Continue Learning →'}
                          </button>
                        ) : (
                          <div className="flex items-center gap-1.5 text-xs text-zinc-400 font-medium px-3 py-2 bg-zinc-100 dark:bg-zinc-800 rounded-lg">
                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                            </svg>
                            <span>Locked (Complete previous)</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
