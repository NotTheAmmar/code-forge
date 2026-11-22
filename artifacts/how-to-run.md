# CodeForge — How to Run & Demonstration Guide

This guide walks you through launching CodeForge from scratch, testing every subsystem, and conducting an end-to-end presentation demo for the Final Jury.

---

## ⚡ Quick Start: Single-Command Launchers

CodeForge features turnkey, cross-platform installers that automatically inspect prerequisites, generate configuration, build the 4 multi-language sandbox containers, launch application services, apply database migrations, and seed initial demo data.

### Option A: Linux, macOS, or Windows WSL2 (Recommended)
```bash
# Clone and enter the repository
git clone <repo-url> code-forge
cd code-forge

# Run the turnkey installer
./codeforge-setup.sh
```
> **Tip:** Pass `--build` to force-rebuild application images: `./codeforge-setup.sh --build`.

### Option B: Windows PowerShell (Native)
Open PowerShell as Administrator:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\codeforge-setup.ps1
```

### Option C: Windows File Explorer
Double-click `codeforge-setup.bat`.

---

## 🛠️ Manual Step-by-Step Setup (Alternative)

If you prefer to start each component manually:

```bash
# 1. Initialize environment configuration
cp .env.example .env

# 2. Build the 4 execution sandbox Docker images
docker build -t codeforge-sandbox-python ./sandbox/python
docker build -t codeforge-sandbox-java ./sandbox/java
docker build -t codeforge-sandbox-c ./sandbox/c
docker build -t codeforge-sandbox-cpp ./sandbox/cpp

# 3. Start core infrastructure and application containers
docker compose up -d --build

# 4. Apply Alembic database migrations
docker compose exec api alembic upgrade head

# 5. Seed the database with demo courses, problems, modules, and exams
docker compose exec api python manage.py seed
```

---

## 🌐 Platform Service Map

Once services are running, access the platform at:

| Service | URL | Default Credentials | Description |
|---|---|---|---|
| **Web Frontend** | [http://localhost](http://localhost) | See below | Single-page application |
| **API Swagger UI** | [http://localhost:8000/docs](http://localhost:8000/docs) | — | Interactive OpenAPI docs |
| **API Readiness** | [http://localhost:8000/health/ready](http://localhost:8000/health/ready) | — | Database & Redis health probe |
| **Grafana** | [http://localhost:3000](http://localhost:3000) | `admin` / `admin` | Live container & hardware metrics |
| **Prometheus** | [http://localhost:9090](http://localhost:9090) | — | Raw metrics scraper |
| **cAdvisor** | [http://localhost:8080](http://localhost:8080) | — | Container CPU, memory & IO metrics |

---

## 📦 What Is Seeded in the Database?

Running `python manage.py seed` populates an entire realistic academic semester environment:

### 1. User Accounts (Password for all: `changeme`)
- **Instructor:**
  - `admin@codeforge.local` ("Admin Instructor") — Course creator, author of all problems, lab sessions, learning modules, exams, and viewer of instructor analytics & audit logs.
- **Students:**
  - `student@codeforge.local` ("Alex Student") — **Demo Hero Account**. Baseline student who has solved only the mandatory problem (`hello-world`). Solving any 2nd problem (`two-sum`) live during the presentation immediately earns a badge!
  - `diana@codeforge.local` ("Diana Prince") — Top student (4 solved, 3 badges, 100% on midterm, 0 violations).
  - `alice@codeforge.local` ("Alice Johnson") — Strong student (3 solved, 2 badges, Module 1 completed, 1 exam violation).
  - `bob@codeforge.local` ("Bob Smith") — In-progress student (2 solved, 1 badge, active exam session with 2 violations).
  - `charlie@codeforge.local` ("Charlie Brown") — Baseline student (1 solved, 0 badges).

### 2. Course
- **CS101: Introduction to Programming**
  - Invite Code: `CS101A`
  - Created by Admin Instructor, with all 5 students enrolled.

### 3. Problems (with Python, Java, C, and C++ Starters)
- `hello-world`: String input/output formatting. 3 test cases (2 visible, 1 hidden).
- `two-sum`: Array index target search. 3 test cases (2 visible, 1 hidden).
- `reverse-string`: String reversal logic. 3 test cases (2 visible, 1 hidden).
- `fizzbuzz`: 3/5 division logic. 2 test cases (1 visible, 1 hidden).

### 4. Lab Sessions & Gamified Badges
- **"Lab 1: Programming Basics & Warm-up"**: Active lab session with 1 mandatory problem requirement.
- Badges awarded when students exceed the mandatory threshold:
  - Diana: 3 badges ⭐⭐⭐
  - Alice: 2 badges ⭐⭐
  - Bob: 1 badge ⭐
  - Charlie: 0 badges
  - Alex Student: 0 badges (primed for live presentation demo).

### 5. Interactive Learning Modules
- **Module 1: "Introduction to Python & Algorithms"** (Published):
  - *Theory:* Markdown guide on Python dynamic typing and object references.
  - *Video:* Embedded YouTube masterclass (`kqtD5dpn9C8`).
  - *Practice:* Interactive challenge linked directly to `hello-world`.
- **Module 2: "Algorithmic Thinking & Control Flow"** (Published):
  - *Theory:* Markdown guide on branching invariants and edge-case handling.
  - *Video:* Embedded YouTube lecture on loop invariants (`6iF8Xb7Z3wQ`).
  - *Practice:* Interactive challenge linked directly to `fizzbuzz`.

### 6. Proctored Exam & Anti-Cheat Engine
- **"CS101 Midterm Proctored Assessment"**:
  - 60-minute duration, full-screen lockdown enforcement, copy/paste blocking, tab-switch limit of 3.
  - Weighted problems: `hello-world` (50 pts) + `two-sum` (50 pts).
  - Pre-seeded Sessions:
    - Diana: 100/100 points, 0 violations.
    - Alice: 100/100 points, 1 violation (`tab_switch` recorded).
    - Bob: In-progress session with 2 recorded violations (`tab_switch`, `fullscreen_exit`) for instructor audit review.

---

## 🎬 Recommended Final Jury Demo Flow

Here is the ideal 5-to-10 minute presentation sequence:

### Step 1: Instructor Perspective (Curriculum & Analytics)
1. Navigate to [http://localhost](http://localhost) and log in as `admin@codeforge.local` / `changeme`.
2. Click **CS101: Introduction to Programming**.
3. **Analytics Tab:** Show the live course KPIs, problem pass rate bar chart, and 7-day submission volume trend.
4. **Learn Tab:** Show the curriculum outline with Module 1 and Module 2.
5. **Labs Tab:** Open **Lab 1: Programming Basics & Warm-up** → View the **Live Badge Leaderboard** (Diana with 3 badges, Alice with 2, Bob with 1).
6. **Exams Tab:** Open **CS101 Midterm Proctored Assessment** → Show the **Audit Dashboard** revealing Alice and Bob's anti-cheat violation logs (`tab_switch`, `fullscreen_exit`).

### Step 2: Student Learning Flow (Interactive Modules)
1. Switch user or log in in an incognito window as `student@codeforge.local` / `changeme`.
2. Go to **CS101** → **Learn** tab.
3. Open **Module 1**:
   - Read the formatted Markdown theory.
   - Play the embedded YouTube video.
   - Click the inline practice challenge to open the Code Editor.

### Step 3: Multi-Language Code Execution & WebSocket Streaming
1. Open the Code Editor for `two-sum` or `hello-world`.
2. Switch languages using the dropdown: **Python**, **Java**, **C**, and **C++**.
3. **Custom Input (Stdin):** Toggle custom input mode, enter custom text, click **Run Custom**, and see output execution instantly.
4. **WebSocket Test Progression:** Click **Run Code** or **Submit Code**:
   - Observe live real-time progress updates streamed via WebSockets: `Queued → Compiling → Running Test 1/3 → Running Test 2/3 → Completed`.

### Step 4: Live Badge Earning Demo
1. While logged in as `student@codeforge.local`, solve and submit `two-sum` in **Lab 1**.
2. Refresh or observe the instructor's **Lab Dashboard** in the other window:
   - Alex Student now earns **1 Badge** ⭐ in real time, moving up the leaderboard!

### Step 5: Proctored Exam & Anti-Cheat Demonstration
1. In the student window, navigate to **Exams** → Click **CS101 Midterm Proctored Assessment**.
2. Click **Start Exam**:
   - Browser requests full-screen mode.
   - Exam timer starts counting down.
3. **Trigger Anti-Cheat Violation:**
   - Press `Alt+Tab` or switch tabs.
   - Observe the warning notification informing the student of the recorded tab switch.
4. Submit the exam. Switch to the instructor window to see the new timestamped violation entry in the audit log.

### Step 6: Security Hardening & Isolation Demo
Open a terminal and demonstrate container isolation:
```bash
# Run the automated security test suite (pids-limit, network disabled, tmpfs noexec)
docker compose run --rm api pytest tests/test_security.py -v
```
Explain the container sandbox parameters:
- Fork bombs are killed by `--pids-limit=64`.
- Network calls fail (`network_disabled=True`).
- Non-root `runner` user with `cap_drop=["ALL"]`.
- 16MB noexec `tmpfs` at `/tmp`.

---

## 🛑 Stopping & Resetting the Platform

### Stopping CodeForge (Preserving All Data)
To pause or stop all running services without losing any course data, submissions, or user accounts:

```bash
# Using the setup script (Linux / macOS / WSL2)
./codeforge-setup.sh --stop

# Or using Windows PowerShell
.\codeforge-setup.ps1 -Stop

# Or using native Docker Compose directly
docker compose down
```

---

### Factory Reset (Completely Wipe & Reinitialize)
To completely wipe all database contents, redis state, and volumes, and re-launch a pristine environment with fresh seed data:

```bash
# Single-command factory reset (Linux / macOS / WSL2)
./codeforge-setup.sh --reset

# Or on Windows PowerShell
.\codeforge-setup.ps1 -Reset

# Or manually via Docker Compose
docker compose down -v
docker compose up -d
docker compose exec api alembic upgrade head
docker compose exec api python manage.py seed
```

---

## 🔧 Maintenance & Diagnostic Commands

```bash
# Check service health and status
./codeforge-setup.sh --status

# Run all 145 automated tests
./codeforge-setup.sh --test

# Re-seed database demo data (idempotent)
./codeforge-setup.sh --seed

# Tail backend and worker logs
docker compose logs -f api worker
```
