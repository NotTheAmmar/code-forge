# DockGrade — Semester Project Proposal

## Project Title
**DockGrade: An Orchestrated Code Sandbox & Automated Assignment Evaluation Pipeline**

**Project Type:** Multi-Container Microservice Application

---

## 🎯 Problem Statement

In computer science education, evaluating student programming assignments manually is slow, error-prone, and inconsistent. Students spend more time fighting environment setup — installing compilers, resolving dependency conflicts, configuring IDEs — than actually learning to code.

While automated grading platforms exist (LeetCode, HackerRank), institutions require private, self-hosted, and flexible solutions that adapt to their specific curriculums without third-party vendor lock-in or licensing fees.

Furthermore, running untrusted, user-submitted code poses serious security risks — infinite loops, system file access, memory exhaustion, or network exploits. Traditional VM-based isolation is too slow and resource-intensive to scale for an entire classroom of concurrent submissions.

---

## 💡 Proposed Solution

**DockGrade** is a lightweight, automated, and secure container-based code execution and grading pipeline. It provides a browser-based "LeetCode-style" coding environment where:

- **Instructors** create coding problems with a problem statement, starter code templates, and a set of input/output test cases (some visible to students, some hidden for final grading).
- **Students** read the problem, write their solution directly in the browser, and submit. No local setup, no configuration — just code and run.
- **The system** instantly executes the submitted code inside a completely isolated, resource-constrained, ephemeral Docker container, validates it against all test cases, and returns results in real time.

### Supported Languages (Semester Scope)
- **Java**
- **Python**

---

## 🏗️ Multi-Container Architecture

DockGrade is structured as a decoupled microservice stack orchestrated using a single `docker-compose.yml`. The architecture splits the workload into four isolated service containers:

```
                            +---------------------------------------+
                            |     User / Browser (Port 80)          |
                            +------------------+--------------------+
                                               | (HTTP)
                                               v
                            +------------------+--------------------+
                            |   Module 1: Web Portal & API Gateway  |
                            +------------------+--------------------+
                                               |
                                               v (Job Dispatch)
                            +------------------+--------------------+
                            |   Module 2: Asynchronous Job Queue    |
                            +------------------+--------------------+
                                               |
                                               v (Pulls Grading Tasks)
  +--------------------+    +------------------+--------------------+
  | Module 4: Database |    | Module 3: Sandbox Execution Engine    |
  | Persistent Storage | <+ |   (Interacts with host Docker API)    |
  |  (Named Volumes)   |    +------------------+--------------------+
  +--------------------+                       |
                                               v (Spawns Ephemeral Sandbox)
                            +------------------+--------------------+
                            |   Student Code Sandbox (--rm, limits) |
                            +---------------------------------------+
```

### Module 1: Classroom Web Portal & API Gateway
- **Role:** The primary interface for instructors and students.
- **Key Features:**
  - **Instructor view:** Create courses, define coding problems with descriptions and constraints, upload input/output test case files, designate test cases as *visible* (students can see expected output) or *hidden* (used only for final grading), and view a gradebook of all submissions.
  - **Student view:** Browse assigned problems, read the problem statement, write code in an integrated browser-based editor, run code against visible test cases for immediate feedback, and submit for final grading against all test cases (including hidden ones).
- **Docker Integration:** Packaged as an optimized, multi-stage Docker build with a reverse proxy to route frontend traffic and API calls.

### Module 2: Asynchronous Job Queue
- **Role:** Buffer layer to handle concurrent student submissions without blocking the web application.
- **Key Features:** When a student clicks "Run" or "Submit", the API registers the submission and pushes a grading task onto the job queue. This decouples the user-facing response time from the actual code execution time.
- **Docker Integration:** Runs as a lightweight container. No ports are exposed to the host machine; communication is entirely restricted to the internal user-defined bridge network, guaranteeing network-level data isolation.

### Module 3: Ephemeral Sandbox Execution Engine *(The Core)*
- **Role:** Programmatic container orchestration and code validation runner.
- **Key Features:** An asynchronous worker service that listens to the job queue. Upon pulling a task, it:
  1. Communicates with the host Docker Engine API.
  2. Spins up a clean, language-specific base container (Java or Python).
  3. Mounts the student's submitted code into the sandbox.
  4. Executes the code with each input test case.
  5. Captures standard output (STDOUT) and errors (STDERR).
  6. Compares actual output against expected output for each test case.
  7. Calculates the final score (e.g., 4/5 test cases passed).
  8. Writes the results back to the database and notifies the student.
- **Docker Integration — Sandbox Hardening:**
  - **Ephemeral execution:** Containers are created per-submission and destroyed immediately after (`--rm`), leaving no residual state.
  - **Resource limits:** Strict cgroup constraints (memory cap, CPU cap, execution timeout) to prevent Denial-of-Service, memory exhaustion, and infinite loops.
  - **Privilege dropping:** All Linux kernel capabilities are dropped (`--cap-drop=ALL`), and the filesystem is mounted read-only to prevent tampering.

### Module 4: Persistent Database & Storage
- **Role:** Permanent ledger for all platform data.
- **Key Features:** Manages relational schemas for users, courses, problems, test cases, submissions, and grades.
- **Docker Integration:** Uses **named Docker volumes** to persist the database data directory, ensuring all records survive container restarts, updates, and redeployments.

---

## 🔄 Submission Flow — End to End

```
Student writes code in browser
        │
        ▼
Clicks "Run" (visible tests) or "Submit" (all tests)
        │
        ▼
API Gateway validates & enqueues a grading job
        │
        ▼
Job Queue holds the task until a worker is free
        │
        ▼
Sandbox Engine picks up the job
        │
        ▼
Spawns an ephemeral Docker container (Java/Python)
        │
        ▼
Mounts student code → Executes with test inputs
        │
        ▼
Captures output → Compares against expected output
        │
        ▼
Calculates score → Writes to Database
        │
        ▼
Student sees results: ✅ Passed / ❌ Failed per test case
```

---

## 📈 Course Outcome & Syllabus Mapping

This project has been deliberately architected to demonstrate core course competencies:

| Course Outcome | How DockGrade Demonstrates It |
|---|---|
| **Orchestration (CO2 / Unit V)** | Entire stack managed by a single `docker-compose up -d` command with DNS-based service discovery — containers resolve each other by service name. |
| **Advanced Storage (Unit III)** | Clean separation of ephemeral state (sandbox runs destroyed after execution) vs. persistent state (grades secured in named Docker volumes). |
| **Monitoring & Visualisation (Lab Exp 7 / Unit V)** | Pre-packaged monitoring stack to visualize live CPU/memory spikes as student code compiles and runs — ideal for jury demonstration. |
| **Container Security (Unit III)** | Practical application of namespaces, cgroups, capability drops, read-only filesystems, and container hardening best practices on the sandbox containers. |

---

## 🧪 Scope Summary (This Semester)

| In Scope | Out of Scope (Future) |
|---|---|
| Browser-based code editor | Learning modules & tutorials |
| Problem creation with test cases (visible + hidden) | Proctored exam environment |
| Code execution in Docker sandboxes (Java, Python) | Anti-cheat / plagiarism detection |
| Automated grading against test cases | AI-assisted learning |
| Real-time result feedback | Multi-institution deployment |
| Instructor gradebook | Additional language support |
| Docker Compose orchestration | Mobile app |
