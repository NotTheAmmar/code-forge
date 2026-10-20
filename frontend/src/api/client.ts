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
}

export interface ProblemDetail extends ProblemSummary {
  description: string
  starter_code_java: string
  starter_code_python: string | null
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

export type Language = 'java' | 'python'

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

export interface CourseResponse {
  id: string
  title: string
  description: string
  join_code: string
  instructor_id: string
  instructor_name?: string
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

// ── Mock Course / Lab Data ────────────────────────────────────────────────────

const MOCK_COURSES: CourseResponse[] = [
  {
    id: 'course-1',
    title: 'Data Structures & Algorithms',
    description: 'Learn fundamental data structures and algorithms with hands-on coding exercises in Java and Python.',
    join_code: 'DSA2024',
    instructor_id: 'mock-instructor-1',
    instructor_name: 'Admin Instructor',
    created_at: '2024-09-01T00:00:00Z',
  },
  {
    id: 'course-2',
    title: 'Introduction to Programming',
    description: 'A beginner-friendly course covering basic programming concepts using Java and Python.',
    join_code: 'INTRO101',
    instructor_id: 'mock-instructor-1',
    instructor_name: 'Admin Instructor',
    created_at: '2024-09-15T00:00:00Z',
  },
]

const MOCK_LAB_SESSIONS: LabSessionDetail[] = [
  {
    id: 'lab-1',
    course_id: 'course-1',
    title: 'Lab 1: Arrays & Strings',
    topic: 'Arrays',
    starts_at: new Date(Date.now() - 3600000).toISOString(),
    ends_at: new Date(Date.now() + 3600000).toISOString(),
    is_active: true,
    problem_count: 3,
    mandatory_count: 1,
    problems: [
      { problem_id: 'two-sum-id', problem_slug: 'two-sum', problem_title: 'Two Sum', is_mandatory: true, order_index: 1, difficulty: 'easy' },
      { problem_id: 'hello-world-id', problem_slug: 'hello-world', problem_title: 'Hello World', is_mandatory: false, order_index: 2, difficulty: 'easy' },
      { problem_id: 'fizzbuzz-id', problem_slug: 'fizzbuzz', problem_title: 'FizzBuzz', is_mandatory: false, order_index: 3, difficulty: 'easy' },
    ],
  },
  {
    id: 'lab-2',
    course_id: 'course-1',
    title: 'Lab 2: Sorting Algorithms',
    topic: 'Sorting',
    starts_at: '2024-10-01T10:00:00Z',
    ends_at: '2024-10-01T12:00:00Z',
    is_active: false,
    problem_count: 2,
    mandatory_count: 1,
    problems: [
      { problem_id: 'fizzbuzz-id', problem_slug: 'fizzbuzz', problem_title: 'FizzBuzz', is_mandatory: true, order_index: 1, difficulty: 'easy' },
      { problem_id: 'hello-world-id', problem_slug: 'hello-world', problem_title: 'Hello World', is_mandatory: false, order_index: 2, difficulty: 'easy' },
    ],
  },
]

// ── Course API Functions ──────────────────────────────────────────────────────

export const getCourses = (): Promise<CourseResponse[]> =>
  apiClient.get<CourseResponse[]>('/courses').then((r) => r.data)
    .catch(() => { console.warn('[Mock] courses'); return MOCK_COURSES })

export const getCourse = (id: string): Promise<CourseResponse> =>
  apiClient.get<CourseResponse>(`/courses/${id}`).then((r) => r.data)
    .catch(() => {
      const c = MOCK_COURSES.find((c) => c.id === id)
      if (!c) throw new Error('Course not found')
      return c
    })

export const createCourse = (data: { title: string; description: string }): Promise<CourseResponse> =>
  apiClient.post<CourseResponse>('/courses', data).then((r) => r.data)
    .catch(() => {
      const c: CourseResponse = {
        id: 'course-' + Math.random().toString(36).substring(2, 8),
        ...data,
        join_code: Math.random().toString(36).substring(2, 8).toUpperCase(),
        instructor_id: 'mock-instructor-1',
        instructor_name: 'Admin Instructor',
        created_at: new Date().toISOString(),
      }
      MOCK_COURSES.push(c)
      return c
    })

export const joinCourse = (joinCode: string): Promise<CourseResponse> =>
  apiClient.post<CourseResponse>('/courses/join', { join_code: joinCode }).then((r) => r.data)
    .catch(() => {
      const c = MOCK_COURSES.find((c) => c.join_code.toLowerCase() === joinCode.toLowerCase())
      if (!c) throw new Error('Invalid join code')
      return c
    })

export const getCourseProblems = (courseId: string): Promise<ProblemSummary[]> =>
  apiClient.get<ProblemSummary[]>(`/courses/${courseId}/problems`).then((r) => r.data)
    .catch(() => {
      console.warn('[Mock] course problems')
      return MOCK_PROBLEMS.map(({ id, slug, title, difficulty, time_limit_sec, memory_limit_mb, created_at }) => ({
        id, slug, title, difficulty, course_id: courseId, time_limit_sec, memory_limit_mb, created_at,
      }))
    })

// ── Lab Session API Functions ─────────────────────────────────────────────────

export const getCourseLabs = (courseId: string): Promise<LabSession[]> =>
  apiClient.get<LabSession[]>(`/courses/${courseId}/lab-sessions`).then((r) => r.data)
    .catch(() => {
      console.warn('[Mock] course labs')
      return MOCK_LAB_SESSIONS.filter((l) => l.course_id === courseId)
    })

export const getLabSession = (id: string): Promise<LabSessionDetail> =>
  apiClient.get<LabSessionDetail>(`/lab-sessions/${id}`).then((r) => r.data)
    .catch(() => {
      const l = MOCK_LAB_SESSIONS.find((l) => l.id === id)
      if (!l) throw new Error('Lab session not found')
      return l
    })

export const createLabSession = (
  courseId: string,
  data: { title: string; topic: string; starts_at: string; ends_at: string; problem_ids: { problem_id: string; is_mandatory: boolean }[] }
): Promise<LabSessionDetail> =>
  apiClient.post<LabSessionDetail>(`/courses/${courseId}/lab-sessions`, data).then((r) => r.data)
    .catch(() => {
      const lab: LabSessionDetail = {
        id: 'lab-' + Math.random().toString(36).substring(2, 8),
        course_id: courseId,
        title: data.title,
        topic: data.topic,
        starts_at: data.starts_at,
        ends_at: data.ends_at,
        is_active: new Date(data.starts_at) <= new Date() && new Date() <= new Date(data.ends_at),
        problem_count: data.problem_ids.length,
        mandatory_count: data.problem_ids.filter((p) => p.is_mandatory).length,
        problems: data.problem_ids.map((p, i) => {
          const mp = MOCK_PROBLEMS.find((mp) => mp.id === p.problem_id)
          return {
            problem_id: p.problem_id,
            problem_slug: mp?.slug ?? 'unknown',
            problem_title: mp?.title ?? 'Unknown Problem',
            is_mandatory: p.is_mandatory,
            order_index: i + 1,
            difficulty: mp?.difficulty ?? 'easy',
          }
        }),
      }
      MOCK_LAB_SESSIONS.push(lab)
      return lab
    })

export const getLabDashboard = (labId: string): Promise<StudentLabProgress[]> =>
  apiClient.get<StudentLabProgress[]>(`/lab-sessions/${labId}/dashboard`).then((r) => r.data)
    .catch(() => {
      console.warn('[Mock] lab dashboard')
      return [
        { user_id: 's1', user_name: 'Alice Johnson', user_email: 'alice@example.com', mandatory_solved: 1, mandatory_total: 1, extra_solved: 2, badges_earned: 2, last_submission_at: new Date().toISOString() },
        { user_id: 's2', user_name: 'Bob Smith', user_email: 'bob@example.com', mandatory_solved: 1, mandatory_total: 1, extra_solved: 1, badges_earned: 1, last_submission_at: new Date(Date.now() - 600000).toISOString() },
        { user_id: 's3', user_name: 'Charlie Brown', user_email: 'charlie@example.com', mandatory_solved: 0, mandatory_total: 1, extra_solved: 0, badges_earned: 0, last_submission_at: null },
        { user_id: 's4', user_name: 'Diana Prince', user_email: 'diana@example.com', mandatory_solved: 1, mandatory_total: 1, extra_solved: 2, badges_earned: 2, last_submission_at: new Date(Date.now() - 300000).toISOString() },
        { user_id: 's5', user_name: 'Eve Adams', user_email: 'eve@example.com', mandatory_solved: 1, mandatory_total: 1, extra_solved: 0, badges_earned: 0, last_submission_at: new Date(Date.now() - 1200000).toISOString() },
      ]
    })

export const getMyLabProgress = (labId: string): Promise<MyLabProgress> =>
  apiClient.get<MyLabProgress>(`/lab-sessions/${labId}/my-progress`).then((r) => r.data)
    .catch(() => {
      const lab = MOCK_LAB_SESSIONS.find((l) => l.id === labId)
      if (!lab) throw new Error('Lab not found')
      return {
        lab_session_id: lab.id,
        mandatory_solved: 1,
        mandatory_total: lab.mandatory_count,
        extra_solved: 1,
        badges_earned: 1,
        problems: lab.problems.map((p) => ({
          problem_id: p.problem_id,
          problem_slug: p.problem_slug,
          problem_title: p.problem_title,
          is_mandatory: p.is_mandatory,
          is_solved: p.order_index <= 2,
          best_score: p.order_index <= 2 ? 100 : null,
        })),
      }
    })

// ── Gradebook API ─────────────────────────────────────────────────────────────

export const getGradebook = (courseId: string): Promise<GradebookRow[]> =>
  apiClient.get<GradebookRow[]>(`/courses/${courseId}/gradebook`).then((r) => r.data)
    .catch(() => {
      console.warn('[Mock] gradebook')
      const labs = MOCK_LAB_SESSIONS.filter((l) => l.course_id === courseId)
      const makeLR = (solved: number[], badges: number[]): LabGradeResult[] =>
        labs.map((l, i) => ({ lab_session_id: l.id, lab_title: l.title, mandatory_solved: solved[i] ?? 0, mandatory_total: l.mandatory_count, badges_earned: badges[i] ?? 0 }))
      return [
        { user_id: 's1', user_name: 'Alice Johnson', user_email: 'alice@example.com', lab_results: makeLR([1, 1], [2, 1]), total_badges: 3, total_mandatory_solved: 2, total_mandatory: 2 },
        { user_id: 's2', user_name: 'Bob Smith', user_email: 'bob@example.com', lab_results: makeLR([1, 0], [1, 0]), total_badges: 1, total_mandatory_solved: 1, total_mandatory: 2 },
        { user_id: 's3', user_name: 'Charlie Brown', user_email: 'charlie@example.com', lab_results: makeLR([0, 0], [0, 0]), total_badges: 0, total_mandatory_solved: 0, total_mandatory: 2 },
        { user_id: 's4', user_name: 'Diana Prince', user_email: 'diana@example.com', lab_results: makeLR([1, 1], [2, 1]), total_badges: 3, total_mandatory_solved: 2, total_mandatory: 2 },
        { user_id: 's5', user_name: 'Eve Adams', user_email: 'eve@example.com', lab_results: makeLR([1, 1], [0, 0]), total_badges: 0, total_mandatory_solved: 2, total_mandatory: 2 },
      ]
    })



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
