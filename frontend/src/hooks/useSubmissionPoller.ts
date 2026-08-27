/**
 * useSubmissionPoller — polls GET /submissions/:id until the submission is
 * in a terminal state (completed, compile_error, error, timeout).
 *
 * Developer B: implement in Phase B2.
 *
 * TODO:
 * - Poll every 1.5 seconds.
 * - Stop polling when status is terminal.
 * - Clean up interval on unmount.
 */

import { useCallback, useRef, useState } from 'react'
import { getSubmission, type Submission } from '../api/client'

const TERMINAL_STATUSES = new Set(['completed', 'compile_error', 'error', 'timeout'])
const POLL_INTERVAL_MS = 1500

export function useSubmissionPoller() {
  const [submission, setSubmission] = useState<Submission | null>(null)
  const [loading, setLoading] = useState(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  const startPolling = useCallback(
    (submissionId: string) => {
      stopPolling()
      setLoading(true)
      setSubmission(null)

      intervalRef.current = setInterval(async () => {
        try {
          const result = await getSubmission(submissionId)
          setSubmission(result)
          if (TERMINAL_STATUSES.has(result.status)) {
            stopPolling()
            setLoading(false)
          }
        } catch {
          stopPolling()
          setLoading(false)
        }
      }, POLL_INTERVAL_MS)
    },
    [stopPolling],
  )

  return { submission, loading, startPolling, stopPolling }
}
