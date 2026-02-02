import { useState } from 'react'
import { useExecuteSingle } from '@/hooks'
import { JsonEditor } from '@/components/common'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { LoadingSpinner } from '@/components/common'
import { Play, Download, Copy } from 'lucide-react'
import { downloadJson, copyToClipboard } from '@/lib/utils'
import { useToast } from '@/hooks'

export default function ExecutePage() {
  const templates = [
    { name: 'Comic Book', data: { issue: 35, title: 'Superman', publisher: 'DC' } },
    { name: 'Product', data: { productId: 'P001', price: 29.99, stock: 100 } },
    { name: 'Empty', data: {} },
  ]

  const [data, setData] = useState<Record<string, any>>(templates[0].data)
  const [dryRun, setDryRun] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  const executeMutation = useExecuteSingle()
  const { success: successToast, error: errorToast } = useToast()

  const handleExecute = async () => {
    setError(null)
    setResult(null)

    try {
      const response = await executeMutation.mutateAsync({
        data,
        dry_run: dryRun,
      })
      setResult(response)
      successToast('Rules executed successfully')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to execute rules')
      errorToast('Failed to execute rules')
    }
  }

  const handleDownload = () => {
    if (result) {
      downloadJson(result, `execution-${Date.now()}.json`)
    }
  }

  const handleCopy = async () => {
    if (result) {
      const success = await copyToClipboard(JSON.stringify(result, null, 2))
      if (success) {
        successToast('Result copied to clipboard')
      } else {
        errorToast('Failed to copy result')
      }
    }
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Execute Rules</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Input Data</CardTitle>
                <select
                  value={JSON.stringify(data)}
                  onChange={(e) => setData(JSON.parse(e.target.value))}
                  className="text-sm border rounded px-2 py-1"
                >
                  {templates.map((template, idx) => (
                    <option key={idx} value={JSON.stringify(template.data)}>
                      {template.name}
                    </option>
                  ))}
                </select>
              </div>
            </CardHeader>
            <CardContent>
              <JsonEditor value={data} onChange={setData} placeholder="Enter JSON data..." />
              <div className="mt-4 flex items-center justify-between gap-2">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={dryRun}
                    onChange={(e) => setDryRun(e.target.checked)}
                    className="rounded"
                  />
                  <span className="text-sm">Dry Run</span>
                </label>
                <Button variant="ghost" size="sm" onClick={() => setData(templates[0].data)}>
                  Reset
                </Button>
              </div>
              <Button
                className="w-full mt-4"
                onClick={handleExecute}
                disabled={executeMutation.isPending}
              >
                {executeMutation.isPending ? (
                  <>
                    <LoadingSpinner size="sm" className="mr-2" />
                    Executing...
                  </>
                ) : (
                  <>
                    <Play className="mr-2 h-4 w-4" />
                    Execute
                  </>
                )}
              </Button>
            </CardContent>
          </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Result</CardTitle>
            {result && (
              <div className="flex gap-2">
                <Button variant="ghost" size="sm" onClick={handleCopy}>
                  <Copy className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="sm" onClick={handleDownload}>
                  <Download className="h-4 w-4" />
                </Button>
              </div>
            )}
          </CardHeader>
          <CardContent>
            {executeMutation.isPending ? (
              <div className="flex items-center justify-center h-64">
                <LoadingSpinner size="lg" />
              </div>
            ) : error ? (
              <div className="p-4 rounded-lg bg-destructive/10 text-destructive border border-destructive">
                <p className="font-semibold">Error</p>
                <p className="text-sm mt-1">{error}</p>
              </div>
            ) : result ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Total Points</p>
                    <p className="text-2xl font-bold">{result.total_points}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Pattern</p>
                    <p className="text-2xl font-bold">{result.pattern_result}</p>
                  </div>
                </div>
                {result.action_recommendation && (
                  <div className="p-4 rounded-lg bg-primary/10 border border-primary">
                    <p className="text-sm text-muted-foreground">Action Recommendation</p>
                    <p className="text-xl font-semibold mt-1">{result.action_recommendation}</p>
                  </div>
                )}
                 {result.execution_time_ms && (
                   <div className="space-y-2">
                     <p className="text-sm text-muted-foreground">
                       Execution time: {result.execution_time_ms.toFixed(2)}ms
                     </p>
                     {result.correlation_id && (
                       <p className="text-xs text-muted-foreground">
                         Correlation ID: <code className="bg-muted px-1 rounded">{result.correlation_id}</code>
                       </p>
                     )}
                   </div>
                 )}
                {dryRun && result.rule_evaluations && (
                  <div className="space-y-2">
                    <h4 className="font-semibold">Rule Evaluations</h4>
                    <div className="max-h-64 overflow-y-auto space-y-2">
                      {result.rule_evaluations.map((ruleEval: any, idx: number) => (
                        <div
                          key={idx}
                          className={`p-3 rounded border ${
                            ruleEval.matched
                              ? 'bg-green-50 border-green-200 dark:bg-green-950 dark:border-green-800'
                              : 'bg-red-50 border-red-200 dark:bg-red-950 dark:border-red-800'
                          }`}
                        >
                          <div className="flex justify-between items-center">
                            <p className="font-medium">{ruleEval.rule_name}</p>
                            <span className="text-sm">{ruleEval.matched ? '✓ Matched' : '✗ Not Matched'}</span>
                          </div>
                          <p className="text-xs text-muted-foreground mt-1">{ruleEval.condition}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center text-muted-foreground py-12">
                Execute rules to see results
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
