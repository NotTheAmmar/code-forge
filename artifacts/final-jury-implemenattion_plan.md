# Final Jury Implementation Plan — Due: November 23

**Goal:** Elevate CodeForge from a class project into a near-production platform. Ship the **proctored assessment module**, **learning module system**, **real-time WebSocket**, **security hardening**, **multi-language support**, **analytics dashboard**, **advanced grading**, **editor upgrades**, and a **cross-platform installer** — with every feature demo-ready for the jury.

**Team:** 2 developers working in parallel (Developer A: Backend, Developer B: Frontend).

---

## TA-2 Feedback Integration

The jury gave us two critical pieces of feedback:

1. **Finish the proctored assessment module** — Build the exam environment with browser lockdown, tab-switch detection, full-screen enforcement, copy/paste restriction, timed sessions, and single-session enforcement.
2. **Add real learning content** — Build a Learning Module system where instructors can create structured learning paths with theory text, embedded YouTube videos, and practice problems. Seed it with actual content.

---

## What the Final Jury Demo Should Look Like

> **Installer demo:** Run `./codeforge-setup.sh` (or the cross-platform executable) on a fresh machine → entire platform comes up. Open browser on another machine → Full platform running.

> **Learning flow:** Student opens a course → navigates to "Learn" tab → sees structured modules (e.g., "Python Basics") → reads theory content with embedded YouTube videos → solves inline practice problems → module marked complete → unlocks the next module.

> **Proctored exam flow:** Instructor creates a timed exam → Student opens the exam → Browser enters full-screen lockdown → Tab switches and copy/paste are detected and logged → Student codes solutions under time pressure → Timer expires → Auto-submit → Instructor sees exam results + anti-cheat violation log.

> **Real-time grading:** Student submits code → WebSocket pushes live status updates: `Queued → Compiling → Running Test 1/5 → Running Test 2/5 → … → Completed (100%)` — no polling lag.

> **Security demo:** Submit a fork bomb → show it being contained (pids-limit). Submit `os.system('curl ...')` → show network disabled. Submit infinite memory allocation → show OOM kill. All contained, no crash.

> **Multi-language:** Student switches between Java, Python, C, and C++ in the editor → code runs in the correct sandbox container.

> **Analytics:** Instructor opens analytics dashboard → sees per-problem pass rates (bar chart), per-student progress over time (line chart), class-wide statistics, common error patterns.

> **Advanced grading:** Instructor configures partial credit per test case (weighted), custom stdin input mode for students.

> **Infrastructure:** `docker compose ps` shows all services healthy. Grafana with live metrics. Structured JSON logs.

The jury should see:

1. **Cross-platform installer** — `./codeforge-setup.sh` or `.exe` on a fresh machine → everything running in under a minute.
2. **Learning Modules** — Instructor creates modules with text + YouTube videos → students progress through them.
3. **Proctored Exam** — Locked-down exam environment with anti-cheat logging.
4. **WebSocket** — Real-time test case results streaming in the browser.
5. **Security hardening** — Live adversarial code demo (fork bomb, network access, memory bomb) → all contained.
6. **Multi-language** — Java, Python, C, C++ all working from the same editor.
7. **Analytics dashboard** — Charts and insights for instructors.
8. **Advanced grading** — Partial credit and custom input mode.
9. **Editor upgrades** — Auto-save, keybinding options, custom stdin.
10. Clean `docker compose up` from scratch → entire platform running.
11. Architecture diagram, explain every container, volume, and network.

---

## Current State (Post TA-2) — Verified from Codebase

### ✅ What's Working
- Auth system (JWT, login/register, roles) — 28 tests passing
- Course system (create, join, invite code, members) — 34 tests passing
- Problem CRUD + bulk import — course-scoped, instructor-gated
- Lab sessions + badge engine — full CRUD, dashboard, student progress
- Python + Java sandbox execution — ephemeral containers, security profile
- Submission history + gradebook — best submission tracking, score matrix
- Frontend fully integrated — 10 pages, Axios client with auto-refresh
- Polling-based submission status (1.5s interval via `useSubmissionPoller`)
- Single-command setup script (`codeforge-setup.sh`)
- Monitoring stack (Prometheus + Grafana + cAdvisor)
- 106 backend tests passing

### 🔲 What's Stubbed / Missing
- **WebSocket** — `submissions_ws.py` is a TODO stub, frontend uses polling
- **Proctored exam module** — not started (no models, routes, or UI)
- **Learning modules** — not started (no models, routes, or UI)
- **C/C++ sandbox images** — only `sandbox/java` and `sandbox/python` exist
- **Security hardening** — basic profile exists but no `--pids-limit`, no adversarial test suite
- **Analytics dashboard** — no charts, no analytics endpoints
- **Advanced grading** — no partial credit, no custom stdin
- **Editor upgrades** — no auto-save, no keybinding options, no custom stdin panel
- **Cross-platform installer/exe** — only the bash script exists

---

## Database Schema Changes

### New Tables

```
learning_modules
├── id (PK, UUID)
├── course_id (FK → courses)
├── title (VARCHAR)                     # "Module 1: Python Basics"
├── description (TEXT, nullable)
├── order_index (INT)                   # Sequential ordering within course
├── is_published (BOOL, default=false)
├── created_by (FK → users)
├── created_at (TIMESTAMP)
```

```
learning_contents
├── id (PK, UUID)
├── module_id (FK → learning_modules)
├── content_type (ENUM: text | video | problem)
├── title (VARCHAR)                     # "What are Variables?"
├── body (TEXT, nullable)               # Markdown for text, YouTube URL for video
├── problem_id (FK → problems, nullable) # Link to existing problem for practice
├── order_index (INT)
├── created_at (TIMESTAMP)
```

```
module_progress
├── id (PK, UUID)
├── user_id (FK → users)
├── module_id (FK → learning_modules)
├── content_id (FK → learning_contents, nullable)  # Last completed content
├── is_completed (BOOL, default=false)
├── completed_at (TIMESTAMP, nullable)
├── UNIQUE(user_id, module_id)
```

```
exams
├── id (PK, UUID)
├── course_id (FK → courses)
├── title (VARCHAR)                     # "Midterm Exam — OOP"
├── description (TEXT, nullable)
├── duration_minutes (INT)              # 60, 90, 120...
├── starts_at (TIMESTAMP)
├── ends_at (TIMESTAMP)
├── is_active (BOOL, default=true)
├── fullscreen_required (BOOL, default=true)
├── tab_switch_limit (INT, default=3)   # Max tab switches before auto-flag
├── copy_paste_blocked (BOOL, default=true)
├── created_by (FK → users)
├── created_at (TIMESTAMP)
```

```
exam_problems
├── id (PK, UUID)
├── exam_id (FK → exams)
├── problem_id (FK → problems)
├── order_index (INT)
├── weight (INT, default=100)           # Points for this problem in the exam
├── UNIQUE(exam_id, problem_id)
```

```
exam_sessions
├── id (PK, UUID)
├── exam_id (FK → exams)
├── user_id (FK → users)
├── started_at (TIMESTAMP)
├── submitted_at (TIMESTAMP, nullable)  # NULL = still in progress
├── is_auto_submitted (BOOL, default=false)
├── total_score (INT, nullable)
├── UNIQUE(exam_id, user_id)            # One session per student per exam
```

```
exam_violations
├── id (PK, UUID)
├── exam_session_id (FK → exam_sessions)
├── violation_type (ENUM: tab_switch | fullscreen_exit | copy_paste | focus_loss)
├── details (TEXT, nullable)            # e.g. "Switched to tab at 14:23:05"
├── occurred_at (TIMESTAMP)
```

### Modified Tables

**`problems`** — add columns:
```
├── starter_code_c (TEXT, nullable)
├── starter_code_cpp (TEXT, nullable)
```

**`submissions`** — add column:
```
├── exam_session_id (FK → exam_sessions, nullable)
├── custom_input (TEXT, nullable)       # For "Run with custom input" mode
```

---

## New API Endpoints

### Learning Modules
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/courses/{id}/modules` | Create a learning module. | Instructor |
| `GET` | `/courses/{id}/modules` | List modules for course (with progress). | Enrolled |
| `GET` | `/modules/{id}` | Module details + all content items. | Enrolled |
| `PUT` | `/modules/{id}` | Update module metadata. | Instructor |
| `DELETE` | `/modules/{id}` | Delete module. | Instructor |
| `POST` | `/modules/{id}/contents` | Add content item (text/video/problem). | Instructor |
| `PUT` | `/contents/{id}` | Update a content item. | Instructor |
| `DELETE` | `/contents/{id}` | Delete a content item. | Instructor |
| `POST` | `/modules/{id}/complete` | Mark module as completed by student. | Student |
| `GET` | `/courses/{id}/module-progress` | Get student's progress across all modules. | Student |

### Proctored Exams
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/courses/{id}/exams` | Create an exam with problems and config. | Instructor |
| `GET` | `/courses/{id}/exams` | List exams for course. | Enrolled |
| `GET` | `/exams/{id}` | Exam details + problems (if session started). | Enrolled |
| `PUT` | `/exams/{id}` | Update exam config. | Instructor |
| `DELETE` | `/exams/{id}` | Delete exam. | Instructor |
| `POST` | `/exams/{id}/start` | Start exam session (creates `exam_sessions` row, enforces single-session). | Student |
| `POST` | `/exams/{id}/submit` | Submit entire exam (or auto-submit on timer expiry). | Student |
| `POST` | `/exam-sessions/{id}/violations` | Log an anti-cheat violation from frontend. | Student |
| `GET` | `/exams/{id}/results` | Exam results dashboard (all students + violations). | Instructor |
| `GET` | `/exams/{id}/my-result` | Student's own exam result. | Student |

### Analytics
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/courses/{id}/analytics` | Course-wide analytics (pass rates, common errors, trends). | Instructor |
| `GET` | `/courses/{id}/analytics/students/{sid}` | Per-student analytics. | Instructor |
| `GET` | `/problems/{id}/analytics` | Per-problem analytics (pass rate, avg score, error distribution). | Instructor |

### WebSocket
| Protocol | Endpoint | Description |
|---|---|---|
| `WS` | `/ws/submissions/{submission_id}` | Real-time submission status + incremental test results. |

### Custom Input
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/problems/{slug}/run-custom` | Run code with student-provided stdin (no test cases). | Student |

---

## Phase-by-Phase Plan (Parallel Developer Tracks)

### Phase 0: Pre-work (Joint — 1 hour) ✅ Completed

> *Done before splitting into parallel tracks.*

- [x] Agree on API contracts for all new endpoints (documented in `artifacts/api-contracts.md` v3.0: learning modules, exams, analytics, WebSocket protocol, custom input).
- [x] Create Alembic migration for all new tables (`learning_modules`, `learning_contents`, `module_progress`, `exams`, `exam_problems`, `exam_sessions`, `exam_violations`) + modified columns on `problems` (`starter_code_c`, `starter_code_cpp`), `test_cases` (`weight`), and `submissions` (`exam_session_id`, `custom_input`) — applied migration `9fdb9d0e7422_final_jury_schema.py`.
- [x] Build C and C++ sandbox images:
  - `sandbox/c/Dockerfile` — `gcc:13-bookworm` with non-root `runner` user.
  - `sandbox/cpp/Dockerfile` — `gcc:13-bookworm` with non-root `runner` user and `g++`.
  - Built and tagged: `codeforge-sandbox-c` and `codeforge-sandbox-cpp` (verified via container execution).
- [x] Update `.env.example`, `codeforge-setup.sh`, and `app/config.py` with sandbox pids limit and setup automation.

---

## Developer A: Backend

### Phase A1: WebSocket Real-Time Submission Updates (2-3 hours) ✅ Completed

**WebSocket Implementation (`app/websocket/submissions_ws.py`):**
- [x] Implement FastAPI WebSocket endpoint: `WS /api/v1/ws/submissions/{submission_id}` and `WS /ws/submissions/{submission_id}`.
- [x] On connect: validate submission exists, immediately stream terminal payload if already completed.
- [x] Use Redis Pub/Sub as the message bus between Celery worker and WebSocket handler:
  - Worker publishes to channel `submission:{submission_id}` after each test case completes.
  - WebSocket handler subscribes to the channel and forwards messages to the client using `pubsub.listen()` with periodic DB fallback.
- [x] Message format pushed to client (`status`, `test_progress`, `completed`).
- [x] Final message includes full results, scores, test case details, and badge awards.
- [x] Close WebSocket on terminal status.

**Worker Integration (`app/worker/tasks.py` + `app/worker/sandbox.py`):**
- [x] After each test case execution, publish incremental result to Redis Pub/Sub.
- [x] Publish status transitions: `queued → compiling → running → completed / error`.

**Route Registration (`app/main.py`):**
- [x] Add WebSocket route to FastAPI app under `/api/v1` and root.
- [x] Update Nginx config (`frontend/nginx.conf`) to proxy `ws://` connections for `/ws/` and `/api/`.
- [x] Tested with full automated test suite: 111/111 tests passed in `tests/test_websocket.py` and across all suites.

### Phase A2: C/C++ Language Support + Security Hardening (2-3 hours)

**C/C++ Sandbox:**
- [ ] Update `worker/sandbox.py` to handle `language="c"` and `language="cpp"`:
  - C: Compile with `gcc -o solution solution.c`, run `./solution`.
  - C++: Compile with `g++ -o solution solution.cpp`, run `./solution`.
  - Same security profile as Java/Python.
  - Use `codeforge-sandbox-c` / `codeforge-sandbox-cpp` images.
- [ ] Add `"c"` and `"cpp"` to the `language` enum in schemas and models.
- [ ] Update the sandbox image map in `sandbox.py`.

**Security Hardening:**
- [ ] Add `--pids-limit=64` to sandbox container creation (prevents fork bombs).
- [ ] Add `--ulimit nofile=64:64` (prevents file descriptor exhaustion).
- [ ] Enforce tmpfs size limit: `--tmpfs /tmp:size=16m,noexec,nosuid` (tighter than current 32m).
- [ ] Add adversarial test cases to the test suite (`tests/test_security.py`):
  - Fork bomb (Python: `os.fork()` loop, C: `fork()` loop) → should hit pids-limit.
  - Memory bomb (`[0] * 10**9`) → should hit memory limit.
  - Network access (`import urllib.request; urllib.request.urlopen(...)`) → should fail (network disabled).
  - File system read (`open('/etc/passwd')`) → should fail (read-only fs).
  - Infinite loop → should hit timeout.
  - Disk write abuse (write large file to `/tmp`) → should hit tmpfs size limit.

### Phase A3: Learning Modules System (2-3 hours)

**Models:**
- [ ] Create `LearningModule` model (`app/models/learning_module.py`).
- [ ] Create `LearningContent` model (`app/models/learning_content.py`).
- [ ] Create `ModuleProgress` model (`app/models/module_progress.py`).

**Schemas:**
- [ ] `ModuleCreate` (title, description, order_index).
- [ ] `ModuleResponse` (id, title, description, order_index, content_count, is_published, progress for current user).
- [ ] `ModuleDetailResponse` (includes list of contents).
- [ ] `ContentCreate` (content_type, title, body, problem_id, order_index).
- [ ] `ContentResponse`.
- [ ] `ModuleProgressResponse` (modules with completion status).

**Router (`app/routers/modules.py`):**
- [ ] Full CRUD for modules and contents (instructor-gated).
- [ ] Progress tracking endpoints (student marks content as viewed / module as complete).
- [ ] List modules with per-student progress data.

**Seed Data:**
- [ ] Seed 2-3 learning modules into the CS101 course with actual content:
  - **Module 1: "Python Basics"** — 3-4 content items:
    - Text: "What is Python?" with real introductory theory.
    - Video: Embedded YouTube link (e.g., a popular Python tutorial).
    - Text: "Variables and Data Types" with examples.
    - Practice problem: Link to `hello-world` problem.
  - **Module 2: "Control Flow"** — 3-4 content items:
    - Text: "If/Else Statements" with examples.
    - Video: YouTube link on control flow.
    - Practice problem: Link to `fizzbuzz` problem.

### Phase A4: Proctored Exam System (3-4 hours)

**Models:**
- [ ] Create `Exam` model (`app/models/exam.py`).
- [ ] Create `ExamProblem` model (association table).
- [ ] Create `ExamSession` model (`app/models/exam_session.py`).
- [ ] Create `ExamViolation` model (`app/models/exam_violation.py`).

**Schemas:**
- [ ] `ExamCreate` (title, description, duration_minutes, starts_at, ends_at, problem_ids, fullscreen_required, tab_switch_limit, copy_paste_blocked).
- [ ] `ExamResponse`, `ExamDetailResponse`.
- [ ] `ExamSessionResponse` (session state, time remaining, violations count).
- [ ] `ExamViolationCreate` (violation_type, details).
- [ ] `ExamResultResponse` (per-student results + violation summary).

**Router (`app/routers/exams.py`):**
- [ ] `POST /courses/{id}/exams` — create exam, attach problems (instructor).
- [ ] `GET /courses/{id}/exams` — list exams (enrolled).
- [ ] `GET /exams/{id}` — exam details; if student, only after session started.
- [ ] `POST /exams/{id}/start` — start exam session:
  - Enforce single session per student (`UNIQUE(exam_id, user_id)`).
  - Enforce time window (`starts_at <= now <= ends_at`).
  - Return session with problems and remaining time.
- [ ] `POST /exams/{id}/submit` — submit exam:
  - Calculate total_score from submission scores × problem weights.
  - Set `submitted_at`, prevent re-submission.
- [ ] `POST /exam-sessions/{id}/violations` — log violation from frontend.
- [ ] `GET /exams/{id}/results` — instructor: all students' results + violation counts.
- [ ] `GET /exams/{id}/my-result` — student: own result.

**Auto-submit Logic:**
- [ ] Background Celery beat task or middleware: check for expired exam sessions (started_at + duration_minutes < now AND submitted_at IS NULL) → auto-submit.

### Phase A5: Analytics + Advanced Grading + Custom Input (2-3 hours)

**Analytics (`app/routers/analytics.py`):**
- [ ] `GET /courses/{id}/analytics` — aggregate:
  - Per-problem: pass rate (%), average score, submission count, most common error type.
  - Per-student: total submissions, improvement trend (scores over time), active days.
  - Class-wide: total submissions, average pass rate, completion rate.
- [ ] `GET /problems/{id}/analytics` — detailed per-problem stats.
- [ ] Return data structured for frontend charting (arrays of `{label, value}` pairs).

**Advanced Grading:**
- [ ] Add `weight` column to `test_cases` table (default 1) — partial credit per test case.
- [ ] Update score calculation in `sandbox.py`:
  - Score = (sum of passed weights / sum of total weights) × 100, rounded.
  - Current: score = (passed_count / total_count) × 100.
- [ ] `PUT /problems/{id}` — allow setting weights per test case.

**Custom Input:**
- [ ] `POST /problems/{slug}/run-custom` — accepts `{ source_code, language, stdin }`.
- [ ] Runs code in sandbox with the student's custom stdin.
- [ ] Returns stdout, stderr, execution time — no test case comparison.
- [ ] Rate-limit to prevent abuse (max 10 custom runs per minute per user).

### Phase A6: Installer + Deployment Polish (1-2 hours)

**Cross-Platform Installer:**
- [ ] Enhance `codeforge-setup.sh` with:
  - Auto-detection of OS (Linux, macOS, WSL).
  - Docker Desktop detection on macOS/Windows.
  - Colored output with progress indicators.
- [ ] Create `codeforge-setup.ps1` (PowerShell) for native Windows support.
- [ ] Create a wrapper script/readme for creating a distributable package:
  - On Linux/Mac: `codeforge-setup.sh` is the entry point.
  - On Windows: `codeforge-setup.ps1` or a `.bat` wrapper.
  - Optionally bundle with PyInstaller or similar into a single executable for demo purposes.

**Deployment Polish:**
- [ ] Add health check endpoints for all services:
  - `/health` already exists on API — add readiness check (DB + Redis ping).
  - Add health checks in `docker-compose.yml` for `api` and `worker`.
- [ ] Add Docker Compose restart policies (`restart: unless-stopped`) for all services.
- [ ] Implement structured JSON logging (replace print-style logs with JSON formatter).
- [ ] Add backup strategy documentation for PostgreSQL volumes.

**Sandbox Image Updates:**
- [ ] Update `codeforge-setup.sh` to build C and C++ sandbox images.
- [ ] Add health verification for all 4 sandbox images in the setup script.

---

## Developer B: Frontend ✅ Completed & Built

### Phase B1: WebSocket Integration + Editor Upgrades ✅ Completed

**WebSocket Client (`hooks/useWebSocket.ts`):**
- [x] Replace `useSubmissionPoller` with `useWebSocket` hook:
  - Opens `ws://<host>/ws/submissions/{submission_id}` on submission.
  - Receives incremental test case results as they complete.
  - Updates UI in real-time: `Queued → Compiling → Running (2/5) → Completed`.
  - Falls back to polling if WebSocket connection fails.
- [x] Update `ProblemPage.tsx` to use the new WebSocket hook.
- [x] Add live progress indicator: animated progress bar showing `Running Test N/M`.

**Editor Upgrades (`ProblemPage.tsx` + `CodeEditor.tsx`):**
- [x] **Auto-save drafts:** Save editor content to `localStorage` keyed by `problem_slug + language`. Restore on page load. Clear on successful submit.
- [x] **Keybinding options:** Add a dropdown selector in the editor toolbar:
  - VS Code (default), Vim, Emacs.
  - Use Monaco's `addKeybindingRules` or `editor.updateOptions({ cursorStyle, ... })`.
- [x] **Custom stdin input panel:** New tab alongside "Test Results" and "History":
  - Textarea for student to type custom stdin.
  - "▶ Run with Custom Input" button → calls `POST /problems/{slug}/run-custom`.
  - Shows stdout and stderr output below.
- [x] **Language switcher update:** Add C and C++ to the language dropdown.
  - Load `starter_code_c` / `starter_code_cpp` from API response.
  - Monaco language mode: `c` / `cpp`.

### Phase B2: Learning Modules UI ✅ Completed

**New Pages:**
- [x] `LearnPage.tsx` (`/courses/:courseId/learn`) — module list with progress:
  - Card-based layout showing each module with title, description, content count.
  - Progress indicator per module (e.g., "3/5 items completed", progress bar).
  - Completed modules show a ✅ checkmark.
  - Sequential unlock: next module is locked until current is completed (visual lock icon, greyed out).
- [x] `ModulePage.tsx` (`/modules/:id`) — module content viewer:
  - Sidebar/stepper showing content items (text, video, problem) with completion state.
  - **Text content:** Rendered as rich Markdown (using `react-markdown` + `rehype-highlight` for code blocks).
  - **Video content:** Embedded YouTube player (`<iframe>` with responsive aspect ratio).
  - **Problem content:** "Practice this problem" card with link to `/problems/:slug` or inline embedded editor.
  - "Mark as Complete" / "Next" button at the bottom of each content item.
  - Progress bar at the top of the module.

**Instructor Module Management:**
- [x] `ModuleCreatePage.tsx` (`/courses/:courseId/modules/create`):
  - Title, description, order input.
  - Add content items: type selector (text/video/problem), title, body/URL/problem picker.
  - Drag-to-reorder content items (move up/down).
  - Publish/unpublish toggle.

**Route Updates (`App.tsx`):**
- [x] Add routes:
  - `/courses/:courseId/learn` → `LearnPage`
  - `/modules/:id` → `ModulePage`
  - `/courses/:courseId/modules/create` → `ModuleCreatePage` (instructor)

**Navigation Updates (`CoursePage.tsx`):**
- [x] Add "Learn" tab/section to course page alongside "Problems" and "Lab Sessions".
- [x] Show module count and overall progress in course card on dashboard.

### Phase B3: Proctored Exam UI ✅ Completed

**Exam Management (Instructor):**
- [x] `ExamCreatePage.tsx` (`/courses/:courseId/exams/create`):
  - Title, description, duration (minutes), start/end datetime pickers.
  - Problem picker with checkboxes (from course problems) + weight input per problem.
  - Anti-cheat config toggles: fullscreen required, tab switch limit, copy/paste blocked.
- [x] Exam list section in `CoursePage.tsx`:
  - Active exams with countdown to start/end.
  - Past exams with "View Results" link.

**Exam Environment (Student — `ExamPage.tsx`, route `/exams/:id`):**
- [x] **Pre-exam screen:** Show exam title, duration, rules, anti-cheat warnings. "Start Exam" button.
- [x] **On start:**
  - Call `POST /exams/{id}/start` → receive session + problems + remaining time.
  - Enter **full-screen mode** (`document.documentElement.requestFullscreen()`).
  - Start countdown timer (synced with server `started_at + duration_minutes`).
- [x] **Anti-cheat enforcement (client-side):**
  - **Tab switch detection:** `document.addEventListener('visibilitychange', ...)` — log each switch via `POST /exam-sessions/{id}/violations`.
  - **Full-screen exit detection:** `document.addEventListener('fullscreenchange', ...)` — warn student, log violation, re-request fullscreen.
  - **Copy/paste blocking:** `document.addEventListener('paste', e => e.preventDefault())` on the editor area. Prevent external paste; allow internal copy/paste within Monaco.
  - **Right-click disabled:** `document.addEventListener('contextmenu', e => e.preventDefault())`.
  - **Keyboard shortcut interception:** Capture `Alt+Tab`, `Cmd+Tab`, `Win` key attempts (best-effort in browser).
  - **Visual warning counter:** Show "⚠ 2/3 tab switches used" — after limit, auto-flag.
- [x] **Problem navigation:** Sidebar with problem list, click to switch. Each problem has its own Monaco editor instance + run/submit buttons.
- [x] **Timer display:** Prominent countdown timer. Last 5 minutes: turns red, pulses.
- [x] **Auto-submit:** When timer expires, automatically submit all problems. Show "Exam submitted" confirmation.
- [x] **Manual submit:** "Submit Exam" button with confirmation dialog.

**Exam Results (Instructor — `ExamResultsPage.tsx`, route `/exams/:id/results`):**
- [x] Table: Student name, total score, per-problem scores, violation count, violation details expandable.
- [x] Color-coded violation count: 0 = green, 1-2 = yellow, 3+ = red.
- [x] Click student → see their code for each problem.

**Exam Result (Student — `/exams/:id/my-result`):**
- [x] Show total score, per-problem scores, violation count (if any).

**Route Updates (`App.tsx`):**
- [x] Add routes:
  - `/courses/:courseId/exams/create` → `ExamCreatePage`
  - `/exams/:id` → `ExamPage` (student exam environment)
  - `/exams/:id/results` → `ExamResultsPage` (instructor)
  - `/exams/:id/my-result` → student result

### Phase B4: Analytics Dashboard + Advanced Grading UI ✅ Completed

**Analytics Dashboard (`AnalyticsPage.tsx`, route `/courses/:courseId/analytics`):**
- [x] **Per-problem stats (bar chart):** Problem title × pass rate (%) with SVG visual bars.
- [x] **Per-student progress (trends):** Submission activity and pass rates.
- [x] **Class-wide stats cards:** Total submissions, average pass rate, completion rate, most solved problem, hardest problem.
- [x] **Common error patterns:** Table showing most frequent error types (compile_error, timeout, runtime) with counts.
- [x] **Student leaderboard:** Top students by total score / badges earned.

**Advanced Grading UI:**
- [x] Update "Add Problem" and "Edit Problem" modals:
  - Add a "Weight" field per test case (default: 1).
  - Show how partial credit would be calculated: "Score = weighted passed / total weight × 100".
- [x] Update test results panel to show weighted scores when weights differ from 1.

**Route Updates:**
- [x] `/courses/:courseId/analytics` → `AnalyticsPage`
- [x] Link from course page ("📊 Analytics" button for instructors).

### Phase B5: UI Polish + Integration Testing ✅ Completed

- [x] Universal Header navigation (`Navbar.tsx`):
  - Global `Ctrl+K` Quick Jump Command Palette with fuzzy search across all entities.
  - Live Student ⇄ Instructor role switcher for fast demo toggling.
  - "Learn" and "Exams" links in course navigation.
  - "Analytics" link for instructors.
- [x] Dark/Light theme support across all 18 pages.
- [x] Mobile responsiveness check for all pages.
- [x] Error boundaries and loading states for all pages.
- [x] Offline & demo login shortcuts on `LoginPage.tsx` (1-click Instructor / Student demo).
- [x] Vite code splitting (`manualChunks` in `vite.config.ts`) dividing monaco, markdown, and react vendors.
- [x] Production container build verified: `docker build -t code-forge-web ./frontend` (0 errors).

---

## New Frontend Routes (Complete)

| Route | Page Component | Access | Description |
|---|---|---|---|
| `/courses/:courseId/learn` | `LearnPage.tsx` | Protected | Learning module list with progress. |
| `/modules/:id` | `ModulePage.tsx` | Protected | Module content viewer (text, video, problem). |
| `/courses/:courseId/modules/create` | `ModuleCreatePage.tsx` | Instructor | Create/edit learning modules. |
| `/courses/:courseId/exams/create` | `ExamCreatePage.tsx` | Instructor | Create proctored exam. |
| `/exams/:id` | `ExamPage.tsx` | Protected | Locked-down exam environment. |
| `/exams/:id/results` | `ExamResultsPage.tsx` | Instructor | Exam results + violation log. |
| `/exams/:id/my-result` | `ExamMyResultPage.tsx` | Student | Student's own exam result. |
| `/courses/:courseId/analytics` | `AnalyticsPage.tsx` | Instructor | Course analytics dashboard. |

---

## Coordination Points

| When | What |
|---|---|
| **After Phase 0** | Both devs aligned on API contracts + DB schema. Migration applied. Sandbox images built. |
| **After Phase A1 + B1** | WebSocket integration: backend pushes, frontend receives real-time results. Test together. |
| **After Phase A2 + B1** | C/C++ working in editor: switch language → sandbox executes → results display. |
| **After Phase A3 + B2** | Learning modules: create module with content → student views and completes → progress tracked. |
| **After Phase A4 + B3** | Proctored exam: full flow — create → start → lockdown → solve → submit → results + violations. |
| **After Phase A5 + B4** | Analytics charts populated with real data. Advanced grading weights working. |
| **After Phase A6 + B5** | Full integration test. Installer works. All pages themed. Demo rehearsal. |

---

## Joint Deliverables Checklist

### Core Platform (from TA-2 — must keep working ✅)
- [x] User registration and login (JWT auth)
- [x] Two roles: instructor and student
- [x] Course creation with auto-generated invite codes
- [x] Students join courses via invite code
- [x] Problems scoped to courses
- [x] Instructor CRUD for problems via UI + bulk import
- [x] Lab sessions + badge system
- [x] Python + Java sandbox execution
- [x] Submission history + gradebook
- [x] Single-command setup script
- [x] Monitoring stack (Prometheus + Grafana + cAdvisor)

### New for Final Jury
- [ ] **WebSocket** — real-time submission results — Frontend ✅ | Backend 📋 (Phase A1)
- [ ] **C/C++ support** — 2 sandbox images built & tested, editor switcher updated — Frontend ✅ | Backend Sandbox Execution 📋 (Phase A2)
- [ ] **Security hardening** — pids-limit, adversarial test suite, live demo — Config ✅ | Backend Sandbox Profile 📋 (Phase A2)
- [ ] **Learning Modules** — text lessons, YouTube videos, practice problems, progress tracking — Frontend ✅ | Backend API 📋 (Phase A3)
- [ ] **Proctored Exams** — fullscreen lockdown, tab-switch detection, copy/paste blocking, timed sessions, auto-submit, violation logging — Frontend ✅ | Backend API 📋 (Phase A4)
- [ ] **Analytics Dashboard** — charts (bar, line), class-wide stats, per-student trends — Frontend ✅ | Backend API 📋 (Phase A5)
- [ ] **Advanced Grading** — weighted test cases / partial credit — Frontend ✅ | Backend Scoring 📋 (Phase A5)
- [ ] **Custom Input Mode** — student types own stdin, runs code — Frontend ✅ | Backend Endpoint 📋 (Phase A5)
- [x] **Editor Upgrades** — auto-save drafts, keybinding options (VS Code/Vim/Emacs), 4-language switcher — Frontend ✅
- [ ] **Cross-Platform Installer** — bash + PowerShell scripts, enhanced setup — Setup Script Updated ✅ | Polish 📋 (Phase A6)
- [ ] **Deployment Polish** — health checks, restart policies, structured logging — Backend 📋 (Phase A6)

---

## What Success Looks Like for Final Jury Demo

1. **Installer:** `./codeforge-setup.sh` on a fresh machine → all 8+ services healthy in under a minute.
2. **Learning:** Student opens course → "Learn" tab → reads theory → watches YouTube video → solves practice problem → module complete ✅.
3. **Proctored Exam:** Instructor creates exam → Student starts → Full-screen lockdown activates → Tab switch detected and logged → Timer counting down → Submit → Instructor sees results + violations.
4. **Real-time:** Student submits code → WebSocket pushes `Running (1/5) → (2/5) → … → Completed` live in the browser.
5. **Security:** Submit fork bomb → PID limit kills it. Submit network access → blocked. Submit memory bomb → OOM. All safe.
6. **Multi-language:** Switch to C → write C code → runs in `codeforge-sandbox-c` → results.
7. **Analytics:** Instructor opens analytics → bar chart of problem pass rates → line chart of student progress.
8. **Advanced grading:** Problem with weighted test cases → partial credit score displayed.
9. **Custom input:** Student types custom stdin → runs code → sees output.
10. **Grafana** showing live infrastructure metrics during the demo.
11. **Architecture diagram** — explain every container, every volume, every network.
