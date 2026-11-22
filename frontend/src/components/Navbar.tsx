import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'

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

  return (
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

        {/* Core Navigation Links */}
        <nav className="flex items-center gap-1 ml-4 border-l border-zinc-200 dark:border-zinc-800 pl-4 text-xs font-semibold">
          <Link
            to="/"
            className={`px-3 py-1.5 rounded-lg transition-colors ${
              location.pathname === '/' || location.pathname.startsWith('/courses')
                ? 'text-orange-600 dark:text-orange-400 bg-orange-500/10'
                : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white'
            }`}
          >
            My Courses
          </Link>
        </nav>
      </div>

      {/* Right: User controls */}
      <div className="flex items-center gap-3">
        {/* User Role Badge */}
        {user && (
          <div className="flex items-center gap-2">
            <span className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-[11px] font-semibold text-zinc-600 dark:text-zinc-300">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              <span className="capitalize text-orange-600 dark:text-orange-400">{user.role}</span>
              <span className="text-zinc-400 truncate max-w-[150px]">({user.email})</span>
            </span>
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
  )
}
