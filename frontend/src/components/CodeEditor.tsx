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

interface CodeEditorProps {
  value: string
  onChange: (value: string) => void
  language?: string
}

export default function CodeEditor({ value, onChange, language = 'java' }: CodeEditorProps) {
  // TODO Phase B2: replace with @monaco-editor/react <Editor /> component
  return (
    <textarea
      className="w-full h-full bg-gray-900 text-gray-100 font-mono text-sm p-4 resize-none outline-none"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={`// Write your ${language} solution here`}
      spellCheck={false}
    />
  )
}
