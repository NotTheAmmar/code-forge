# TA-2 Implementation Plan — Due: October 19-24 (Tentative)

**Goal:** Transform the TA-1 raw engine demo into a real platform with users, courses, and multi-language support. By TA-2, this should feel like a usable product, not just a tech demo.

---

## Key Additions

### 1. Authentication & User Management
- User registration and login (JWT-based).
- Two roles: `instructor` and `student`.
- Protected API routes — no more anonymous access.
- Login/register pages on the frontend.

### 2. Course & Classroom System
- Instructors can create courses.
- Students join courses via invite code.
- Problems are scoped to courses (not global).
- Course dashboard showing enrolled students and problem list.

### 3. Instructor Problem Management UI
- Full CRUD UI for problems: create, edit, delete — no more seeding via scripts.
- Upload/create test cases through the UI (mark as visible or hidden).
- Set time/memory limits per problem.
- Starter code templates (per language).

### 4. Java Language Support
- Build `dockgrade-sandbox-java` container image.
- Backend handles Java compilation (`javac`) + execution (`java`) in the sandbox.
- Compilation error handling (show compile errors distinctly from runtime errors).
- Frontend language switcher: Python ↔ Java.
- Starter code loaded per selected language.

### 5. Submission History
- Students can view their past submissions for each problem.
- Shows: timestamp, language, score, status.
- Click into a submission to see the code and test case results.
- "Best submission" indicator.

### 6. Gradebook
- Instructor view: Student × Problem matrix with scores.
- Click any cell to view the student's submission details and code.
- Export to CSV (stretch).

### 7. Monitoring Stack
- Prometheus scraping container metrics.
- cAdvisor exporting Docker container stats.
- Grafana dashboards showing:
  - CPU/memory usage per container.
  - Sandbox container spawn rate.
  - API request latency.
- Pre-configured dashboards (JSON provisioning) so it works out of the box.

### 8. UI/UX Improvements
- Proper navigation and routing.
- Responsive layout refinements.
- Toast notifications for actions (submission submitted, error, etc.).
- Loading skeletons instead of spinners.
- Dark/light theme toggle (stretch).

---

## Rough Architecture Changes
- Add `users` and `enrollments` tables to the database.
- Add auth middleware to FastAPI (JWT dependency injection).
- Refactor API routes to be course-scoped (`/courses/{id}/problems/...`).
- Add `prometheus.yml`, Grafana provisioning configs, cAdvisor to Docker Compose.

---

## What Success Looks Like for TA-2 Demo
1. Instructor logs in → creates a course → gets an invite code.
2. Student logs in → joins the course with the code → sees the problem list.
3. Instructor creates a problem with test cases via the UI.
4. Student opens the problem → writes code in Java or Python → runs → sees results.
5. Instructor opens the gradebook → sees all student scores.
6. Jury sees the Grafana dashboard with live metrics as code runs.
7. Show `docker compose ps` — all services healthy, monitoring stack running.
