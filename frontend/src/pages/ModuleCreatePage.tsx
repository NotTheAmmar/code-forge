import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  createCourseModule,
  addModuleContent,
  getCourseProblems,
  ProblemSummary,
} from '../api/client'

interface DraftContent {
  id: string
  content_type: 'text' | 'video' | 'problem'
  title: string
  body: string
  problem_id: string
}

export default function ModuleCreatePage() {
  const { courseId } = useParams<{ courseId: string }>()
  const navigate = useNavigate()

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [orderIndex, setOrderIndex] = useState(1)
  const [isPublished, setIsPublished] = useState(true)

  const [contents, setContents] = useState<DraftContent[]>([
    {
      id: 'c-1',
      content_type: 'text',
      title: 'Introduction & Concepts',
      body: '## Overview\nExplain key algorithmic theory and principles here.',
      problem_id: '',
    },
  ])

  const [courseProblems, setCourseProblems] = useState<ProblemSummary[]>([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!courseId) return
    getCourseProblems(courseId)
      .then(setCourseProblems)
      .catch(() => {})
  }, [courseId])

  const handleAddContent = (type: 'text' | 'video' | 'problem') => {
    const newDraft: DraftContent = {
      id: 'c-' + Math.random().toString(36).substring(2, 7),
      content_type: type,
      title: type === 'video' ? 'Video Lecture' : type === 'problem' ? 'Practice Exercise' : 'Theory Lesson',
      body: type === 'video' ? 'https://www.youtube.com/watch?v=kqtD5dpn9C8' : '',
      problem_id: courseProblems[0]?.id || '',
    }
    setContents([...contents, newDraft])
  }

  const handleUpdateContent = (id: string, field: keyof DraftContent, value: string) => {
    setContents((prev) =>
      prev.map((c) => (c.id === id ? { ...c, [field]: value } : c))
    )
  }

  const handleRemoveContent = (id: string) => {
    setContents((prev) => prev.filter((c) => c.id !== id))
  }

  const handleMove = (index: number, direction: 'up' | 'down') => {
    const targetIndex = direction === 'up' ? index - 1 : index + 1
    if (targetIndex < 0 || targetIndex >= contents.length) return
    const updated = [...contents]
    const temp = updated[index]
    updated[index] = updated[targetIndex]
    updated[targetIndex] = temp
    setContents(updated)
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!courseId) return
    if (!title.trim()) {
      setError('Module title is required.')
      return
    }

    setSaving(true)
    setError(null)
    try {
      const createdModule = await createCourseModule(courseId, {
        title: title.trim(),
        description: description.trim() || undefined,
        order_index: orderIndex,
        is_published: isPublished,
      })

      // Add all contents sequentially
      for (let i = 0; i < contents.length; i++) {
        const item = contents[i]
        await addModuleContent(createdModule.id, {
          content_type: item.content_type,
          title: item.title,
          body: item.body || null,
          problem_id: item.problem_id || null,
          order_index: i + 1,
        })
      }

      navigate(`/courses/${courseId}/learn`)
    } catch (err) {
      console.error(err)
      setError('Failed to create learning module.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 flex flex-col font-sans transition-colors">
      {/* Main Form */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-6 py-8 flex flex-col gap-6">
        <div>
          <Link
            to={`/courses/${courseId}/learn`}
            className="inline-flex items-center gap-1.5 text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-white text-xs font-semibold uppercase tracking-wider transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            <span>Back to Curriculum</span>
          </Link>
        </div>
        <form onSubmit={handleSave} className="flex flex-col gap-6">
          {error && (
            <div className="p-4 bg-red-500/10 border border-red-500/20 text-red-500 rounded-xl text-xs font-semibold">
              {error}
            </div>
          )}

          {/* Module Metadata Card */}
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 shadow-sm flex flex-col gap-4">
            <h2 className="text-base font-bold text-zinc-900 dark:text-white">
              Module Details
            </h2>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-zinc-600 dark:text-zinc-400">
                Module Title *
              </label>
              <input
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Module 3: Dynamic Programming Foundations"
                className="w-full px-3.5 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 focus:outline-none focus:ring-1 focus:ring-orange-500"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-zinc-600 dark:text-zinc-400">
                Short Description
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
                placeholder="Key concepts, learning goals, and skills learned in this module."
                className="w-full px-3.5 py-2 text-xs rounded-xl bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 focus:outline-none focus:ring-1 focus:ring-orange-500"
              />
            </div>

            <div className="flex items-center gap-6 pt-2">
              <div className="flex items-center gap-2">
                <label className="text-xs font-semibold text-zinc-600 dark:text-zinc-400">
                  Sequence Order:
                </label>
                <input
                  type="number"
                  min={1}
                  value={orderIndex}
                  onChange={(e) => setOrderIndex(parseInt(e.target.value) || 1)}
                  className="w-20 px-3 py-1 text-xs rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 focus:outline-none"
                />
              </div>

              <label className="flex items-center gap-2 text-xs font-medium cursor-pointer">
                <input
                  type="checkbox"
                  checked={isPublished}
                  onChange={(e) => setIsPublished(e.target.checked)}
                  className="rounded text-orange-600 focus:ring-orange-500"
                />
                <span>Publish Immediately</span>
              </label>
            </div>
          </div>

          {/* Content Items Builder */}
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 shadow-sm flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-zinc-900 dark:text-white">
                  Curriculum Content Items
                </h2>
                <p className="text-xs text-zinc-500">
                  Add reading materials, embedded video lectures, or practice problems.
                </p>
              </div>

              {/* Add buttons */}
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => handleAddContent('text')}
                  className="px-2.5 py-1.5 bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-800 dark:text-zinc-200 rounded-lg text-xs font-medium transition"
                >
                  + 📄 Text
                </button>
                <button
                  type="button"
                  onClick={() => handleAddContent('video')}
                  className="px-2.5 py-1.5 bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-800 dark:text-zinc-200 rounded-lg text-xs font-medium transition"
                >
                  + 🎥 Video
                </button>
                <button
                  type="button"
                  onClick={() => handleAddContent('problem')}
                  className="px-2.5 py-1.5 bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-800 dark:text-zinc-200 rounded-lg text-xs font-medium transition"
                >
                  + ⚡ Problem
                </button>
              </div>
            </div>

            <div className="flex flex-col gap-3 mt-2">
              {contents.map((item, index) => (
                <div
                  key={item.id}
                  className="p-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl flex flex-col gap-3"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-orange-500">
                        #{index + 1}
                      </span>
                      <span className="text-xs font-bold uppercase tracking-wider text-zinc-500">
                        {item.content_type}
                      </span>
                    </div>

                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => handleMove(index, 'up')}
                        disabled={index === 0}
                        className="p-1 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 disabled:opacity-20"
                      >
                        ▲
                      </button>
                      <button
                        type="button"
                        onClick={() => handleMove(index, 'down')}
                        disabled={index === contents.length - 1}
                        className="p-1 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 disabled:opacity-20"
                      >
                        ▼
                      </button>
                      <button
                        type="button"
                        onClick={() => handleRemoveContent(item.id)}
                        className="p-1 text-red-500 hover:text-red-700 text-xs ml-1"
                      >
                        ✕
                      </button>
                    </div>
                  </div>

                  <div className="flex flex-col gap-1.5">
                    <label className="text-[11px] font-semibold text-zinc-500">Title</label>
                    <input
                      type="text"
                      value={item.title}
                      onChange={(e) => handleUpdateContent(item.id, 'title', e.target.value)}
                      placeholder="Item Title"
                      className="w-full px-3 py-1.5 text-xs rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 focus:outline-none"
                    />
                  </div>

                  {item.content_type === 'video' ? (
                    <div className="flex flex-col gap-1.5">
                      <label className="text-[11px] font-semibold text-zinc-500">
                        YouTube Video URL
                      </label>
                      <input
                        type="url"
                        value={item.body}
                        onChange={(e) => handleUpdateContent(item.id, 'body', e.target.value)}
                        placeholder="https://www.youtube.com/watch?v=..."
                        className="w-full px-3 py-1.5 text-xs rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 focus:outline-none"
                      />
                    </div>
                  ) : item.content_type === 'text' ? (
                    <div className="flex flex-col gap-1.5">
                      <label className="text-[11px] font-semibold text-zinc-500">
                        Theory Body (Markdown)
                      </label>
                      <textarea
                        value={item.body}
                        onChange={(e) => handleUpdateContent(item.id, 'body', e.target.value)}
                        rows={4}
                        placeholder="Write markdown theory, explanation, and code examples..."
                        className="w-full px-3 py-2 text-xs rounded-lg font-mono bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 focus:outline-none"
                      />
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div className="flex flex-col gap-1.5">
                        <label className="text-[11px] font-semibold text-zinc-500">
                          Select Practice Problem
                        </label>
                        <select
                          value={item.problem_id}
                          onChange={(e) => handleUpdateContent(item.id, 'problem_id', e.target.value)}
                          className="w-full px-3 py-1.5 text-xs rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 focus:outline-none"
                        >
                          <option value="">-- Choose a course problem --</option>
                          {courseProblems.map((p) => (
                            <option key={p.id} value={p.id}>
                              {p.title} ({p.difficulty})
                            </option>
                          ))}
                        </select>
                      </div>

                      <div className="flex flex-col gap-1.5">
                        <label className="text-[11px] font-semibold text-zinc-500">
                          Exercise Instructions
                        </label>
                        <input
                          type="text"
                          value={item.body}
                          onChange={(e) => handleUpdateContent(item.id, 'body', e.target.value)}
                          placeholder="Brief prompt for students..."
                          className="w-full px-3 py-1.5 text-xs rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 focus:outline-none"
                        />
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-4">
            <Link
              to={`/courses/${courseId}/learn`}
              className="px-5 py-2.5 rounded-xl border border-zinc-300 dark:border-zinc-800 text-xs font-semibold hover:bg-zinc-100 dark:hover:bg-zinc-900 transition"
            >
              Cancel
            </Link>
            <button
              type="submit"
              disabled={saving}
              className="px-6 py-2.5 bg-orange-600 hover:bg-orange-500 text-white rounded-xl text-xs font-bold transition shadow-md disabled:opacity-50"
            >
              {saving ? 'Creating Module…' : 'Create & Publish Module →'}
            </button>
          </div>
        </form>
      </main>
    </div>
  )
}
