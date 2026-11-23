import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getCourse, getGradebook, CourseResponse, GradebookRow } from '../api/client'

type SortKey = 'name' | 'badges' | 'mandatory'
type SortDir = 'asc' | 'desc'

export default function GradebookPage() {
  const { courseId } = useParams<{ courseId: string }>()

  const [course, setCourse] = useState<CourseResponse | null>(null)
  const [rows, setRows] = useState<GradebookRow[]>([])
  const [loading, setLoading] = useState(true)
  const [sortKey, setSortKey] = useState<SortKey>('badges')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  useEffect(() => {
    if (!courseId) return
    Promise.all([getCourse(courseId), getGradebook(courseId)])
      .then(([c, g]) => { setCourse(c); setRows(g) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [courseId])

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortKey(key); setSortDir('desc') }
  }

  const sorted = [...rows].sort((a, b) => {
    const mul = sortDir === 'asc' ? 1 : -1
    switch (sortKey) {
      case 'name': return mul * a.user_name.localeCompare(b.user_name)
      case 'badges': return mul * (a.total_badges - b.total_badges)
      case 'mandatory': return mul * (a.total_mandatory_solved - b.total_mandatory_solved)
      default: return 0
    }
  })

  // Collect unique lab columns
  const labColumns = rows.length > 0 ? rows[0].lab_results : []

  const SortIcon = ({ active, dir }: { active: boolean; dir: SortDir }) => (
    <span className={`ml-1 text-[10px] ${active ? 'text-orange-500' : 'text-zinc-400 dark:text-zinc-600'}`}>
      {active ? (dir === 'asc' ? '▲' : '▼') : '↕'}
    </span>
  )

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex items-center justify-center gap-3">
        <div className="w-8 h-8 rounded-full border-4 border-orange-500/10 border-t-orange-500 animate-spin" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 font-sans flex flex-col transition-colors duration-200">
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-8 flex flex-col gap-6">
        <div>
          <Link
            to={courseId ? `/courses/${courseId}?tab=gradebook` : '/'}
            className="inline-flex items-center gap-1.5 text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-white text-xs font-semibold uppercase tracking-wider transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            <span>Back to Course</span>
          </Link>
        </div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-extrabold text-zinc-900 dark:text-white tracking-tight">Gradebook</h1>
            <p className="text-zinc-500 dark:text-zinc-400 text-sm mt-0.5">{course?.title} · {rows.length} students</p>
          </div>
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5">
            <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Total Students</span>
            <p className="text-3xl font-bold text-zinc-900 dark:text-white mt-1">{rows.length}</p>
          </div>
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5">
            <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Lab Sessions</span>
            <p className="text-3xl font-bold text-zinc-900 dark:text-white mt-1">{labColumns.length}</p>
          </div>
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5">
            <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Total Badges Awarded</span>
            <p className="text-3xl font-bold text-orange-500 mt-1">🏅 {rows.reduce((s, r) => s + r.total_badges, 0)}</p>
          </div>
        </div>

        {/* Gradebook table */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-zinc-200 dark:border-zinc-800 text-[10px] font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider bg-zinc-50 dark:bg-zinc-900/50">
                  <th className="px-5 py-3.5 cursor-pointer select-none hover:text-orange-500 transition-colors sticky left-0 bg-zinc-50 dark:bg-zinc-900/50 z-10" onClick={() => handleSort('name')}>
                    Student <SortIcon active={sortKey === 'name'} dir={sortDir} />
                  </th>
                  {labColumns.map((lc) => (
                    <th key={lc.lab_session_id} className="px-4 py-3.5 text-center whitespace-nowrap">
                      <div className="flex flex-col items-center gap-0.5">
                        <span>{lc.lab_title}</span>
                      </div>
                    </th>
                  ))}
                  <th className="px-5 py-3.5 text-center cursor-pointer select-none hover:text-orange-500 transition-colors" onClick={() => handleSort('mandatory')}>
                    Mandatory <SortIcon active={sortKey === 'mandatory'} dir={sortDir} />
                  </th>
                  <th className="px-5 py-3.5 text-center cursor-pointer select-none hover:text-orange-500 transition-colors" onClick={() => handleSort('badges')}>
                    Badges <SortIcon active={sortKey === 'badges'} dir={sortDir} />
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/50">
                {sorted.map((row) => (
                  <tr key={row.user_id} className="hover:bg-zinc-50 dark:hover:bg-zinc-800/30 transition-colors">
                    <td className="px-5 py-3.5 sticky left-0 bg-white dark:bg-zinc-900 z-10">
                      <div>
                        <span className="font-semibold text-zinc-800 dark:text-white text-sm">{row.user_name}</span>
                        <span className="block text-[10px] text-zinc-400 font-mono">{row.user_email}</span>
                      </div>
                    </td>
                    {row.lab_results.map((lr) => (
                      <td key={lr.lab_session_id} className="px-4 py-3.5 text-center">
                        <div className="flex flex-col items-center gap-1">
                          <span className={`text-xs font-mono ${lr.mandatory_solved >= lr.mandatory_total ? 'text-green-500 font-bold' : 'text-zinc-500 dark:text-zinc-400'}`}>
                            {lr.mandatory_solved}/{lr.mandatory_total}
                          </span>
                          {lr.badges_earned > 0 && (
                            <span className="text-[10px] text-orange-500 font-semibold">🏅 {lr.badges_earned}</span>
                          )}
                        </div>
                      </td>
                    ))}
                    <td className="px-5 py-3.5 text-center">
                      <span className={`font-mono text-sm font-bold ${row.total_mandatory_solved >= row.total_mandatory ? 'text-green-500' : 'text-zinc-600 dark:text-zinc-400'}`}>
                        {row.total_mandatory_solved}/{row.total_mandatory}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-center">
                      {row.total_badges > 0 ? (
                        <span className="inline-flex items-center gap-1 text-orange-500 font-bold text-sm">🏅 {row.total_badges}</span>
                      ) : (
                        <span className="text-zinc-400">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  )
}
