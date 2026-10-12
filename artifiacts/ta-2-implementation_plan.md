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

### Phase A1: Auth System (2-3 days)

**Models:**
- [ ] Create `User` model (`app/models/user.py`).
- [ ] Create password hashing utilities (`app/services/auth_service.py`) — bcrypt.

**Schemas:**
- [ ] `RegisterRequest` (email, name, password, role).
- [ ] `LoginRequest` (email, password).
- [ ] `TokenResponse` (access_token, refresh_token, token_type).
- [ ] `UserResponse` (id, email, name, role).

**Router:**
- [ ] Implement `POST /auth/register` — validate email uniqueness, hash password, create user.
- [ ] Implement `POST /auth/login` — verify credentials, issue JWT tokens.
- [ ] Implement `POST /auth/refresh` — validate refresh token, issue new access token.
- [ ] Implement `GET /auth/me` — return current user from token.

**Middleware:**
- [ ] Create `get_current_user` dependency (`app/dependencies.py`) — decodes JWT, fetches user from DB.
- [ ] Create `require_role(role)` dependency — checks user role.
- [ ] Create `require_enrollment(course_id)` dependency — checks user is enrolled in the course.

### Phase A2: Course System + Problem CRUD API (2-3 days)

**Models:**
- [ ] Create `Course` model (`app/models/course.py`).
- [ ] Create `Enrollment` model (`app/models/enrollment.py`).
- [ ] Update `Problem` model — add `course_id`, `created_by`, `starter_code_python` columns.
- [ ] Update `Submission` model — add `user_id` column.

**Schemas:**
- [ ] Course schemas: `CourseCreate`, `CourseResponse`, `JoinRequest`.
- [ ] Updated Problem schemas: `ProblemCreate` (with test cases inline), `ProblemUpdate`.
- [ ] Gradebook schemas: `GradebookEntry`, `GradebookResponse`.

**Routers:**
- [ ] `POST /courses` — create course, auto-generate 6-char invite code, auto-enroll creator as instructor.
- [ ] `GET /courses` — list courses for current user (via enrollments).
- [ ] `GET /courses/{id}` — course details (enrolled users only).
- [ ] `POST /courses/{id}/join` — join with invite code.
- [ ] `GET /courses/{id}/members` — list members (instructor only).
- [ ] `POST /courses/{id}/problems` — create problem with test cases (instructor only).
- [ ] `PUT /problems/{id}` — update problem (instructor only).
- [ ] `DELETE /problems/{id}` — delete problem + test cases (instructor only).
- [ ] Refactor existing problem list endpoint to be course-scoped (all routes require auth — no anonymous access).
- [ ] `POST /courses/{id}/problems/bulk-import` — accept a JSON array of problems (title, description, difficulty, starter codes, test cases) to quickly load a batch. Useful for seeding a course with a prepared problem set.

**Gradebook:**
- [ ] `GET /courses/{id}/gradebook` — query all submissions for course problems, pivot into Student × Problem matrix with best scores.

### Phase A3: Lab Sessions + Badge Engine (2-3 days)

**Models:**
- [ ] Create `LabSession` model (`app/models/lab_session.py`).
- [ ] Create `LabSessionProblem` model (association table).
- [ ] Create `Badge` model (`app/models/badge.py`).
- [ ] Update `Submission` model — add `lab_session_id` column.

**Badge Logic (`app/services/badge_service.py`):**
- [ ] After each successful submission (all tests passed) during a lab session:
  1. Count how many distinct problems the student has solved in this lab.
  2. If solved > mandatory_count → insert a badge row for the newly solved problem (if not already awarded).
  3. Each badge = one row in the `badges` table, linked to the specific problem.
- [ ] This runs as a post-submission hook in the grading task.

**Routers:**
- [ ] `POST /courses/{id}/labs` — create lab session, attach problems.
- [ ] `GET /courses/{id}/labs` — list labs for course.
- [ ] `GET /labs/{id}` — lab details + problems.
- [ ] `PUT /labs/{id}` — update lab session.
- [ ] `GET /labs/{id}/dashboard` — aggregate: for each enrolled student, count problems solved, badge count (extras beyond mandatory), last submission time. Sorted by badge count desc, then solve count desc.
- [ ] `GET /labs/{id}/my-progress` — for the current student: problems solved list, badge count, problems remaining.
- [ ] Update the submission flow: when submitting, if there's an active lab session for this problem, tag the submission with `lab_session_id` and trigger badge evaluation.

### Phase A4: Python Sandbox + Submission History API (1-2 days)

**Python Execution:**
- [ ] Update `worker/sandbox.py` to handle `language="python"`:
  - No compilation step — directly run `python3 Solution.py`.
  - Same container security profile as Java.
  - Use `codeforge-sandbox-python` image.
- [ ] Add language detection to the grading task dispatch.

**Submission History:**
- [ ] `GET /problems/{id}/submissions` — return current user's submissions for this problem, ordered by `submitted_at desc`. Include: id, language, status, score, total_cases, submitted_at.
- [ ] Mark the best submission (highest score, earliest if tied).

### Phase A5: Setup Script + Integration (1-2 days)

**`codeforge-setup.sh`:**
- [ ] Check for Docker and Docker Compose (exit with clear error if missing).
- [ ] Check port availability (80, 8000, 5432, 6379, 9090, 3000).
- [ ] Generate `.env` from `.env.example` with random `JWT_SECRET_KEY`.
- [ ] Build sandbox images (`codeforge-sandbox-java`, `codeforge-sandbox-python`).
- [ ] Run `docker compose up -d --build`.
- [ ] Wait for DB health check, then run `docker compose exec api alembic upgrade head`.
- [ ] Seed a default instructor account (admin@codeforge.local / changeme).
- [ ] Seed a sample course with a few problems via the bulk import API (so the demo isn't empty on first launch).
- [ ] Print access URL and default credentials.
- [ ] Make it idempotent (safe to re-run).

**Integration:**
- [ ] Test all API endpoints via Swagger UI.
- [ ] Verify the full flow: register → create course → join → create problem → submit Java → submit Python → see results → check gradebook.
- [ ] Verify lab session flow: create lab → submit during lab → badge awarded → dashboard shows it.
- [ ] Run `codeforge-setup.sh` from scratch on a clean environment.

---

## Developer B: Frontend

### Phase B1: Auth Pages + Route Guards (2-3 days)

**Auth Pages:**
- [ ] Create `LoginPage.tsx` — email/password form, calls `POST /auth/login`, stores JWT in localStorage.
- [ ] Create `RegisterPage.tsx` — email/name/password/role form, calls `POST /auth/register`, auto-login on success.
- [ ] Create `useAuth` hook (`hooks/useAuth.ts`) — manages token storage, provides `user`, `login()`, `logout()`, `isAuthenticated`.
- [ ] Create `AuthContext` provider — wraps the app, fetches `/auth/me` on mount.
- [ ] Create `ProtectedRoute` component — redirects to `/login` if not authenticated.

**API Client Update:**
- [ ] Update Axios client to attach `Authorization: Bearer <token>` header.
- [ ] Add interceptor: on 401 response, try to refresh token; if refresh fails, redirect to login.

**Route Structure:**
- [ ] `/login` → LoginPage
- [ ] `/register` → RegisterPage
- [ ] `/dashboard` → DashboardPage (protected)
- [ ] `/courses/:id` → CoursePage (protected)
- [ ] `/courses/:id/labs/:labId` → LabPage (protected)
- [ ] `/problems/:id` → ProblemPage (protected, updated)
- [ ] `/courses/:id/gradebook` → GradebookPage (protected, instructor only)

### Phase B2: Course System + Dashboard UI (2-3 days)

**Dashboard Page (`DashboardPage.tsx`):**
- [ ] **Student view:** List of enrolled courses (cards with title, invite code, problem count). Button to join a course (modal with invite code input).
- [ ] **Instructor view:** Same list + "Create Course" button (modal form: title, description). Each course card shows member count.

**Course Page (`CoursePage.tsx`):**
- [ ] Problem list for this course (reuse/adapt existing `ProblemListPage` component).
- [ ] Instructor sees: "+ Add Problem" button, edit/delete actions per problem.
- [ ] Lab Sessions section: list of labs with status (upcoming / active / ended).
- [ ] Invite code display with copy button.
- [ ] Members tab (instructor only): list of enrolled students.

**Problem Creation/Edit UI (Instructor):**
- [ ] `ProblemFormModal.tsx` — form with:
  - Title, description (markdown textarea with preview).
  - Difficulty selector (easy/medium/hard).
  - Starter code editors for Java and Python (two Monaco editors or tabs).
  - Test cases: add/remove rows with input textarea + expected output textarea + visible checkbox.
  - Time limit and memory limit inputs.
- [ ] Submit calls `POST /courses/{id}/problems` or `PUT /problems/{id}`.
- [ ] "Bulk Import" button → upload a JSON file with an array of problems (title, description, difficulty, starter codes, test cases). Calls `POST /courses/{id}/problems/bulk-import`. Shows a progress/result summary.

### Phase B3: Lab Session UI + Badge Display (2-3 days)

**Lab Session Management (Instructor):**
- [ ] `LabSessionFormModal.tsx` — create/edit a lab session:
  - Title, description.
  - Start time and end time (date-time pickers).
  - Select problems from the course's problem list (checkboxes, drag to reorder).
  - Mandatory count (number input, default 1).
- [ ] Lab session cards on the course page showing status: 🟡 Upcoming, 🟢 Active, ⚫ Ended.

**Lab Dashboard (Instructor — `LabDashboardPage.tsx`):**
- [ ] Table: Student Name | Problems Solved | Badge Count (⭐) | Last Submission Time.
- [ ] Badge count column shows the number of extra problems solved as stars (e.g., "⭐⭐⭐" or "3 badges").
- [ ] Sortable columns. Color-coded rows (more badges = more highlighted).
- [ ] Auto-refresh every 15 seconds during active labs (simple polling — WebSocket deferred to final jury).
- [ ] Summary stats at top: total students, average solved, total badges awarded.

**Student Lab Experience:**
- [ ] When a student opens a problem that belongs to an active lab session, show a "Lab Mode" banner:
  - Lab title, time remaining, their progress ("2/4 solved | ⭐⭐ 2 badges").
- [ ] After solving a problem beyond mandatory, show a celebratory toast notification with ⭐.
- [ ] Lab progress card on the course page showing their current standing.

**Badge Components:**
- [ ] `BadgeIcon.tsx` — renders ⭐ with appropriate styling and count.
- [ ] `BadgeToast.tsx` — animated toast that shows when a new badge is earned.
- [ ] `LabProgressBar.tsx` — visual progress indicator for the lab.

### Phase B4: Python Support + Submission History + Gradebook UI (2-3 days)

**Language Switcher:**
- [ ] Add language dropdown on the ProblemPage: Java ↔ Python.
- [ ] When switching, load the corresponding starter code (`starter_code_java` or `starter_code_python`).
- [ ] Monaco editor language mode switches accordingly.
- [ ] Store selected language in submission payload.

**Submission History:**
- [ ] Add a "History" tab/panel on the ProblemPage.
- [ ] Shows list of past submissions: timestamp, language, score, status.
- [ ] Click a submission → loads its code into a read-only viewer and shows its test results.
- [ ] "Best" submission highlighted with a star icon.

**Gradebook Page (`GradebookPage.tsx` — Instructor):**
- [ ] Table: rows = students, columns = problems.
- [ ] Each cell shows the best score (e.g., "3/5") with color coding (green if 100%, yellow if partial, red if 0/failed).
- [ ] Click a cell → modal showing the student's best submission code + test results.
- [ ] "Export CSV" button (stretch — generate client-side CSV download).

### Phase B5: UI Polish + Deployment (1-2 days)

- [ ] Proper navbar with: logo, navigation links, user name, logout button.
- [ ] Role-based navigation: instructor sees "Create Course" and "Gradebook", student doesn't.
- [ ] Toast notifications for all actions (course created, problem saved, joined course, badge earned, etc.).
- [ ] Loading skeletons for all data-fetching pages.
- [ ] Error states: network errors, 403 forbidden, 404 not found.
- [ ] Responsive layout: works on tablets (lab setting — students on various devices).
- [ ] Update Nginx config if any new routes need proxying.
- [ ] Full end-to-end testing through Docker Compose.

---

## Coordination Points

| When | What |
|---|---|
| **Phase 0** | Joint: agree on API contracts, run migration, build Python sandbox image. |
| **After A1 + B1** | First integration: frontend auth flow connects to live backend auth API. |
| **After A2 + B2** | Course system integration: create course, join, see problems in the UI. |
| **After A3 + B3** | Lab session integration: create lab, student submits during lab, badge appears on dashboard. |
| **After A4 + B4** | Python support + submission history working end-to-end. Language switcher + history panel. |
| **A5 + B5** | Joint: run `codeforge-setup.sh` from scratch, full end-to-end testing, UI polish pass. |

---

## Monitoring Stack Wiring (Joint — done during integration)

The monitoring containers (Prometheus, Grafana, cAdvisor) already exist in `docker-compose.yml` from TA-1 but aren't properly wired. During TA-2:

- [ ] Add a `/health` endpoint to the API (returns service status, DB connectivity, Redis connectivity).
- [ ] Configure Prometheus to scrape the API's `/metrics` endpoint (add `prometheus_fastapi_instrumentator` to backend).
- [ ] Configure Grafana datasource provisioning (auto-connect to Prometheus on startup).
- [ ] Create a basic Grafana dashboard (JSON provisioning) showing:
  - Container CPU/memory (from cAdvisor).
  - API request count and latency.
  - Submission count over time.
- [ ] Verify Grafana is accessible at `http://<server>:3000` with pre-loaded dashboard.

---

## TA-2 Deliverables Checklist

### Core Platform
- [ ] User registration and login (JWT auth).
- [ ] Two roles: instructor and student.
- [ ] Course creation with auto-generated invite codes.
- [ ] Students join courses via invite code.
- [ ] Problems scoped to courses.
- [ ] Instructor CRUD for problems via the UI + bulk import (JSON upload) for quick batch loading.

### Lab Sessions & Badges (★ Jury Feature)
- [ ] Instructor creates lab sessions with time windows and problem sets.
- [ ] Mandatory problem count — students must solve at least N.
- [ ] One badge earned per extra problem solved beyond mandatory count.
- [ ] Live lab dashboard for instructors — student progress, badge counts (⭐), sortable.
- [ ] Student sees lab mode banner, progress bar, badge notifications.

### Multi-Language
- [ ] Python sandbox container built and working.
- [ ] Language switcher (Java ↔ Python) in the editor.
- [ ] Starter code loaded per language.
- [ ] Both languages execute correctly in the sandbox.

### Submission History & Gradebook
- [ ] Students can view past submissions per problem.
- [ ] Best submission highlighted.
- [ ] Instructor gradebook: Student × Problem score matrix.

### Deployment
- [ ] `codeforge-setup.sh` — single command to deploy on a server.
- [ ] Others on the network can access via URL.
- [ ] Monitoring stack wired: Grafana dashboard with live metrics.
- [ ] `docker compose ps` shows all services healthy.

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
