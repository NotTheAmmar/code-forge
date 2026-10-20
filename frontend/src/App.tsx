import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ThemeProvider } from './context/ThemeContext'

// Pages
import LoginPage from './pages/LoginPage'
import CourseListPage from './pages/CourseListPage'
import CoursePage from './pages/CoursePage'
import ProblemListPage from './pages/ProblemListPage'
import ProblemPage from './pages/ProblemPage'
import LabCreatePage from './pages/LabCreatePage'
import LabDashboardPage from './pages/LabDashboardPage'
import StudentLabPage from './pages/StudentLabPage'
import GradebookPage from './pages/GradebookPage'

/**
 * Redirects unauthenticated users to /login, preserving the
 * original destination so they're sent back after signing in.
 */
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center gap-3">
        <div className="w-8 h-8 rounded-full border-4 border-orange-500/10 border-t-orange-500 animate-spin" />
        <span className="text-zinc-500 text-sm font-medium">Restoring session…</span>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  return <>{children}</>
}

/**
 * Root router.
 *
 * Routes:
 *   /login                      → LoginPage (public)
 *   /                           → CourseListPage — course dashboard (protected)
 *   /practice                   → ProblemListPage — standalone practice (protected)
 *   /courses/:id                → CoursePage — course detail with tabs (protected)
 *   /courses/:courseId/labs/create → LabCreatePage — create lab session (instructor)
 *   /courses/:courseId/gradebook  → GradebookPage — gradebook table (instructor)
 *   /labs/:id                   → StudentLabPage — student lab mode (protected)
 *   /labs/:id/dashboard         → LabDashboardPage — instructor dashboard (protected)
 *   /problems/:slug             → ProblemPage — Monaco editor + results (protected)
 */
export default function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <Routes>
            {/* Public */}
            <Route path="/login" element={<LoginPage />} />

            {/* Protected — Course Dashboard (Home) */}
            <Route path="/" element={<ProtectedRoute><CourseListPage /></ProtectedRoute>} />

            {/* Protected — Standalone Practice */}
            <Route path="/practice" element={<ProtectedRoute><ProblemListPage /></ProtectedRoute>} />

            {/* Protected — Course Detail */}
            <Route path="/courses/:id" element={<ProtectedRoute><CoursePage /></ProtectedRoute>} />

            {/* Protected — Lab Session Create (Instructor) */}
            <Route path="/courses/:courseId/labs/create" element={<ProtectedRoute><LabCreatePage /></ProtectedRoute>} />

            {/* Protected — Gradebook (Instructor) */}
            <Route path="/courses/:courseId/gradebook" element={<ProtectedRoute><GradebookPage /></ProtectedRoute>} />

            {/* Protected — Student Lab Mode */}
            <Route path="/labs/:id" element={<ProtectedRoute><StudentLabPage /></ProtectedRoute>} />

            {/* Protected — Instructor Lab Dashboard */}
            <Route path="/labs/:id/dashboard" element={<ProtectedRoute><LabDashboardPage /></ProtectedRoute>} />

            {/* Protected — Problem Workspace */}
            <Route path="/problems/:slug" element={<ProtectedRoute><ProblemPage /></ProtectedRoute>} />

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  )
}
