import { BrowserRouter, Route, Routes } from 'react-router-dom'
import ProblemListPage from './pages/ProblemListPage'
import ProblemPage from './pages/ProblemPage'

/**
 * Root router.
 *
 * Routes:
 *   /                  → Problem list
 *   /problems/:slug    → Problem coding page (Monaco editor + results)
 */
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ProblemListPage />} />
        <Route path="/problems/:slug" element={<ProblemPage />} />
      </Routes>
    </BrowserRouter>
  )
}
