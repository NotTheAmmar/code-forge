# Final Jury Implementation Plan — Due: November 23-26 (Tentative)

**Goal:** Polish, harden, and add advanced features that elevate DockGrade from a class project to a near-production system. This is the "wow factor" phase.

---

## Key Additions

### 1. Security Hardening & Edge Cases
- Comprehensive sandbox security audit — verify all cgroup/capability restrictions are actually enforced.
- Fork bomb protection (`--pids-limit`).
- Disk write abuse prevention (tmpfs size enforcement).
- Test with adversarial inputs: infinite loops, memory bombs, `os.system()` calls, network access attempts, file system traversal.
- Demonstrate each security measure failing gracefully to the jury.

### 2. Real-Time WebSocket (If Not Done in TA-2)
- Replace polling with WebSocket for submission status.
- Incremental test case results pushed as each test completes (not all at once at the end).
- Live status indicator in the UI: `Queued → Running (2/5) → Completed`.

### 3. Enhanced Code Editor Experience
- Syntax error highlighting in-editor (linting) for Python and Java.
- Auto-save drafts (localStorage or server-side).
- Multiple file support (stretch — e.g., Java where the class name matters).
- Editor keybinding options (VS Code / Vim / Emacs).
- Run code with custom input (student types their own stdin, not just test cases).

### 4. Analytics & Insights Dashboard
- Per-problem analytics: pass rate, average score, common errors.
- Per-student analytics: submission count, improvement over time, time spent.
- Class-wide statistics for instructors.
- Visual charts (bar charts, line graphs for progress over time).

### 5. Advanced Grading Features
- Partial credit (configurable weight per test case).
- Penalty for multiple submissions (optional, instructor-configurable).
- Time-based scoring (faster correct solutions score higher — optional).
- Code execution statistics: memory used, time taken per test case.

### 6. Deployment & DevOps Polish
- Environment-based configuration (dev / staging / production).
- Health check endpoints for all services.
- Docker Compose health checks and restart policies.
- Proper logging (structured JSON logs, centralized via Docker log driver).
- Backup strategy for PostgreSQL volumes.

### 7. Stretch Goals (If Time Permits)
- **C/C++ language support** — add a GCC-based sandbox image.
- **Basic plagiarism detection** — code similarity scoring between submissions using token-based comparison (e.g., Moss-like algorithm).
- **Student leaderboard** — anonymous or named ranking by score per problem.
- **Email notifications** — grade published, new assignment posted.
- **Containerized CI/CD** — automated tests run on every push via GitHub Actions, building and testing the entire Docker Compose stack.

---

## What Success Looks Like for Final Jury Demo
1. Everything from TA-1 and TA-2 working flawlessly.
2. Live security demo: submit malicious code (fork bomb, network access, file read) → show it being contained and failing safely.
3. Real-time results streaming in the browser as test cases execute one by one.
4. Instructor analytics dashboard with charts and insights.
5. Grafana showing live infrastructure metrics during the demo.
6. Clean `docker compose up` from scratch → entire platform running in under a minute.
7. Present the architecture diagram, explain every container, every volume, every network.
