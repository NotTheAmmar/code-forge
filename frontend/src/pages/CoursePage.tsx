import { useEffect, useState } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import {
  getCourse,
  getCourseProblems,
  getCourseLabs,
  createProblem,
  bulkImportProblems,
  CourseResponse,
  ProblemSummary,
  LabSession,
  ProblemCreateInput,
  TestCaseInput,
} from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'

type Tab = 'problems' | 'labs' | 'gradebook'

export default function CoursePage() {
  const { id } = useParams<{ id: string }>()
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const navigate = useNavigate()

  const [course, setCourse] = useState<CourseResponse | null>(null)
  const [problems, setProblems] = useState<ProblemSummary[]>([])
  const [labs, setLabs] = useState<LabSession[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<Tab>('problems')
  const [showCode, setShowCode] = useState(false)
  const [copied, setCopied] = useState(false)

  // Modals for instructor
  const [showAddProblem, setShowAddProblem] = useState(false)
  const [showBulkImport, setShowBulkImport] = useState(false)

  // Add Problem form state
  const [newTitle, setNewTitle] = useState('')
  const [newSlug, setNewSlug] = useState('')
  const [newDifficulty, setNewDifficulty] = useState<'easy' | 'medium' | 'hard'>('easy')
  const [newDesc, setNewDesc] = useState('')
  const [newPythonStarter, setNewPythonStarter] = useState('def solution():\n    # Write your solution here\n    pass\n')
  const [newJavaStarter, setNewJavaStarter] = useState('public class Solution {\n    public static void main(String[] args) {\n        // Write your solution here\n    }\n}\n')
  const [testCases, setTestCases] = useState<TestCaseInput[]>([
    { label: 'Sample 1', input_data: '5\n', expected_output: '10\n', is_visible: true, order_index: 0 },
  ])
  const [submittingProblem, setSubmittingProblem] = useState(false)
  const [addProblemError, setAddProblemError] = useState<string | null>(null)

  // Bulk Import state
  const [bulkJson, setBulkJson] = useState('')
  const [bulkImporting, setBulkImporting] = useState(false)
  const [bulkResult, setBulkResult] = useState<{ imported_count: number; failed_count: number; errors: string[] } | null>(null)
  const [bulkError, setBulkError] = useState<string | null>(null)

  const isInstructor = user?.role === 'instructor'

  const refreshData = () => {
    if (!id) return
    getCourseProblems(id).then(setProblems).catch(() => {})
  }

  useEffect(() => {
    if (!id) return
    Promise.all([getCourse(id), getCourseProblems(id), getCourseLabs(id)])
      .then(([c, p, l]) => { setCourse(c); setProblems(p); setLabs(l) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [id])

  const handleCopyCode = () => {
    if (!course) return
    navigator.clipboard.writeText(course.join_code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleTitleChange = (val: string) => {
    setNewTitle(val)
    // auto-generate slug if slug wasn't heavily customized
    const autoSlug = val.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '')
    setNewSlug(autoSlug)
  }

  const addTestCase = () => {
    setTestCases([
      ...testCases,
      { label: `Case ${testCases.length + 1}`, input_data: '', expected_output: '', is_visible: true, order_index: testCases.length },
    ])
  }

  const removeTestCase = (idx: number) => {
    if (testCases.length <= 1) return
    setTestCases(testCases.filter((_, i) => i !== idx))
  }

  const updateTestCase = (idx: number, field: keyof TestCaseInput, value: any) => {
    const updated = [...testCases]
    updated[idx] = { ...updated[idx], [field]: value }
    setTestCases(updated)
  }

  const handleCreateProblemSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!id) return
    if (!newTitle.trim() || !newSlug.trim() || !newDesc.trim()) {
      setAddProblemError('Please fill in title, slug, and description.')
      return
    }
    if (testCases.length === 0) {
      setAddProblemError('At least one test case is required.')
      return
    }

    setSubmittingProblem(true)
    setAddProblemError(null)

    const payload: ProblemCreateInput = {
      title: newTitle.trim(),
      slug: newSlug.trim(),
      difficulty: newDifficulty,
      description: newDesc.trim(),
      starter_code_python: newPythonStarter,
      starter_code_java: newJavaStarter,
      test_cases: testCases,
    }

    try {
      await createProblem(id, payload)
      setShowAddProblem(false)
      // Reset form
      setNewTitle('')
      setNewSlug('')
      setNewDesc('')
      setTestCases([{ label: 'Sample 1', input_data: '', expected_output: '', is_visible: true, order_index: 0 }])
      refreshData()
    } catch (err: any) {
      setAddProblemError(err.response?.data?.detail || 'Failed to create problem. Check slug uniqueness.')
    } finally {
      setSubmittingProblem(false)
    }
  }

  const handleBulkImportSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!id) return
    setBulkError(null)
    setBulkResult(null)

    let parsed: ProblemCreateInput[]
    try {
      parsed = JSON.parse(bulkJson)
      if (!Array.isArray(parsed)) {
        throw new Error('Root JSON must be an array of problem objects.')
      }
    } catch (err: any) {
      setBulkError(err.message || 'Invalid JSON format.')
      return
    }

    setBulkImporting(true)
    try {
      const res = await bulkImportProblems(id, parsed)
      setBulkResult(res)
      refreshData()
      if (res.failed_count === 0) {
        setTimeout(() => {
          setShowBulkImport(false)
          setBulkJson('')
          setBulkResult(null)
        }, 1500)
      }
    } catch (err: any) {
      setBulkError(err.response?.data?.detail || 'Bulk import request failed.')
    } finally {
      setBulkImporting(false)
    }
  }

  const loadExampleTemplate = () => {
    const template: ProblemCreateInput[] = [
      {
        title: 'Sum of Two Numbers',
        slug: 'sum-of-two-numbers',
        difficulty: 'easy',
        description: 'Read two integers and print their sum.',
        starter_code_python: 'import sys\n\ndef main():\n    lines = sys.stdin.read().split()\n    if not lines: return\n    a = int(lines[0])\n    b = int(lines[1])\n    print(a + b)\n\nif __name__ == "__main__":\n    main()\n',
        starter_code_java: 'import java.util.Scanner;\n\npublic class Solution {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int a = sc.nextInt();\n        int b = sc.nextInt();\n        System.out.println(a + b);\n    }\n}\n',
        test_cases: [
          { label: 'Sample 1', input_data: '3 5\n', expected_output: '8\n', is_visible: true, order_index: 0 },
          { label: 'Hidden Case 1', input_data: '-10 20\n', expected_output: '10\n', is_visible: false, order_index: 1 },
        ],
      },
    ]
    setBulkJson(JSON.stringify(template, null, 2))
  }

  const isSolved = (slug: string) => localStorage.getItem(`solved_${slug}`) === 'true'

  const activeLabs = labs.filter((l) => l.is_active)
  const pastLabs = labs.filter((l) => !l.is_active)

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex items-center justify-center gap-3">
        <div className="w-8 h-8 rounded-full border-4 border-orange-500/10 border-t-orange-500 animate-spin" />
        <span className="text-zinc-500 text-sm font-medium">Loading course…</span>
      </div>
    )
  }

  if (!course) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex items-center justify-center">
        <div className="text-center">
          <p className="text-zinc-500 mb-4">Course not found.</p>
          <Link to="/" className="text-orange-500 hover:text-orange-600 font-medium text-sm">← Back to Courses</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 font-sans flex flex-col transition-colors duration-200">
      {/* Header */}
      <header className="border-b border-zinc-200 dark:border-zinc-900 bg-white/80 dark:bg-zinc-900/20 backdrop-blur sticky top-0 z-50 px-6 py-4 flex items-center justify-between transition-colors">
        <div className="flex items-center gap-3">
          <Link to="/" className="flex items-center gap-1.5 text-zinc-500 dark:text-zinc-400 hover:text-orange-500 dark:hover:text-orange-400 text-xs font-semibold uppercase tracking-wider transition-colors">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
            Courses
          </Link>
          <div className="h-4 w-[1px] bg-zinc-200 dark:bg-zinc-800" />
          <span className="font-bold text-sm text-zinc-900 dark:text-white tracking-tight">{course.title}</span>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={toggleTheme} className="p-1.5 rounded-lg bg-zinc-100 dark:bg-zinc-900 text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white border border-zinc-200 dark:border-zinc-800 transition-colors">
            {theme === 'dark' ? (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m0-12.728l.707.707m12.728 12.728l.707.707M12 8a4 4 0 100 8 4 4 0 000-8z" /></svg>
            ) : (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" /></svg>
            )}
          </button>
          <button onClick={() => { logout(); navigate('/login') }} className="text-xs text-zinc-500 dark:text-zinc-400 hover:text-red-500 transition-colors font-medium">Sign out</button>
        </div>
      </header>

      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8 flex flex-col gap-6">
        {/* Course header card */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-bl from-orange-500/5 to-transparent rounded-full -translate-y-1/2 translate-x-1/4" />
          <div className="relative">
            <div className="flex flex-wrap items-center justify-between gap-4 mb-2">
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-extrabold text-zinc-900 dark:text-white tracking-tight">{course.title}</h1>
              </div>

              {/* Invite Code Badge with Copy Action */}
              <div className="flex items-center gap-2 bg-zinc-100 dark:bg-zinc-800/80 px-3 py-1.5 rounded-xl border border-zinc-200 dark:border-zinc-700">
                <span className="text-xs text-zinc-500 dark:text-zinc-400 font-medium">Invite Code:</span>
                <span className="font-mono text-xs font-bold text-zinc-900 dark:text-white">
                  {showCode ? course.join_code : '••••••••'}
                </span>
                <button
                  type="button"
                  onClick={() => setShowCode(!showCode)}
                  className="text-xs text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 ml-1"
                  title={showCode ? 'Hide code' : 'Show code'}
                >
                  {showCode ? 'Hide' : 'Show'}
                </button>
                <div className="h-3.5 w-[1px] bg-zinc-300 dark:bg-zinc-700 mx-1" />
                <button
                  type="button"
                  onClick={handleCopyCode}
                  className="text-xs font-semibold text-orange-600 dark:text-orange-400 hover:text-orange-700 dark:hover:text-orange-300 flex items-center gap-1 transition-colors"
                >
                  {copied ? (
                    <>
                      <svg className="w-3.5 h-3.5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" /></svg>
                      <span className="text-green-500">Copied!</span>
                    </>
                  ) : (
                    <>
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                      <span>Copy</span>
                    </>
                  )}
                </button>
              </div>
            </div>
            <p className="text-zinc-500 dark:text-zinc-400 text-sm max-w-2xl">{course.description}</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-1 bg-zinc-100 dark:bg-zinc-900 rounded-lg p-1 self-start border border-zinc-200 dark:border-zinc-800">
          {(['problems', 'labs', ...(isInstructor ? ['gradebook'] : [])] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 rounded-md text-sm font-semibold capitalize transition-all ${
                tab === t
                  ? 'bg-white dark:bg-zinc-800 text-zinc-900 dark:text-white shadow-sm'
                  : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200'
              }`}
            >
              {t === 'labs' ? 'Lab Sessions' : t}
            </button>
          ))}
        </div>

        {/* ── Problems Tab ── */}
        {tab === 'problems' && (
          <div className="flex flex-col gap-4">
            {isInstructor && (
              <div className="flex items-center justify-between bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl px-5 py-3">
                <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Instructor Problem Controls</span>
                <div className="flex items-center gap-2.5">
                  <button
                    onClick={() => setShowAddProblem(true)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-orange-500 hover:bg-orange-600 text-white rounded-lg text-xs font-semibold shadow-sm transition-all"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                    + Add Problem
                  </button>
                  <button
                    onClick={() => setShowBulkImport(true)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-200 border border-zinc-300 dark:border-zinc-700 rounded-lg text-xs font-semibold transition-all"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
                    Bulk Import
                  </button>
                </div>
              </div>
            )}

            <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden shadow-sm">
              <div className="px-6 py-4 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
                <h2 className="font-bold text-zinc-900 dark:text-white">Problems</h2>
                <span className="text-xs bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400 px-2 py-0.5 rounded-full">{problems.length} total</span>
              </div>
              <div className="divide-y divide-zinc-100 dark:divide-zinc-800/50">
                {problems.map((p) => {
                  const solved = isSolved(p.slug)
                  return (
                    <Link key={p.id} to={`/problems/${p.slug}`} className="flex items-center justify-between px-6 py-4 hover:bg-zinc-50 dark:hover:bg-zinc-800/30 transition-colors group">
                      <div className="flex items-center gap-4">
                        <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold border ${solved ? 'bg-green-500/10 border-green-500/20 text-green-500' : 'border-zinc-200 dark:border-zinc-700 text-zinc-400'}`}>
                          {solved ? '✓' : '·'}
                        </span>
                        <div>
                          <span className="font-semibold text-zinc-800 dark:text-white group-hover:text-orange-500 transition-colors">{p.title}</span>
                          <span className={`ml-3 text-xs px-2 py-0.5 rounded font-medium uppercase border ${
                            p.difficulty === 'easy' ? 'text-green-500 border-green-500/20 bg-green-500/5'
                            : p.difficulty === 'medium' ? 'text-yellow-500 border-yellow-500/20 bg-yellow-500/5'
                            : 'text-red-500 border-red-500/20 bg-red-500/5'
                          }`}>{p.difficulty}</span>
                        </div>
                      </div>
                      <svg className="w-4 h-4 text-zinc-400 group-hover:text-orange-500 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
                    </Link>
                  )
                })}
                {problems.length === 0 && (
                  <div className="text-center py-12 text-zinc-400 text-sm">
                    No problems in this course yet.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ── Labs Tab ── */}
        {tab === 'labs' && (
          <div className="flex flex-col gap-5">
            {isInstructor && (
              <Link
                to={`/courses/${id}/labs/create`}
                className="inline-flex items-center gap-1.5 self-start px-4 py-2.5 bg-orange-500 hover:bg-orange-600 text-white rounded-lg text-sm font-semibold transition-all shadow-lg shadow-orange-500/20"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                Create Lab Session
              </Link>
            )}

            {/* Active labs */}
            {activeLabs.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-green-500 uppercase tracking-wider mb-3 flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" /> Active Labs
                </h3>
                <div className="grid gap-3">
                  {activeLabs.map((lab) => (
                    <Link key={lab.id} to={isInstructor ? `/labs/${lab.id}/dashboard` : `/labs/${lab.id}`}
                      className="bg-white dark:bg-zinc-900 border border-green-500/20 rounded-xl p-5 flex items-center justify-between hover:shadow-lg hover:border-green-500/40 transition-all group"
                    >
                      <div>
                        <h4 className="font-bold text-zinc-900 dark:text-white group-hover:text-green-500 transition-colors">{lab.title}</h4>
                        <p className="text-zinc-500 dark:text-zinc-400 text-sm mt-0.5">{lab.topic} · {lab.problem_count} problems · {lab.mandatory_count} mandatory</p>
                        <p className="text-xs text-zinc-400 mt-1">Ends {new Date(lab.ends_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
                      </div>
                      <div className="px-3 py-1.5 rounded-full bg-green-500/10 text-green-500 text-xs font-semibold border border-green-500/20">
                        LIVE
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            )}

            {/* Past labs */}
            {pastLabs.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-3">Past Labs</h3>
                <div className="grid gap-3">
                  {pastLabs.map((lab) => (
                    <Link key={lab.id} to={isInstructor ? `/labs/${lab.id}/dashboard` : `/labs/${lab.id}`}
                      className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5 flex items-center justify-between hover:shadow-md transition-all group"
                    >
                      <div>
                        <h4 className="font-semibold text-zinc-700 dark:text-zinc-300 group-hover:text-orange-500 transition-colors">{lab.title}</h4>
                        <p className="text-zinc-500 dark:text-zinc-400 text-sm mt-0.5">{lab.topic} · {lab.problem_count} problems</p>
                        <p className="text-xs text-zinc-400 mt-1">{new Date(lab.starts_at).toLocaleDateString()}</p>
                      </div>
                      <span className="text-xs text-zinc-400 dark:text-zinc-600">Ended</span>
                    </Link>
                  ))}
                </div>
              </div>
            )}

            {labs.length === 0 && (
              <div className="text-center py-16 text-zinc-500 dark:text-zinc-400 text-sm">
                No lab sessions yet.{isInstructor && ' Create one to get started!'}
              </div>
            )}
          </div>
        )}

        {/* ── Gradebook Tab ── */}
        {tab === 'gradebook' && isInstructor && (
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-6 text-center">
            <Link
              to={`/courses/${id}/gradebook`}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-orange-500 hover:bg-orange-600 text-white rounded-lg font-semibold text-sm shadow-lg shadow-orange-500/20 transition-all"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
              Open Full Gradebook
            </Link>
          </div>
        )}
      </main>

      {/* ── Add Problem Modal ── */}
      {showAddProblem && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 w-full max-w-2xl my-8 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-zinc-200 dark:border-zinc-800">
              <h3 className="text-lg font-bold text-zinc-900 dark:text-white">Create New Problem</h3>
              <button onClick={() => setShowAddProblem(false)} className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 text-xl font-bold">×</button>
            </div>

            {addProblemError && (
              <div className="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-xs font-medium">
                {addProblemError}
              </div>
            )}

            <form onSubmit={handleCreateProblemSubmit} className="mt-4 flex flex-col gap-4 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-zinc-600 dark:text-zinc-300 font-semibold mb-1">Problem Title</label>
                  <input
                    type="text"
                    required
                    value={newTitle}
                    onChange={(e) => handleTitleChange(e.target.value)}
                    placeholder="e.g. Palindrome Number"
                    className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg text-zinc-900 dark:text-white focus:outline-none focus:border-orange-500"
                  />
                </div>
                <div>
                  <label className="block text-zinc-600 dark:text-zinc-300 font-semibold mb-1">Slug (Identifier)</label>
                  <input
                    type="text"
                    required
                    value={newSlug}
                    onChange={(e) => setNewSlug(e.target.value)}
                    placeholder="e.g. palindrome-number"
                    className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg text-zinc-900 dark:text-white focus:outline-none focus:border-orange-500 font-mono text-xs"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-zinc-600 dark:text-zinc-300 font-semibold mb-1">Difficulty</label>
                  <select
                    value={newDifficulty}
                    onChange={(e: any) => setNewDifficulty(e.target.value)}
                    className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg text-zinc-900 dark:text-white focus:outline-none focus:border-orange-500"
                  >
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-zinc-600 dark:text-zinc-300 font-semibold mb-1">Description (Markdown)</label>
                <textarea
                  rows={4}
                  required
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  placeholder="Problem description, input/output specifications, and constraints..."
                  className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg text-zinc-900 dark:text-white focus:outline-none focus:border-orange-500 font-mono text-xs"
                />
              </div>

              {/* Starter Codes */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-zinc-600 dark:text-zinc-300 font-semibold mb-1">Python Starter</label>
                  <textarea
                    rows={4}
                    value={newPythonStarter}
                    onChange={(e) => setNewPythonStarter(e.target.value)}
                    className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg text-zinc-900 dark:text-white focus:outline-none focus:border-orange-500 font-mono text-[11px]"
                  />
                </div>
                <div>
                  <label className="block text-zinc-600 dark:text-zinc-300 font-semibold mb-1">Java Starter</label>
                  <textarea
                    rows={4}
                    value={newJavaStarter}
                    onChange={(e) => setNewJavaStarter(e.target.value)}
                    className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg text-zinc-900 dark:text-white focus:outline-none focus:border-orange-500 font-mono text-[11px]"
                  />
                </div>
              </div>

              {/* Test Cases */}
              <div className="mt-2 border-t border-zinc-200 dark:border-zinc-800 pt-3">
                <div className="flex items-center justify-between mb-2">
                  <label className="text-zinc-600 dark:text-zinc-300 font-semibold">Test Cases ({testCases.length})</label>
                  <button
                    type="button"
                    onClick={addTestCase}
                    className="text-xs text-orange-500 hover:text-orange-600 font-semibold"
                  >
                    + Add Test Case
                  </button>
                </div>
                <div className="space-y-3 max-h-48 overflow-y-auto pr-1">
                  {testCases.map((tc, idx) => (
                    <div key={idx} className="p-3 bg-zinc-50 dark:bg-zinc-800/50 rounded-lg border border-zinc-200 dark:border-zinc-700">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-semibold text-zinc-700 dark:text-zinc-300">Case #{idx + 1}</span>
                        <div className="flex items-center gap-3">
                          <label className="flex items-center gap-1.5 cursor-pointer text-zinc-600 dark:text-zinc-400 text-[11px]">
                            <input
                              type="checkbox"
                              checked={tc.is_visible}
                              onChange={(e) => updateTestCase(idx, 'is_visible', e.target.checked)}
                              className="rounded border-zinc-400 text-orange-500 focus:ring-orange-500"
                            />
                            Visible to Student
                          </label>
                          {testCases.length > 1 && (
                            <button
                              type="button"
                              onClick={() => removeTestCase(idx)}
                              className="text-red-500 hover:text-red-700 text-xs font-semibold"
                            >
                              Remove
                            </button>
                          )}
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <span className="text-[10px] text-zinc-500 block mb-1">Standard Input:</span>
                          <textarea
                            rows={2}
                            required
                            value={tc.input_data}
                            onChange={(e) => updateTestCase(idx, 'input_data', e.target.value)}
                            placeholder="Input data"
                            className="w-full px-2 py-1 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 rounded text-zinc-900 dark:text-white font-mono text-[11px]"
                          />
                        </div>
                        <div>
                          <span className="text-[10px] text-zinc-500 block mb-1">Expected Output:</span>
                          <textarea
                            rows={2}
                            required
                            value={tc.expected_output}
                            onChange={(e) => updateTestCase(idx, 'expected_output', e.target.value)}
                            placeholder="Expected stdout"
                            className="w-full px-2 py-1 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 rounded text-zinc-900 dark:text-white font-mono text-[11px]"
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Action buttons */}
              <div className="flex items-center justify-end gap-3 pt-4 border-t border-zinc-200 dark:border-zinc-800">
                <button
                  type="button"
                  onClick={() => setShowAddProblem(false)}
                  className="px-4 py-2 rounded-lg border border-zinc-200 dark:border-zinc-700 text-zinc-600 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingProblem}
                  className="px-5 py-2 bg-orange-500 hover:bg-orange-600 disabled:opacity-50 text-white rounded-lg font-semibold shadow-md shadow-orange-500/20 transition-all flex items-center gap-2"
                >
                  {submittingProblem ? 'Saving…' : 'Create Problem'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Bulk Import Modal ── */}
      {showBulkImport && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 w-full max-w-2xl shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-zinc-200 dark:border-zinc-800">
              <div>
                <h3 className="text-lg font-bold text-zinc-900 dark:text-white">Bulk Import Problems</h3>
                <p className="text-zinc-500 dark:text-zinc-400 text-xs mt-0.5">Paste a JSON array containing problem definitions and test cases.</p>
              </div>
              <button onClick={() => setShowBulkImport(false)} className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 text-xl font-bold">×</button>
            </div>

            {bulkError && (
              <div className="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-xs font-medium">
                {bulkError}
              </div>
            )}

            {bulkResult && (
              <div className="mt-4 p-3 rounded-lg bg-green-500/10 border border-green-500/20 text-green-700 dark:text-green-300 text-xs font-medium">
                ✅ Imported {bulkResult.imported_count} problem(s). {bulkResult.failed_count > 0 && `(${bulkResult.failed_count} failed)`}
                {bulkResult.errors.length > 0 && (
                  <div className="mt-1 text-red-500">Errors: {bulkResult.errors.join(', ')}</div>
                )}
              </div>
            )}

            <form onSubmit={handleBulkImportSubmit} className="mt-4 flex flex-col gap-4 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-zinc-700 dark:text-zinc-300">JSON Problem Array:</span>
                <button
                  type="button"
                  onClick={loadExampleTemplate}
                  className="text-xs text-orange-500 hover:text-orange-600 font-semibold"
                >
                  Load Example Template
                </button>
              </div>

              <textarea
                rows={12}
                required
                value={bulkJson}
                onChange={(e) => setBulkJson(e.target.value)}
                placeholder='[\n  {\n    "title": "Sum of Two",\n    "slug": "sum-of-two",\n    "difficulty": "easy",\n    "description": "...",\n    "test_cases": [...]\n  }\n]'
                className="w-full p-3 bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg text-zinc-900 dark:text-white focus:outline-none focus:border-orange-500 font-mono text-[11px]"
              />

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-zinc-200 dark:border-zinc-800">
                <button
                  type="button"
                  onClick={() => setShowBulkImport(false)}
                  className="px-4 py-2 rounded-lg border border-zinc-200 dark:border-zinc-700 text-zinc-600 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={bulkImporting}
                  className="px-5 py-2 bg-orange-500 hover:bg-orange-600 disabled:opacity-50 text-white rounded-lg font-semibold shadow-md shadow-orange-500/20 transition-all flex items-center gap-2"
                >
                  {bulkImporting ? 'Importing…' : 'Import Problems'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
