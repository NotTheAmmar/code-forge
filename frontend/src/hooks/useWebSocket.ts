/**
 * useWebSocket — Real-time WebSocket streaming hook for submission updates.
 *
 * Connects to ws://<host>/api/v1/ws/submissions/:id?token=:token
 * Dispatches live status transitions: Queued → Compiling → Running (N/M) → Completed
 * Seamlessly falls back to HTTP polling if WebSocket is unsupported or fails.
 */

import { useCallback, useRef, useState, useEffect } from 'react'
import { getSubmission, getStoredToken, type Submission, type SubmissionStatus, type TestCaseResult } from '../api/client'

const TERMINAL_STATUSES = new Set(['completed', 'compile_error', 'error', 'timeout'])
const POLL_INTERVAL_MS = 1200

export interface LiveProgress {
  status: SubmissionStatus | 'idle'
  message: string
  currentCase: number
  totalCases: number
  resultsSoFar: TestCaseResult[]
}

export function useWebSocket() {
  const [submission, setSubmission] = useState<Submission | null>(null)
  const [loading, setLoading] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [progress, setProgress] = useState<LiveProgress>({
    status: 'idle',
    message: '',
    currentCase: 0,
    totalCases: 0,
    resultsSoFar: [],
  })

  const wsRef = useRef<WebSocket | null>(null)
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const activeSubmissionId = useRef<string | null>(null)

  const stopTracking = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
    }
    setIsStreaming(false)
  }, [])

  // HTTP polling fallback
  const startPollingFallback = useCallback((submissionId: string) => {
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)

    pollIntervalRef.current = setInterval(async () => {
      try {
        const result = await getSubmission(submissionId)
        setSubmission(result)
        setProgress((prev) => ({
          ...prev,
          status: result.status,
          currentCase: result.passed_cases ?? prev.currentCase,
          totalCases: result.total_cases ?? prev.totalCases,
          resultsSoFar: result.results_json ?? prev.resultsSoFar,
        }))

        if (TERMINAL_STATUSES.has(result.status)) {
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current)
            pollIntervalRef.current = null
          }
          setLoading(false)
          setIsStreaming(false)
        }
      } catch {
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current)
          pollIntervalRef.current = null
        }
        setLoading(false)
        setIsStreaming(false)
      }
    }, POLL_INTERVAL_MS)
  }, [])

  const startTracking = useCallback(
    (submissionId: string) => {
      stopTracking()
      activeSubmissionId.current = submissionId
      setLoading(true)
      setIsStreaming(true)
      setSubmission(null)
      setProgress({
        status: 'queued',
        message: 'Submission queued...',
        currentCase: 0,
        totalCases: 0,
        resultsSoFar: [],
      })

      // Determine WebSocket URL
      const loc = window.location
      const protocol = loc.protocol === 'https:' ? 'wss:' : 'ws:'
      const host = loc.host
      const token = getStoredToken()
      const tokenParam = token ? `?token=${encodeURIComponent(token)}` : ''
      const wsUrl = `${protocol}//${host}/api/v1/ws/submissions/${submissionId}${tokenParam}`

      let fallbackTriggered = false
      const triggerFallback = () => {
        if (fallbackTriggered) return
        fallbackTriggered = true
        console.warn(`WebSocket connection failed, falling back to HTTP polling for submission: ${submissionId}`)
        startPollingFallback(submissionId)
      }

      try {
        const ws = new WebSocket(wsUrl)
        wsRef.current = ws

        const connectTimeout = setTimeout(() => {
          if (ws.readyState !== WebSocket.OPEN) {
            ws.close()
            triggerFallback()
          }
        }, 3000)

        ws.onopen = () => {
          clearTimeout(connectTimeout)
          setIsStreaming(true)
        }

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)

            if (data.event === 'status') {
              setProgress((prev) => ({
                ...prev,
                status: data.status,
                message: data.message || `Status: ${data.status}`,
              }))
            } else if (data.event === 'test_progress') {
              setProgress((prev) => {
                const nextResults = data.case_result
                  ? [...prev.resultsSoFar.filter((r) => r.test_case_id !== data.case_result.test_case_id), data.case_result]
                  : prev.resultsSoFar
                return {
                  ...prev,
                  status: 'running',
                  currentCase: data.current_case ?? prev.currentCase,
                  totalCases: data.total_cases ?? prev.totalCases,
                  resultsSoFar: nextResults,
                  message: `Running Test ${data.current_case || 1} of ${data.total_cases || '?'}...`,
                }
              })
            } else if (data.event === 'completed' || TERMINAL_STATUSES.has(data.status)) {
              const finalSubmission: Submission = {
                id: submissionId,
                problem_id: data.problem_id || '',
                user_id: data.user_id || null,
                lab_session_id: null,
                language: data.language || 'python',
                status: data.status || 'completed',
                score: data.score ?? null,
                total_cases: data.total_cases ?? null,
                passed_cases: data.passed_cases ?? null,
                results_json: data.results_json ?? null,
                execution_time_ms: data.execution_time_ms ?? null,
                badge_awarded: data.badge_awarded ?? false,
                new_badge_count: data.new_badge_count ?? null,
                submitted_at: new Date().toISOString(),
              }
              setSubmission(finalSubmission)
              setProgress((prev) => ({
                ...prev,
                status: data.status,
                message: 'Evaluation completed.',
                currentCase: data.total_cases || prev.totalCases,
                totalCases: data.total_cases || prev.totalCases,
                resultsSoFar: data.results_json || prev.resultsSoFar,
              }))
              setLoading(false)
              setIsStreaming(false)
              ws.close()
            }
          } catch (err) {
            console.error('Failed to parse WebSocket message:', err)
          }
        }

        ws.onerror = () => {
          clearTimeout(connectTimeout)
          triggerFallback()
        }

        ws.onclose = () => {
          clearTimeout(connectTimeout)
          // If connection closed before terminal state, poll for final result
          if (activeSubmissionId.current === submissionId) {
            getSubmission(submissionId).then((res) => {
              setSubmission(res)
              if (TERMINAL_STATUSES.has(res.status)) {
                setLoading(false)
                setIsStreaming(false)
              } else {
                triggerFallback()
              }
            }).catch(() => {
              triggerFallback()
            })
          }
        }
      } catch {
        triggerFallback()
      }
    },
    [startPollingFallback, stopTracking]
  )

  useEffect(() => {
    return () => {
      stopTracking()
    }
  }, [stopTracking])

  return {
    submission,
    loading,
    isStreaming,
    progress,
    startTracking,
    stopTracking,
  }
}
