import { useEffect, useState, useCallback, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { getLabSession, getLabDashboard, LabSessionDetail, StudentLabProgress } from '../api/client'
import Navbar from '../components/Navbar'

type SortKey = 'name' | 'mandatory' | 'badges' | 'last_submission'
type SortDir = 'asc' | 'desc'

export default function LabDashboardPage() {
  const { id } = useParams<{ id: string }>()

  const [lab, setLab] = useState<LabSessionDetail | null>(null)
  const [students, setStudents] = useState<StudentLabProgress[]>([])
  const [loading, setLoading] = useState(true)
  const [sortKey, setSortKey] = useState<SortKey>('badges')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date())
  const refreshRef = useRef<number | null>(null)

  const fetchDashboard = useCallback(() => {
    if (!id) return
    getLabDashboard(id).then((s) => { setStudents(s); setLastRefresh(new Date()) }).catch(() => {})
  }, [id])

  useEffect(() => {
    if (!id) return
    Promise.all([getLabSession(id), getLabDashboard(id)])
      .then(([l, s]) => { setLab(l); setStudents(s); setLastRefresh(new Date()) })
      .catch(() => {})
      .finally(() => setLoading(false))

    // Auto-refresh every 15 seconds
    refreshRef.current = window.setInterval(() => {
      getLabDashboard(id).then((s) => { setStudents(s); setLastRefresh(new Date()) }).catch(() => {})
    }, 15000)

    return () => { if (refreshRef.current) clearInterval(refreshRef.current) }
  }, [id])

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortKey(key); setSortDir('desc') }
  }

  const sorted = [...students].sort((a, b) => {
    const mul = sortDir === 'asc' ? 1 : -1
    switch (sortKey) {
      case 'name': return mul * a.user_name.localeCompare(b.user_name)
      case 'mandatory': return mul * (a.mandatory_solved - b.mandatory_solved)
      case 'badges': return mul * (a.badges_earned - b.badges_earned)
      case 'last_submission': {
        const at = a.last_submission_at ? new Date(a.last_submission_at).getTime() : 0
        const bt = b.last_submission_at ? new Date(b.last_submission_at).getTime() : 0
        return mul * (at - bt)
      }
      default: return 0
    }
  })

  const totalBadges = students.reduce((s, st) => s + st.badges_earned, 0)
  const completionRate = students.length > 0
    ? Math.round((students.filter((s) => s.mandatory_solved >= s.mandatory_total).length / students.length) * 100)
    : 0

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
      {/* Header */}
      <Navbar
        customTitle={lab?.title ? `${lab.title} (Live Dashboard)` : 'Lab Dashboard'}
        backTo={lab ? `/courses/${lab.course_id}` : '/'}
        backLabel="Course"
      />

      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8 flex flex-col gap-6">
        {/* Summary cards */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5">
            <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Students</span>
            <p className="text-3xl font-bold text-zinc-900 dark:text-white mt-1">{students.length}</p>
          </div>
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5">
            <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Completion Rate</span>
            <p className="text-3xl font-bold text-zinc-900 dark:text-white mt-1">{completionRate}%</p>
          </div>
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5">
            <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Total Badges</span>
            <p className="text-3xl font-bold text-orange-500 mt-1">🏅 {totalBadges}</p>
          </div>
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5">
            <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">Problems</span>
            <p className="text-3xl font-bold text-zinc-900 dark:text-white mt-1">{lab?.problem_count ?? 0}</p>
            <span className="text-xs text-zinc-400">{lab?.mandatory_count ?? 0} mandatory</span>
          </div>
        </div>

        {/* Auto-refresh indicator */}
        <div className="flex items-center justify-between">
          <h2 className="font-bold text-zinc-900 dark:text-white">Student Progress</h2>
          <div className="flex items-center gap-2 text-xs text-zinc-400 dark:text-zinc-500">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <span>Auto-refreshing · Last: {lastRefresh.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
            <button onClick={fetchDashboard} className="ml-2 px-2 py-1 rounded border border-zinc-200 dark:border-zinc-700 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors text-zinc-500 dark:text-zinc-400">
              Refresh
            </button>
          </div>
        </div>

        {/* Student table */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-zinc-200 dark:border-zinc-800 text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider bg-zinc-50 dark:bg-zinc-900/50">
                  <th className="px-6 py-3.5 cursor-pointer select-none hover:text-orange-500 transition-colors" onClick={() => handleSort('name')}>
                    Student <SortIcon active={sortKey === 'name'} dir={sortDir} />
                  </th>
                  <th className="px-6 py-3.5 cursor-pointer select-none hover:text-orange-500 transition-colors" onClick={() => handleSort('mandatory')}>
                    Mandatory <SortIcon active={sortKey === 'mandatory'} dir={sortDir} />
                  </th>
                  <th className="px-6 py-3.5">Extra Solved</th>
                  <th className="px-6 py-3.5 cursor-pointer select-none hover:text-orange-500 transition-colors" onClick={() => handleSort('badges')}>
                    Badges <SortIcon active={sortKey === 'badges'} dir={sortDir} />
                  </th>
                  <th className="px-6 py-3.5 cursor-pointer select-none hover:text-orange-500 transition-colors" onClick={() => handleSort('last_submission')}>
                    Last Activity <SortIcon active={sortKey === 'last_submission'} dir={sortDir} />
                  </th>
                  <th className="px-6 py-3.5">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/50">
                {sorted.map((s) => {
                  const mandatoryDone = s.mandatory_solved >= s.mandatory_total
                  return (
                    <tr key={s.user_id} className="hover:bg-zinc-50 dark:hover:bg-zinc-800/30 transition-colors">
                      <td className="px-6 py-4">
                        <div>
                          <span className="font-semibold text-zinc-800 dark:text-white">{s.user_name}</span>
                          <span className="block text-xs text-zinc-400 dark:text-zinc-500 font-mono">{s.user_email}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <div className="w-16 bg-zinc-100 dark:bg-zinc-800 rounded-full h-2 overflow-hidden">
                            <div className={`h-full rounded-full transition-all ${mandatoryDone ? 'bg-green-500' : 'bg-orange-500'}`} style={{ width: `${s.mandatory_total > 0 ? (s.mandatory_solved / s.mandatory_total) * 100 : 0}%` }} />
                          </div>
                          <span className="text-xs font-mono text-zinc-600 dark:text-zinc-400">{s.mandatory_solved}/{s.mandatory_total}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-zinc-600 dark:text-zinc-400 font-mono">{s.extra_solved}</td>
                      <td className="px-6 py-4">
                        {s.badges_earned > 0 ? (
                          <span className="inline-flex items-center gap-1 text-orange-500 font-bold">
                            🏅 {s.badges_earned}
                          </span>
                        ) : (
                          <span className="text-zinc-400 dark:text-zinc-600">—</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-xs text-zinc-400 dark:text-zinc-500">
                        {s.last_submission_at
                          ? new Date(s.last_submission_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                          : 'No activity'}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border ${
                          mandatoryDone
                            ? 'bg-green-500/10 text-green-500 border-green-500/20'
                            : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400 border-zinc-200 dark:border-zinc-700'
                        }`}>
                          {mandatoryDone ? 'Complete' : 'In Progress'}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  )
}
