/**
 * ProblemDescription — renders the markdown problem statement.
 * Developer B: implement in Phase B1.
 *
 * TODO:
 * - Use react-markdown to render description
 * - Show title + difficulty badge (green/yellow/red)
 */

interface ProblemDescriptionProps {
  title: string
  difficulty: 'easy' | 'medium' | 'hard'
  description: string
}

const difficultyColor = {
  easy: 'text-green-400',
  medium: 'text-yellow-400',
  hard: 'text-red-400',
}

export default function ProblemDescription({
  title,
  difficulty,
  description,
}: ProblemDescriptionProps) {
  return (
    <div className="p-6 overflow-y-auto h-full">
      <h1 className="text-xl font-semibold mb-1">{title}</h1>
      <span className={`text-sm font-medium capitalize ${difficultyColor[difficulty]}`}>
        {difficulty}
      </span>
      {/* TODO Phase B1: replace pre with <ReactMarkdown> */}
      <pre className="mt-4 text-sm text-gray-300 whitespace-pre-wrap font-sans leading-relaxed">
        {description}
      </pre>
    </div>
  )
}
