/**
 * ProblemDescription — renders the markdown problem statement.
 * Developer B: implement in Phase B1.
 *
 * TODO:
 * - Use react-markdown to render description
 * - Show title + difficulty badge (green/yellow/red)
 */

import ReactMarkdown from 'react-markdown'

interface ProblemDescriptionProps {
  title: string
  difficulty: 'easy' | 'medium' | 'hard'
  description: string
}

export default function ProblemDescription({
  title,
  difficulty,
  description,
}: ProblemDescriptionProps) {
  return (
    <div className="p-6 overflow-y-auto h-full bg-white dark:bg-zinc-950 text-zinc-800 dark:text-zinc-100 flex flex-col gap-4 transition-colors">
      <div>
        <h1 className="text-2xl font-bold text-zinc-950 dark:text-white tracking-tight">{title}</h1>
        <div className="mt-2 flex items-center gap-2">
          <span
            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider border
              ${
                difficulty === 'easy'
                  ? 'bg-green-500/10 text-green-605 dark:text-green-400 border-green-500/20'
                  : difficulty === 'medium'
                    ? 'bg-yellow-500/10 text-yellow-605 dark:text-yellow-400 border-yellow-500/20'
                    : 'bg-red-500/10 text-red-605 dark:text-red-400 border-red-500/20'
              }`}
          >
            {difficulty}
          </span>
          <span className="text-zinc-400 dark:text-zinc-500 text-xs">•</span>
          <span className="text-zinc-500 dark:text-zinc-400 text-xs font-medium">Java (JDK 21)</span>
        </div>
      </div>

      <div className="border-t border-zinc-200 dark:border-zinc-800/80 my-1"></div>

      <div className="text-zinc-700 dark:text-zinc-300 text-sm leading-relaxed">
        <ReactMarkdown
          components={{
            h1: ({ ...props }) => <h1 className="text-xl font-bold text-zinc-905 dark:text-white mt-6 mb-3" {...props} />,
            h2: ({ ...props }) => (
              <h2 className="text-lg font-bold text-zinc-905 dark:text-white mt-5 mb-2 border-b border-zinc-200 dark:border-zinc-805 pb-1" {...props} />
            ),
            h3: ({ ...props }) => <h3 className="text-md font-bold text-zinc-800 dark:text-zinc-100 mt-4 mb-2" {...props} />,
            p: ({ ...props }) => <p className="mb-4 text-zinc-600 dark:text-zinc-300 leading-relaxed font-sans" {...props} />,
            ul: ({ ...props }) => <ul className="list-disc pl-5 mb-4 space-y-1 text-zinc-600 dark:text-zinc-300" {...props} />,
            ol: ({ ...props }) => <ol className="list-decimal pl-5 mb-4 space-y-1 text-zinc-600 dark:text-zinc-300" {...props} />,
            li: ({ ...props }) => <li className="mb-1" {...props} />,
            code: ({ className, children, ...props }) => {
              const match = /language-(\w+)/.exec(className || '')
              const inline = !match
              return inline ? (
                <code
                  className="bg-zinc-100 dark:bg-zinc-905 text-orange-600 dark:text-orange-400 px-1.5 py-0.5 rounded font-mono text-xs border border-zinc-200 dark:border-zinc-800/50"
                  {...props}
                >
                  {children}
                </code>
              ) : (
                <pre className="bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded p-4 font-mono text-xs text-zinc-800 dark:text-zinc-200 my-4 overflow-x-auto leading-normal">
                  <code className={className} {...props}>
                    {children}
                  </code>
                </pre>
              )
            },
            strong: ({ ...props }) => <strong className="font-semibold text-zinc-950 dark:text-white" {...props} />,
            blockquote: ({ ...props }) => (
              <blockquote className="border-l-4 border-zinc-300 dark:border-zinc-700 pl-4 my-4 italic text-zinc-500 dark:text-zinc-400" {...props} />
            ),
          }}
        >
          {description}
        </ReactMarkdown>
      </div>
    </div>
  )
}
