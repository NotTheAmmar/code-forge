# CodeForge — Frontend Documentation (TA-2 Milestone)

This document provides a comprehensive overview of the frontend implementation for **CodeForge TA-2**, including authentication, course management, problem management, lab sessions, badge mechanics, Python/Java execution, and backend integration.

---

## 🎨 Design Language & Theme Engine
The design is modeled after modern competitive programming and learning platforms (Striver's A2Z DSA sheet style):
- **Themes**: Deep slate/zinc dark mode (default) and clean high-contrast light mode.
- **Accents**: Vibrant orange/amber gradient (`#f97316` / `#f59e0b`).
- **Engine**: [`frontend/src/context/ThemeContext.tsx`](./frontend/src/context/ThemeContext.tsx) toggles the `dark` class on the root node, persists to `localStorage`, and binds Monaco editor themes (`vs-dark` / `light`).

---

## 🔐 Auth & Security Layer (Phase B1)
- **`AuthContext.tsx`**: Provides `user`, `login()`, `register()`, `logout()`, `isAuthenticated`, and `isLoading`. Restores session via `GET /api/v1/auth/me` on startup.
- **`ProtectedRoute`**: Guards authenticated routes in `App.tsx`, redirecting unauthenticated users to `/login` while preserving location state.
- **Axios Client (`client.ts`)**:
  - Request interceptor injects `Authorization: Bearer <access_token>`.
  - Response interceptor handles 401 Unauthorized by queuing requests and invoking `POST /api/v1/auth/refresh`.
  - Clean error propagation: Direct connection to backend API without misleading mock fallback swallowing.

---

## 🧭 Pages & Route Map (TA-2)

| Route | Page Component | Access | Description |
|---|---|---|---|
| `/login` | `LoginPage.tsx` | Public | Dual-mode login & registration with role selector (`student` / `instructor`). |
| `/` | `CourseListPage.tsx` | Protected | Dashboard showing enrolled courses, Join Course modal (with invite code), and Create Course modal. |
| `/practice` | `ProblemListPage.tsx` | Protected | Legacy standalone practice problem list. |
| `/courses/:id` | `CoursePage.tsx` | Protected | Course workspace with problem list, "+ Add Problem" modal, "Bulk Import" modal, active/past lab sessions, and copyable invite code. |
| `/courses/:courseId/labs/create` | `LabCreatePage.tsx` | Instructor | Create lab session with problem selection and mandatory solve count. |
| `/courses/:courseId/gradebook` | `GradebookPage.tsx` | Instructor | Course-wide Student × Problem score matrix with sortable rankings. |
| `/labs/:id` | `StudentLabPage.tsx` | Protected | Student lab mode with active countdown timer, solve progress, and badge counter. |
| `/labs/:id/dashboard` | `LabDashboardPage.tsx` | Instructor | Live instructor dashboard with auto-refreshing (15s) student badge leaderboard (⭐). |
| `/problems/:slug` | `ProblemPage.tsx` | Protected | Monaco editor, Java/Python language switcher, test cases, live submission polling, and past submission history tab. |

---

## 🏅 Lab Sessions & Badge System (Phase B3)
- **Lab Mode Banner**: Shows live countdown timer and badges earned during an active lab.
- **Badge Notification (`BadgeToast`)**: Displays a celebratory popup notification when a student submits an extra solved problem beyond the mandatory count during a lab session.
- **Auto-Refreshing Dashboard**: Polls every 15 seconds to update the instructor with real-time student solves and earned badges (⭐).

---

## 🛠️ Problem Management & Bulk Import (Instructor)
- **"+ Add Problem" Modal**: In `CoursePage.tsx`, instructors can define title, auto-slug, difficulty (`easy`, `medium`, `hard`), markdown description, Python starter code, Java starter code, and dynamic visible/hidden test cases.
- **"Bulk Import" Modal**: In `CoursePage.tsx`, instructors can paste a JSON array of problems with test cases, or click "Load Example Template" to populate standard templates directly into the database.
- **Copy Invite Code**: 1-click clipboard button with visual checkmark feedback ("Copied!") allows instructors to easily share course codes with students.

---

## ✅ Integration Verification Status

All frontend services and routes are 100% integrated with the FastAPI backend and Docker environment:
1. **`POST /api/v1/courses/join`**: Students can join courses directly with invite codes.
2. **Schema Alignment**: Pydantic models return `join_code` and `instructor_id` computed fields.
3. **Lab Routes**: Mapped directly to `/courses/{id}/labs` and `/labs/{id}`.
4. **Lab Dashboards**: Unpacks student leaderboard array with Diana (3 ⭐), Alice (2 ⭐), Bob (1 ⭐).
5. **Gradebook**: Renders the complete score matrix for all enrolled students.
6. **Execution Engine**: Celery worker evaluates submissions in isolated Docker containers (`codeforge-sandbox-java` and `codeforge-sandbox-python`) and awards badges dynamically upon solve.
