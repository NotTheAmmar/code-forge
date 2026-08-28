# CodeForge — Frontend Documentation (TA-1 Phase)

This document provides an overview of the frontend implementation completed for the **TA-1 Phase** of CodeForge. It explains the features, components, theme styling, and the mock integration layer so other developers can understand the structure.

---

## 🎨 Theme & Design Language
The design is modeled after the **Striver's A2Z DSA sheet** visual scheme:
*   **Default theme**: Deep slate/zinc dark mode.
*   **Accent color**: Vibrant orange/red-orange (`#f97316` / `#ff5533`).
*   **Light theme**: Supports clean white/slate backgrounds with high-contrast text.
*   **Transitions**: Smooth transitions (`transition-colors duration-200`) applied to root nodes.

---

## 🧩 Key Additions & Files

### 1. Global Theme Engine
*   **[`frontend/src/context/ThemeContext.tsx`](./frontend/src/context/ThemeContext.tsx)**: Implements a global `ThemeProvider` using React Context. Toggles the `dark` class on the `<html>` root node, sets the browser's `colorScheme`, and persists preference in `localStorage`.
*   **[`frontend/tailwind.config.js`](./frontend/tailwind.config.js)**: Configured `darkMode: 'class'` to allow manual theme toggling via class selectors rather than prefers-color-scheme media queries.
*   **[`frontend/src/vite-env.d.ts`](./frontend/src/vite-env.d.ts)**: Added Vite client typings to resolve side-effect asset imports (like `import './index.css'`) under TypeScript's strict module resolution.

### 2. Mock API Fallback Layer
*   **[`frontend/src/api/client.ts`](./frontend/src/api/client.ts)**: Intercepts network failures. If the backend API is unreachable, the client catches the error and redirects calls to an in-memory data store containing mock details for `hello-world`, `two-sum`, and `fizzbuzz`.
*   **Simulation Engine**: Includes an async simulation runner inside the API client. When a code submission is triggered, it spawns a simulated timer representing backend compilation and execution, transitioning status from `queued` -> `running` -> `completed` / `compile_error` / `timeout` with representative logs.

### 3. Pages
*   **[`frontend/src/pages/ProblemListPage.tsx`](./frontend/src/pages/ProblemListPage.tsx)**: 
    *   Renders a statistics grid showing overall completion stats, active languages, and database sandbox health status.
    *   Tracks problem completion checkmarks using `localStorage` keys matching `solved_<slug>`.
    *   Adapts tables, columns, and badges dynamically between light and dark modes.
*   **[`frontend/src/pages/ProblemPage.tsx`](./frontend/src/pages/ProblemPage.tsx)**:
    *   Builds the workspace structure with horizontal resizable split-panes via `react-resizable-panels`.
    *   Handles code state hooks, submission click handlers, and queries results via short polling.

### 4. Components
*   **[`frontend/src/components/CodeEditor.tsx`](./frontend/src/components/CodeEditor.tsx)**:
    *   Integrates Monaco Editor via `@monaco-editor/react`.
    *   Binds the editor theme context directly to the global theme (`vs-dark` in dark mode, `light` in light mode).
    *   Configures options like auto-layout resize listener, line numbers, and disabled minimap.
*   **[`frontend/src/components/ProblemDescription.tsx`](./frontend/src/components/ProblemDescription.tsx)**:
    *   Uses `ReactMarkdown` to parse and render Markdown problem definitions.
    *   Overrides rendering components for list bullets, bold text, inline code highlights, block quotes, and block pre-formatted text to match the theme.
*   **[`frontend/src/components/TestCasePanel.tsx`](./frontend/src/components/TestCasePanel.tsx)**:
    *   Renders tab selectors for each case, showing green dots for passing inputs and red for failures.
    *   Displays details (stdin, expected stdout, actual stdout, execution duration) for visible cases.
    *   Hides all logs (except pass/fail status) for hidden cases to prevent hardcoded cheats.
    *   Renders compile error stack traces inside a dedicated console console widget when syntax/build errors are caught.

---

## 🚀 How to Run & Verify

1. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```
2. Launch Vite local dev server:
   ```bash
   npm run dev
   ```
3. Test code submissions with the following mock triggers in Monaco Editor:
    *   **Syntax / Compile Error**: Include the string `syntax_error_here` in the solution code.
    *   **Runtime Error**: Include the string `runtime_error_here` or a `/ 0` division.
    *   **Time Limit Exceeded**: Include an infinite loop or `while(true)`.
    *   **Failed Case**: Leave the code empty or unmodified.
    *   **Success Solution**: Write a standard correct java format solution longer than 50 characters.
