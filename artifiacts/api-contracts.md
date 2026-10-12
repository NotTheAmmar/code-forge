# CodeForge API Contract Specification — TA-2

**Version:** 2.0 (TA-2 Milestone)  
**Base URL:** `/api/v1`  
**Authentication:** Bearer token in HTTP header `Authorization: Bearer <access_token>`

All endpoints return JSON responses. Errors use standard HTTP status codes with an `{ "detail": "message" }` payload.

---

## 1. Authentication Endpoints

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
> Note: `role` can be `"instructor"` or `"student"`. Defaults to `"student"`.

- **Response (`201 Created` - `AuthResponse`):**
```json
{
  "user": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "email": "student@university.edu",
    "name": "Jane Doe",
    "role": "student",
    "created_at": "2026-10-12T17:30:00Z"
  },
  "tokens": {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "token_type": "bearer"
  }
}
```

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
- **Response (`200 OK` - `TokenResponse`):**
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

### 1.3 Refresh Token
- **Endpoint:** `POST /api/v1/auth/refresh`
- **Auth Required:** No
- **Request Body (`RefreshRequest`):**
```json
{
  "refresh_token": "eyJhbGciOi..."
}
```
- **Response (`200 OK` - `TokenRefreshResponse`):**
```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer"
}
```

### 1.4 Current User Profile
- **Endpoint:** `GET /api/v1/auth/me`
- **Auth Required:** Yes
- **Response (`200 OK` - `UserResponse`):**
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "email": "student@university.edu",
  "name": "Jane Doe",
  "role": "student",
  "created_at": "2026-10-12T17:30:00Z"
}
```

---

## 2. Course Endpoints

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
- **Response (`201 Created` - `CourseResponse`):**
```json
{
  "id": "b1a2c3d4-0000-0000-0000-000000000001",
  "title": "CS101: Introduction to Programming",
  "description": "Fall semester introductory computer science lab course",
  "invite_code": "CS101A",
  "created_by": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "member_count": 1,
  "problem_count": 0,
  "created_at": "2026-10-12T17:30:00Z"
}
```

### 2.2 List Courses (User Enrolled / Created)
- **Endpoint:** `GET /api/v1/courses`
- **Auth Required:** Yes
- **Response (`200 OK` - `List[CourseResponse]`):**
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

### 2.3 Get Course Details
- **Endpoint:** `GET /api/v1/courses/{id}`
- **Auth Required:** Yes (must be enrolled or instructor)
- **Response (`200 OK` - `CourseDetailResponse`):**
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

### 2.4 Join Course via Invite Code
- **Endpoint:** `POST /api/v1/courses/join`
- **Auth Required:** Yes
- **Request Body (`CourseJoinRequest`):**
```json
{
  "invite_code": "CS101A"
}
```
- **Response (`200 OK` - `EnrollmentResponse`):**
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

### 2.5 List Course Members
- **Endpoint:** `GET /api/v1/courses/{id}/members`
- **Auth Required:** Yes (`instructor` only)
- **Response (`200 OK` - `List[CourseMemberResponse]`):**
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

---

## 3. Problem Endpoints (Course-Scoped, Auth Required)

### 3.1 Create Problem
- **Endpoint:** `POST /api/v1/courses/{id}/problems`
- **Auth Required:** Yes (`instructor` only)
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
- **Response (`201 Created` - `ProblemDetailResponse`):**
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
  "test_cases": [
    {
      "id": "t1a2b3c4-0000-0000-0000-000000000001",
      "label": "01",
      "input_data": "5\n1 2 3 4 5",
      "expected_output": "5 4 3 2 1",
      "is_visible": true,
      "order_index": 1
    }
  ],
  "created_at": "2026-10-12T17:30:00Z"
}
```
> Note: For students, hidden test cases (`is_visible: false`) are filtered out from the `test_cases` list.

### 3.2 Bulk Import Problems
- **Endpoint:** `POST /api/v1/courses/{id}/problems/bulk-import`
- **Auth Required:** Yes (`instructor` only)
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
      "starter_code_python": "...",
      "time_limit_sec": 10,
      "memory_limit_mb": 128,
      "test_cases": [
        {
          "label": "01",
          "input_data": "1",
          "expected_output": "1",
          "is_visible": true,
          "order_index": 1
        }
      ]
    }
  ]
}
```
- **Response (`200 OK` - `BulkImportResponse`):**
```json
{
  "imported_count": 3,
  "failed_count": 0,
  "imported_slugs": ["problem-1", "problem-2", "problem-3"],
  "errors": []
}
```

### 3.3 List Course Problems
- **Endpoint:** `GET /api/v1/courses/{id}/problems`
- **Auth Required:** Yes (enrolled in course)
- **Response (`200 OK` - `List[ProblemSummaryResponse]`):**
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

### 3.4 Get Problem by ID
- **Endpoint:** `GET /api/v1/problems/{id}`
- **Auth Required:** Yes (enrolled in the problem's course)
- **Response (`200 OK` - `ProblemDetailResponse`):**
Returns problem description, limits, starter codes for both Java and Python, and visible test cases.

### 3.5 Update Problem
- **Endpoint:** `PUT /api/v1/problems/{id}`
- **Auth Required:** Yes (`instructor` only)
- **Request Body (`ProblemUpdate`):**
Any fields from `ProblemCreate` (partial update supported).

### 3.6 Delete Problem
- **Endpoint:** `DELETE /api/v1/problems/{id}`
- **Auth Required:** Yes (`instructor` only)
- **Response (`200 OK`):**
```json
{
  "message": "Problem deleted successfully",
  "id": "c1d2e3f4-0000-0000-0000-000000000001"
}
```

---

## 4. Lab Session & Badge Endpoints

### 4.1 Create Lab Session
- **Endpoint:** `POST /api/v1/courses/{id}/labs`
- **Auth Required:** Yes (`instructor` only)
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
- **Response (`201 Created` - `LabSessionResponse`):**
```json
{
  "id": "l1a2b3c4-0000-0000-0000-000000000001",
  "course_id": "b1a2c3d4-0000-0000-0000-000000000001",
  "title": "Lab 3 — Pointers and Memory",
  "description": "2-hour lab covering pointer arithmetic and dynamic allocation",
  "starts_at": "2026-10-12T14:00:00Z",
  "ends_at": "2026-10-12T16:00:00Z",
  "mandatory_count": 1,
  "problem_count": 3,
  "is_active": true,
  "created_at": "2026-10-12T17:30:00Z"
}
```

### 4.2 List Course Labs
- **Endpoint:** `GET /api/v1/courses/{id}/labs`
- **Auth Required:** Yes (enrolled in course)
- **Response (`200 OK` - `List[LabSessionResponse]`):**
Returns all lab sessions for the course.

### 4.3 Get Lab Session Details
- **Endpoint:** `GET /api/v1/labs/{id}`
- **Auth Required:** Yes (enrolled in course)
- **Response (`200 OK` - `LabSessionDetailResponse`):**
```json
{
  "id": "l1a2b3c4-0000-0000-0000-000000000001",
  "course_id": "b1a2c3d4-0000-0000-0000-000000000001",
  "title": "Lab 3 — Pointers and Memory",
  "description": "...",
  "starts_at": "2026-10-12T14:00:00Z",
  "ends_at": "2026-10-12T16:00:00Z",
  "mandatory_count": 1,
  "is_active": true,
  "problems": [
    {
      "id": "c1d2e3f4-0000-0000-0000-000000000001",
      "slug": "pointer-basics",
      "title": "Pointer Arithmetic Basics",
      "difficulty": "medium",
      "order_index": 0
    }
  ]
}
```

### 4.4 Live Lab Dashboard (Instructor View)
- **Endpoint:** `GET /api/v1/labs/{id}/dashboard`
- **Auth Required:** Yes (`instructor` only)
- **Response (`200 OK` - `LabDashboardResponse`):**
```json
{
  "lab_id": "l1a2b3c4-0000-0000-0000-000000000001",
  "title": "Lab 3 — Pointers and Memory",
  "mandatory_count": 1,
  "total_students": 25,
  "active_students": 22,
  "total_badges_awarded": 18,
  "students": [
    {
      "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "name": "Jane Doe",
      "email": "student@university.edu",
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
      "last_submission_at": "2026-10-12T15:10:00Z"
    }
  ]
}
```

### 4.5 Student Lab Progress
- **Endpoint:** `GET /api/v1/labs/{id}/my-progress`
- **Auth Required:** Yes (`student`)
- **Response (`200 OK` - `StudentLabProgressResponse`):**
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

---

## 5. Execution & Submission Endpoints

### 5.1 Run Code (Visible Test Cases Only)
- **Endpoint:** `POST /api/v1/problems/{id}/run`
- **Auth Required:** Yes
- **Request Body (`RunRequest`):**
```json
{
  "source_code": "print('hello')",
  "language": "python"
}
```
> Supported `language`: `"java"` | `"python"`.

- **Response (`202 Accepted` - `SubmissionCreated`):**
```json
{
  "submission_id": "s1a2b3c4-0000-0000-0000-000000000001",
  "status": "queued"
}
```

### 5.2 Submit Code (Full Grade + Lab Session Tagging)
- **Endpoint:** `POST /api/v1/problems/{id}/submit`
- **Auth Required:** Yes
- **Request Body (`SubmitRequest`):**
```json
{
  "source_code": "def solve():\n    return 42",
  "language": "python",
  "lab_session_id": "l1a2b3c4-0000-0000-0000-000000000001"
}
```
- **Response (`202 Accepted` - `SubmissionCreated`):**
```json
{
  "submission_id": "s1a2b3c4-0000-0000-0000-000000000002",
  "status": "queued"
}
```

### 5.3 Poll Submission Status
- **Endpoint:** `GET /api/v1/submissions/{id}`
- **Auth Required:** Yes (submission owner or course instructor)
- **Response (`200 OK` - `SubmissionResponse`):**
```json
{
  "id": "s1a2b3c4-0000-0000-0000-000000000002",
  "problem_id": "c1d2e3f4-0000-0000-0000-000000000001",
  "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "language": "python",
  "source_code": "...",
  "status": "completed",
  "is_full_submit": true,
  "score": 100,
  "total_cases": 4,
  "passed_cases": 4,
  "execution_time_ms": 112,
  "results": [
    {
      "test_case_id": "t1a2b3c4-0000-0000-0000-000000000001",
      "label": "01",
      "is_visible": true,
      "passed": true,
      "actual_output": "42",
      "expected_output": "42",
      "error": null,
      "execution_time_ms": 28
    },
    {
      "test_case_id": "t1a2b3c4-0000-0000-0000-000000000002",
      "label": "02",
      "is_visible": false,
      "passed": true,
      "actual_output": null,
      "expected_output": null,
      "error": null,
      "execution_time_ms": 30
    }
  ],
  "badge_awarded": true,
  "new_badge_count": 2,
  "submitted_at": "2026-10-12T15:42:10Z"
}
```

### 5.4 Get User Problem Submissions History
- **Endpoint:** `GET /api/v1/problems/{id}/submissions`
- **Auth Required:** Yes
- **Response (`200 OK` - `List[SubmissionSummaryResponse]`):**
```json
[
  {
    "id": "s1a2b3c4-0000-0000-0000-000000000002",
    "language": "python",
    "status": "completed",
    "score": 100,
    "passed_cases": 4,
    "total_cases": 4,
    "is_best": true,
    "submitted_at": "2026-10-12T15:42:10Z"
  },
  {
    "id": "s1a2b3c4-0000-0000-0000-000000000001",
    "language": "python",
    "status": "completed",
    "score": 50,
    "passed_cases": 2,
    "total_cases": 4,
    "is_best": false,
    "submitted_at": "2026-10-12T15:30:00Z"
  }
]
```

---

## 6. Gradebook Endpoints

### 6.1 Course Gradebook Matrix
- **Endpoint:** `GET /api/v1/courses/{id}/gradebook`
- **Auth Required:** Yes (`instructor` only)
- **Response (`200 OK` - `GradebookResponse`):**
```json
{
  "course_id": "b1a2c3d4-0000-0000-0000-000000000001",
  "problems": [
    {
      "id": "c1d2e3f4-0000-0000-0000-000000000001",
      "slug": "pointer-basics",
      "title": "Pointer Arithmetic Basics",
      "total_cases": 4
    }
  ],
  "students": [
    {
      "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "name": "Jane Doe",
      "email": "student@university.edu",
      "scores": {
        "c1d2e3f4-0000-0000-0000-000000000001": {
          "score": 100,
          "passed_cases": 4,
          "total_cases": 4,
          "submission_id": "s1a2b3c4-0000-0000-0000-000000000002",
          "submitted_at": "2026-10-12T15:42:10Z"
        }
      }
    }
  ]
}
```

### 6.2 Detailed Student Submissions in Course
- **Endpoint:** `GET /api/v1/courses/{id}/gradebook/{student_id}`
- **Auth Required:** Yes (`instructor` only)
- **Response (`200 OK` - `StudentGradebookDetailResponse`):**
Returns all submissions and problem history for that specific student in this course.
