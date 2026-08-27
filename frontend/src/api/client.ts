/**
 * Axios API client.
 *
 * All API calls go through this client so the base URL is configured in one place.
 * During Docker Compose the Nginx proxy forwards /api/* → api container.
 * During local dev the Vite proxy (vite.config.ts) handles the same forwarding.
 */

import axios from 'axios'

export const apiClient = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

// ── Types ────────────────────────────────────────────────────────────────────

export interface ProblemSummary {
  id: string
  slug: string
  title: string
  difficulty: 'easy' | 'medium' | 'hard'
}

export interface TestCaseSummary {
  id: string
  label: string
  input_data: string
  expected_output: string
  is_visible: boolean
  order_index: number
}

export interface ProblemDetail extends ProblemSummary {
  description: string
  starter_code_java: string
  time_limit_sec: number
  memory_limit_mb: number
  test_cases: TestCaseSummary[]
}

export type SubmissionStatus =
  | 'queued'
  | 'running'
  | 'completed'
  | 'compile_error'
  | 'error'
  | 'timeout'

export interface TestCaseResult {
  test_case_id: string
  label: string
  is_visible: boolean
  passed: boolean
  expected_output: string | null
  actual_output: string | null
  execution_time_ms: number | null
  error: string | null
}

export interface Submission {
  id: string
  problem_id: string
  language: string
  status: SubmissionStatus
  score: number | null
  total_cases: number | null
  passed_cases: number | null
  results_json: TestCaseResult[] | null
  execution_time_ms: number | null
  submitted_at: string
}

// ── API functions ─────────────────────────────────────────────────────────────

export const getProblems = () =>
  apiClient.get<ProblemSummary[]>('/problems').then((r) => r.data)

export const getProblem = (slug: string) =>
  apiClient.get<ProblemDetail>(`/problems/${slug}`).then((r) => r.data)

export const runCode = (slug: string, sourceCode: string) =>
  apiClient
    .post<{ submission_id: string }>(`/problems/${slug}/run`, {
      source_code: sourceCode,
      language: 'java',
    })
    .then((r) => r.data)

export const submitCode = (slug: string, sourceCode: string) =>
  apiClient
    .post<{ submission_id: string }>(`/problems/${slug}/submit`, {
      source_code: sourceCode,
      language: 'java',
    })
    .then((r) => r.data)

export const getSubmission = (id: string) =>
  apiClient.get<Submission>(`/submissions/${id}`).then((r) => r.data)
