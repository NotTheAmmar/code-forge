# TA-2 Implementation Plan — Due: October 19-24

**Goal:** Transform the TA-1 raw engine demo into a real, deployable platform — with users, courses, Python support, a **badge system for lab sessions**, and a **single-command installer** for setting it up on any server.

**Team:** 2 developers working in parallel.

---

## What Changed Since TA-1 (Jury Feedback)

The jury gave us two key pieces of feedback:

1. **Single executable / one-command setup:** They want a way to deploy CodeForge on a server machine easily — run one thing and it's live. Others on the network can then open the URL in their browser and use the platform. No manual Docker fiddling, no multi-step setup.

2. **Badge system for lab sessions:** Faculty should be able to run a lab session (e.g., 2-hour session on "Pointers"), assign problems under that topic, and every time a student solves a problem beyond the mandatory one, they earn **a badge**. No tiers — just one badge per extra problem. At the end of the lab, the faculty sees a dashboard of who earned how many badges — instantly visible who went above and beyond vs. who just did the bare minimum.

---

## What the TA-2 Demo Should Look Like

> Jury sees: **One script run on a server → entire platform comes up.** Open browser on another machine → Register / Login → Instructor creates a course → Students join with invite code → Instructor sets up a **lab session** with problems → Students code in Java or Python → As they solve beyond the minimum, badges appear → Faculty opens the **live lab dashboard** and sees badge counts per student. Gradebook shows cumulative scores. Grafana shows live infrastructure metrics.

The jury should see:

1. **Single-command deploy:** `./codeforge-setup.sh` on a fresh machine → everything running.
2. Instructor logs in → creates a course → generates invite code.
3. Student logs in → joins the course → sees problem list.
4. Instructor creates a **lab session** ("Pointers — Lab 3") with tagged problems and a mandatory count.
5. Student solves the mandatory problem → baseline. Solves more → earns **one badge per extra problem** (⭐).
6. Instructor opens the **Lab Dashboard** → sees a live view of all students with badge counts (e.g., "3 badges").
7. Student solves in **Python or Java** — language switcher works.
8. Instructor opens the **Gradebook** → sees Student × Problem score matrix.
9. `docker compose ps` shows all services healthy. Grafana dashboard with live metrics.
10. Show submission history — student can review past attempts.

---

## Scoping: TA-2 vs. Final Jury

We can't (and shouldn't) do everything for TA-2. Here's the split:

| Feature | TA-2 | Final Jury |
|---|---|---|
| Auth (JWT, login/register, roles) | ✅ | — |
| Course system (create, join, invite code) | ✅ | — |
| Python language support | ✅ | — |
| Lab sessions + badge system | ✅ | — |
| Instructor problem management UI (CRUD) | ✅ | — |
| Submission history | ✅ | — |
| Gradebook (instructor view) | ✅ | — |
| Single-command installer script | ✅ | — |
| Monitoring stack (Prometheus/Grafana/cAdvisor) | ✅ (wire up) | Polish dashboards |
| Real-time WebSocket (replace polling) | Defer | ✅ |
| Security hardening (fork bombs, adversarial tests) | Defer | ✅ |
| Analytics & insights dashboard (charts, trends) | Defer | ✅ |
| Advanced grading (partial credit, penalties) | Defer | ✅ |
| Custom input run mode | Defer | ✅ |
| Editor enhancements (keybindings, auto-save) | Defer | ✅ |
| C/C++ language support | Defer | ✅ (stretch) |

---

## Key New Concepts

### Lab Sessions & Badge System

This is the standout feature the jury wants to see. Here's the model:

**Lab Session:** A time-bounded event created by the instructor within a course.
- Has a title ("Lab 3 — Pointers"), date/time window, and a topic tag.
- Contains a set of problems (ordered), with a configurable **mandatory count** (e.g., "must solve at least 1").

**Badges:** Simple — **one badge per extra problem solved** beyond the mandatory count.
- If mandatory count = 1 and a student solves 4 problems → they earned **3 badges**.
- No tiers, no bronze/silver/gold — just a count. Clean and easy to understand.
- Badges are tracked per student per lab session.

**Lab Dashboard (Instructor view):**
- Live view during the lab: student name, problems solved count, badge count (⭐×N), time of last submission.
- Can see who's idle, who's crushing it.
- Sortable by badge count / problems solved.

**Student view:**
- During a lab session, the student sees a "Lab Mode" banner with the session info.
- A progress bar: "1/1 mandatory ✅ | 2 extra solved ⭐⭐"
- Badge animation when they earn one (simple, satisfying).

### Single-Command Installer

A shell script (`codeforge-setup.sh`) that:
1. Checks prerequisites (Docker, Docker Compose, port availability).
2. Generates a `.env` file with sensible defaults (random JWT secret, etc.).
3. Builds the sandbox images.
4. Runs `docker compose up -d --build`.
5. Waits for health checks to pass.
6. Runs database migrations.
7. Seeds the default admin/instructor account.
8. Prints the access URL (`http://<server-ip>:80`).

For the jury: run this on the demo machine, hand a URL to a phone/laptop on the same network → instant access.

---

## Database Schema Changes

### New Tables

```
users
├── id (PK, UUID)
├── email (VARCHAR, unique)
├── name (VARCHAR)
├── role (ENUM: instructor | student)
├── password_hash (VARCHAR)          # bcrypt
├── created_at (TIMESTAMP)
```

```
courses
├── id (PK, UUID)
├── title (VARCHAR)
├── description (TEXT, nullable)
├── created_by (FK → users)
├── invite_code (VARCHAR, unique)    # 6-char alphanumeric, auto-generated
├── created_at (TIMESTAMP)
```

```
enrollments
├── id (PK, UUID)
├── user_id (FK → users)
├── course_id (FK → courses)
├── role (ENUM: instructor | student | ta)
├── joined_at (TIMESTAMP)
├── UNIQUE(user_id, course_id)
```

```
lab_sessions
├── id (PK, UUID)
├── course_id (FK → courses)
├── title (VARCHAR)                   # "Lab 3 — Pointers"
├── description (TEXT, nullable)
├── starts_at (TIMESTAMP)
├── ends_at (TIMESTAMP)
├── mandatory_count (INT, default=1)  # How many problems must be solved as baseline
├── is_active (BOOL, default=true)
├── created_at (TIMESTAMP)
```

```
lab_session_problems
├── id (PK, UUID)
├── lab_session_id (FK → lab_sessions)
├── problem_id (FK → problems)
├── order_index (INT)
├── UNIQUE(lab_session_id, problem_id)
```

```
badges
├── id (PK, UUID)
├── user_id (FK → users)
├── lab_session_id (FK → lab_sessions)
├── problem_id (FK → problems)           # Which problem earned this badge
├── earned_at (TIMESTAMP)
├── UNIQUE(user_id, lab_session_id, problem_id)  # One badge per student per problem per lab
```

> Each badge is a single row — one per extra problem solved. To get a student's badge count for a lab, simply `COUNT(*) WHERE user_id = ? AND lab_session_id = ?`.

### Modified Tables

**`problems`** — add columns:
```
├── course_id (FK → courses)             # Scoped to a course
├── created_by (FK → users)              # Who created it
├── starter_code_python (TEXT, nullable)  # Python starter code
```

**`submissions`** — add columns:
```
├── user_id (FK → users)                          # Who submitted
├── lab_session_id (FK → lab_sessions, nullable)   # If submitted during a lab session
```

---

## New API Endpoints

### Auth
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Register (email, name, password, role). |
| `POST` | `/api/v1/auth/login` | Returns JWT access + refresh tokens. |
| `POST` | `/api/v1/auth/refresh` | Refresh an expired access token. |
| `GET` | `/api/v1/auth/me` | Get current user profile. |

### Courses
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/api/v1/courses` | Create a course (auto-generates invite code). | Instructor |
| `GET` | `/api/v1/courses` | List user's enrolled courses. | Any |
| `GET` | `/api/v1/courses/{id}` | Course details. | Enrolled |
| `POST` | `/api/v1/courses/{id}/join` | Join via invite code. | Student |
| `GET` | `/api/v1/courses/{id}/members` | List enrolled members. | Instructor |

### Problems (now course-scoped — all routes require auth)
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/api/v1/courses/{id}/problems` | Create a problem with test cases. | Instructor |
| `POST` | `/api/v1/courses/{id}/problems/bulk-import` | Bulk import problems from JSON array. | Instructor |
| `GET` | `/api/v1/courses/{id}/problems` | List problems in a course. | Enrolled |
| `GET` | `/api/v1/problems/{id}` | Problem details + visible tests + starter code. | Enrolled |
| `PUT` | `/api/v1/problems/{id}` | Update a problem. | Instructor |
| `DELETE` | `/api/v1/problems/{id}` | Delete a problem. | Instructor |

### Lab Sessions
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/api/v1/courses/{id}/labs` | Create a lab session with problem IDs. | Instructor |
| `GET` | `/api/v1/courses/{id}/labs` | List lab sessions for a course. | Enrolled |
| `GET` | `/api/v1/labs/{id}` | Lab session details + problems. | Enrolled |
| `PUT` | `/api/v1/labs/{id}` | Update a lab session. | Instructor |
| `GET` | `/api/v1/labs/{id}/dashboard` | Live lab dashboard (students, progress, badges). | Instructor |
| `GET` | `/api/v1/labs/{id}/my-progress` | Student's own progress + badge in this lab. | Student |

### Submissions (updated)
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/api/v1/problems/{id}/run` | Run code (visible tests only). | Student |
| `POST` | `/api/v1/problems/{id}/submit` | Submit for grading (all tests). | Student |
| `GET` | `/api/v1/problems/{id}/submissions` | Current user's submission history. | Student |
| `GET` | `/api/v1/submissions/{id}` | Submission details. | Owner/Instructor |

### Gradebook
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/api/v1/courses/{id}/gradebook` | Student × Problem score matrix. | Instructor |
| `GET` | `/api/v1/courses/{id}/gradebook/{student_id}` | Detailed view for one student. | Instructor |

---

## Phase-by-Phase Plan (Parallel Developer Tracks)

### Phase 0: Pre-work (Joint — 1 day) ✅

> *Done before splitting into parallel tracks.*

- [x] Agree on final API contracts (request/response JSON shapes for all new endpoints — documented in `artifiacts/api-contracts.md` and Pydantic schemas in `app/schemas/`).
- [x] Set up Alembic migration for the new schema (migration `8f615a4a5063_ta2_schema.py` applied, creating `users`, `courses`, `enrollments`, `lab_sessions`, `lab_session_problems`, `badges` tables, and modifying `problems` / `submissions`).
- [x] Create the Python sandbox image (`sandbox/python/Dockerfile` — `python:3.12-slim` with non-root user).
- [x] Build and tag: `docker build -t codeforge-sandbox-python ./sandbox/python`.
- [x] Update `.env.example` and `.env` with new variables (`JWT_SECRET_KEY`, `JWT_ALGORITHM`, etc.) and updated `app/config.py`.

---

## Developer A: Backend

### Phase A1: Auth System ✅ (2-3 days)

**Models:**
- [x] Create `User` model (`app/models/user.py`).
- [x] Create password hashing utilities (`app/services/auth_service.py`) — bcrypt via passlib.

**Schemas:**
- [x] `RegisterRequest` (email, name, password, role).
- [x] `LoginRequest` (email, password).
- [x] `TokenResponse` (access_token, refresh_token, token_type).
- [x] `UserResponse` (id, email, name, role).

**Router:**
- [x] Implement `POST /auth/register` — validate email uniqueness, hash password, create user.
- [x] Implement `POST /auth/login` — verify credentials, issue JWT tokens.
- [x] Implement `POST /auth/refresh` — validate refresh token, issue new access token.
- [x] Implement `GET /auth/me` — return current user from token.

**Middleware:**
- [x] Create `get_current_user` dependency (`app/dependencies.py`) — decodes JWT, fetches user from DB.
- [x] Create `require_role(role)` dependency — `require_instructor` checks user role, raises 403.
- [x] Create `require_enrollment(course_id)` dependency — checks user is enrolled in the course.

**Tests:** `backend/tests/test_auth.py` — 28 tests, all passing (`52 passed` total suite).

### Phase A2: Course System + Problem CRUD API ✅ (2-3 days)

**Models:**
- [x] Create `Course` model (`app/models/course.py`).
- [x] Create `Enrollment` model (`app/models/enrollment.py`).
- [x] Update `Problem` model — add `course_id`, `created_by`, `starter_code_python` columns.
- [x] Update `Submission` model — add `user_id` column.

**Schemas:**
- [x] Course schemas: `CourseCreate`, `CourseResponse`, `CourseDetailResponse`, `CourseJoinRequest`, `EnrollmentResponse`, `CourseMemberResponse`.
- [x] Updated Problem schemas: `ProblemCreate` (with test cases inline), `ProblemUpdate`, `BulkImportRequest`, `BulkImportResponse`.
- [x] Gradebook schemas: inline dict response (`problems` list + `rows` with per-student score map).

**Routers (`app/routers/courses.py`):**
- [x] `POST /courses` — create course, auto-generate 6-char invite code, auto-enroll creator as instructor.
- [x] `GET /courses` — list courses for current user (via enrollments), with member/problem counts.
- [x] `GET /courses/{id}` — course details (enrolled users only).
- [x] `POST /courses/{id}/join` — join with invite code (case-insensitive, idempotent 409).
- [x] `GET /courses/{id}/members` — list members (instructor of this course only).
- [x] `POST /courses/{id}/problems` — create problem with test cases (instructor of this course only).
- [x] `PUT /problems/{id}` — update problem, optionally replace full test case set (instructor only).
- [x] `DELETE /problems/{id}` — delete problem + cascades, returns 204 (instructor only).
- [x] Refactor `problems.py` run/submit — now require auth (`get_current_user`), use `current_user.id`.
- [x] `POST /courses/{id}/problems/bulk-import` — per-problem transactional commit; partial failures skip and report.

**Gradebook:**
- [x] `GET /courses/{id}/gradebook` — aggregates best score per (student, problem); returns `{ problems, rows }` matrix.

**Tests:** `backend/tests/test_courses.py` — 34 tests, all passing. Total suite: 86 tests.

### Phase A3: Lab Sessions + Badge Engine ✅ (2-3 days)

**Models:**
- [x] Create `LabSession` model (`app/models/lab_session.py`).
- [x] Create `LabSessionProblem` model (association table).
- [x] Create `Badge` model (`app/models/badge.py`).
- [x] Update `Submission` model — add `lab_session_id` column.

**Badge Logic (`app/services/badge_service.py`):**
- [x] After each successful submission (all tests passed) during a lab session:
  1. Count how many distinct problems the student has solved in this lab.
  2. If solved > mandatory_count → insert a badge row for the newly solved problem (if not already awarded).
  3. Each badge = one row in the `badges` table, linked to the specific problem.
- [x] This runs as a post-submission hook in the grading task (`app/worker/tasks.py`), with async support (`evaluate_badges_async`).

**Routers (`app/routers/labs.py`):**
- [x] `POST /courses/{id}/labs` — create lab session, attach problems (instructor only).
- [x] `GET /courses/{id}/labs` — list labs for course (enrolled users).
- [x] `GET /labs/{id}` — lab details + problems (enrolled users).
- [x] `PUT /labs/{id}` — update lab session metadata & problem assignments (instructor only).
- [x] `GET /labs/{id}/dashboard` — aggregate: for each enrolled student, count problems solved, badge count (extras beyond mandatory), last submission time. Sorted by badge count desc, then solve count desc.
- [x] `GET /labs/{id}/my-progress` — for the current student: problems solved list, badge count, recent badge earned, mandatory completed status.
- [x] Update the submission flow: when submitting, if there's an active lab session for this problem (or explicit `lab_session_id`), tag the submission with `lab_session_id` and trigger badge evaluation.

**Tests:** `backend/tests/test_labs.py` — 10 tests across CRUD, badge logic, and dashboards. Full suite: 91 tests passing.

### Phase A4: Python Sandbox + Submission History API ✅ (1-2 days)

**Python Execution:**
- [x] Update `worker/sandbox.py` to handle `language="python"`:
  - No compilation step — directly run `python3 Solution.py`.
  - Same container security profile as Java.
  - Use `codeforge-sandbox-python` image.
- [x] Add language detection to the grading task dispatch.

**Submission History:**
- [x] `GET /problems/{id}/submissions` — return current user's submissions for this problem, ordered by `submitted_at desc`. Include: id, language, status, score, total_cases, submitted_at (accepts problem UUID or slug).
- [x] Mark the best submission (highest score, earliest if tied).
- [x] Secure `GET /submissions/{id}` to require authentication and verify student ownership or instructor role.

**Tests:** `backend/tests/test_sandbox.py` (6 Python sandbox tests) + `backend/tests/test_submissions_history.py` (8 history & authorization tests). Full suite: 106 tests passing.

### Phase A5: Setup Script + Integration ✅ (1-2 days)

**`codeforge-setup.sh`:**
- [x] Check for Docker and Docker Compose (exit with clear error if missing).
- [x] Check port availability (80, 8000, 5432, 6379, 9090, 3000).
- [x] Generate `.env` from `.env.example` with random `JWT_SECRET_KEY`.
- [x] Build sandbox images (`codeforge-sandbox-java`, `codeforge-sandbox-python`).
- [x] Run `docker compose up -d` (with optional `--build` flag).
- [x] Wait for DB health check, then run `alembic upgrade head`.
- [x] Seed a default instructor account (`admin@codeforge.local` / `changeme`) and student (`student@codeforge.local` / `changeme`).
- [x] Seed a sample course (`CS101`) with problems (`hello-world`, `two-sum`, `reverse-string`, `fizzbuzz`) and an active lab session (`Lab 1`).
- [x] Print access URL and default credentials.
- [x] Make it idempotent (safe to re-run).

**Integration:**
- [x] Test all API endpoints via Swagger UI / live HTTP requests.
- [x] Verify the full flow: register → login → course → problem → submit Python/Java → polling → history → gradebook.
- [x] Verify lab session flow: active lab → submit during lab → badge awarded → dashboard & progress show it.
- [x] Run `codeforge-setup.sh` end-to-end; verified all 8 services healthy and 106 tests passing.

---

## Developer B: Frontend ✅ 100% Integrated

> **Integration Complete & Verified:**
> All frontend routes, state management, and API calls in `frontend/src/api/client.ts` are now directly wired to the live FastAPI backend. Mock fallbacks have been removed so live PostgreSQL data, Celery worker submissions, and badge evaluations render cleanly in the UI.

### Phase B1: Auth Pages + Route Guards ✅ Completed & Integrated

**Auth Pages:**
- [x] Create `LoginPage.tsx` — Email/password form, calls `POST /auth/login`, stores JWT in localStorage (`frontend/src/pages/LoginPage.tsx`).
- [x] Create `RegisterPage.tsx` — Built as a seamless tab mode toggle inside `LoginPage.tsx` (email, name, password, role selection).
- [x] Create `useAuth` hook — Manages token storage, exposes `user`, `login()`, `logout()`, `isAuthenticated` (exported from `frontend/src/context/AuthContext.tsx`).
- [x] Create `AuthContext` provider — Wraps app, validates `/auth/me` on mount, persists session (`frontend/src/context/AuthContext.tsx`).
- [x] Create `ProtectedRoute` component — Redirects to `/login`, preserving destination (`frontend/src/App.tsx`).

**API Client Update:**
- [x] Update Axios client to attach `Authorization: Bearer <token>` header (`frontend/src/api/client.ts`).
- [x] Add interceptor: on 401 response, automatically try to refresh token via `POST /auth/refresh`; if refresh fails, clears session (`frontend/src/api/client.ts`).
- [x] Clean error propagation: Removed mock fallback in `AuthContext.tsx` so real backend authentication errors surface properly to the user.

**Route Structure:**
- [x] `/login` → LoginPage (public)
- [x] `/` → CourseListPage (protected dashboard)
- [x] `/practice` → ProblemListPage (protected standalone practice)
- [x] `/courses/:id` → CoursePage (protected)
- [x] `/courses/:courseId/labs/create` → LabCreatePage (protected instructor)
- [x] `/courses/:courseId/gradebook` → GradebookPage (protected instructor)
- [x] `/labs/:id` → StudentLabPage (protected student lab mode)
- [x] `/labs/:id/dashboard` → LabDashboardPage (protected instructor dashboard)
- [x] `/problems/:slug` → ProblemPage (protected workspace)

### Phase B2: Course System + Dashboard UI ✅ Completed & Integrated

**Dashboard Page (`CourseListPage.tsx`):**
- [x] **Student view:** List of enrolled courses (gradient cards with join code, instructor, problem count). Join Course modal.
- [x] **Instructor view:** Course list + "Create Course" modal (title, description).
- [x] Universal `POST /api/v1/courses/join` implemented on backend to allow students to join courses directly using invite code.
- [x] Backend schemas updated with computed `join_code` and `instructor_id` so UI displays real codes and instructor references seamlessly.

**Course Page (`CoursePage.tsx`):**
- [x] Problem list for course with difficulty badges and solved status indicators.
- [x] Lab Sessions list showing Active (LIVE, countdown) and Past sections.
- [x] Invite code display with toggle.
- [x] "Copy Invite Code" button with instant visual feedback ("Copied!").
- [x] Instructor "+ Add Problem" modal with title, slug generator, difficulty, Markdown description, Python/Java starters, and dynamic test cases.
- [x] Instructor "Bulk Import" modal with JSON textarea, example template button, and import status reporting.

### Phase B3: Lab Session UI + Badge Display ✅ Completed & Integrated

**Lab Session Management (Instructor):**
- [x] `LabCreatePage.tsx` — Title, topic, starts_at, ends_at, problem picker checkboxes with mandatory toggle.
- [x] Direct mapping to backend `POST /courses/{course_id}/labs` with `{ title, description, starts_at, ends_at, mandatory_count, problem_ids }`.

**Lab Dashboard (Instructor — `LabDashboardPage.tsx`):**
- [x] Live leaderboard table: student name, solved count, badge count, last submission time.
- [x] Auto-refresh every 15 seconds + manual refresh button.
- [x] Sortable columns (by badges, mandatory solved, name, last submission).
- [x] Summary stat cards (total badges, completion rate, total students, problem count).
- [x] Direct mapping to `GET /labs/{id}/dashboard` unpacking student progress array.

**Student Lab Experience:**
- [x] "Lab Mode" banner on `StudentLabPage.tsx` and `ProblemPage.tsx` with live countdown timer.
- [x] Lab progress indicator and badge counter.
- [x] Direct mapping to `GET /labs/{id}/my-progress` combined with `GET /labs/{id}`.

**Badge Components:**
- [x] `BadgeToast`: Celebratory toast notification when student earns a badge on problem submit (`ProblemPage.tsx`).
- [x] Badge count rendering with medal emoji / styling.

### Phase B4: Python Support + Submission History + Gradebook UI ✅ Completed & Integrated

**Language Switcher:**
- [x] Language dropdown on `ProblemPage.tsx`: Java ↔ Python.
- [x] Loads language-specific starter code (`starter_code_java` or `starter_code_python`).
- [x] Monaco editor language mode switches automatically.
- [x] Selected language included in submission payload (`source_code`, `language`, `lab_session_id`).

**Submission History:**
- [x] "History" tab alongside Monaco Editor.
- [x] Table of past submissions: status, score, Run vs Submit, language, timestamp.
- [x] Best submission highlighted with star (`★`).
- [x] Submissions polled until completion, then dynamically re-fetched.

**Gradebook Page (`GradebookPage.tsx` — Instructor):**
- [x] Gradebook layout and sorting by student name, badges, and mandatory solved.
- [x] Connected directly to `GET /courses/{id}/gradebook`, mapping the backend score matrix into full student rows.

### Phase B5: UI Polish + Deployment ✅ Completed & Verified

- [x] Clean header navigation with logo, user badge, theme toggle, and logout button.
- [x] Role-based UI visibility (Instructor buttons hidden from students).
- [x] Dark / Light theme support via `ThemeContext`.
- [x] Frontend container rebuilt with production React bundle in Nginx (`code-forge-web`).
- [x] End-to-end verified across API proxy, JWT authentication, submission judge, and badge awarding.

---

## 🚨 Critical Integration Discrepancies Resolution Matrix

| Feature | Frontend Call (`client.ts`) | Backend Contract | Resolution Applied | Status |
|---|---|---|---|---|
| **Join Course** | `POST /courses/join` `{ join_code }` | Added `POST /courses/join` on backend | Accepts `{ invite_code, join_code }` | ✅ Resolved & Verified |
| **Course Fields** | `course.join_code`, `course.instructor_id` | Added `@computed_field` to Course schema | Returns `join_code` and `instructor_id` aliases | ✅ Resolved & Verified |
| **List Labs** | `GET /courses/{id}/labs` | `GET /courses/{id}/labs` | Updated client path from `/lab-sessions` | ✅ Resolved & Verified |
| **Create Lab** | `POST /courses/{id}/labs` | `POST /courses/{id}/labs` | Formats payload with `mandatory_count` | ✅ Resolved & Verified |
| **Lab Details** | `GET /labs/{id}` | `GET /labs/{id}` | Updated client path from `/lab-sessions` | ✅ Resolved & Verified |
| **Lab Dashboard**| `GET /labs/{id}/dashboard` | `GET /labs/{id}/dashboard` | Client unwraps response `.students` array | ✅ Resolved & Verified |
| **Student Progress**| `GET /labs/{id}/my-progress` | `GET /labs/{id}/my-progress` | Client combines with lab detail for full stats | ✅ Resolved & Verified |
| **Gradebook** | `GET /courses/{id}/gradebook` | Score matrix schema | Client adapts `{ problems, rows }` matrix | ✅ Resolved & Verified |
| **Problem CRUD** | `POST /courses/{id}/problems` | `POST /courses/{id}/problems` | Added "+ Add Problem" modal in `CoursePage.tsx` | ✅ Resolved & Verified |
| **Bulk Import** | `POST /courses/{id}/problems/bulk-import` | `POST /courses/{id}/problems/bulk-import` | Added "Bulk Import" modal in `CoursePage.tsx` | ✅ Resolved & Verified |

---

## Joint Deliverables Checklist Status

### Core Platform
- [x] User registration and login (JWT auth) — Backend ✅ | Frontend ✅
- [x] Two roles: instructor and student — Backend ✅ | Frontend ✅
- [x] Course creation with auto-generated invite codes — Backend ✅ | Frontend ✅
- [x] Students join courses via invite code — Backend ✅ | Frontend ✅
- [x] Problems scoped to courses — Backend ✅ | Frontend ✅
- [x] Instructor CRUD for problems via UI + bulk import — Backend ✅ | Frontend ✅

### Lab Sessions & Badges (★ Jury Feature)
- [x] Instructor creates lab sessions with time windows and problem sets — Backend ✅ | Frontend ✅
- [x] Mandatory problem count — students must solve at least N — Backend ✅ | Frontend ✅
- [x] One badge earned per extra problem solved beyond mandatory count — Backend ✅ | Frontend ✅
- [x] Live lab dashboard for instructors — student progress, badge counts (⭐) — Backend ✅ | Frontend ✅
- [x] Student sees lab mode banner, progress bar, badge notifications — Backend ✅ | Frontend ✅

### Multi-Language
- [x] Python sandbox container built and working — Backend ✅ | Frontend ✅
- [x] Language switcher (Java ↔ Python) in the editor — Backend ✅ | Frontend ✅
- [x] Starter code loaded per language — Backend ✅ | Frontend ✅
- [x] Both languages execute correctly in the sandbox — Backend ✅ | Frontend ✅

### Submission History & Gradebook
- [x] Students can view past submissions per problem — Backend ✅ | Frontend ✅
- [x] Best submission highlighted — Backend ✅ | Frontend ✅
- [x] Instructor gradebook: Student × Problem score matrix — Backend ✅ | Frontend ✅

### Deployment
- [x] `codeforge-setup.sh` — single command to deploy on a server — ✅
- [x] Others on the network can access via URL — ✅
- [x] Monitoring stack wired: Grafana dashboard with live metrics — ✅
- [x] `docker compose ps` shows all services healthy — ✅

---

## What We're NOT Building for TA-2

- ❌ Real-time WebSocket (keeping polling for now — WebSocket in final jury).
- ❌ Security hardening demo (fork bombs, adversarial tests — final jury).
- ❌ Analytics charts and trend visualizations — final jury.
- ❌ Partial credit / weighted test cases — final jury.
- ❌ Custom stdin input mode (student types own input) — final jury.
- ❌ Editor keybinding options / auto-save — final jury.
- ❌ C/C++ language support — final jury stretch.
- ❌ Plagiarism detection — final jury stretch.
- ❌ Email notifications — final jury stretch.
- ❌ Proctored exam mode — beyond semester scope.
- ❌ AI tutor — beyond semester scope.

---

## Updated Final Jury Plan Preview

After TA-2, the final jury plan should include everything deferred above, plus:
- **WebSocket** for real-time submission updates (replace polling).
- **Security hardening** with live adversarial demo.
- **Advanced grading**: partial credit, time-based scoring.
- **Analytics dashboard**: per-problem pass rates, per-student trends, class-wide stats.
- **Custom input mode**: students can type their own stdin for testing.
- **Editor upgrades**: keybindings, auto-save drafts.
- **Student leaderboard** per course.
- **Badge history page** for students (all badges earned across all labs — like an achievement wall).
- Health checks, structured logging, restart policies.
