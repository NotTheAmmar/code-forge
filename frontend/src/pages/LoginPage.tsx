import { useState, useCallback } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'

type Mode = 'login' | 'register'

export default function LoginPage() {
  const { login, register } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const navigate = useNavigate()
  const location = useLocation()
  const redirectTo = (location.state as { from?: string })?.from ?? '/'

  const [mode, setMode] = useState<Mode>('login')
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<'student' | 'instructor'>('student')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      setError(null)
      setLoading(true)
      try {
        if (mode === 'login') {
          await login({ email, password })
        } else {
          await register({ email, name, password, role })
        }
        navigate(redirectTo, { replace: true })
      } catch (err: unknown) {
        const msg =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          'Something went wrong. Please try again.'
        setError(msg)
      } finally {
        setLoading(false)
      }
    },
    [mode, email, name, password, role, login, register, navigate, redirectTo]
  )

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 font-sans flex flex-col transition-colors duration-200">
      {/* Navbar */}
      <header className="border-b border-zinc-200 dark:border-zinc-900 bg-white/80 dark:bg-zinc-900/20 backdrop-blur sticky top-0 z-50 px-6 py-4 flex items-center justify-between transition-colors">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-8 h-8 rounded bg-gradient-to-tr from-orange-600 to-orange-400 flex items-center justify-center font-bold text-white shadow-lg shadow-orange-500/10">
            CF
          </div>
          <span className="font-bold text-lg text-zinc-900 dark:text-white tracking-tight">
            CodeForge
          </span>
        </Link>
        <button
          onClick={toggleTheme}
          className="p-1.5 rounded-lg bg-zinc-100 dark:bg-zinc-900 text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white border border-zinc-200 dark:border-zinc-800 transition-colors"
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
      </header>

      {/* Card */}
      <main className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-md">
          {/* Logo accent */}
          <div className="flex justify-center mb-8">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-orange-600 to-orange-400 flex items-center justify-center font-bold text-white text-xl shadow-xl shadow-orange-500/20">
              CF
            </div>
          </div>

          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-xl dark:shadow-zinc-950/50 p-8">
            {/* Mode toggle */}
            <div className="flex bg-zinc-100 dark:bg-zinc-800 rounded-lg p-1 mb-8">
              {(['login', 'register'] as Mode[]).map((m) => (
                <button
                  key={m}
                  onClick={() => { setMode(m); setError(null) }}
                  className={`flex-1 py-2 rounded-md text-sm font-semibold transition-all capitalize ${
                    mode === m
                      ? 'bg-white dark:bg-zinc-700 text-zinc-900 dark:text-white shadow-sm'
                      : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200'
                  }`}
                >
                  {m === 'login' ? 'Sign In' : 'Register'}
                </button>
              ))}
            </div>

            {/* Quick Demo Sign-in */}
            <div className="mb-6 p-3.5 bg-orange-500/5 dark:bg-orange-500/10 border border-orange-500/20 rounded-xl">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-bold text-orange-600 dark:text-orange-400 uppercase tracking-wider">
                  ⚡ Quick Demo Accounts
                </span>
                <span className="text-[10px] text-zinc-400 dark:text-zinc-500">1-click fill</span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setMode('login')
                    setEmail('test@test.com')
                    setPassword('password123')
                    setError(null)
                  }}
                  className="px-2.5 py-1.5 text-xs font-semibold bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 hover:border-orange-500 dark:hover:border-orange-500 rounded-lg text-zinc-700 dark:text-zinc-200 hover:text-orange-600 dark:hover:text-orange-400 transition shadow-sm text-left flex items-center justify-between"
                >
                  <span>Student</span>
                  <span className="text-[10px] opacity-60">→</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setMode('login')
                    setEmail('admin@test.com')
                    setPassword('password123')
                    setError(null)
                  }}
                  className="px-2.5 py-1.5 text-xs font-semibold bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 hover:border-orange-500 dark:hover:border-orange-500 rounded-lg text-zinc-700 dark:text-zinc-200 hover:text-orange-600 dark:hover:text-orange-400 transition shadow-sm text-left flex items-center justify-between"
                >
                  <span>Instructor</span>
                  <span className="text-[10px] opacity-60">→</span>
                </button>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="flex flex-col gap-5">
              {/* Name field — register only */}
              {mode === 'register' && (
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
                    Full Name
                  </label>
                  <input
                    id="auth-name"
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                    minLength={2}
                    placeholder="Jane Doe"
                    className="w-full bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg px-4 py-2.5 text-sm text-zinc-900 dark:text-white placeholder-zinc-400 dark:placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500 transition"
                  />
                </div>
              )}

              {/* Email */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
                  Email Address
                </label>
                <input
                  id="auth-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="jane@example.com"
                  className="w-full bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg px-4 py-2.5 text-sm text-zinc-900 dark:text-white placeholder-zinc-400 dark:placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500 transition"
                />
              </div>

              {/* Password */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
                  Password
                </label>
                <input
                  id="auth-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={6}
                  placeholder={mode === 'register' ? 'Minimum 6 characters' : '••••••••'}
                  className="w-full bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg px-4 py-2.5 text-sm text-zinc-900 dark:text-white placeholder-zinc-400 dark:placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500 transition"
                />
              </div>

              {/* Role — register only */}
              {mode === 'register' && (
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
                    Account Role
                  </label>
                  <div className="flex gap-3">
                    {(['student', 'instructor'] as const).map((r) => (
                      <button
                        key={r}
                        type="button"
                        onClick={() => setRole(r)}
                        className={`flex-1 py-2 rounded-lg text-sm font-medium border transition-all capitalize ${
                          role === r
                            ? 'bg-orange-500/10 border-orange-500/40 text-orange-600 dark:text-orange-400'
                            : 'bg-zinc-50 dark:bg-zinc-800 border-zinc-200 dark:border-zinc-700 text-zinc-500 dark:text-zinc-400 hover:border-zinc-300 dark:hover:border-zinc-600'
                        }`}
                      >
                        {r}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Error */}
              {error && (
                <div className="bg-red-500/5 border border-red-500/20 text-red-600 dark:text-red-400 text-sm rounded-lg px-4 py-3">
                  {error}
                </div>
              )}

              {/* Submit */}
              <button
                id="auth-submit"
                type="submit"
                disabled={loading}
                className="w-full bg-orange-500 hover:bg-orange-600 text-white font-semibold py-2.5 rounded-lg transition-all shadow-lg shadow-orange-500/20 disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2 mt-1"
              >
                {loading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    {mode === 'login' ? 'Signing in…' : 'Creating account…'}
                  </>
                ) : mode === 'login' ? (
                  'Sign In'
                ) : (
                  'Create Account'
                )}
              </button>
            </form>

            {/* Quick Demo Shortcuts (Offline / Preview Mode) */}
            <div className="mt-6 pt-5 border-t border-zinc-200 dark:border-zinc-800 flex flex-col gap-2">
              <span className="text-[10px] uppercase font-bold tracking-wider text-zinc-400 text-center">
                Quick Demo Access
              </span>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={async () => {
                    await login({ email: 'instructor@codeforge.edu', password: 'password123' })
                    navigate(redirectTo, { replace: true })
                  }}
                  className="px-3 py-1.5 rounded-lg bg-orange-500/10 hover:bg-orange-500/20 text-orange-600 dark:text-orange-400 text-xs font-semibold border border-orange-500/30 transition text-center"
                >
                  Instructor Demo
                </button>
                <button
                  type="button"
                  onClick={async () => {
                    await login({ email: 'student@codeforge.edu', password: 'password123' })
                    navigate(redirectTo, { replace: true })
                  }}
                  className="px-3 py-1.5 rounded-lg bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-800 dark:text-zinc-200 text-xs font-semibold border border-zinc-200 dark:border-zinc-700 transition text-center"
                >
                  Student Demo
                </button>
              </div>
            </div>

            {/* Footer note */}
            <p className="text-center text-xs text-zinc-400 dark:text-zinc-600 mt-6">
              {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
              <button
                onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(null) }}
                className="text-orange-500 hover:text-orange-600 font-medium transition-colors"
              >
                {mode === 'login' ? 'Register here' : 'Sign in'}
              </button>
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}
