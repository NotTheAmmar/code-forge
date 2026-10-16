# CodeForge API Contract Specification — TA-2

**Version:** 2.4 (TA-2 Milestone — Phase A1 to A5 complete)
**Base URL:** `/api/v1`
**Authentication:** Bearer token in HTTP header `Authorization: Bearer <access_token>`

All endpoints return JSON responses. Errors use standard HTTP status codes with an `{ "detail": "message" }` payload.

> **Implementation status key:** ✅ Implemented & tested (all Developer A backend phases A1–A5 complete)

---

## 1. Authentication Endpoints ✅

### 1.1 Register
- **Endpoint:** `POST /api/v1/auth/register`
- **Auth Required:** No
- **Request Body (`RegisterRequest`):**
```json
{
  "email": "student@university.edu",
  "name": "Jane Doe",
  "password": "SecurePassword123",
  "role": "student"
}
```
> `role` can be `"instructor"` or `"student"`. Defaults to `"student"`. Password min length: 6.

- **Response (`201 Created` — `TokenResponse`):**
```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "user": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "email": "student@university.edu",
    "name": "Jane Doe",
    "role": "student",
    "created_at": "2026-10-12T17:30:00Z"
  }
}
```
- **Errors:** `409` — email already registered. `422` — validation failure.

### 1.2 Login
- **Endpoint:** `POST /api/v1/auth/login`
- **Auth Required:** No
- **Request Body (`LoginRequest`):**
```json
{
  "email": "student@university.edu",
  "password": "SecurePassword123"
}
```
- **Response (`200 OK` — `TokenResponse`):** *(same shape as 1.1)*
- **Errors:** `401` — invalid email or password (same message for both — prevents account enumeration).

### 1.3 Refresh Token
- **Endpoint:** `POST /api/v1/auth/refresh`
- **Auth Required:** No
- **Request Body (`RefreshRequest`):**
```json
{
  "refresh_token": "eyJhbGciOi..."
}
```
- **Response (`200 OK` — `TokenRefreshResponse`):**
```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer"
}
```
- **Errors:** `401` — expired or invalid refresh token. Sending an access token here also returns 401.

### 1.4 Current User Profile
- **Endpoint:** `GET /api/v1/auth/me`
- **Auth Required:** Yes
- **Response (`200 OK` — `UserResponse`):**
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "email": "student@university.edu",
  "name": "Jane Doe",
  "role": "student",
  "created_at": "2026-10-12T17:30:00Z"
}
```
- **Errors:** `403` — no token provided. `401` — invalid/expired token.

---

## 2. Course Endpoints ✅

### 2.1 Create Course
- **Endpoint:** `POST /api/v1/courses`
- **Auth Required:** Yes (`instructor` only)
- **Request Body (`CourseCreate`):**
```json
{
  "title": "CS101: Introduction to Programming",
  "description": "Fall semester introductory computer science lab course"
}
```
- **Response (`201 Created` — `CourseResponse`):**
```json
{
  "id": "b1a2c3d4-0000-0000-0000-000000000001",
  "title": "CS101: Introduction to Programming",
  "description": "Fall semester introductory computer science lab course",
  "invite_code": "CS101A",
  "created_by": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "role": "instructor",
  "member_count": 1,
  "problem_count": 0,
  "created_at": "2026-10-12T17:30:00Z"
}
```
> Creator is automatically enrolled as instructor. `invite_code` is 6 uppercase alphanumeric characters.
- **Errors:** `403` — user is not an instructor.

### 2.2 List Courses (Enrolled / Created)
- **Endpoint:** `GET /api/v1/courses`
- **Auth Required:** Yes
- **Response (`200 OK` — `List[CourseResponse]`):**
```json
[
  {
    "id": "b1a2c3d4-0000-0000-0000-000000000001",
    "title": "CS101: Introduction to Programming",
    "description": "Fall semester introductory computer science lab course",
    "invite_code": "CS101A",
    "created_by": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "role": "instructor",
    "member_count": 35,
    "problem_count": 12,
    "created_at": "2026-10-12T17:30:00Z"
  }
]
```
> Returns only courses the current user is enrolled in. Empty list if not enrolled in anything.

### 2.3 Get Course Details
- **Endpoint:** `GET /api/v1/courses/{course_id}`
- **Auth Required:** Yes (must be enrolled)
- **Response (`200 OK` — `CourseDetailResponse`):**
```json
{
  "id": "b1a2c3d4-0000-0000-0000-000000000001",
  "title": "CS101: Introduction to Programming",
  "description": "Fall semester introductory computer science lab course",
  "invite_code": "CS101A",
  "created_by": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "user_role": "student",
  "member_count": 35,
  "created_at": "2026-10-12T17:30:00Z"
}
```
- **Errors:** `403` — not enrolled. `404` — course not found.

### 2.4 Join Course via Invite Code
- **Endpoint:** `POST /api/v1/courses/{course_id}/join`
- **Auth Required:** Yes
- **Request Body (`CourseJoinRequest`):**
```json
{
  "invite_code": "CS101A"
}
```
- **Response (`201 Created` — `EnrollmentResponse`):**
```json
{
  "id": "e1f2a3b4-0000-0000-0000-000000000001",
  "course_id": "b1a2c3d4-0000-0000-0000-000000000001",
  "course_title": "CS101: Introduction to Programming",
  "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "role": "student",
  "joined_at": "2026-10-12T17:35:00Z"
}
```
> Invite code matching is case-insensitive.
- **Errors:** `400` — wrong invite code. `404` — course not found. `409` — already enrolled.

### 2.5 List Course Members
- **Endpoint:** `GET /api/v1/courses/{course_id}/members`
- **Auth Required:** Yes (must be instructor **of this course**)
- **Response (`200 OK` — `List[CourseMemberResponse]`):**
```json
[
  {
    "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "Jane Doe",
    "email": "student@university.edu",
    "role": "student",
    "joined_at": "2026-10-12T17:35:00Z"
  }
]
```
- **Errors:** `403` — not enrolled or not an instructor of this course.

---

## 3. Problem Endpoints (Course-Scoped) ✅

### 3.1 Create Problem
- **Endpoint:** `POST /api/v1/courses/{course_id}/problems`
- **Auth Required:** Yes (must be instructor of this course)
- **Request Body (`ProblemCreate`):**
```json
{
  "slug": "pointer-basics",
  "title": "Pointer Arithmetic Basics",
  "description": "## Problem Statement\nImplement a function that reverses an array...",
  "difficulty": "medium",
  "starter_code_java": "public class Solution {\n  public static void main(String[] args) {\n  }\n}",
  "starter_code_python": "import sys\n\ndef main():\n    pass\n\nif __name__ == '__main__':\n    main()",
  "time_limit_sec": 5,
  "memory_limit_mb": 128,
  "test_cases": [
    {
      "label": "01",
      "input_data": "5\n1 2 3 4 5",
      "expected_output": "5 4 3 2 1",
      "is_visible": true,
      "order_index": 1
    },
    {
      "label": "02",
      "input_data": "1\n99",
      "expected_output": "99",
      "is_visible": false,
      "order_index": 2
    }
  ]
}
```
> `difficulty`: `"easy"` | `"medium"` | `"hard"`. `slug` must be unique across all problems.
- **Response (`201 Created` — `ProblemDetail`):**
```json
{
  "id": "c1d2e3f4-0000-0000-0000-000000000001",
  "course_id": "b1a2c3d4-0000-0000-0000-000000000001",
  "slug": "pointer-basics",
  "title": "Pointer Arithmetic Basics",
  "description": "## Problem Statement\n...",
  "difficulty": "medium",
  "starter_code_java": "...",
  "starter_code_python": "...",
  "time_limit_sec": 5,
  "memory_limit_mb": 128,
  "created_at": "2026-10-12T17:30:00Z",
  "test_cases": [
    {
      "id": "t1a2b3c4-0000-0000-0000-000000000001",
      "label": "01",
      "input_data": "5\n1 2 3 4 5",
      "expected_output": "5 4 3 2 1",
      "is_visible": true,
      "order_index": 1
    }
  ]
}
```
- **Errors:** `403` — not enrolled or not instructor. `409` — slug already exists.

### 3.2 Bulk Import Problems
- **Endpoint:** `POST /api/v1/courses/{course_id}/problems/bulk-import`
- **Auth Required:** Yes (instructor of this course)
- **Request Body (`BulkImportRequest`):**
```json
{
  "problems": [
    {
      "slug": "problem-1",
      "title": "Problem 1",
      "description": "Description...",
      "difficulty": "easy",
      "starter_code_java": "...",
      "time_limit_sec": 10,
      "memory_limit_mb": 128,
      "test_cases": [
        { "label": "01", "input_data": "1", "expected_output": "1", "is_visible": true, "order_index": 1 }
      ]
    }
  ]
}
```
- **Response (`201 Created` — `BulkImportResponse`):**
```json
{
  "imported_count": 2,
  "failed_count": 1,
  "imported_slugs": ["problem-1", "problem-2"],
  "errors": ["problem-3: A problem with slug 'problem-3' already exists."]
}
```
> Import is per-problem transactional — failures are skipped and reported; successful ones are committed individually.

### 3.3 List Course Problems
- **Endpoint:** `GET /api/v1/courses/{course_id}/problems`
- **Auth Required:** Yes (enrolled in course)
- **Response (`200 OK` — `List[ProblemSummary]`):**
```json
[
  {
    "id": "c1d2e3f4-0000-0000-0000-000000000001",
    "course_id": "b1a2c3d4-0000-0000-0000-000000000001",
    "slug": "pointer-basics",
    "title": "Pointer Arithmetic Basics",
    "difficulty": "medium",
    "time_limit_sec": 5,
    "memory_limit_mb": 128,
    "created_at": "2026-10-12T17:30:00Z"
  }
]
```

### 3.4 Get Problem Detail
- **Endpoint:** `GET /api/v1/courses/{course_id}/problems/{problem_id}`
- **Auth Required:** Yes (enrolled in the course)
- **Response (`200 OK` — `ProblemDetail`):** Full detail including test cases (same shape as 3.1 response).
- **Errors:** `403` — not enrolled. `404` — problem not found in this course.

### 3.5 Update Problem
- **Endpoint:** `PUT /api/v1/problems/{problem_id}`
- **Auth Required:** Yes (instructor of the problem's course)
- **Request Body (`ProblemUpdate`):** All fields optional (partial update):
```json
{
  "title": "Updated Title",
  "description": "New description",
  "difficulty": "hard",
  "starter_code_java": "...",
  "starter_code_python": "...",
  "time_limit_sec": 10,
  "memory_limit_mb": 256,
  "test_cases": [
    { "label": "01", "input_data": "x", "expected_output": "y", "is_visible": true, "order_index": 0 }
  ]
}
```
> If `test_cases` is provided, it **fully replaces** the existing test case set.
- **Response (`200 OK` — `ProblemDetail`):** Updated problem with refreshed test cases.
- **Errors:** `403` — not instructor. `404` — problem not found.

### 3.6 Delete Problem
- **Endpoint:** `DELETE /api/v1/problems/{problem_id}`
- **Auth Required:** Yes (instructor of the problem's course)
- **Response:** `204 No Content`
> Cascades to test cases and submissions.
- **Errors:** `403` — not instructor. `404` — problem not found.

---

## 4. Legacy Problem Endpoints (Public — Backward Compat)

> These endpoints are kept for backward compatibility with existing tests. New frontend code should use the course-scoped endpoints above.

### 4.1 List All Problems (Public)
- **Endpoint:** `GET /api/v1/problems`
- **Auth Required:** No
- **Response (`200 OK`):** `List[ProblemSummary]` — all problems across all courses.

### 4.2 Get Problem by Slug (Public)
- **Endpoint:** `GET /api/v1/problems/{slug}`
- **Auth Required:** No
- **Response (`200 OK`):** `ProblemDetail` — full detail with all test cases.

---

## 5. Gradebook ✅

### 5.1 Course Gradebook Matrix
- **Endpoint:** `GET /api/v1/courses/{course_id}/gradebook`
- **Auth Required:** Yes (instructor of this course)
- **Response (`200 OK`):**
```json
{
  "problems": [
    {
      "id": "c1d2e3f4-0000-0000-0000-000000000001",
      "slug": "pointer-basics",
      "title": "Pointer Arithmetic Basics"
    }
  ],
  "rows": [
    {
      "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "name": "Jane Doe",
      "email": "student@university.edu",
      "scores": {
        "c1d2e3f4-0000-0000-0000-000000000001": 100
      }
    },
    {
      "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa7",
      "name": "John Smith",
      "email": "john@university.edu",
      "scores": {
        "c1d2e3f4-0000-0000-0000-000000000001": null
      }
    }
  ]
}
```
> `scores` maps `problem_id → best score (0–100)`. `null` means no full submission yet.
- **Errors:** `403` — not instructor of this course.

---

## 6. Execution & Submission Endpoints ✅

### 6.1 Run Code (Visible Test Cases Only)
- **Endpoint:** `POST /api/v1/problems/{slug}/run`
- **Auth Required:** Yes
- **Request Body (`RunRequest`):**
```json
{
  "source_code": "print('hello')",
  "language": "python"
}
```
> Supported `language`: `"java"` | `"python"`.

- **Response (`202 Accepted` — `SubmissionCreated`):**
```json
{
  "submission_id": "s1a2b3c4-0000-0000-0000-000000000001"
}
```

### 6.2 Submit Code (Full Grade)
- **Endpoint:** `POST /api/v1/problems/{slug}/submit`
- **Auth Required:** Yes
- **Request Body (`SubmitRequest`):**
```json
{
  "source_code": "print('hello')",
  "language": "python",
  "lab_session_id": "l1a2b3c4-0000-0000-0000-000000000001"
}
```
> Supported `language`: `"java"` | `"python"`. `lab_session_id` is optional. If omitted, the server checks if the problem belongs to a course with a currently active lab session (`starts_at <= now <= ends_at` or `is_active=True`), auto-tagging the submission to award badges.
- **Response (`202 Accepted` — `SubmissionCreated`):** *(same shape as run)*
> Runs against ALL test cases (visible + hidden). Score is persisted, counts toward gradebook, and triggers badge evaluation if solved during a lab session.

### 6.3 Poll Submission Status
- **Endpoint:** `GET /api/v1/submissions/{id}`
- **Auth Required:** Yes (student owner or instructor)
- **Response (`200 OK` — `SubmissionResponse`):**
```json
{
  "id": "s1a2b3c4-0000-0000-0000-000000000002",
  "problem_id": "c1d2e3f4-0000-0000-0000-000000000001",
  "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "lab_session_id": "l1a2b3c4-0000-0000-0000-000000000001",
  "language": "python",
  "status": "completed",
  "score": 100,
  "total_cases": 4,
  "passed_cases": 4,
  "execution_time_ms": 112,
  "badge_awarded": true,
  "new_badge_count": 2,
  "results_json": [
    {
      "test_case_id": "t1a2b3c4-0000-0000-0000-000000000001",
      "label": "01",
      "is_visible": true,
      "passed": true,
      "actual_output": "42",
      "expected_output": "42",
      "error": null,
      "execution_time_ms": 28
    }
  ],
  "submitted_at": "2026-10-12T15:42:10Z"
}
```
> `badge_awarded` indicates if a new badge was unlocked by this specific submission. `new_badge_count` contains the student's updated total badge count in this lab session. Frontend polls this every 1.5s until `status` is not `"queued"` or `"running"`.
- **Errors:** `401` — unauthenticated. `403` — forbidden (another student's submission). `404` — submission not found.

### 6.4 Submission History
- **Endpoint:** `GET /api/v1/problems/{id_or_slug}/submissions`
- **Auth Required:** Yes
- **Parameters:** `id_or_slug` — Problem UUID or URL slug
- **Response (`200 OK` — `list[SubmissionSummaryResponse]`):**
```json
[
  {
    "id": "s1a2b3c4-0000-0000-0000-000000000003",
    "language": "python",
    "status": "completed",
    "score": 100,
    "passed_cases": 4,
    "total_cases": 4,
    "is_full_submit": true,
    "is_best": false,
    "submitted_at": "2026-10-12T16:00:00Z"
  },
  {
    "id": "s1a2b3c4-0000-0000-0000-000000000002",
    "language": "python",
    "status": "completed",
    "score": 100,
    "passed_cases": 4,
    "total_cases": 4,
    "is_full_submit": true,
    "is_best": true,
    "submitted_at": "2026-10-12T15:42:10Z"
  },
  {
    "id": "s1a2b3c4-0000-0000-0000-000000000001",
    "language": "java",
    "status": "completed",
    "score": 75,
    "passed_cases": 3,
    "total_cases": 4,
    "is_full_submit": true,
    "is_best": false,
    "submitted_at": "2026-10-12T15:20:00Z"
  }
]
```
> Returns the authenticated user's past submissions for this problem, ordered by `submitted_at DESC`. The best submission (highest score, earliest if tied) has `is_best: true`.
- **Errors:** `401` — unauthenticated. `404` — problem not found.

---

## 7. Lab Session & Badge Endpoints ✅

### 7.1 Create Lab Session
- **Endpoint:** `POST /api/v1/courses/{course_id}/labs`
- **Auth Required:** Yes (course instructor)
- **Request Body (`LabSessionCreate`):**
```json
{
  "title": "Lab 3 — Pointers and Memory",
  "description": "2-hour lab covering pointer arithmetic and dynamic allocation",
  "starts_at": "2026-10-12T14:00:00Z",
  "ends_at": "2026-10-12T16:00:00Z",
  "mandatory_count": 1,
  "problem_ids": [
    "c1d2e3f4-0000-0000-0000-000000000001",
    "c1d2e3f4-0000-0000-0000-000000000002",
    "c1d2e3f4-0000-0000-0000-000000000003"
  ]
}
```
- **Response (`201 Created` — `LabSessionResponse`):**
```json
{
  "id": "l1a2b3c4-0000-0000-0000-000000000001",
  "course_id": "b1c2d3e4-0000-0000-0000-000000000001",
  "title": "Lab 3 — Pointers and Memory",
  "description": "2-hour lab covering pointer arithmetic and dynamic allocation",
  "starts_at": "2026-10-12T14:00:00Z",
  "ends_at": "2026-10-12T16:00:00Z",
  "mandatory_count": 1,
  "problem_count": 3,
  "is_active": true,
  "created_at": "2026-10-12T13:30:00Z"
}
```
- **Errors:** `400` — problem not in course. `403` — not course instructor.

### 7.2 List Course Labs
- **Endpoint:** `GET /api/v1/courses/{course_id}/labs`
- **Auth Required:** Yes (enrolled in course)
- **Response (`200 OK` — `list[LabSessionResponse]`):**
```json
[
  {
    "id": "l1a2b3c4-0000-0000-0000-000000000001",
    "course_id": "b1c2d3e4-0000-0000-0000-000000000001",
    "title": "Lab 3 — Pointers and Memory",
    "description": "2-hour lab covering pointer arithmetic and dynamic allocation",
    "starts_at": "2026-10-12T14:00:00Z",
    "ends_at": "2026-10-12T16:00:00Z",
    "mandatory_count": 1,
    "problem_count": 3,
    "is_active": true,
    "created_at": "2026-10-12T13:30:00Z"
  }
]
```
- **Errors:** `403` — not enrolled.

### 7.3 Get Lab Session Details
- **Endpoint:** `GET /api/v1/labs/{lab_id}`
- **Auth Required:** Yes (enrolled in course)
- **Response (`200 OK` — `LabSessionDetailResponse`):**
```json
{
  "id": "l1a2b3c4-0000-0000-0000-000000000001",
  "course_id": "b1c2d3e4-0000-0000-0000-000000000001",
  "title": "Lab 3 — Pointers and Memory",
  "description": "2-hour lab covering pointer arithmetic and dynamic allocation",
  "starts_at": "2026-10-12T14:00:00Z",
  "ends_at": "2026-10-12T16:00:00Z",
  "mandatory_count": 1,
  "is_active": true,
  "problems": [
    {
      "id": "c1d2e3f4-0000-0000-0000-000000000001",
      "slug": "reverse-string",
      "title": "Reverse a String",
      "difficulty": "easy",
      "order_index": 0
    },
    {
      "id": "c1d2e3f4-0000-0000-0000-000000000002",
      "slug": "pointer-swap",
      "title": "Pointer Swap",
      "difficulty": "medium",
      "order_index": 1
    }
  ],
  "created_at": "2026-10-12T13:30:00Z"
}
```
- **Errors:** `403` — not enrolled. `404` — lab not found.

### 7.4 Update Lab Session
- **Endpoint:** `PUT /api/v1/labs/{lab_id}`
- **Auth Required:** Yes (course instructor)
- **Request Body (`LabSessionUpdate`):**
```json
{
  "title": "Lab 3 — Pointers and Memory (Extended)",
  "ends_at": "2026-10-12T17:00:00Z",
  "mandatory_count": 2,
  "is_active": true,
  "problem_ids": [
    "c1d2e3f4-0000-0000-0000-000000000001",
    "c1d2e3f4-0000-0000-0000-000000000002",
    "c1d2e3f4-0000-0000-0000-000000000003"
  ]
}
```
- **Response (`200 OK` — `LabSessionDetailResponse`):** *(same shape as 7.3)*
- **Errors:** `400` — problem not in course. `403` — not instructor. `404` — lab not found.

### 7.5 Live Lab Dashboard (Instructor)
- **Endpoint:** `GET /api/v1/labs/{lab_id}/dashboard`
- **Auth Required:** Yes (course instructor)
- **Response (`200 OK` — `LabDashboardResponse`):**
```json
{
  "lab_id": "l1a2b3c4-0000-0000-0000-000000000001",
  "title": "Lab 3 — Pointers and Memory",
  "mandatory_count": 1,
  "total_students": 25,
  "active_students": 18,
  "total_badges_awarded": 14,
  "students": [
    {
      "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "name": "Jane Doe",
      "email": "jane@university.edu",
      "problems_solved": 3,
      "mandatory_completed": true,
      "badge_count": 2,
      "last_submission_at": "2026-10-12T15:42:10Z"
    },
    {
      "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa7",
      "name": "John Smith",
      "email": "john@university.edu",
      "problems_solved": 1,
      "mandatory_completed": true,
      "badge_count": 0,
      "last_submission_at": "2026-10-12T14:35:00Z"
    }
  ]
}
```
> Sorted by `badge_count DESC, problems_solved DESC, name ASC`.
- **Errors:** `403` — not course instructor. `404` — lab not found.

### 7.6 Student Lab Progress
- **Endpoint:** `GET /api/v1/labs/{lab_id}/my-progress`
- **Auth Required:** Yes (enrolled in course)
- **Response (`200 OK` — `StudentLabProgressResponse`):**
```json
{
  "lab_id": "l1a2b3c4-0000-0000-0000-000000000001",
  "mandatory_count": 1,
  "problems_solved_count": 3,
  "mandatory_completed": true,
  "badge_count": 2,
  "solved_problem_ids": [
    "c1d2e3f4-0000-0000-0000-000000000001",
    "c1d2e3f4-0000-0000-0000-000000000002",
    "c1d2e3f4-0000-0000-0000-000000000003"
  ],
  "recent_badge_earned": {
    "problem_id": "c1d2e3f4-0000-0000-0000-000000000003",
    "earned_at": "2026-10-12T15:42:10Z"
  }
}
```
- **Errors:** `403` — not enrolled. `404` — lab not found.

---

## Error Reference

| Status | Meaning |
|---|---|
| `400` | Bad request (wrong invite code, invalid input) |
| `401` | Unauthenticated (missing/expired/invalid token) |
| `403` | Forbidden (not enrolled, wrong role) |
| `404` | Resource not found |
| `409` | Conflict (duplicate email, duplicate slug, already enrolled) |
| `422` | Validation error (Pydantic — field missing or out of range) |
| `500` | Server error |

All error responses have the shape: `{ "detail": "human-readable message" }`
