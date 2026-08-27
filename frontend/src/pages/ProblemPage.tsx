/**
 * Problem Page — Route: /problems/:slug
 *
 * Developer B: implement this page in Phase B1 + B2.
 *
 * TODO:
 * - Split-pane layout: left (description) | right (Monaco editor)
 * - Bottom panel: test results
 * - "▶ Run" → POST /api/v1/problems/:slug/run
 * - "✓ Submit" → POST /api/v1/problems/:slug/submit
 * - Poll GET /api/v1/submissions/:id until complete
 */

import { useParams } from 'react-router-dom'

export default function ProblemPage() {
  const { slug } = useParams<{ slug: string }>()

  return (
    <div className="min-h-screen flex items-center justify-center">
      <p className="text-gray-400">Problem page for "{slug}" — implement in Phase B1</p>
    </div>
  )
}
