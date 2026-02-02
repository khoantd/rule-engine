import { useState, useEffect, useRef, useMemo } from 'react'
import { cn } from '@/lib/cn'

interface JsonEditorProps {
  value: Record<string, any>
  onChange: (value: Record<string, any>) => void
  readOnly?: boolean
  placeholder?: string
  className?: string
}

export function JsonEditor({ value, onChange, readOnly = false, placeholder, className }: JsonEditorProps) {
  const initialText = useMemo(() => JSON.stringify(value, null, 2), [])
  const [text, setText] = useState(initialText)
  const [error, setError] = useState<string | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    setText(JSON.stringify(value, null, 2))
    setError(null)
  }, [value])

  const handleChange = (newValue: string) => {
    setText(newValue)

    try {
      const parsed = JSON.parse(newValue)
      setError(null)
      onChange(parsed)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid JSON')
    }
  }

  const handleFormat = () => {
    try {
      const parsed = JSON.parse(text)
      setText(JSON.stringify(parsed, null, 2))
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid JSON')
    }
  }

  return (
    <div className={cn('relative', className)}>
      <textarea
        ref={textareaRef}
        value={text}
        onChange={(e) => !readOnly && handleChange(e.target.value)}
        readOnly={readOnly}
        placeholder={placeholder}
        className={cn(
          'min-h-[300px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 font-mono',
          error && 'border-destructive',
        )}
        style={{
          resize: 'vertical',
        }}
      />
      {error && <p className="text-sm text-destructive mt-2">{error}</p>}
      {!readOnly && (
        <button
          onClick={handleFormat}
          className="absolute top-2 right-2 px-2 py-1 text-xs bg-secondary rounded hover:bg-secondary/80"
        >
          Format
        </button>
      )}
    </div>
  )
}
