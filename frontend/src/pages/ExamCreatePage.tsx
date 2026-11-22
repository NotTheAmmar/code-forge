import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  createExam,
  getCourseProblems,
  ProblemSummary,
} from '../api/client'
import Navbar from '../components/Navbar'

interface SelectedExamProblem {
  problem_id: string
  title: string
  weight: number
  order_index: number
}

export default function ExamCreatePage() {
  const { courseId } = useParams<{ courseId: string }>()
  const navigate = useNavigate()

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [durationMinutes, setDurationMinutes] = useState(60)

  // Start & End datetimes
  const now = new Date()
  const defaultStart = new Date(now.getTime() + 10 * 60000).toISOString().slice(0, 16)
  const defaultEnd = new Date(now.getTime() + 24 * 3600000).toISOString().slice(0, 16)
  const [startsAt, setStartsAt] = useState(defaultStart)
  const [endsAt, setEndsAt] = useState(defaultEnd)

  // Anti-cheat config
  const [fullscreenRequired, setFullscreenRequired] = useState(true)
  const [tabSwitchLimit, setTabSwitchLimit] = useState(3)
  const [copyPasteBlocked, setCopyPasteBlocked] = useState(true)

  // Problem selection
  const [courseProblems, setCourseProblems] = useState<ProblemSummary[]>([])
  const [selectedProblems, setSelectedProblems] = useState<SelectedExamProblem[]>([])

  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!courseId) return
    getCourseProblems(courseId)
      .then((probs) => {
        setCourseProblems(probs)
        // Select first 2 problems by default if available
        if (probs.length > 0) {
          const initial = probs.slice(0, 2).map((p, idx) => ({
            problem_id: p.id,
            title: p.title,
            weight: 50,
            order_index: idx + 1,
          }))
          setSelectedProblems(initial)
        }
      })
      .catch(() => {})
  }, [courseId])

  const toggleProblem = (p: ProblemSummary) => {
    const exists = selectedProblems.some((sp) => sp.problem_id === p.id)
    if (exists) {
      setSelectedProblems(selectedProblems.filter((sp) => sp.problem_id !== p.id))
    } else {
      setSelectedProblems([
        ...selectedProblems,
        {
          problem_id: p.id,
          title: p.title,
          weight: 50,
          order_index: selectedProblems.length + 1,
        },
      ])
    }
  }

  const updateWeight = (problemId: string, weight: number) => {
    setSelectedProblems((prev) =>
      prev.map((p) => (p.problem_id === problemId ? { ...p, weight } : p))
    )
  }

  const totalPoints = selectedProblems.reduce((acc, curr) => acc + curr.weight, 0)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!courseId) return

    if (!title.trim()) {
      setError('Exam title is required.')
      return
    }
    if (selectedProblems.length === 0) {
      setError('At least one problem must be attached to the exam.')
      return
    }

    setSaving(true)
    setError(null)

    try {
      await createExam(courseId, {
        title: title.trim(),
        description: description.trim() || undefined,
        duration_minutes: durationMinutes,
        starts_at: new Date(startsAt).toISOString(),
        ends_at: new Date(endsAt).toISOString(),
        fullscreen_required: fullscreenRequired,
        tab_switch_limit: tabSwitchLimit,
        copy_paste_blocked: copyPasteBlocked,
        problems: selectedProblems.map((p, idx) => ({
          problem_id: p.problem_id,
          order_index: idx + 1,
          weight: p.weight,
        })),
      })

      navigate(`/courses/${courseId}`)
    } catch (err) {
      console.error(err)
      setError('Failed to create proctored exam.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 flex flex-col font-sans transition-colors">
      {/* Header */}
      <Navbar
        customTitle="Create Proctored Exam"
        backTo={`/courses/${courseId}`}
        backLabel="Course"
      />

      {/* Main Content Form */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-6 py-8">
        <form onSubmit={handleSubmit} className="flex flex-col gap-6">
          {error && (
            <div className="p-4 bg-red-500/10 border border-red-500/20 text-red-500 rounded-xl text-xs font-semibold">
              {error}
            </div>
          )}

          {/* Exam Details Card */}
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 shadow-sm flex flex-col gap-4">
            <h2 className="text-base font-bold text-zinc-900 dark:text-white">
              Exam Details & Timing
            </h2>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-zinc-600 dark:text-zinc-400">
                Exam Title *
              </label>
              <input
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Midterm Examination: Data Structures & Algorithms"
                className="w-full px-3.5 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 focus:outline-none focus:ring-1 focus:ring-orange-500"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-zinc-600 dark:text-zinc-400">
                Instructions / Description
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
                placeholder="Exam rules, coverage, and guidelines for students."
                className="w-full px-3.5 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 focus:outline-none focus:ring-1 focus:ring-orange-500"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-zinc-600 dark:text-zinc-400">
                  Duration (Minutes)
                </label>
                <input
                  type="number"
                  min={5}
                  max={360}
                  value={durationMinutes}
                  onChange={(e) => setDurationMinutes(parseInt(e.target.value) || 60)}
                  className="w-full px-3.5 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 focus:outline-none"
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-zinc-600 dark:text-zinc-400">
                  Starts At
                </label>
                <input
                  type="datetime-local"
                  value={startsAt}
                  onChange={(e) => setStartsAt(e.target.value)}
                  className="w-full px-3.5 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 focus:outline-none"
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-zinc-600 dark:text-zinc-400">
                  Ends At
                </label>
                <input
                  type="datetime-local"
                  value={endsAt}
                  onChange={(e) => setEndsAt(e.target.value)}
                  className="w-full px-3.5 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 focus:outline-none"
                />
              </div>
            </div>
          </div>

          {/* Anti-Cheat Configuration */}
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 shadow-sm flex flex-col gap-4">
            <div>
              <h2 className="text-base font-bold text-zinc-900 dark:text-white">
                Proctoring & Anti-Cheat Controls
              </h2>
              <p className="text-xs text-zinc-500">
                Configure browser lockdown and violation logging parameters for students.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
              <label className="flex items-start gap-3 p-3.5 bg-zinc-50 dark:bg-zinc-950 rounded-xl border border-zinc-200 dark:border-zinc-800 cursor-pointer">
                <input
                  type="checkbox"
                  checked={fullscreenRequired}
                  onChange={(e) => setFullscreenRequired(e.target.checked)}
                  className="mt-0.5 rounded text-orange-600 focus:ring-orange-500"
                />
                <div className="flex flex-col gap-0.5">
                  <span className="text-xs font-bold text-zinc-900 dark:text-white">
                    Enforce Fullscreen
                  </span>
                  <span className="text-[11px] text-zinc-500">
                    Auto-locks browser in fullscreen mode on exam start.
                  </span>
                </div>
              </label>

              <label className="flex items-start gap-3 p-3.5 bg-zinc-50 dark:bg-zinc-950 rounded-xl border border-zinc-200 dark:border-zinc-800 cursor-pointer">
                <input
                  type="checkbox"
                  checked={copyPasteBlocked}
                  onChange={(e) => setCopyPasteBlocked(e.target.checked)}
                  className="mt-0.5 rounded text-orange-600 focus:ring-orange-500"
                />
                <div className="flex flex-col gap-0.5">
                  <span className="text-xs font-bold text-zinc-900 dark:text-white">
                    Block External Paste
                  </span>
                  <span className="text-[11px] text-zinc-500">
                    Disables external clipboard pastes into the code editor.
                  </span>
                </div>
              </label>

              <div className="p-3.5 bg-zinc-50 dark:bg-zinc-950 rounded-xl border border-zinc-200 dark:border-zinc-800 flex flex-col gap-1.5">
                <label className="text-xs font-bold text-zinc-900 dark:text-white">
                  Tab Switch Limit
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min={0}
                    max={10}
                    value={tabSwitchLimit}
                    onChange={(e) => setTabSwitchLimit(parseInt(e.target.value) || 0)}
                    className="w-20 px-2.5 py-1 text-xs rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 focus:outline-none"
                  />
                  <span className="text-[11px] text-zinc-500">switches allowed</span>
                </div>
              </div>
            </div>
          </div>

          {/* Problem Selection & Weights */}
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 shadow-sm flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-zinc-900 dark:text-white">
                  Exam Problems & Point Weights
                </h2>
                <p className="text-xs text-zinc-500">
                  Select which problems appear on the exam and allocate points. Total: {totalPoints} pts.
                </p>
              </div>
            </div>

            <div className="flex flex-col gap-2 mt-2">
              {courseProblems.length === 0 ? (
                <p className="text-xs text-zinc-500 italic">No course problems found.</p>
              ) : (
                courseProblems.map((prob) => {
                  const selected = selectedProblems.find((p) => p.problem_id === prob.id)

                  return (
                    <div
                      key={prob.id}
                      className={`p-3.5 rounded-xl border flex items-center justify-between transition-colors ${
                        selected
                          ? 'bg-orange-500/5 border-orange-500/30'
                          : 'bg-zinc-50 dark:bg-zinc-950 border-zinc-200 dark:border-zinc-800'
                      }`}
                    >
                      <label className="flex items-center gap-3 cursor-pointer flex-1">
                        <input
                          type="checkbox"
                          checked={!!selected}
                          onChange={() => toggleProblem(prob)}
                          className="rounded text-orange-600 focus:ring-orange-500"
                        />
                        <div className="flex flex-col">
                          <span className="text-xs font-bold text-zinc-900 dark:text-white">
                            {prob.title}
                          </span>
                          <span className="text-[10px] text-zinc-500 uppercase tracking-wider">
                            {prob.difficulty} • {prob.time_limit_sec}s timeout
                          </span>
                        </div>
                      </label>

                      {selected && (
                        <div className="flex items-center gap-2">
                          <label className="text-[11px] text-zinc-500 font-medium">Points:</label>
                          <input
                            type="number"
                            min={1}
                            max={500}
                            value={selected.weight}
                            onChange={(e) =>
                              updateWeight(prob.id, parseInt(e.target.value) || 0)
                            }
                            className="w-20 px-2.5 py-1 text-xs rounded-lg bg-white dark:bg-zinc-900 border border-zinc-300 dark:border-zinc-700 font-mono text-center focus:outline-none"
                          />
                        </div>
                      )}
                    </div>
                  )
                })
              )}
            </div>
          </div>

          {/* Form Actions */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <Link
              to={`/courses/${courseId}`}
              className="px-5 py-2.5 rounded-xl border border-zinc-300 dark:border-zinc-800 text-xs font-semibold hover:bg-zinc-100 dark:hover:bg-zinc-900 transition"
            >
              Cancel
            </Link>
            <button
              type="submit"
              disabled={saving}
              className="px-6 py-2.5 bg-orange-600 hover:bg-orange-500 text-white rounded-xl text-xs font-bold transition shadow-md disabled:opacity-50"
            >
              {saving ? 'Creating Proctored Exam…' : 'Create & Schedule Exam →'}
            </button>
          </div>
        </form>
      </main>
    </div>
  )
}
