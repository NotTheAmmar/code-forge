import { useState, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'

interface NavItem {
  label: string
  path: string
  icon: string
  category: 'Curriculum' | 'Assessments' | 'Coding IDE' | 'Management'
  description: string
  instructorOnly?: boolean
}

const ALL_PAGES: NavItem[] = [
  // Curriculum
  {
    label: 'All Courses',
    path: '/',
    icon: '🏛️',
    category: 'Curriculum',
    description: 'Enrolled courses, course cards, and join/create modal',
  },
  {
    label: 'Course Detail (Tabs)',
    path: '/courses/default',
    icon: '📂',
    category: 'Curriculum',
    description: 'Course workspace with Problems, Learn, Labs, Exams, & Analytics tabs',
  },
  {
    label: 'Learning Path (Learn)',
    path: '/courses/default/learn',
    icon: '📚',
    category: 'Curriculum',
    description: 'Sequential curriculum modules with progress tracking',
  },
  {
    label: 'Interactive Lesson Viewer',
    path: '/modules/m1a2b3c4-0000-0000-0000-000000000001',
    icon: '📖',
    category: 'Curriculum',
    description: 'Theory markdown, embedded YouTube video, and practice problem',
  },
  {
    label: 'Create Learning Module',
    path: '/courses/default/modules/create',
    icon: '✏️',
    category: 'Curriculum',
    description: 'Instructor curriculum builder: lessons, videos, and exercises',
    instructorOnly: true,
  },

  // Coding IDE
  {
    label: 'Problem Workspace (Two Sum)',
    path: '/problems/two-sum',
    icon: '💻',
    category: 'Coding IDE',
    description: 'Monaco editor with C, C++, Python, Java, auto-save, & custom stdin',
  },
  {
    label: 'Problem Workspace (Hello World)',
    path: '/problems/hello-world',
    icon: '⚡',
    category: 'Coding IDE',
    description: 'Basic warmup challenge with live test feedback',
  },
  {
    label: 'Standalone Practice List',
    path: '/practice',
    icon: '🎯',
    category: 'Coding IDE',
    description: 'Catalog of algorithmic coding challenges',
  },

  // Assessments
  {
    label: 'Proctored Exam (Lockdown)',
    path: '/exams/exam-midterm-1',
    icon: '🛡️',
    category: 'Assessments',
    description: 'Fullscreen lockdown, tab-switch tracking, and timer',
  },
  {
    label: 'Exam Audit & Results',
    path: '/exams/exam-midterm-1/results',
    icon: '📋',
    category: 'Assessments',
    description: 'Instructor proctoring audit, violation logs, and scoreboards',
    instructorOnly: true,
  },
  {
    label: 'Student Exam Scorecard',
    path: '/exams/exam-midterm-1/my-result',
    icon: '🏅',
    category: 'Assessments',
    description: 'Student exam results and per-problem score breakdown',
  },
  {
    label: 'Create Proctored Exam',
    path: '/courses/default/exams/create',
    icon: '⏱️',
    category: 'Assessments',
    description: 'Instructor exam setup: weights, duration, and lockdown rules',
    instructorOnly: true,
  },

  // Management & Labs
  {
    label: 'Course Analytics Dashboard',
    path: '/courses/default/analytics',
    icon: '📊',
    category: 'Management',
    description: 'KPIs, problem pass rates, error distributions, & 7-day trends',
    instructorOnly: true,
  },
  {
    label: 'Gradebook Matrix',
    path: '/courses/default/gradebook',
    icon: '📑',
    category: 'Management',
    description: 'Student × Problem score matrix with badge tallies',
    instructorOnly: true,
  },
  {
    label: 'Create Lab Session',
    path: '/courses/default/labs/create',
    icon: '🧪',
    category: 'Management',
    description: 'Timed live lab session with mandatory solve limits',
    instructorOnly: true,
  },
]

interface NavbarProps {
  customTitle?: string
  backTo?: string
  backLabel?: string
}

export default function Navbar({ customTitle, backTo, backLabel }: NavbarProps) {
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const navigate = useNavigate()
  const location = useLocation()

  const [showQuickJump, setShowQuickJump] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  const isInstructor = user?.role === 'instructor'

  // Keyboard shortcut Ctrl+K or Cmd+K to toggle Quick Jump
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setShowQuickJump((prev) => !prev)
      } else if (e.key === 'Escape') {
        setShowQuickJump(false)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  const filteredPages = ALL_PAGES.filter((p) => {
    if (searchQuery.trim() === '') return true
    const q = searchQuery.toLowerCase()
    return (
      p.label.toLowerCase().includes(q) ||
      p.description.toLowerCase().includes(q) ||
      p.category.toLowerCase().includes(q)
    )
  })

  // Group pages by category
  const categories: Array<'Curriculum' | 'Coding IDE' | 'Assessments' | 'Management'> = [
    'Curriculum',
    'Coding IDE',
    'Assessments',
    'Management',
  ]

  const handleRoleToggle = () => {
    if (!user) return
    const newRole = user.role === 'instructor' ? 'student' : 'instructor'
    const updated = { ...user, role: newRole as 'student' | 'instructor' }
    localStorage.setItem('cf_mock_user', JSON.stringify(updated))
    window.location.reload()
  }

  return (
    <>
      <header className="h-14 border-b border-zinc-200 dark:border-zinc-900 bg-white/95 dark:bg-zinc-950/95 backdrop-blur sticky top-0 z-40 px-4 sm:px-6 flex items-center justify-between shrink-0 transition-colors">
        {/* Left: Brand or Back navigation */}
        <div className="flex items-center gap-3">
          {backTo ? (
            <Link
              to={backTo}
              className="flex items-center gap-1.5 text-zinc-500 dark:text-zinc-400 hover:text-zinc-950 dark:hover:text-white transition-colors text-xs font-semibold uppercase tracking-wider"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              <span>{backLabel || 'Back'}</span>
            </Link>
          ) : (
            <Link to="/" className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-orange-600 to-orange-400 flex items-center justify-center font-bold text-white text-xs shadow-md shadow-orange-500/20">
                CF
              </div>
              <span className="font-bold text-base text-zinc-900 dark:text-white tracking-tight">
                CodeForge
              </span>
            </Link>
          )}

          {customTitle && (
            <>
              <div className="h-4 w-[1px] bg-zinc-200 dark:bg-zinc-800" />
              <span className="font-bold text-xs sm:text-sm text-zinc-900 dark:text-white truncate max-w-[200px] sm:max-w-xs">
                {customTitle}
              </span>
            </>
          )}

          {/* Core Desktop Navigation Links */}
          <nav className="hidden lg:flex items-center gap-1 ml-4 border-l border-zinc-200 dark:border-zinc-800 pl-4 text-xs font-semibold">
            <Link
              to="/"
              className={`px-2.5 py-1 rounded-lg transition-colors ${
                location.pathname === '/'
                  ? 'text-orange-600 dark:text-orange-400 bg-orange-500/10'
                  : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white'
              }`}
            >
              Courses
            </Link>
            <Link
              to="/courses/default/learn"
              className={`px-2.5 py-1 rounded-lg transition-colors ${
                location.pathname.includes('/learn')
                  ? 'text-orange-600 dark:text-orange-400 bg-orange-500/10'
                  : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white'
              }`}
            >
              Learn
            </Link>
            <Link
              to="/practice"
              className={`px-2.5 py-1 rounded-lg transition-colors ${
                location.pathname === '/practice'
                  ? 'text-orange-600 dark:text-orange-400 bg-orange-500/10'
                  : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white'
              }`}
            >
              Practice
            </Link>
            <Link
              to="/exams/exam-midterm-1"
              className={`px-2.5 py-1 rounded-lg transition-colors ${
                location.pathname.includes('/exams')
                  ? 'text-orange-600 dark:text-orange-400 bg-orange-500/10'
                  : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white'
              }`}
            >
              Exams
            </Link>
            {isInstructor && (
              <>
                <Link
                  to="/courses/default/analytics"
                  className={`px-2.5 py-1 rounded-lg transition-colors ${
                    location.pathname.includes('/analytics')
                      ? 'text-orange-600 dark:text-orange-400 bg-orange-500/10'
                      : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white'
                  }`}
                >
                  Analytics
                </Link>
                <Link
                  to="/courses/default/gradebook"
                  className={`px-2.5 py-1 rounded-lg transition-colors ${
                    location.pathname.includes('/gradebook')
                      ? 'text-orange-600 dark:text-orange-400 bg-orange-500/10'
                      : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white'
                  }`}
                >
                  Gradebook
                </Link>
              </>
            )}
          </nav>
        </div>

        {/* Center / Right: Quick Jump Button & User controls */}
        <div className="flex items-center gap-2.5">
          {/* Quick Jump Command Button */}
          <button
            onClick={() => setShowQuickJump(true)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-900 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-800 text-xs font-medium transition shadow-sm"
            title="Navigate to any webpage (Ctrl+K)"
          >
            <span className="text-orange-500">⚡</span>
            <span className="hidden sm:inline font-semibold">Jump to Webpage</span>
            <span className="sm:hidden font-semibold">Pages</span>
            <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono text-zinc-400 bg-white dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 rounded shadow-xs">
              Ctrl+K
            </kbd>
          </button>

          {/* User & Role Toggle */}
          {user && (
            <div className="flex items-center gap-2">
              <button
                onClick={handleRoleToggle}
                title="Click to toggle role (Instructor ⟷ Student)"
                className="hidden md:flex items-center gap-1.5 px-2 py-1 rounded-lg bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-[11px] font-medium text-zinc-600 dark:text-zinc-300 hover:border-orange-500/50 transition cursor-pointer"
              >
                <span className="w-2 h-2 rounded-full bg-green-500" />
                <span className="capitalize font-bold text-orange-600 dark:text-orange-400">{user.role}</span>
                <span className="text-zinc-400 text-[10px]">⇄</span>
              </button>
            </div>
          )}

          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            className="p-1.5 rounded-lg bg-zinc-100 dark:bg-zinc-900 text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white border border-zinc-200 dark:border-zinc-800 transition"
            aria-label="Toggle Theme"
          >
            {theme === 'dark' ? (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m0-12.728l.707.707m12.728 12.728l.707.707M12 8a4 4 0 100 8 4 4 0 000-8z" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
              </svg>
            )}
          </button>

          {/* Sign Out */}
          <button
            onClick={() => {
              logout()
              navigate('/login')
            }}
            className="text-xs text-zinc-500 dark:text-zinc-400 hover:text-red-500 dark:hover:text-red-400 font-medium transition"
          >
            Sign out
          </button>
        </div>
      </header>

      {/* ── Quick Jump Modal (Command Palette) ── */}
      {showQuickJump && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-start justify-center p-4 pt-16 sm:pt-20">
          <div
            className="max-w-2xl w-full bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[80vh] animate-in zoom-in-95 duration-150"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Search Header */}
            <div className="p-4 border-b border-zinc-200 dark:border-zinc-800 flex items-center gap-3 bg-zinc-50 dark:bg-zinc-950">
              <span className="text-lg">🔍</span>
              <input
                type="text"
                autoFocus
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search or jump to any webpage... (e.g. 'exams', 'module', 'analytics', 'c++')"
                className="w-full bg-transparent text-sm text-zinc-900 dark:text-white placeholder-zinc-400 focus:outline-none"
              />
              <button
                onClick={() => setShowQuickJump(false)}
                className="px-2 py-1 text-xs text-zinc-400 hover:text-zinc-200 rounded font-mono"
              >
                ESC
              </button>
            </div>

            {/* List by category */}
            <div className="overflow-y-auto p-4 flex flex-col gap-6">
              {categories.map((cat) => {
                const items = filteredPages.filter((p) => p.category === cat)
                if (items.length === 0) return null

                return (
                  <div key={cat} className="flex flex-col gap-2">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-400 dark:text-zinc-500 px-2">
                      {cat}
                    </span>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {items.map((item) => (
                        <button
                          key={item.path}
                          onClick={() => {
                            setShowQuickJump(false)
                            navigate(item.path)
                          }}
                          className="flex items-start gap-3 p-3 rounded-xl text-left bg-zinc-50 hover:bg-orange-50 dark:bg-zinc-950 dark:hover:bg-zinc-800/80 border border-zinc-200 dark:border-zinc-800/80 hover:border-orange-500/40 transition group"
                        >
                          <span className="text-xl shrink-0 mt-0.5">{item.icon}</span>
                          <div className="flex flex-col min-w-0">
                            <div className="flex items-center gap-1.5">
                              <span className="text-xs font-bold text-zinc-900 dark:text-white group-hover:text-orange-600 dark:group-hover:text-orange-400 truncate">
                                {item.label}
                              </span>
                              {item.instructorOnly && (
                                <span className="text-[9px] px-1.5 py-0.2 rounded bg-orange-500/10 text-orange-500 font-semibold uppercase">
                                  Inst
                                </span>
                              )}
                            </div>
                            <span className="text-[11px] text-zinc-500 dark:text-zinc-400 line-clamp-1 mt-0.5">
                              {item.description}
                            </span>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                )
              })}

              {filteredPages.length === 0 && (
                <div className="py-12 text-center text-zinc-400 text-xs">
                  No matching webpage found for "{searchQuery}".
                </div>
              )}
            </div>

            {/* Footer tips */}
            <div className="px-4 py-2.5 bg-zinc-50 dark:bg-zinc-950 border-t border-zinc-200 dark:border-zinc-800 flex items-center justify-between text-[11px] text-zinc-400 font-mono">
              <span>Navigate quickly during jury demo</span>
              <span>Press ESC to close</span>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
