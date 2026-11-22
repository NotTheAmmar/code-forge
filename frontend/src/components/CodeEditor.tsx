/**
 * CodeEditor — Monaco Editor wrapper with multi-language & keybinding support.
 */

import Editor, { OnMount } from '@monaco-editor/react'
import { useRef } from 'react'
import { useTheme } from '../context/ThemeContext'

export type KeybindingMode = 'vscode' | 'vim' | 'emacs'

interface CodeEditorProps {
  value: string
  onChange: (value: string) => void
  language?: string
  keybindingMode?: KeybindingMode
  readOnly?: boolean
}

export default function CodeEditor({
  value,
  onChange,
  language = 'java',
  keybindingMode = 'vscode',
  readOnly = false,
}: CodeEditorProps) {
  const { theme } = useTheme()
  const editorRef = useRef<any>(null)

  // Map language string to Monaco's syntax highlighter
  const monacoLanguage = (() => {
    switch (language) {
      case 'c':
        return 'c'
      case 'cpp':
        return 'cpp'
      case 'python':
        return 'python'
      case 'java':
      default:
        return 'java'
    }
  })()

  const handleEditorDidMount: OnMount = (editor) => {
    editorRef.current = editor

    // Apply cursor & styling options based on keybinding preference
    if (keybindingMode === 'vim') {
      editor.updateOptions({
        cursorStyle: 'block',
        cursorBlinking: 'solid',
      })
    } else if (keybindingMode === 'emacs') {
      editor.updateOptions({
        cursorStyle: 'line',
        cursorBlinking: 'smooth',
      })
    } else {
      editor.updateOptions({
        cursorStyle: 'line',
        cursorBlinking: 'blink',
      })
    }
  }

  return (
    <div className="w-full h-full bg-white dark:bg-zinc-950 overflow-hidden">
      <Editor
        height="100%"
        language={monacoLanguage}
        theme={theme === 'dark' ? 'vs-dark' : 'light'}
        value={value}
        onChange={(val) => onChange(val || '')}
        onMount={handleEditorDidMount}
        options={{
          readOnly,
          fontSize: 14,
          fontFamily: "'Fira Code', 'JetBrains Mono', Menlo, Monaco, Consolas, monospace",
          minimap: { enabled: false },
          lineNumbers: 'on',
          automaticLayout: true,
          scrollBeyondLastLine: false,
          padding: { top: 12, bottom: 12 },
          tabSize: language === 'python' ? 4 : 2,
          wordWrap: 'on',
          cursorStyle: keybindingMode === 'vim' ? 'block' : 'line',
          cursorBlinking: keybindingMode === 'vim' ? 'solid' : 'smooth',
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
