# DockGrade — Full Vision Proposal

## The Vision

**DockGrade** is an all-in-one platform for teaching, practicing, and assessing programming — purpose-built for educational institutions. It eliminates the gap between "learning to code" and "proving you can code" by combining three tightly integrated pillars:

1. **Learn** — Structured, institution-customizable learning modules with embedded tutorials, practice problems, and an AI tutor.
2. **Practice** — A LeetCode-style coding environment where students solve problems, run code against test cases, and get instant feedback — all in the browser, zero setup.
3. **Assess** — A proctored, locked-down exam environment with comprehensive anti-cheat measures, randomized problem variants, and automated grading.

The core principle: **students should spend their time writing code, not configuring environments.** Open a browser, pick a problem, write code, run it. That's it.

---

## 🧩 Platform Pillars

### Pillar 1: The Coding Engine *(Foundation)*

At the heart of DockGrade is a containerized code execution engine. Every piece of code — whether from a tutorial exercise, a practice problem, or a proctored exam — runs through the same pipeline:

- Student writes code in a browser-based editor.
- Code is executed inside an isolated, ephemeral, resource-constrained container.
- Output is captured and compared against predefined test cases.
- Results are returned in real time.

**Test Case Model:**
- **Visible test cases:** Students can see the input, expected output, and their actual output. Used for learning and debugging.
- **Hidden test cases:** Students only see pass/fail. Used for grading to prevent hard-coding answers.

**Language Support:**
- Initial: Java, Python
- Planned: C, C++, JavaScript, Go, Rust, and more — each language is simply a new base container image.

**Zero Configuration Promise:**
- No local compiler installation. No IDE setup. No dependency management.
- The platform handles compilation, execution, and runtime environments entirely server-side.

---

### Pillar 2: Learning Modules

Structured, progressive learning paths that institutions can customize or build from scratch.

**Content Types:**
- **Text lessons** — Concept explanations, syntax references, best practices.
- **Video lessons** — Embedded instructional videos (recorded lectures, walkthroughs).
- **Interactive code exercises** — Inline coding challenges where students read, write, and run code within the lesson itself. Powered by the same coding engine.
- **Practice problem sets** — Graded sets of problems (easy → medium → hard) that reinforce the concepts taught in lessons.

**Progression & Gating:**
- Modules are organized into sequential tracks (e.g., "Java Fundamentals → OOP → Data Structures → Algorithms").
- Institutions define the completion criteria: finish all lessons, score above a threshold on practice problems, or both.
- **Assessment gating:** The proctored exam module for a topic only unlocks after the student has completed the corresponding learning module. This ensures students have genuinely engaged with the material before being assessed.

**Institutional Customization:**
- Institutions can create their own learning modules with their own content, branding, and structure.
- They can also use DockGrade's built-in content library as a starting point and customize from there.
- Full control over curriculum sequencing, problem banks, and grading rubrics.

---

### Pillar 3: Proctored Assessment Module

A locked-down, anti-cheat examination environment for high-stakes coding assessments. Once a student enters an exam, the environment transforms from an open learning space into a controlled testing zone.

#### Anti-Cheat Mechanisms

| Category | Mechanism | Details |
|---|---|---|
| **Browser Lockdown** | Tab switch detection | Detects and logs any attempt to switch tabs or open new windows. Configurable: warn, flag, or auto-submit. |
| | Right-click disabled | Context menu is blocked except where platform functionality requires it (e.g., editor-specific actions). |
| | Copy/paste restriction | External paste into the code editor is blocked. Internal copy/paste within the editor is allowed. |
| | Notification suppression | Browser notifications are suppressed during the exam session. |
| | Keyboard shortcut blocking | OS-level shortcuts (Alt+Tab, Win key, Cmd+Tab, desktop switching) are intercepted or flagged. |
| **Desktop Lockdown** | Full-screen enforcement | The exam launches in a full-screen mode. Exiting full-screen triggers a warning and is logged. |
| | Start menu / taskbar detection | On Windows, detects attempts to open the Start menu, taskbar, or system tray — a common bypass on other platforms. |
| | Application switching detection | Monitors for process-level application switches beyond just browser tab changes. |
| | Optional: Lockdown browser/agent | A lightweight desktop agent that enforces OS-level restrictions for institutions that require maximum security. |
| **Code Integrity** | Plagiarism detection | Cross-submission similarity analysis across all students in a cohort. Detects copied code, renamed variables, and structural clones. |
| | AI-generation detection | Behavioral analysis of coding patterns — typing speed, pause patterns, edit history, and code style consistency — to flag potentially AI-generated submissions. |
| | Randomized problem variants | Each student receives a variant of the same problem — different input ranges, variable names, constraints, or problem phrasing — making answer-sharing ineffective. |
| | Submission integrity | Timestamps, keystroke logs, and edit history are recorded to verify the code was written during the exam window. |
| **Session Control** | Timed sessions | Strict countdown timer. Auto-submits when time expires. |
| | Single-session enforcement | Once an exam is started, it cannot be restarted or opened in another browser/device. |
| | IP/device fingerprinting | Detects if the same exam is being accessed from multiple locations or devices. |

#### Exam Workflow
```
Student opens exam → System verifies identity
        │
        ▼
Environment locks down (full-screen, restrictions activate)
        │
        ▼
Student receives randomized problem variant
        │
        ▼
Codes solution in locked-down editor
        │
        ▼
Can "Run" against visible test cases (limited attempts, if configured)
        │
        ▼
Clicks "Submit" → Code graded against all test cases (including hidden)
        │
        ▼
Session ends → Lockdown releases
        │
        ▼
Instructor reviews: score + anti-cheat flags + edit history
```

---

### Pillar 4: AI Tutor *(Learning Mode Only)*

An integrated AI assistant available **only in learning modules and practice** — never during proctored assessments.

**Design Philosophy:** The AI helps students *understand* — it does not write code for them.

**What the AI will do:**
- **Syntax help:** "How do I declare an array in Java?" → Explains syntax with a generic example, does not write the student's solution.
- **Logic guidance:** "My loop isn't terminating" → Asks guiding questions ("What's your loop condition? When does it change?") rather than fixing the code.
- **Error explanation:** "What does NullPointerException mean?" → Explains the concept and common causes, points the student to the relevant line.
- **Concept reinforcement:** "What's the difference between an ArrayList and a LinkedList?" → Provides a conceptual explanation with trade-offs.
- **Hints, not answers:** For practice problems, the AI can provide progressively stronger hints (Hint 1: general approach → Hint 2: algorithm suggestion → Hint 3: pseudocode outline) but never the full solution code.

**What the AI will NOT do:**
- Write complete solutions or functions.
- Directly fix the student's code by rewriting it.
- Provide copy-pasteable code blocks that solve the assigned problem.

**Institutional Control:**
- Institutions can configure the AI's behavior: how many hints per problem, whether the AI is available at all for certain modules, and the level of assistance provided.

---

## 🏢 Deployment & Multi-Institution Model

### SaaS Platform
- DockGrade is deployed as a centralized cloud platform, sold to multiple educational institutions.
- Each institution gets its own isolated tenant with separate data, branding, and configuration.

### Institutional Customization
Each institution controls:

| What They Control | Examples |
|---|---|
| **Learning content** | Upload their own lessons, videos, and practice problems, or customize DockGrade's built-in library. |
| **Exam questions** | Create their own problem bank with custom test cases for assessments. |
| **Grading policies** | Define scoring rubrics, partial credit rules, and passing thresholds. |
| **Curriculum structure** | Arrange modules and assessments in their own sequence. |
| **AI tutor settings** | Enable/disable the AI, configure hint levels, restrict for certain modules. |
| **Anti-cheat strictness** | Choose which lockdown features to enforce (e.g., some may not need desktop-level lockdown). |
| **Branding** | Custom logo, colors, and institution name on the platform. |

### Licensing Model (Tentative)
- Per-institution subscription (annual or per-semester).
- Tiered pricing based on number of students and feature set (e.g., basic coding engine vs. full proctoring + AI).

---

## 🗺️ Roadmap

### Phase 1: Foundation *(Current Semester)*
- Core coding engine: browser-based editor → containerized execution → test case grading.
- Problem creation with visible and hidden test cases.
- Java and Python support.
- Docker Compose orchestration.
- Basic instructor and student interfaces.

### Phase 2: Platform Maturity
- User authentication and role management (instructor, student, admin).
- Course/classroom management (invitations, enrollment).
- Submission history and detailed gradebook.
- Additional language support (C, C++, JavaScript).
- Performance monitoring and infrastructure dashboards.

### Phase 3: Learning Modules
- Content authoring tools for institutions.
- Text, video, and interactive code lessons.
- Practice problem sets with progression tracking.
- Module completion gating for assessments.

### Phase 4: Proctored Assessment
- Browser lockdown and anti-cheat enforcement.
- Randomized problem variant generation.
- Plagiarism and code similarity detection.
- Exam session management and proctoring dashboard.
- Optional desktop lockdown agent.

### Phase 5: AI Tutor & Scale
- Integrated AI assistant for learning mode.
- Configurable AI behavior per institution.
- Multi-institution SaaS deployment.
- Tenant isolation, branding, and billing.

---

## 🎯 Summary

| Aspect | Details |
|---|---|
| **What** | All-in-one platform for learning, practicing, and assessing programming. |
| **Who** | Educational institutions teaching practical programming subjects. |
| **Core** | LeetCode-style containerized code execution with automated test case grading. |
| **Learn** | Customizable learning modules with text, video, and interactive code exercises. |
| **Assess** | Proctored exams with comprehensive anti-cheat and randomized problem variants. |
| **AI** | Integrated tutor that guides understanding without writing code for students. |
| **Deploy** | Multi-institution SaaS with full institutional customization. |
| **Languages** | Starting with Java & Python, expanding to C, C++, JavaScript, Go, Rust, and more. |
