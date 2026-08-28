/**
 * CodeEditor — Monaco Editor wrapper.
 * Developer B: implement in Phase B2.
 *
 * TODO:
 * - Language: java
 * - Theme: vs-dark
 * - Load starter code from props
 * - Font size 14, minimap off, line numbers on
 * - Call onChange with editor content on each change
 */

import Editor from '@monaco-editor/react'
import { useTheme } from '../context/ThemeContext'

interface CodeEditorProps {
  value: string
  onChange: (value: string) => void
  language?: string
}

export default function CodeEditor({ value, onChange, language = 'java' }: CodeEditorProps) {
  const { theme } = useTheme()

  return (
    <div className="w-full h-full bg-white dark:bg-zinc-950">
      <Editor
        height="100%"
        language={language}
        theme={theme === 'dark' ? 'vs-dark' : 'light'}
        value={value}
        onChange={(val) => onChange(val || '')}
        options={{
          fontSize: 14,
          minimap: { enabled: false },
          lineNumbers: 'on',
          automaticLayout: true,
          scrollBeyondLastLine: false,
          padding: { top: 12, bottom: 12 },
          scrollbar: {
            vertical: 'visible',
            horizontal: 'visible',
            verticalScrollbarSize: 8,
            horizontalScrollbarSize: 8,
          },
        }}
      />
    </div>
  )
}
