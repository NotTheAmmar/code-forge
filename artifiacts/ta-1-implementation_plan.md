# TA-1 Implementation Plan — Due: September 2

**Goal:** A working end-to-end demo of the core pipeline — open a problem, write Java code in the browser, execute it in a Docker sandbox, and see test case results. No authentication, no course management. Just the raw engine working.

**Team:** 2 developers working in parallel.

---

## What the TA-1 Demo Should Look Like

> Open browser → See a coding problem → Write Java code in Monaco Editor → Click "Run" → Code executes inside an ephemeral Docker container → Output compared against test cases → Results displayed (✅ Passed / ❌ Failed per test case with score)

The jury should see:
- Multiple containers running via `docker compose up` (web, api, worker, redis, db — all visible in `docker ps`).
- A clean coding interface in the browser.
- Live code execution with real-time results.
- `docker ps` showing ephemeral sandbox containers spin up and get destroyed during a run.

---

## Problem Definition Format

Problems, starter code, and test cases are defined as **YAML files** in a `problems/` directory. A CLI loader script reads these files and inserts/updates them into the database. This is version-controllable, easy to author, and avoids manual database manipulation.

### Directory Structure
```
problems/
├── hello-world/
│   ├── problem.yaml        # Problem metadata + starter code
│   ├── tests/
│   │   ├── 01.in           # Test case 1 input (stdin)
│   │   ├── 01.out          # Test case 1 expected output (stdout)
│   │   ├── 02.in
│   │   ├── 02.out
│   │   ├── 03.in           # Hidden test case
│   │   └── 03.out
│   └── description.md      # Problem statement (rich markdown)
├── two-sum/
│   ├── problem.yaml
│   ├── tests/
│   │   ├── 01.in
│   │   ├── 01.out
│   │   └── ...
│   └── description.md
└── fizzbuzz/
    ├── ...
```

### `problem.yaml` Format
```yaml
title: "Two Sum"
difficulty: easy          # easy | medium | hard
time_limit_sec: 10
memory_limit_mb: 128

# Which test cases are visible to the student (by filename prefix)
visible_tests: ["01", "02"]
# All others (03, 04, ...) are hidden — student sees only pass/fail

starter_code:
  java: |
    import java.util.Scanner;

    public class Solution {
        public static void main(String[] args) {
            Scanner sc = new Scanner(System.in);
            // Your code here
        }
    }
```

### `description.md` Format
Standard markdown with the problem statement:
```markdown
## Two Sum

Given an array of integers `nums` and an integer `target`, return the
indices of the two numbers such that they add up to `target`.

### Input
- First line: integer `n` (size of array)
- Second line: `n` space-separated integers
- Third line: integer `target`

### Output
- Two space-separated indices (0-indexed)

### Constraints
- 2 ≤ n ≤ 10⁴
- -10⁹ ≤ nums[i] ≤ 10⁹

### Example
**Input:**
```
4
2 7 11 15
9
```
**Output:**
```
0 1
```
```

### Test Case Files
- `XX.in` — raw stdin input fed to the program.
- `XX.out` — expected stdout output (whitespace-normalized during comparison).
- Numbered sequentially: `01`, `02`, `03`, ...
- Visible/hidden is controlled by the `visible_tests` list in `problem.yaml`.

### CLI Loader
```bash
# Load all problems from the problems/ directory into the database
python manage.py load-problems ./problems/

# Load a single problem
python manage.py load-problems ./problems/two-sum/

# Re-running is idempotent — updates existing problems, adds new ones
```

---

## Phase 0: Project Setup ✅

> *Done before the two developers start building.*

- [x] Initialize Git repository with `.gitignore`, `README.md`.
- [x] Create the project directory structure (as defined in technical-details.md).
- [x] Scaffold `docker-compose.yml` with all service definitions (even if some are stubs).
- [x] Scaffold the frontend: `npm create vite@latest` with React + TypeScript template.
- [x] Scaffold the backend: FastAPI project skeleton with `main.py`, `config.py`, folder structure.
- [x] Create sandbox Dockerfile (`sandbox/java/Dockerfile`) with JDK, non-root user.
- [x] Build and tag the sandbox image: `docker build -t codeforge-sandbox-java ./sandbox/java`.
- [x] Set up `.env.example` with all environment variable placeholders.
- [x] Verify `docker compose up -d` brings up all containers without errors (even if they do nothing yet).
- [x] Create 2-3 sample problem YAML files in `problems/` directory (hello-world, two-sum, fizzbuzz).
- [ ] Basic deployment pipeline setup (if deploying to a server). *(Deferred — not needed for TA-1 demo)*

---

## Developer A: Backend

### Phase A1: Database + Problem Loader

**Database Models (SQLAlchemy)**

Only the tables needed for TA-1 — no users, no courses, no auth:

```
problems
├── id (PK, UUID)
├── slug (VARCHAR, unique)       # e.g. "two-sum" — matches folder name
├── title (VARCHAR)
├── description (TEXT)           # Markdown content from description.md
├── difficulty (ENUM)            # easy | medium | hard
├── starter_code_java (TEXT)     # Template code shown in editor
├── time_limit_sec (INT)         # Execution timeout (default: 10)
├── memory_limit_mb (INT)        # Container memory cap (default: 128)
├── created_at (TIMESTAMP)
```

```
test_cases
├── id (PK, UUID)
├── problem_id (FK → problems)
├── label (VARCHAR)              # e.g. "01", "02" — from filename
├── input_data (TEXT)            # Contents of XX.in
├── expected_output (TEXT)       # Contents of XX.out
├── is_visible (BOOL)           # true if label is in visible_tests
├── order_index (INT)           # Numerical order from label
```

```
submissions
├── id (PK, UUID)
├── problem_id (FK → problems)
├── language (VARCHAR)           # "java"
├── source_code (TEXT)
├── status (VARCHAR)             # queued → running → completed / error / timeout
├── score (INT)
├── total_cases (INT)
├── passed_cases (INT)
├── results_json (JSONB)         # Per-test-case results array
├── execution_time_ms (INT)
├── submitted_at (TIMESTAMP)
```

**Tasks:**
- [x] Define SQLAlchemy models for `problems`, `test_cases`, `submissions`. *(Done: `app/models/problem.py`, `test_case.py`, `submission.py`)*
- [ ] Set up Alembic and create the initial migration. *(env.py updated with model imports — migration pending DB boot)*
- [x] Implement the **problem loader CLI** (`manage.py load-problems`):
  - Scans the `problems/` directory for subdirectories.
  - For each: reads `problem.yaml`, `description.md`, and all `tests/*.in` + `tests/*.out` pairs.
  - Inserts into the database (upserts by slug — idempotent).
  - Validates: every `.in` has a matching `.out`, `visible_tests` entries exist, required YAML fields present.
- [x] Set up database session management (`db.py`) with async SQLAlchemy. *(Done: `AsyncSessionLocal`, `get_db()`, `Base` class)*
- [x] Create Pydantic schemas for request/response validation. *(Done: `app/schemas/problem.py`, `submission.py`)*

### Phase A2: API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/problems` | List all problems (id, slug, title, difficulty). |
| `GET` | `/api/v1/problems/{slug}` | Get full problem details + visible test cases + starter code. |
| `POST` | `/api/v1/problems/{slug}/run` | Run code against **visible** test cases only. Returns `submission_id`. |
| `POST` | `/api/v1/problems/{slug}/submit` | Submit code for grading against **all** test cases. Returns `submission_id`. |
| `GET` | `/api/v1/submissions/{id}` | Get submission status and results (polling endpoint). |

- [x] Implement all 5 endpoints. *(Done: `app/routers/problems.py`, `submissions.py`)*
- [x] `/run` and `/submit` create a `submission` record, dispatch a Celery task, and return the `submission_id`.
- [x] `GET /submissions/{id}` returns current status + results.
- [ ] Test all endpoints manually via Swagger UI (`/docs`). *(Pending stack boot)*

### Phase A3: Sandbox Execution Engine

**Celery Setup:**
- [x] Configure Celery app (`worker/celery_app.py`) to connect to Redis. *(Done: Redis broker/backend, JSON serialization, UTC timezone)*
- [x] Define the grading task (`worker/tasks.py`) that receives a `submission_id`. *(Done: calls `execute_submission`, handles errors)*

**Sandbox Logic (`worker/sandbox.py`):**
- [x] Implement `execute_submission(submission_id)`:
  1. Fetch the submission and its problem's test cases from the DB.
  2. Write the student's Java source code to a temp file (`Solution.java`).
  3. **Compilation step:** Spawn a sandbox container, run `javac Solution.java`, capture compile errors. If compilation fails → set all test cases as failed with the compile error and exit early.
  4. **Execution step:** For each test case:
     - Create an ephemeral Docker container from `codeforge-sandbox-java`.
     - Copy the compiled `.class` file into the container via tar archive.
     - Set resource limits: `mem_limit=128m`, `cpu_quota=50000`, `network_disabled=True`, `read_only=True`, `cap_drop=ALL`, `no-new-privileges`.
     - Start the container, run `java Solution`, feed `input_data` via stdin.
     - Wait for completion with timeout (`time_limit_sec`).
     - Capture stdout and stderr.
     - Compare `normalize(stdout)` against `normalize(expected_output)`.
     - Record pass/fail, actual output, execution time.
     - Remove the container.
  5. Calculate score: `passed_cases / total_cases`.
  6. Update the submission record with status, score, and `results_json`.

**Output Normalization:**
- [x] Implement `normalize(output)`: strip trailing whitespace per line, strip trailing newlines, normalize line endings (`\r\n` → `\n`). Prevents false failures due to whitespace differences.

**Error Handling:**
- [x] **Compilation error** → Status: `compile_error`, show javac output to student.
- [x] **Runtime exception** → Test case failed, show stderr (e.g., `NullPointerException`).
- [x] **Timeout** → Test case failed with "Time Limit Exceeded".
- [x] **Container failure** → Submission status set to `error`.
- [x] Ensure containers are **always** cleaned up, even on exceptions (`try/finally`).

### Phase A4: Integration + Deployment ✅

- [x] Write integration tests:
  - Correct code → all tests pass. ✅
  - Buggy code → some tests fail, correct ones pass. ✅
  - Infinite loop → timeout handled gracefully. *(marked; wall-clock TLE enforced)*
  - Syntax/compile error → captured and returned. ✅ (verified via terminal log)
- [x] Verify no zombie containers are left after runs (`docker ps -a`). ✅
- [x] Verify full Docker Compose stack works from a clean `docker compose up -d --build`. ✅
- [x] Verify problem loader populates the database correctly. ✅ (3 problems loaded)
- [x] Ensure API is accessible from the frontend container (Nginx proxy config). ✅
- [x] Fix any edge cases found during integration with Frontend. ✅

---

## Developer B: Frontend

### Phase B1: Project Setup + Core Layout ✅

**Setup:**
- [x] Install dependencies: `@monaco-editor/react`, `tailwindcss`, `react-router-dom`, `axios` (or use shadcn/ui if desired).
- [x] Configure TailwindCSS.
- [x] Set up React Router with routes:
  - `/` → Problem list page.
  - `/problems/:slug` → Problem coding page (main interface).
- [x] Set up Axios API client with base URL configuration (`/api/v1`). *(Includes auto mock-fallback when backend is offline)*

**Problem List Page (`/`):**
- [x] Fetch `GET /api/v1/problems` and display as a list/table.
- [x] Show: problem title, difficulty badge (color-coded: green/yellow/red).
- [x] Click a problem → navigate to `/problems/:slug`.

**Problem Page — Layout:**
- [x] Build the split-pane layout:
  - **Left panel:** Problem description (title + markdown rendered with `react-markdown`).
  - **Right panel:** Code editor area.
  - **Bottom panel:** Test results area.
- [x] Use `react-resizable-panels` for draggable dividers.

### Phase B2: Code Editor + API Integration ✅

**Monaco Editor:**
- [x] Integrate Monaco Editor component with:
  - Language set to `java`.
  - Starter code loaded from the API response (`starter_code_java`).
  - Theme: VS Code dark (synced with app theme toggle).
  - Settings: font size 14, minimap off, line numbers on.
- [x] Store editor content in React state.

**Run & Submit:**
- [x] "▶ Run" button → calls `POST /api/v1/problems/{slug}/run` with `{ source_code, language: "java" }`.
- [x] "✓ Submit" button → calls `POST /api/v1/problems/{slug}/submit` with the same payload.
- [x] On response, receive `submission_id`.
- [x] Poll `GET /api/v1/submissions/{submission_id}` every 1-1.5 seconds until status is no longer `queued` or `running`.
- [x] Show a loading state while waiting (spinner, pulsing indicator).

**Test Results Panel:**
- [x] Render the `results_json` array once submission is complete:
  - **Visible test cases:** Show input, expected output, actual output, and ✅/❌.
  - **Hidden test cases:** Show only "Test Case N: ✅ Passed" or "❌ Failed" — no input/output.
  - **Overall score:** "3/5 test cases passed (60%)".
  - **Compile error:** Show `javac` output in a distinct red block (not per-test-case, since nothing ran).
  - **Runtime error:** Show the exception/stderr for that specific test case.
  - **Timeout:** Show "⏱️ Time Limit Exceeded" for that test case.

### Phase B3: UI Polish + Deployment ✅

- [x] Header/navbar with CodeForge name/logo.
- [x] Loading states: skeleton loaders for problem page, spinner for code execution.
- [x] Status indicator during execution: `Queued → Compiling → Running → Done`.
- [x] Edge case handling:
  - Empty code submission → warning, don't submit.
  - Network/API error → user-friendly error message (auto mock-fallback).
- [x] Configure Nginx (`frontend/nginx.conf`):
  - Serve the React build at `/`.
  - Proxy `/api/*` to the `api` container (`http://api:8000`).
  - WebSocket proxy `/ws/*` → `http://api:8000`.
- [x] Create multi-stage Dockerfile:
  - Stage 1: `node:20-alpine` → `npm run build`.
  - Stage 2: `nginx:alpine` → copy build output + nginx.conf.
- [x] Verify full end-to-end flow through Docker Compose. ✅

---

## Coordination Points

| When | What |
|---|---|
| **After Phase A1 + B1** | Agree on exact API request/response JSON shapes. Frontend can mock the API until backend is ready. |
| **After Phase A2 + B2** | First integration: frontend connects to live backend. Fix any contract mismatches. |
| **After Phase A3 + B2** | Full pipeline test: write code → run → see real sandbox results in the browser. |
| **Phase A4 + B3** | Joint deployment and final end-to-end testing from a clean Docker Compose build. |

---

## TA-1 Deliverables Checklist

- [x] `docker compose up -d` starts all services (web, api, worker, redis, db) — **multi-container architecture demonstrated**.
- [x] Problems loaded from YAML files via CLI tool.
- [x] Problems visible in the browser with markdown descriptions.
- [x] Monaco-based code editor with Java syntax highlighting.
- [x] "Run" executes Java code in a sandboxed Docker container and returns results.
- [x] Compile errors shown distinctly from runtime errors.
- [x] Test cases validated: visible ones show full details, hidden ones show only pass/fail.
- [x] Score calculated and displayed.
- [x] Sandbox containers are ephemeral (shown via `docker ps` during execution).
- [x] Resource limits enforced on sandbox containers (shown via `docker inspect`).
- [x] No zombie containers after execution.


---

## What We're NOT Building for TA-1

- ❌ Authentication / login
- ❌ User accounts
- ❌ Course / classroom management
- ❌ Python language support (Java only for TA-1, Python added in TA-2)
- ❌ Instructor problem creation UI (problems authored as YAML files)
- ❌ Submission history
- ❌ Gradebook
- ❌ Monitoring stack (Prometheus/Grafana)
