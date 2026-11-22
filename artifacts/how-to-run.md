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
- **Instructors:**
  - `admin@codeforge.local` ("Admin Instructor") — System Administrator & Faculty Head (enrolled in CS101, CS201, CS301).
  - `prof.chen@codeforge.local` ("Prof. Alan Chen") — Associate Professor of Algorithms (CS201, MATH150).
  - `dr.stone@codeforge.local` ("Dr. Elena Stone") — Systems Programming & Architecture Faculty (CS301).
- **Students (12 total accounts):**
  - `student@codeforge.local` ("Alex Student") — **Demo Hero Account**. Fresh baseline student who has solved only the mandatory problem (`hello-world`) in Lab 1. Solving a 2nd problem (`two-sum`) live during the presentation immediately earns a badge! In exams, Alex has not started yet, so you can test starting exams cleanly.
  - `diana@codeforge.local` ("Diana Prince") — Top student (Rank 1 on Leaderboard: 5 solved, 4 badges in Lab 1, 100% on midterm, 0 violations).
  - `alice@codeforge.local` ("Alice Johnson") — Strong student (4 solved, 3 badges, Module progress completed, 1 exam violation).
  - `bob@codeforge.local` ("Bob Smith") — In-progress student (3 solved, 2 badges, active exam session with 2 violations).
  - `evan@codeforge.local` ("Evan Wright") — 2 solved, 1 badge in Lab 1, enrolled in CS201.
  - `fiona@codeforge.local` ("Fiona Gallagher") — 2 solved, 1 badge in Lab 1, 2 exam violations (`focus_loss`, `copy_paste`).
  - `george@codeforge.local` ("George Clark") — Enrolled in CS101 & CS201 (CS201 midterm 70% with 1 violation).
  - `hannah@codeforge.local` ("Hannah Abbott") — Baseline student (1 solved, 0 badges).
  - `ian@codeforge.local` ("Ian Malcolm") — CS301 systems student (solved bitwise-parity).
  - `julia@codeforge.local` ("Julia Roberts") — CS101 & CS301 student.
  - `kevin@codeforge.local` ("Kevin Mitnick") — Systems hacker (CS301 exam 100% with 2 violations: `fullscreen_exit`, `focus_loss`).
  - `charlie@codeforge.local` ("Charlie Brown") — Baseline student (1 solved, 0 badges).

### 2. Courses (4 Distinct Academic Curricula)
1. **CS101: Introduction to Programming** (Invite Code: `CS101A`)
   - Foundational programming paradigms, algorithm formulation, standard I/O, and control flow in Python, Java, C, and C++.
2. **CS201: Data Structures & Algorithms** (Invite Code: `CS201B`)
   - Algorithmic complexity, asymptotic analysis, search invariants, divide & conquer, and dynamic memory structures.
3. **CS301: Systems & Low-Level C/C++ Programming** (Invite Code: `CS301C`)
   - Low-level systems programming, pointer mechanics, manual memory layout, bitwise manipulation, and system boundaries.
4. **MATH150: Discrete Mathematics for CS** (Invite Code: `M150D`)
   - Mathematical foundations for computer science: propositional logic, bitwise parity, modular arithmetic, and recurrence relations.

### 3. Problem Catalog (11 Problems with Python, Java, C, and C++ Starters)
- **CS101 Problems:**
  - `hello-world` (Easy): Stdin/stdout greeting formatting.
  - `two-sum` (Easy): Array index target search.
  - `reverse-string` (Easy): String reversal logic.
  - `fizzbuzz` (Easy): 3/5/15 multiples handling.
  - `palindrome-number` (Easy): Integer palindrome check.
- **CS201 Problems:**
  - `valid-palindrome` (Easy): Alphanumeric palindrome filtering.
  - `binary-search` (Medium): Logarithmic O(log n) sorted array search.
  - `merge-sorted-arrays` (Medium): Two-pointer linear array combination.
  - `maximum-subarray` (Medium): Kadane's dynamic algorithm for contiguous subarray sum.
- **CS301 / MATH150 Problems:**
  - `bitwise-parity` (Easy): 32-bit integer parity bit computation.
  - `pointer-swap-reverse` (Medium): In-place array traversal & reversal.

### 4. Lab Sessions (4 Sessions Across Courses)
- **CS101: "Lab 1: Programming Basics & Warm-up"** (Active, mandatory: 1 problem):
  - Pre-seeded badges awarded for solving beyond mandatory:
    - Diana: 4 badges ⭐⭐⭐⭐
    - Alice: 3 badges ⭐⭐⭐
    - Bob: 2 badges ⭐⭐
    - Evan, Fiona, Kevin: 1 badge each ⭐
    - Charlie, Hannah, Ian, Julia, Alex: 0 badges
- **CS201: "Lab 2: Searching & Pointer Invariants"** (Active, mandatory: 2 problems)
- **CS301: "Lab 3: C/C++ Memory & Bitwise Lab"** (Active, mandatory: 1 problem)
- **CS101: "Lab 0: Diagnostic Orientation"** (Closed / Archived baseline lab)

### 5. Interactive Learning Modules (6 Modules Across Courses)
- **CS101 Module 1:** "Introduction to Python & Algorithms" (Theory + YouTube video + `hello-world`)
- **CS101 Module 2:** "Algorithmic Thinking & Control Flow" (Theory + YouTube video + `fizzbuzz`)
- **CS101 Module 3:** "String Mechanics & Reversal" (Theory + `reverse-string`)
- **CS201 Module 1:** "Asymptotic Analysis & Binary Search" (Theory + YouTube video + `binary-search`)
- **CS201 Module 2:** "Divide & Conquer and Subarray Invariants" (Theory + `merge-sorted-arrays`)
- **CS301 Module 1:** "Computer Architecture & Bitwise Logic" (Theory + `bitwise-parity`)

### 6. Proctored Exams & Anti-Cheat Engine (4 Assessments)
- **"CS101 Midterm Proctored Assessment"** (Active window, 60 mins):
  - Problems: `hello-world` (40 pts) + `two-sum` (60 pts).
  - Pre-seeded Sessions:
    - Diana: 100/100 points, 0 violations.
    - Alice: 100/100 points, 1 violation (`tab_switch` recorded).
    - Fiona: 100/100 points, 2 violations (`focus_loss`, `copy_paste`).
    - Evan: 40/100 points, 0 violations.
    - Bob: In-progress session with 2 violations (`tab_switch`, `fullscreen_exit`).
    - Alex Student: Ready to be taken live during demo!
- **"CS101 Final Assessment: Problem Solving Mastery"** (Scheduled future window, 90 mins).
- **"CS201 Midterm: Algorithmic Efficiency & Searching"** (Active window, 75 mins, George Clark session).
- **"CS301 Practical Systems Exam: Memory & Bitwise Ops"** (Active window, 90 mins, Kevin Mitnick session with violations).

### 7. Socratic AI Programming Tutor (Pedagogical Guidance)
- Embedded in the Problem Solving view (non-exam sessions).
- Uses Google Gemini Flash (or intelligent offline fallback).
- Guiding principle: **Never generates full solutions or direct code blocks**; guides students with targeted hints, conceptual explanations, and edge-case questions.

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

# Run all 149 automated tests
./codeforge-setup.sh --test

# Re-seed database demo data (idempotent)
./codeforge-setup.sh --seed

# Tail backend and worker logs
docker compose logs -f api worker
```
