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

// ── Auth token helpers ────────────────────────────────────────────────────────

const TOKEN_KEY = 'cf_access_token'
const REFRESH_KEY = 'cf_refresh_token'

export const getStoredToken = (): string | null => localStorage.getItem(TOKEN_KEY)
export const getStoredRefreshToken = (): string | null => localStorage.getItem(REFRESH_KEY)

export const storeTokens = (accessToken: string, refreshToken: string) => {
  localStorage.setItem(TOKEN_KEY, accessToken)
  localStorage.setItem(REFRESH_KEY, refreshToken)
}

export const clearTokens = () => {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

// ── Axios request interceptor — inject Bearer token ───────────────────────────
apiClient.interceptors.request.use((config) => {
  const token = getStoredToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ── Axios response interceptor — auto-refresh on 401 ─────────────────────────
let _isRefreshing = false
let _failedQueue: Array<{ resolve: (v: string) => void; reject: (e: unknown) => void }> = []

const processQueue = (error: unknown, token: string | null) => {
  _failedQueue.forEach((p) => {
    if (error) p.reject(error)
    else p.resolve(token as string)
  })
  _failedQueue = []
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (_isRefreshing) {
        return new Promise((resolve, reject) => {
          _failedQueue.push({ resolve, reject })
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`
            return apiClient(originalRequest)
          })
          .catch((err) => Promise.reject(err))
      }

      originalRequest._retry = true
      _isRefreshing = true

      const refresh = getStoredRefreshToken()
      if (!refresh) {
        _isRefreshing = false
        clearTokens()
        return Promise.reject(error)
      }

      try {
        const { data } = await axios.post('/api/v1/auth/refresh', { refresh_token: refresh })
        const newToken: string = data.access_token
        localStorage.setItem(TOKEN_KEY, newToken)
        processQueue(null, newToken)
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return apiClient(originalRequest)
      } catch (err) {
        processQueue(err, null)
        clearTokens()
        return Promise.reject(err)
      } finally {
        _isRefreshing = false
      }
    }
    return Promise.reject(error)
  }
)

// ── Types ─────────────────────────────────────────────────────────────────────

export interface UserResponse {
  id: string
  email: string
  name: string
  role: 'student' | 'instructor'
  created_at: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: UserResponse
}

export interface TokenRefreshResponse {
  access_token: string
  token_type: string
}

export interface ProblemSummary {
  id: string
  course_id: string | null
  slug: string
  title: string
  difficulty: 'easy' | 'medium' | 'hard'
  time_limit_sec: number
  memory_limit_mb: number
  created_at: string | null
}

export interface TestCaseSummary {
  id: string
  label: string
  input_data: string
  expected_output: string
  is_visible: boolean
  order_index: number
  weight?: number
}

export interface ProblemDetail extends ProblemSummary {
  description: string
  starter_code_java: string
  starter_code_python: string | null
  starter_code_c?: string | null
  starter_code_cpp?: string | null
  test_cases: TestCaseSummary[]
}

export type SubmissionStatus =
  | 'queued'
  | 'compiling'
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
  weight?: number
}

export interface Submission {
  id: string
  problem_id: string
  user_id: string | null
  lab_session_id: string | null
  language: string
  status: SubmissionStatus
  score: number | null
  total_cases: number | null
  passed_cases: number | null
  results_json: TestCaseResult[] | null
  execution_time_ms: number | null
  badge_awarded: boolean
  new_badge_count: number | null
  submitted_at: string
}

export interface SubmissionSummary {
  id: string
  language: string
  status: SubmissionStatus
  score: number | null
  passed_cases: number | null
  total_cases: number | null
  is_full_submit: boolean
  is_best: boolean
  submitted_at: string
}

export type Language = 'java' | 'python' | 'c' | 'cpp'

// ── Learning Modules Types ──────────────────────────────────────────────────
export interface LearningContent {
  id: string
  module_id: string
  content_type: 'text' | 'video' | 'problem'
  title: string
  body: string | null
  problem_id: string | null
  order_index: number
  created_at: string
}

export interface LearningModule {
  id: string
  course_id: string
  title: string
  description: string | null
  order_index: number
  is_published: boolean
  content_count: number
  is_completed: boolean
  created_at: string
}

export interface LearningModuleDetail extends LearningModule {
  contents: LearningContent[]
}

export interface ModuleProgressResponse {
  module_id: string
  user_id: string
  is_completed: boolean
  completed_at: string | null
}

export interface CourseProgressResponse {
  course_id: string
  total_modules: number
  completed_modules: number
  progress_percentage: number
  completed_module_ids: string[]
}

// ── Proctored Exam Types ────────────────────────────────────────────────────
export interface ExamProblem {
  id: string
  slug: string
  title: string
  difficulty: 'easy' | 'medium' | 'hard'
  weight: number
  order_index: number
  description: string
  starter_code_python?: string | null
  starter_code_java?: string | null
  starter_code_c?: string | null
  starter_code_cpp?: string | null
}

export interface Exam {
  id: string
  course_id: string
  title: string
  description: string | null
  duration_minutes: number
  starts_at: string
  ends_at: string
  is_active: boolean
  fullscreen_required: boolean
  tab_switch_limit: number
  copy_paste_blocked: boolean
  problem_count?: number
  has_session?: boolean
  session_status?: 'in_progress' | 'submitted' | null
  created_at?: string
}

export interface ExamDetail extends Exam {
  problems?: ExamProblem[]
}

export interface ExamSessionStartResponse {
  session_id: string
  exam_id: string
  started_at: string
  duration_seconds: number
  remaining_seconds: number
  fullscreen_required: boolean
  tab_switch_limit: number
  copy_paste_blocked: boolean
  problems: ExamProblem[]
}

export interface ExamViolationResponse {
  id: string
  exam_session_id: string
  violation_type: string
  total_violations: number
  tab_switches_remaining: number
  flagged: boolean
  occurred_at: string
}

export interface ExamSessionSummary {
  session_id: string
  exam_id: string
  submitted_at: string
  is_auto_submitted: boolean
  total_score: number
  problem_scores: Record<string, number>
  violation_count: number
}

export interface ExamStudentResult {
  user_id: string
  name: string
  email: string
  status: 'in_progress' | 'submitted'
  started_at: string
  submitted_at: string | null
  is_auto_submitted: boolean
  total_score: number | null
  violation_count: number
  violations: Array<{
    violation_type: string
    details: string | null
    occurred_at: string
  }>
}

export interface ExamResultsDashboard {
  exam_id: string
  course_id?: string
  title: string
  total_enrolled: number
  submissions_count: number
  average_score: number
  students: ExamStudentResult[]
}

export interface ExamMyResult {
  exam_id: string
  course_id?: string
  total_score: number
  submitted_at: string
  is_auto_submitted: boolean
  problem_scores: Record<string, number>
}

// ── Analytics Types ─────────────────────────────────────────────────────────
export interface CourseAnalytics {
  course_id: string
  summary: {
    total_students: number
    total_submissions: number
    average_pass_rate: number
    active_students_7d: number
  }
  problem_pass_rates: Array<{
    problem_id: string
    title: string
    difficulty: string
    submissions_count: number
    pass_rate: number
    average_score: number
  }>
  common_error_distribution: Array<{
    error_type: string
    count: number
  }>
  submission_trends: Array<{
    date: string
    count: number
  }>
}

export interface StudentAnalytics {
  user_id: string
  name: string
  total_submissions: number
  problems_solved: number
  badges_earned: number
  score_progression: Array<{
    submitted_at: string
    problem: string
    score: number
  }>
}

export interface ProblemAnalytics {
  problem_id: string
  slug: string
  title: string
  total_submissions: number
  unique_students: number
  pass_rate: number
  language_breakdown: Record<string, number>
  average_execution_time_ms: number
}

// ── Custom Input Types ──────────────────────────────────────────────────────
export interface RunCustomResponse {
  language: string
  status: string
  stdout: string | null
  stderr: string | null
  execution_time_ms: number | null
  exit_code: number | null
}

// ── API functions ─────────────────────────────────────────────────────────────

// --- Mock Data Store ---
const MOCK_PROBLEMS: ProblemDetail[] = [
  {
    id: "hello-world-id",
    slug: "hello-world",
    title: "Hello World",
    difficulty: "easy",
    course_id: null,
    time_limit_sec: 5,
    memory_limit_mb: 128,
    created_at: null,
    description: `## Hello World\n\nWrite a program that reads a name from stdin and prints a greeting.\n\n### Input\n- A single line containing a name (e.g., \`Alice\`).\n\n### Output\n- A single line: \`Hello, <name>!\`\n\n### Example\n\n**Input:**\n\`\`\`\nAlice\n\`\`\`\n\n**Output:**\n\`\`\`\nHello, Alice!\n\`\`\`\n\n### Constraints\n- The name will be a single word with no spaces.\n- Length: 1–50 characters.`,
    starter_code_java: `import java.util.Scanner;\n\npublic class Solution {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        // Your code here\n    }\n}`,
    starter_code_python: `import sys\n\ndef main():\n    name = input()\n    # Your code here\n\nif __name__ == '__main__':\n    main()`,
    test_cases: [
      {
        id: "hw-tc-1",
        label: "01",
        input_data: "Alice",
        expected_output: "Hello, Alice!",
        is_visible: true,
        order_index: 1
      },
      {
        id: "hw-tc-2",
        label: "02",
        input_data: "Bob",
        expected_output: "Hello, Bob!",
        is_visible: false,
        order_index: 2
      }
    ]
  },
  {
    id: "two-sum-id",
    slug: "two-sum",
    title: "Two Sum",
    difficulty: "easy",
    course_id: null,
    time_limit_sec: 10,
    memory_limit_mb: 128,
    created_at: null,
    description: `## Two Sum\n\nGiven an array of integers \`nums\` and an integer \`target\`, return the **0-based indices** of the two numbers such that they add up to \`target\`. There is exactly one valid answer.\n\n### Input\n- First line: integer \`n\` (size of array, 2 ≤ n ≤ 10⁴)\n- Second line: \`n\` space-separated integers\n- Third line: integer \`target\`\n\n### Output\n- Two space-separated 0-based indices (smaller index first)\n\n### Example\n\n**Input:**\n\`\`\`\n4\n2 7 11 15\n9\n\`\`\`\n\n**Output:**\n\`\`\`\n0 1\n\`\`\`\n\n### Constraints\n- 2 ≤ n ≤ 10⁴\n- -10⁹ ≤ nums[i] ≤ 10⁹\n- Exactly one valid answer exists.`,
    starter_code_java: `import java.util.Scanner;\n\npublic class Solution {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        int[] nums = new int[n];\n        for (int i = 0; i < n; i++) {\n            nums[i] = sc.nextInt();\n        }\n        int target = sc.nextInt();\n        // Your code here\n    }\n}`,
    starter_code_python: `import sys\n\ndef main():\n    n = int(input())\n    nums = list(map(int, input().split()))\n    target = int(input())\n    # Your code here\n\nif __name__ == '__main__':\n    main()`,
    test_cases: [
      {
        id: "ts-tc-1",
        label: "01",
        input_data: "4\n2 7 11 15\n9",
        expected_output: "0 1",
        is_visible: true,
        order_index: 1
      },
      {
        id: "ts-tc-2",
        label: "02",
        input_data: "3\n3 2 4\n6",
        expected_output: "1 2",
        is_visible: true,
        order_index: 2
      },
      {
        id: "ts-tc-3",
        label: "03",
        input_data: "2\n3 3\n6",
        expected_output: "0 1",
        is_visible: false,
        order_index: 3
      }
    ]
  },
  {
    id: "fizzbuzz-id",
    slug: "fizzbuzz",
    title: "FizzBuzz",
    difficulty: "easy",
    course_id: null,
    time_limit_sec: 5,
    memory_limit_mb: 128,
    created_at: null,
    description: `## FizzBuzz\n\nFor each integer from 1 to \`n\`, print:\n- \`FizzBuzz\` if the number is divisible by both 3 and 5\n- \`Fizz\` if divisible by 3 only\n- \`Buzz\` if divisible by 5 only\n- The number itself otherwise\n\n### Input\n- A single integer \`n\` (1 ≤ n ≤ 10⁵)\n\n### Output\n- \`n\` lines, one result per line\n\n### Example\n\n**Input:**\n\`\`\`\n15\n\`\`\`\n\n**Output:**\n\`\`\`\n1\n2\nFizz\n4\nBuzz\nFizz\n7\n8\nFizz\nBuzz\n11\nFizz\n3\n14\nFizzBuzz\n\`\`\``,
    starter_code_java: `import java.util.Scanner;\n\npublic class Solution {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        // Your code here\n    }\n}`,
    starter_code_python: `import sys\n\ndef main():\n    n = int(input())\n    # Your code here\n\nif __name__ == '__main__':\n    main()`,
    test_cases: [
      {
        id: "fb-tc-1",
        label: "01",
        input_data: "15",
        expected_output: "1\n2\nFizz\n4\nBuzz\nFizz\n7\n8\nFizz\nBuzz\n11\nFizz\n13\n14\nFizzBuzz",
        is_visible: true,
        order_index: 1
      },
      {
        id: "fb-tc-2",
        label: "02",
        input_data: "5",
        expected_output: "1\n2\nFizz\n4\nBuzz",
        is_visible: true,
        order_index: 2
      }
    ]
  }
]

const mockSubmissions: Record<string, Submission> = {}

function simulateSubmission(id: string, slug: string, sourceCode: string, isFullSubmit: boolean) {
  const problem = MOCK_PROBLEMS.find(p => p.slug === slug)
  if (!problem) return

  let steps = 0
  const interval = setInterval(() => {
    steps++
    const sub = mockSubmissions[id]
    if (!sub) {
      clearInterval(interval)
      return
    }

    if (steps === 1) {
      sub.status = 'running'
    } else if (steps >= 3) {
      clearInterval(interval)

      const hasSyntaxError = sourceCode.includes("syntax_error_here") || (sourceCode.includes("class") && !sourceCode.includes("class Solution"))
      const hasTimeout = sourceCode.includes("while(true)") || sourceCode.includes("Thread.sleep")
      const hasRuntimeError = sourceCode.includes("runtime_error_here") || sourceCode.includes("/ 0")

      if (hasSyntaxError) {
        sub.status = 'compile_error'
        sub.results_json = []
        sub.score = 0
        sub.passed_cases = 0
        sub.total_cases = problem.test_cases.length
      } else if (hasTimeout) {
        sub.status = 'timeout'
        sub.results_json = problem.test_cases.map(tc => ({
          test_case_id: tc.id,
          label: tc.label,
          is_visible: tc.is_visible || isFullSubmit,
          passed: false,
          expected_output: tc.is_visible || isFullSubmit ? tc.expected_output : null,
          actual_output: null,
          execution_time_ms: problem.time_limit_sec * 1000,
          error: "Time Limit Exceeded"
        }))
        sub.score = 0
        sub.passed_cases = 0
        sub.total_cases = problem.test_cases.length
      } else {
        sub.status = 'completed'

        let passed = 0
        const testResults = problem.test_cases.map(tc => {
          const isCaseVisible = tc.is_visible
          const shouldEval = isFullSubmit || isCaseVisible

          if (!shouldEval) {
            return {
              test_case_id: tc.id,
              label: tc.label,
              is_visible: false,
              passed: false,
              expected_output: null,
              actual_output: null,
              execution_time_ms: 0,
              error: "Not run (Hidden test case during Run)"
            }
          }

          let casePassed = true
          let actualOutput: string | null = tc.expected_output
          let error: string | null = null

          if (hasRuntimeError) {
            casePassed = false
            actualOutput = null
            error = "java.lang.ArithmeticException: / by zero\n\tat Solution.main(Solution.java:12)"
          } else if (sourceCode.includes("fail_case_2") && tc.label === "02") {
            casePassed = false
            actualOutput = "Unexpected Output or Empty"
          } else if (sourceCode.trim().length < 50 || sourceCode.includes("Your code here")) {
            casePassed = false
            actualOutput = ""
          }

          if (casePassed) passed++

          return {
            test_case_id: tc.id,
            label: tc.label,
            is_visible: isCaseVisible,
            passed: casePassed,
            expected_output: isCaseVisible ? tc.expected_output : null,
            actual_output: isCaseVisible ? actualOutput : null,
            execution_time_ms: Math.floor(Math.random() * 50) + 15,
            error: error
          }
        })

        sub.results_json = testResults
        const totalEvaluated = isFullSubmit
          ? problem.test_cases.length
          : problem.test_cases.filter(tc => tc.is_visible).length
        sub.total_cases = totalEvaluated
        sub.passed_cases = passed
        sub.score = totalEvaluated > 0 ? Math.round((passed / totalEvaluated) * 100) : 0
        sub.execution_time_ms = testResults.reduce((acc, curr) => acc + (curr.execution_time_ms || 0), 0)

        // Mock badge award for perfect score on full submit
        if (isFullSubmit && sub.score === 100) {
          sub.badge_awarded = true
          sub.new_badge_count = 1
        }
      }
    }
  }, 1000)
}

// ── Auth API ──────────────────────────────────────────────────────────────────

export interface RegisterPayload {
  email: string
  name: string
  password: string
  role?: 'student' | 'instructor'
}

export interface LoginPayload {
  email: string
  password: string
}

export const register = (payload: RegisterPayload): Promise<TokenResponse> =>
  apiClient
    .post<TokenResponse>('/auth/register', payload)
    .then((r) => r.data)

export const login = (payload: LoginPayload): Promise<TokenResponse> =>
  apiClient
    .post<TokenResponse>('/auth/login', payload)
    .then((r) => r.data)

export const refreshToken = (refresh_token: string): Promise<TokenRefreshResponse> =>
  apiClient
    .post<TokenRefreshResponse>('/auth/refresh', { refresh_token })
    .then((r) => r.data)

export const getMe = (): Promise<UserResponse> =>
  apiClient
    .get<UserResponse>('/auth/me')
    .then((r) => r.data)

// ── Problem API ───────────────────────────────────────────────────────────────

export const getProblems = (): Promise<ProblemSummary[]> =>
  apiClient
    .get<ProblemSummary[]>('/problems')
    .then((r) => r.data)
    .catch(() => {
      console.warn("API unavailable, falling back to mock problems")
      return MOCK_PROBLEMS.map(({ id, slug, title, difficulty, course_id, time_limit_sec, memory_limit_mb, created_at }) => ({
        id, slug, title, difficulty, course_id, time_limit_sec, memory_limit_mb, created_at,
      }))
    })

export const getProblem = (slug: string): Promise<ProblemDetail> =>
  apiClient
    .get<ProblemDetail>(`/problems/${slug}`)
    .then((r) => r.data)
    .catch(() => {
      console.warn(`API unavailable, falling back to mock problem: ${slug}`)
      const found = MOCK_PROBLEMS.find((p) => p.slug === slug)
      if (!found) throw new Error(`Problem not found: ${slug}`)
      return found
    })

// ── Course API ────────────────────────────────────────────────────────────────

// ── Course API ────────────────────────────────────────────────────────────────

export interface CourseResponse {
  id: string
  title: string
  description: string | null
  invite_code: string
  join_code: string
  created_by: string
  instructor_id: string
  instructor_name?: string
  role?: string
  member_count?: number
  problem_count?: number
  created_at: string
}

export interface LabSession {
  id: string
  course_id: string
  title: string
  topic: string
  starts_at: string
  ends_at: string
  is_active: boolean
  problem_count: number
  mandatory_count: number
}

export interface LabProblem {
  problem_id: string
  problem_slug: string
  problem_title: string
  is_mandatory: boolean
  order_index: number
  difficulty: string
}

export interface LabSessionDetail extends LabSession {
  problems: LabProblem[]
}

export interface StudentLabProgress {
  user_id: string
  user_name: string
  user_email: string
  mandatory_solved: number
  mandatory_total: number
  extra_solved: number
  badges_earned: number
  last_submission_at: string | null
}

export interface MyLabProgress {
  lab_session_id: string
  mandatory_solved: number
  mandatory_total: number
  extra_solved: number
  badges_earned: number
  problems: MyLabProblemProgress[]
}

export interface MyLabProblemProgress {
  problem_id: string
  problem_slug: string
  problem_title: string
  is_mandatory: boolean
  is_solved: boolean
  best_score: number | null
}

export interface GradebookRow {
  user_id: string
  user_name: string
  user_email: string
  lab_results: LabGradeResult[]
  total_badges: number
  total_mandatory_solved: number
  total_mandatory: number
}

export interface LabGradeResult {
  lab_session_id: string
  lab_title: string
  mandatory_solved: number
  mandatory_total: number
  badges_earned: number
}

// ── Course API Functions ──────────────────────────────────────────────────────

const normalizeCourse = (c: any): CourseResponse => ({
  id: c.id,
  title: c.title,
  description: c.description || '',
  invite_code: c.invite_code || c.join_code || '',
  join_code: c.join_code || c.invite_code || '',
  created_by: c.created_by || c.instructor_id || '',
  instructor_id: c.instructor_id || c.created_by || '',
  instructor_name: c.instructor_name || 'Admin Instructor',
  role: c.role || c.user_role,
  member_count: c.member_count ?? 0,
  problem_count: c.problem_count ?? 0,
  created_at: c.created_at || new Date().toISOString(),
})

export const getCourses = (): Promise<CourseResponse[]> =>
  apiClient.get<CourseResponse[]>('/courses').then((r) => r.data.map(normalizeCourse))

export const getCourse = (id: string): Promise<CourseResponse> =>
  apiClient.get<CourseResponse>(`/courses/${id}`).then((r) => normalizeCourse(r.data))

export const createCourse = (data: { title: string; description: string }): Promise<CourseResponse> =>
  apiClient.post<CourseResponse>('/courses', data).then((r) => normalizeCourse(r.data))

export const joinCourse = (joinCode: string): Promise<CourseResponse> =>
  apiClient
    .post<CourseResponse>('/courses/join', {
      join_code: joinCode.trim(),
      invite_code: joinCode.trim(),
    })
    .then((r) => normalizeCourse(r.data))

export const getCourseProblems = (courseId: string): Promise<ProblemSummary[]> =>
  apiClient.get<ProblemSummary[]>(`/courses/${courseId}/problems`).then((r) => r.data)

export interface TestCaseInput {
  label: string
  input_data: string
  expected_output: string
  is_visible: boolean
  order_index?: number
  weight?: number
}

export interface ProblemCreateInput {
  slug: string
  title: string
  description: string
  difficulty: 'easy' | 'medium' | 'hard'
  starter_code_java?: string
  starter_code_python?: string
  time_limit_sec?: number
  memory_limit_mb?: number
  test_cases: TestCaseInput[]
}

export const createProblem = (courseId: string, data: ProblemCreateInput): Promise<ProblemDetail> =>
  apiClient.post<ProblemDetail>(`/courses/${courseId}/problems`, data).then((r) => r.data)

export const bulkImportProblems = (
  courseId: string,
  problems: ProblemCreateInput[]
): Promise<{ imported_count: number; failed_count: number; imported_slugs: string[]; errors: string[] }> =>
  apiClient.post(`/courses/${courseId}/problems/bulk-import`, { problems }).then((r) => r.data)

// ── Lab Session API Functions ─────────────────────────────────────────────────

export const getCourseLabs = (courseId: string): Promise<LabSession[]> =>
  apiClient.get<any[]>(`/courses/${courseId}/labs`).then((r) =>
    r.data.map((l) => ({
      id: l.id,
      course_id: l.course_id,
      title: l.title,
      topic: l.description || l.topic || 'Lab Session',
      starts_at: l.starts_at || new Date().toISOString(),
      ends_at: l.ends_at || new Date(Date.now() + 7 * 86400000).toISOString(),
      is_active: l.is_active,
      problem_count: l.problem_count ?? (l.problems ? l.problems.length : 0),
      mandatory_count: l.mandatory_count ?? 1,
    }))
  )

export const getLabSession = (id: string): Promise<LabSessionDetail> =>
  apiClient.get<any>(`/labs/${id}`).then((r) => {
    const l = r.data
    return {
      id: l.id,
      course_id: l.course_id,
      title: l.title,
      topic: l.description || l.topic || 'Lab Session',
      starts_at: l.starts_at || new Date().toISOString(),
      ends_at: l.ends_at || new Date(Date.now() + 7 * 86400000).toISOString(),
      is_active: l.is_active,
      problem_count: l.problems ? l.problems.length : (l.problem_count ?? 0),
      mandatory_count: l.mandatory_count ?? 1,
      problems: (l.problems || []).map((p: any, idx: number) => ({
        problem_id: p.id,
        problem_slug: p.slug,
        problem_title: p.title,
        is_mandatory: idx < (l.mandatory_count ?? 1),
        order_index: p.order_index ?? idx + 1,
        difficulty: p.difficulty ?? 'easy',
      })),
    }
  })

export const createLabSession = (
  courseId: string,
  data: {
    title: string
    topic: string
    starts_at: string
    ends_at: string
    problem_ids: { problem_id: string; is_mandatory: boolean }[]
  }
): Promise<LabSessionDetail> => {
  const mandatoryCount = data.problem_ids.filter((p) => p.is_mandatory).length || 1
  const payload = {
    title: data.title,
    description: data.topic,
    starts_at: data.starts_at,
    ends_at: data.ends_at,
    mandatory_count: mandatoryCount,
    problem_ids: data.problem_ids.map((p) => p.problem_id),
  }
  return apiClient.post<any>(`/courses/${courseId}/labs`, payload).then((r) => {
    const l = r.data
    return {
      id: l.id,
      course_id: l.course_id,
      title: l.title,
      topic: l.description || data.topic,
      starts_at: l.starts_at,
      ends_at: l.ends_at,
      is_active: l.is_active,
      problem_count: data.problem_ids.length,
      mandatory_count: mandatoryCount,
      problems: (l.problems || []).map((p: any, idx: number) => ({
        problem_id: p.id,
        problem_slug: p.slug,
        problem_title: p.title,
        is_mandatory: idx < mandatoryCount,
        order_index: p.order_index ?? idx + 1,
        difficulty: p.difficulty ?? 'easy',
      })),
    }
  })
}

export const getLabDashboard = (labId: string): Promise<StudentLabProgress[]> =>
  apiClient.get<any>(`/labs/${labId}/dashboard`).then((r) => {
    const data = r.data
    const students = data.students || []
    return students.map((s: any) => ({
      user_id: s.user_id,
      user_name: s.name,
      user_email: s.email,
      mandatory_solved: s.mandatory_completed
        ? data.mandatory_count
        : Math.min(s.problems_solved, data.mandatory_count),
      mandatory_total: data.mandatory_count,
      extra_solved: Math.max(0, s.problems_solved - data.mandatory_count),
      badges_earned: s.badge_count,
      last_submission_at: s.last_submission_at,
    }))
  })

export const getMyLabProgress = async (labId: string): Promise<MyLabProgress> => {
  const [lab, progressRes] = await Promise.all([
    getLabSession(labId),
    apiClient.get<any>(`/labs/${labId}/my-progress`).then((r) => r.data),
  ])
  const solvedSet = new Set((progressRes.solved_problem_ids || []).map((id: string) => String(id)))
  const mandTotal = progressRes.mandatory_count || lab.mandatory_count || 1
  const solvedCount = progressRes.problems_solved_count || 0
  return {
    lab_session_id: labId,
    mandatory_solved: progressRes.mandatory_completed
      ? mandTotal
      : Math.min(solvedCount, mandTotal),
    mandatory_total: mandTotal,
    extra_solved: Math.max(0, solvedCount - mandTotal),
    badges_earned: progressRes.badge_count || 0,
    problems: (lab.problems || []).map((p) => ({
      problem_id: p.problem_id,
      problem_slug: p.problem_slug,
      problem_title: p.problem_title,
      is_mandatory: p.is_mandatory,
      is_solved: solvedSet.has(String(p.problem_id)),
      best_score: solvedSet.has(String(p.problem_id)) ? 100 : null,
    })),
  }
}

// ── Gradebook API ─────────────────────────────────────────────────────────────

export const getGradebook = async (courseId: string): Promise<GradebookRow[]> => {
  // Fetch real gradebook and course labs in parallel
  const [gbData, labs] = await Promise.all([
    apiClient.get<any>(`/courses/${courseId}/gradebook`).then((r) => r.data),
    getCourseLabs(courseId).catch(() => []),
  ])

  // Also fetch lab dashboard for the active labs if present to get accurate badge counts
  const labDashboards: Record<string, StudentLabProgress[]> = {}
  await Promise.all(
    labs.map(async (l) => {
      try {
        labDashboards[l.id] = await getLabDashboard(l.id)
      } catch {
        labDashboards[l.id] = []
      }
    })
  )

  const rows: any[] = gbData.rows || []
  return rows.map((r) => {
    let totalBadges = 0
    let totalMandatorySolved = 0
    let totalMandatory = 0

    const labResults: LabGradeResult[] = labs.map((l) => {
      const studentDash = (labDashboards[l.id] || []).find((s) => s.user_id === r.user_id)
      const badges = studentDash?.badges_earned ?? 0
      const mandSolved = studentDash?.mandatory_solved ?? 0
      const mandTotal = l.mandatory_count || 1

      totalBadges += badges
      totalMandatorySolved += mandSolved
      totalMandatory += mandTotal

      return {
        lab_session_id: l.id,
        lab_title: l.title,
        mandatory_solved: mandSolved,
        mandatory_total: mandTotal,
        badges_earned: badges,
      }
    })

    // If no labs in course yet, build virtual entry from problems
    if (labs.length === 0) {
      const solvedProblems = Object.values(r.scores || {}).filter((sc) => sc === 100).length
      totalMandatorySolved = solvedProblems
      totalMandatory = (gbData.problems || []).length || 1
    }

    return {
      user_id: r.user_id,
      user_name: r.name,
      user_email: r.email,
      lab_results: labResults,
      total_badges: totalBadges,
      total_mandatory_solved: totalMandatorySolved,
      total_mandatory: totalMandatory || 1,
    }
  })
}



// ── Submission API ────────────────────────────────────────────────────────────

export const runCode = (slug: string, sourceCode: string, language: Language = 'java'): Promise<{ submission_id: string }> =>
  apiClient
    .post<{ submission_id: string }>(`/problems/${slug}/run`, {
      source_code: sourceCode,
      language,
    })
    .then((r) => r.data)
    .catch(() => {
      console.warn("API unavailable, running code using local mock simulation")
      const id = 'mock-sub-' + Math.random().toString(36).substring(2, 11)
      mockSubmissions[id] = {
        id,
        problem_id: slug + '-id',
        user_id: null,
        lab_session_id: null,
        language,
        status: 'queued',
        score: null,
        total_cases: null,
        passed_cases: null,
        results_json: null,
        execution_time_ms: null,
        badge_awarded: false,
        new_badge_count: null,
        submitted_at: new Date().toISOString(),
      }
      simulateSubmission(id, slug, sourceCode, false)
      return { submission_id: id }
    })

export const submitCode = (slug: string, sourceCode: string, language: Language = 'java', lab_session_id?: string): Promise<{ submission_id: string }> =>
  apiClient
    .post<{ submission_id: string }>(`/problems/${slug}/submit`, {
      source_code: sourceCode,
      language,
      lab_session_id: lab_session_id ?? null,
    })
    .then((r) => r.data)
    .catch(() => {
      console.warn("API unavailable, submitting code using local mock simulation")
      const id = 'mock-sub-' + Math.random().toString(36).substring(2, 11)
      mockSubmissions[id] = {
        id,
        problem_id: slug + '-id',
        user_id: null,
        lab_session_id: lab_session_id ?? null,
        language,
        status: 'queued',
        score: null,
        total_cases: null,
        passed_cases: null,
        results_json: null,
        execution_time_ms: null,
        badge_awarded: false,
        new_badge_count: null,
        submitted_at: new Date().toISOString(),
      }
      simulateSubmission(id, slug, sourceCode, true)
      return { submission_id: id }
    })

export const getSubmission = (id: string): Promise<Submission> =>
  apiClient
    .get<Submission>(`/submissions/${id}`)
    .then((r) => r.data)
    .catch(() => {
      if (mockSubmissions[id]) {
        return mockSubmissions[id]
      }
      throw new Error(`Submission not found: ${id}`)
    })

export const getSubmissionHistory = (slug: string): Promise<SubmissionSummary[]> =>
  apiClient
    .get<SubmissionSummary[]>(`/problems/${slug}/submissions`)
    .then((r) => r.data)
    .catch(() => {
      // Return empty array on auth failure / no history — graceful degradation
      return []
    })

// ── Custom Input API ─────────────────────────────────────────────────────────

export const runCustomInput = async (
  slug: string,
  sourceCode: string,
  language: Language = 'python',
  stdin: string = ''
): Promise<RunCustomResponse> => {
  return apiClient
    .post<RunCustomResponse>(`/problems/${slug}/run-custom`, {
      source_code: sourceCode,
      language,
      stdin,
    })
    .then((r) => r.data)
    .catch(() => {
      console.warn("API run-custom unavailable, using local execution simulation")
      // Quick local simulation for demo purposes
      let stdout = ''
      if (sourceCode.includes('print') || sourceCode.includes('System.out') || sourceCode.includes('printf')) {
        stdout = stdin ? `[Custom Run Output with stdin="${stdin}"]\nExecution completed successfully.` : 'Hello from CodeForge sandbox!\nExecution completed successfully.'
      } else {
        stdout = `Program finished with no output. Stdin provided: ${stdin || '(none)'}`
      }
      return {
        language,
        status: 'completed',
        stdout,
        stderr: null,
        execution_time_ms: Math.floor(Math.random() * 40) + 15,
        exit_code: 0,
      }
    })
}

// ── Learning Modules API ────────────────────────────────────────────────────

// Mock store for modules
const MOCK_MODULES: Record<string, LearningModuleDetail[]> = {
  default: [
    {
      id: 'm1a2b3c4-0000-0000-0000-000000000001',
      course_id: 'default',
      title: 'Module 1: Introduction to Python & Control Flow',
      description: 'Fundamental variables, conditionals, loops, and first algorithmic problems.',
      order_index: 1,
      is_published: true,
      content_count: 3,
      is_completed: false,
      created_at: new Date(Date.now() - 86400000 * 5).toISOString(),
      contents: [
        {
          id: 'c1a2b3c4-0000-0000-0000-000000000001',
          module_id: 'm1a2b3c4-0000-0000-0000-000000000001',
          content_type: 'text',
          title: 'Understanding Python Variables & Memory Model',
          body: `## Variables in Python\n\nIn Python, variables are references to objects in memory, not direct memory addresses like in C/C++.\n\n### Key Concepts:\n- **Dynamic Typing:** You do not declare types explicitly. Python dynamically binds types at runtime.\n- **Everything is an Object:** Integers, strings, functions, and classes are all first-class objects.\n- **Mutability:** Primitive types like \`int\`, \`float\`, \`str\`, and \`tuple\` are immutable. Lists and dictionaries are mutable.\n\n\`\`\`python\n# Variable assignment\nx = 42\ny = x\nprint(id(x) == id(y))  # True — both reference the same object\n\`\`\`\n\nTake note of this when passing lists into helper functions!`,
          problem_id: null,
          order_index: 1,
          created_at: new Date(Date.now() - 86400000 * 5).toISOString(),
        },
        {
          id: 'c1a2b3c4-0000-0000-0000-000000000002',
          module_id: 'm1a2b3c4-0000-0000-0000-000000000001',
          content_type: 'video',
          title: 'Python Control Flow & Functions Masterclass',
          body: 'https://www.youtube.com/watch?v=kqtD5dpn9C8',
          problem_id: null,
          order_index: 2,
          created_at: new Date(Date.now() - 86400000 * 4).toISOString(),
        },
        {
          id: 'c1a2b3c4-0000-0000-0000-000000000003',
          module_id: 'm1a2b3c4-0000-0000-0000-000000000001',
          content_type: 'problem',
          title: 'Practice: Hello World & Stdin Basics',
          body: 'Apply basic stdin reading and output formatting with the standard Hello World exercise.',
          problem_id: 'hello-world-id',
          order_index: 3,
          created_at: new Date(Date.now() - 86400000 * 3).toISOString(),
        },
      ],
    },
    {
      id: 'm2a2b3c4-0000-0000-0000-000000000002',
      course_id: 'default',
      title: 'Module 2: Algorithmic Thinking & Array Search',
      description: 'Master time and space complexity, array manipulation, and hash map lookups.',
      order_index: 2,
      is_published: true,
      content_count: 2,
      is_completed: false,
      created_at: new Date(Date.now() - 86400000 * 2).toISOString(),
      contents: [
        {
          id: 'c2a2b3c4-0000-0000-0000-000000000001',
          module_id: 'm2a2b3c4-0000-0000-0000-000000000002',
          content_type: 'text',
          title: 'Hash Maps & O(N) Lookup Patterns',
          body: `## The Two-Sum Problem: From O(N²) to O(N)\n\nWhen searching for complementary pairs in an array:\n\n1. **Brute Force:** Nested loops check every pair (Time: O(N²), Space: O(1)).\n2. **Hash Map Lookup:** Store each element's complement in a map as you traverse (Time: O(N), Space: O(N)).\n\n\`\`\`python\ndef two_sum(nums, target):\n    seen = {}\n    for i, num in enumerate(nums):\n        diff = target - num\n        if diff in seen:\n            return [seen[diff], i]\n        seen[num] = i\n    return []\n\`\`\``,
          problem_id: null,
          order_index: 1,
          created_at: new Date(Date.now() - 86400000 * 2).toISOString(),
        },
        {
          id: 'c2a2b3c4-0000-0000-0000-000000000002',
          module_id: 'm2a2b3c4-0000-0000-0000-000000000002',
          content_type: 'problem',
          title: 'Practice: Two Sum Solution',
          body: 'Implement the optimal O(N) Two Sum lookup in the CodeForge IDE.',
          problem_id: 'two-sum-id',
          order_index: 2,
          created_at: new Date(Date.now() - 86400000 * 1).toISOString(),
        },
      ],
    },
  ],
}

export const getCourseModules = async (courseId: string): Promise<LearningModule[]> => {
  return apiClient
    .get<LearningModule[]>(`/courses/${courseId}/modules`)
    .then((r) => r.data)
    .catch(() => {
      return (MOCK_MODULES[courseId] || MOCK_MODULES['default']).map((m) => ({
        id: m.id,
        course_id: courseId,
        title: m.title,
        description: m.description,
        order_index: m.order_index,
        is_published: m.is_published,
        content_count: m.contents.length,
        is_completed: m.is_completed,
        created_at: m.created_at,
      }))
    })
}

export const getModuleDetail = async (moduleId: string): Promise<LearningModuleDetail> => {
  return apiClient
    .get<LearningModuleDetail>(`/modules/${moduleId}`)
    .then((r) => r.data)
    .catch(() => {
      for (const list of Object.values(MOCK_MODULES)) {
        const found = list.find((m) => m.id === moduleId)
        if (found) return found
      }
      return MOCK_MODULES['default'][0]
    })
}

export const createCourseModule = async (
  courseId: string,
  data: { title: string; description?: string; order_index?: number; is_published?: boolean }
): Promise<LearningModule> => {
  return apiClient
    .post<LearningModule>(`/courses/${courseId}/modules`, data)
    .then((r) => r.data)
    .catch(() => {
      const newMod: LearningModuleDetail = {
        id: 'mod-' + Math.random().toString(36).substring(2, 9),
        course_id: courseId,
        title: data.title,
        description: data.description || null,
        order_index: data.order_index ?? (MOCK_MODULES[courseId]?.length || 0) + 1,
        is_published: data.is_published ?? true,
        content_count: 0,
        is_completed: false,
        created_at: new Date().toISOString(),
        contents: [],
      }
      if (!MOCK_MODULES[courseId]) MOCK_MODULES[courseId] = []
      MOCK_MODULES[courseId].push(newMod)
      return newMod
    })
}

export const updateCourseModule = async (
  moduleId: string,
  data: Partial<{ title: string; description?: string; order_index?: number; is_published?: boolean }>
): Promise<LearningModule> => {
  return apiClient
    .put<LearningModule>(`/modules/${moduleId}`, data)
    .then((r) => r.data)
    .catch(() => {
      for (const list of Object.values(MOCK_MODULES)) {
        const found = list.find((m) => m.id === moduleId)
        if (found) {
          Object.assign(found, data)
          return found
        }
      }
      throw new Error(`Module not found: ${moduleId}`)
    })
}

export const deleteCourseModule = async (moduleId: string): Promise<void> => {
  return apiClient
    .delete(`/modules/${moduleId}`)
    .then(() => {})
    .catch(() => {
      for (const key of Object.keys(MOCK_MODULES)) {
        MOCK_MODULES[key] = MOCK_MODULES[key].filter((m) => m.id !== moduleId)
      }
    })
}

export const addModuleContent = async (
  moduleId: string,
  data: {
    content_type: 'text' | 'video' | 'problem'
    title: string
    body?: string | null
    problem_id?: string | null
    order_index?: number
  }
): Promise<LearningContent> => {
  return apiClient
    .post<LearningContent>(`/modules/${moduleId}/contents`, data)
    .then((r) => r.data)
    .catch(() => {
      const newContent: LearningContent = {
        id: 'cnt-' + Math.random().toString(36).substring(2, 9),
        module_id: moduleId,
        content_type: data.content_type,
        title: data.title,
        body: data.body || null,
        problem_id: data.problem_id || null,
        order_index: data.order_index ?? 1,
        created_at: new Date().toISOString(),
      }
      for (const list of Object.values(MOCK_MODULES)) {
        const found = list.find((m) => m.id === moduleId)
        if (found) {
          found.contents.push(newContent)
          found.content_count = found.contents.length
        }
      }
      return newContent
    })
}

export const updateModuleContent = async (
  contentId: string,
  data: Partial<{
    title: string
    body?: string | null
    problem_id?: string | null
    order_index?: number
  }>
): Promise<LearningContent> => {
  return apiClient
    .put<LearningContent>(`/contents/${contentId}`, data)
    .then((r) => r.data)
    .catch(() => {
      for (const list of Object.values(MOCK_MODULES)) {
        for (const mod of list) {
          const content = mod.contents.find((c) => c.id === contentId)
          if (content) {
            Object.assign(content, data)
            return content
          }
        }
      }
      throw new Error(`Content not found: ${contentId}`)
    })
}

export const deleteModuleContent = async (contentId: string): Promise<void> => {
  return apiClient
    .delete(`/contents/${contentId}`)
    .then(() => {})
    .catch(() => {
      for (const list of Object.values(MOCK_MODULES)) {
        for (const mod of list) {
          mod.contents = mod.contents.filter((c) => c.id !== contentId)
          mod.content_count = mod.contents.length
        }
      }
    })
}

export const completeModule = async (
  moduleId: string,
  lastContentId?: string
): Promise<ModuleProgressResponse> => {
  return apiClient
    .post<ModuleProgressResponse>(`/modules/${moduleId}/complete`, {
      last_content_id: lastContentId ?? null,
    })
    .then((r) => r.data)
    .catch(() => {
      for (const list of Object.values(MOCK_MODULES)) {
        const found = list.find((m) => m.id === moduleId)
        if (found) found.is_completed = true
      }
      return {
        module_id: moduleId,
        user_id: 'current-user',
        is_completed: true,
        completed_at: new Date().toISOString(),
      }
    })
}

export const getCourseModuleProgress = async (courseId: string): Promise<CourseProgressResponse> => {
  return apiClient
    .get<CourseProgressResponse>(`/courses/${courseId}/module-progress`)
    .then((r) => r.data)
    .catch(() => {
      const mods = MOCK_MODULES[courseId] || MOCK_MODULES['default']
      const completed = mods.filter((m) => m.is_completed)
      return {
        course_id: courseId,
        total_modules: mods.length,
        completed_modules: completed.length,
        progress_percentage: mods.length > 0 ? Math.round((completed.length / mods.length) * 100) : 0,
        completed_module_ids: completed.map((m) => m.id),
      }
    })
}

// ── Proctored Exams API ─────────────────────────────────────────────────────

export const getCourseExams = async (courseId: string): Promise<Exam[]> => {
  return apiClient
    .get<Exam[]>(`/courses/${courseId}/exams`)
    .then((r) => r.data)
}

export const getExamDetail = async (examId: string): Promise<ExamDetail> => {
  return apiClient
    .get<ExamDetail>(`/exams/${examId}`)
    .then((r) => r.data)
}

export const createExam = async (
  courseId: string,
  data: {
    title: string
    description?: string
    duration_minutes: number
    starts_at: string
    ends_at: string
    fullscreen_required?: boolean
    tab_switch_limit?: number
    copy_paste_blocked?: boolean
    problems: Array<{ problem_id: string; order_index: number; weight: number }>
  }
): Promise<ExamDetail> => {
  return apiClient
    .post<ExamDetail>(`/courses/${courseId}/exams`, data)
    .then((r) => r.data)
}

export const startExamSession = async (examId: string): Promise<ExamSessionStartResponse> => {
  return apiClient
    .post<ExamSessionStartResponse>(`/exams/${examId}/start`)
    .then((r) => r.data)
}

export const logExamViolation = async (
  sessionId: string,
  violation: {
    violation_type: 'tab_switch' | 'fullscreen_exit' | 'copy_paste' | 'focus_loss'
    details?: string
  }
): Promise<ExamViolationResponse> => {
  return apiClient
    .post<ExamViolationResponse>(`/exam-sessions/${sessionId}/violations`, violation)
    .then((r) => r.data)
}

export const submitExamSession = async (
  examId: string,
  isAutoSubmitted: boolean = false
): Promise<ExamSessionSummary> => {
  return apiClient
    .post<ExamSessionSummary>(`/exams/${examId}/submit`, {
      is_auto_submitted: isAutoSubmitted,
    })
    .then((r) => r.data)
}

export const getExamResults = async (examId: string): Promise<ExamResultsDashboard> => {
  return apiClient
    .get<ExamResultsDashboard>(`/exams/${examId}/results`)
    .then((r) => r.data)
}

export const getMyExamResult = async (examId: string): Promise<ExamMyResult> => {
  return apiClient
    .get<ExamMyResult>(`/exams/${examId}/my-result`)
    .then((r) => r.data)
}

// ── Analytics API ───────────────────────────────────────────────────────────

export const getCourseAnalytics = async (courseId: string): Promise<CourseAnalytics> => {
  return apiClient
    .get<CourseAnalytics>(`/courses/${courseId}/analytics`)
    .then((r) => r.data)
    .catch(() => ({
      course_id: courseId,
      summary: {
        total_students: 35,
        total_submissions: 412,
        average_pass_rate: 78.4,
        active_students_7d: 29,
      },
      problem_pass_rates: [
        {
          problem_id: 'hello-world-id',
          title: 'Hello World',
          difficulty: 'easy',
          submissions_count: 142,
          pass_rate: 96.5,
          average_score: 98.2,
        },
        {
          problem_id: 'two-sum-id',
          title: 'Two Sum',
          difficulty: 'easy',
          submissions_count: 120,
          pass_rate: 82.5,
          average_score: 87.0,
        },
        {
          problem_id: 'fizzbuzz-id',
          title: 'FizzBuzz Modulo',
          difficulty: 'medium',
          submissions_count: 98,
          pass_rate: 68.3,
          average_score: 72.4,
        },
        {
          problem_id: 'pointer-id',
          title: 'Pointer Arithmetic',
          difficulty: 'hard',
          submissions_count: 52,
          pass_rate: 42.1,
          average_score: 49.5,
        },
      ],
      common_error_distribution: [
        { error_type: 'wrong_answer', count: 88 },
        { error_type: 'compile_error', count: 54 },
        { error_type: 'runtime_error', count: 32 },
        { error_type: 'timeout', count: 21 },
      ],
      submission_trends: [
        { date: 'Nov 16', count: 28 },
        { date: 'Nov 17', count: 42 },
        { date: 'Nov 18', count: 65 },
        { date: 'Nov 19', count: 58 },
        { date: 'Nov 20', count: 89 },
        { date: 'Nov 21', count: 110 },
        { date: 'Nov 22', count: 94 },
      ],
    }))
}

export const getStudentAnalytics = async (
  courseId: string,
  userId: string
): Promise<StudentAnalytics> => {
  return apiClient
    .get<StudentAnalytics>(`/courses/${courseId}/analytics/students/${userId}`)
    .then((r) => r.data)
    .catch(() => ({
      user_id: userId,
      name: 'Sample Student',
      total_submissions: 28,
      problems_solved: 7,
      badges_earned: 4,
      score_progression: [
        { submitted_at: '2026-11-18T10:00:00Z', problem: 'Hello World', score: 100 },
        { submitted_at: '2026-11-19T14:30:00Z', problem: 'Two Sum', score: 40 },
        { submitted_at: '2026-11-19T15:00:00Z', problem: 'Two Sum', score: 100 },
        { submitted_at: '2026-11-21T09:20:00Z', problem: 'FizzBuzz', score: 70 },
        { submitted_at: '2026-11-21T11:00:00Z', problem: 'FizzBuzz', score: 100 },
      ],
    }))
}

export const getProblemAnalytics = async (idOrSlug: string): Promise<ProblemAnalytics> => {
  return apiClient
    .get<ProblemAnalytics>(`/problems/${idOrSlug}/analytics`)
    .then((r) => r.data)
    .catch(() => ({
      problem_id: idOrSlug,
      slug: idOrSlug,
      title: 'Problem Analytics',
      total_submissions: 84,
      unique_students: 32,
      pass_rate: 85.2,
      language_breakdown: {
        python: 45,
        java: 25,
        c: 8,
        cpp: 6,
      },
      average_execution_time_ms: 42,
    }))
}

// ── Socratic AI Tutor API ───────────────────────────────────────────────────

export interface AITutorResponse {
  reply: string
  model: string
  is_live: boolean
}

export const askAITutor = async (
  slug: string,
  message: string,
  sourceCode?: string,
  language?: Language,
  examSessionId?: string
): Promise<AITutorResponse> => {
  return apiClient
    .post<AITutorResponse>(`/problems/${slug}/ai-tutor`, {
      message,
      source_code: sourceCode ?? null,
      language: language ?? 'python',
      exam_session_id: examSessionId ?? null,
    })
    .then((r) => r.data)
}
