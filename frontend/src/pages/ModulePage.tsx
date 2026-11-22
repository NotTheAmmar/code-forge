import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import {
  getModuleDetail,
  completeModule,
  LearningModuleDetail,
  LearningContent,
} from '../api/client'
import Navbar from '../components/Navbar'

// Helper to convert any YouTube URL into an embed URL
function getYouTubeEmbedUrl(url: string | null): string | null {
  if (!url) return null
  try {
    const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*/
    const match = url.match(regExp)
    if (match && match[2].length === 11) {
      return `https://www.youtube.com/embed/${match[2]}?rel=0`
    }
  } catch {
    // fallback
  }
  return url
}

export default function ModulePage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [module, setModule] = useState<LearningModuleDetail | null>(null)
  const [activeContentIndex, setActiveContentIndex] = useState<number>(0)
  const [completedContents, setCompletedContents] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState<boolean>(true)
  const [completing, setCompleting] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    getModuleDetail(id)
      .then((data) => {
        setModule(data)
        if (data.is_completed) {
          // Mark all completed
          setCompletedContents(new Set(data.contents.map((c) => c.id)))
        }
        setLoading(false)
      })
      .catch((err) => {
        console.error(err)
        setError('Failed to load learning module.')
        setLoading(false)
      })
  }, [id])

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex items-center justify-center gap-3">
        <div className="w-8 h-8 rounded-full border-4 border-orange-500/10 border-t-orange-500 animate-spin" />
        <span className="text-zinc-500 text-sm">Loading module content…</span>
      </div>
    )
  }

  if (error || !module) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex flex-col items-center justify-center p-6 text-center">
        <p className="text-red-500 font-semibold mb-4">{error || 'Module not found'}</p>
        <button
          onClick={() => navigate(-1)}
          className="px-4 py-2 bg-zinc-200 dark:bg-zinc-800 rounded text-xs font-semibold text-zinc-800 dark:text-zinc-200"
        >
          Go Back
        </button>
      </div>
    )
  }

  const contents = module.contents || []
  const activeContent: LearningContent | undefined = contents[activeContentIndex]
  const isLast = activeContentIndex === contents.length - 1

  const handleNextOrComplete = async () => {
    if (!activeContent) return

    // Mark current content as viewed
    const nextSet = new Set(completedContents)
    nextSet.add(activeContent.id)
    setCompletedContents(nextSet)

    if (isLast) {
      setCompleting(true)
      try {
        await completeModule(module.id, activeContent.id)
        module.is_completed = true
        navigate(`/courses/${module.course_id}/learn`)
      } catch (err) {
        console.error(err)
      } finally {
        setCompleting(false)
      }
    } else {
      setActiveContentIndex((prev) => prev + 1)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }

  const progressPercentage = contents.length > 0 ? Math.round((completedContents.size / contents.length) * 100) : 0

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 flex flex-col font-sans transition-colors">
      {/* Top Bar */}
      <Navbar
        customTitle={module.title}
        backTo={`/courses/${module.course_id}/learn`}
        backLabel="Curriculum"
      />

      {/* Main Two-Column Layout */}
      <div className="flex-1 max-w-7xl w-full mx-auto flex flex-col md:flex-row">
        {/* Left Sidebar / Stepper */}
        <aside className="w-full md:w-80 border-b md:border-b-0 md:border-r border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-5 shrink-0">
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">
                Lessons & Exercises
              </span>
              <span className="text-xs font-mono font-bold text-orange-500">
                {progressPercentage}%
              </span>
            </div>

            <div className="w-full bg-zinc-200 dark:bg-zinc-800 h-1.5 rounded-full overflow-hidden mb-1">
              <div
                className="bg-orange-500 h-full transition-all duration-300 rounded-full"
                style={{ width: `${progressPercentage}%` }}
              />
            </div>

            <div className="flex flex-col gap-1.5 mt-2">
              {contents.map((c, index) => {
                const isActive = index === activeContentIndex
                const isDone = completedContents.has(c.id)

                const icon =
                  c.content_type === 'video' ? '🎥' : c.content_type === 'problem' ? '⚡' : '📄'

                return (
                  <button
                    key={c.id}
                    onClick={() => setActiveContentIndex(index)}
                    className={`flex items-center gap-3 p-3 rounded-xl text-left text-xs transition-all ${
                      isActive
                        ? 'bg-orange-500/10 text-orange-600 dark:text-orange-400 font-bold border border-orange-500/20 shadow-sm'
                        : 'text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-900 border border-transparent'
                    }`}
                  >
                    <span className="text-base shrink-0">{icon}</span>
                    <div className="flex-1 min-w-0">
                      <p className="truncate font-medium">{c.title}</p>
                      <span className="text-[10px] uppercase text-zinc-400 tracking-wider">
                        {c.content_type}
                      </span>
                    </div>
                    {isDone && <span className="text-green-500 font-bold text-sm">✓</span>}
                  </button>
                )
              })}
            </div>
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 p-6 md:p-10 flex flex-col max-w-4xl">
          {activeContent ? (
            <div className="flex flex-col gap-6 flex-1">
              {/* Content Header */}
              <div className="border-b border-zinc-200 dark:border-zinc-800 pb-4">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-orange-600 dark:text-orange-400 mb-1">
                  <span>Part {activeContentIndex + 1} of {contents.length}</span>
                  <span>•</span>
                  <span>{activeContent.content_type}</span>
                </div>
                <h1 className="text-2xl md:text-3xl font-extrabold text-zinc-900 dark:text-white tracking-tight">
                  {activeContent.title}
                </h1>
              </div>

              {/* Render by type */}
              {activeContent.content_type === 'video' && (
                <div className="flex flex-col gap-4">
                  <div className="relative w-full aspect-video rounded-2xl overflow-hidden bg-black shadow-lg border border-zinc-800">
                    <iframe
                      src={getYouTubeEmbedUrl(activeContent.body) || ''}
                      title={activeContent.title}
                      className="w-full h-full"
                      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                      allowFullScreen
                    />
                  </div>
                  {activeContent.body && (
                    <p className="text-xs text-zinc-400">
                      Source link:{' '}
                      <a
                        href={activeContent.body}
                        target="_blank"
                        rel="noreferrer"
                        className="text-orange-500 hover:underline"
                      >
                        {activeContent.body}
                      </a>
                    </p>
                  )}
                </div>
              )}

              {activeContent.content_type === 'text' && (
                <div className="prose dark:prose-invert max-w-none text-sm text-zinc-700 dark:text-zinc-300 leading-relaxed">
                  <ReactMarkdown>{activeContent.body || ''}</ReactMarkdown>
                </div>
              )}

              {activeContent.content_type === 'problem' && (
                <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 shadow-sm flex flex-col gap-4">
                  <div className="flex items-center gap-3">
                    <span className="text-3xl">💻</span>
                    <div>
                      <h2 className="text-lg font-bold text-zinc-900 dark:text-white">
                        Practice Coding Exercise
                      </h2>
                      <p className="text-xs text-zinc-500 dark:text-zinc-400">
                        Solve this algorithmic challenge in the CodeForge IDE with instant test feedback.
                      </p>
                    </div>
                  </div>

                  {activeContent.body && (
                    <p className="text-sm text-zinc-600 dark:text-zinc-300 bg-zinc-50 dark:bg-zinc-950 p-4 rounded-xl border border-zinc-200 dark:border-zinc-800">
                      {activeContent.body}
                    </p>
                  )}

                  <div className="pt-2">
                    <Link
                      to={
                        activeContent.problem_id
                          ? `/problems/${activeContent.problem_id}?courseId=${module.course_id}&moduleId=${module.id}`
                          : `/courses/${module.course_id}?tab=problems`
                      }
                      className="inline-flex items-center gap-2 px-5 py-2.5 bg-orange-600 hover:bg-orange-500 text-white rounded-xl text-xs font-semibold transition-all shadow-md"
                    >
                      <span>Open in CodeForge IDE →</span>
                    </Link>
                  </div>
                </div>
              )}

              {/* Footer Navigation */}
              <div className="mt-auto pt-10 border-t border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
                <button
                  onClick={() => setActiveContentIndex((prev) => Math.max(0, prev - 1))}
                  disabled={activeContentIndex === 0}
                  className="px-4 py-2 border border-zinc-200 dark:border-zinc-800 text-zinc-600 dark:text-zinc-400 rounded-xl text-xs font-semibold disabled:opacity-30 disabled:cursor-not-allowed hover:bg-zinc-100 dark:hover:bg-zinc-900 transition"
                >
                  ← Previous
                </button>

                <button
                  onClick={handleNextOrComplete}
                  disabled={completing}
                  className="px-6 py-2.5 bg-orange-600 hover:bg-orange-500 text-white rounded-xl text-xs font-bold transition shadow-md flex items-center gap-2"
                >
                  {completing ? (
                    <span>Saving progress…</span>
                  ) : isLast ? (
                    <span>Complete Module ✓</span>
                  ) : (
                    <span>Mark as Done & Next →</span>
                  )}
                </button>
              </div>
            </div>
          ) : (
            <p className="text-zinc-500">No content found.</p>
          )}
        </main>
      </div>
    </div>
  )
}
