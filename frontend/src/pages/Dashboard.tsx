import { useRules, useConditions, useActions, useRuleSets } from '@/hooks'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { BookOpen, FileText, Layers, Activity } from 'lucide-react'
import { LoadingSpinner } from '@/components/common'
import { Link } from 'react-router-dom'

export default function Dashboard() {
  const { data: rulesData, isLoading: rulesLoading } = useRules()
  const { data: conditionsData, isLoading: conditionsLoading } = useConditions()
  const { data: actionsData, isLoading: actionsLoading } = useActions()
  const { data: rulesetsData, isLoading: rulesetsLoading } = useRuleSets()

  const isLoading = rulesLoading || conditionsLoading || actionsLoading || rulesetsLoading

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  const stats = [
    {
      title: 'Total Rules',
      value: rulesData?.count || 0,
      icon: BookOpen,
      color: 'text-blue-500',
      bgColor: 'bg-blue-50 dark:bg-blue-950',
      link: '/rules',
    },
    {
      title: 'Conditions',
      value: conditionsData?.count || 0,
      icon: FileText,
      color: 'text-green-500',
      bgColor: 'bg-green-50 dark:bg-green-950',
      link: '/conditions',
    },
    {
      title: 'Actions',
      value: actionsData?.count || 0,
      icon: Activity,
      color: 'text-purple-500',
      bgColor: 'bg-purple-50 dark:bg-purple-950',
      link: '/actions',
    },
    {
      title: 'Rulesets',
      value: rulesetsData?.count || 0,
      icon: Layers,
      color: 'text-orange-500',
      bgColor: 'bg-orange-50 dark:bg-orange-950',
      link: '/rulesets',
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Dashboard</h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => {
          const Icon = stat.icon
          return (
            <Link key={stat.title} to={stat.link}>
              <Card className="hover:shadow-lg transition-shadow cursor-pointer">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    {stat.title}
                  </CardTitle>
                  <div className={`${stat.bgColor} ${stat.color} p-2 rounded-lg`}>
                    <Icon className="h-5 w-5" />
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{stat.value}</div>
                </CardContent>
              </Card>
            </Link>
          )
        })}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Link to="/execute">
            <Button className="w-full" variant="default">
              Execute Rules
            </Button>
          </Link>
          <Link to="/batch">
            <Button className="w-full" variant="outline">
              Batch Execute
            </Button>
          </Link>
          <Link to="/workflow">
            <Button className="w-full" variant="outline">
              Execute Workflow
            </Button>
          </Link>
          <Link to="/dmn">
            <Button className="w-full" variant="outline">
              Execute DMN
            </Button>
          </Link>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Getting Started</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-semibold">
              1
            </div>
            <div>
              <h3 className="font-semibold">Create Rules</h3>
              <p className="text-sm text-muted-foreground">
                Define your business rules with conditions and actions
              </p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-semibold">
              2
            </div>
            <div>
              <h3 className="font-semibold">Test Rules</h3>
              <p className="text-sm text-muted-foreground">
                Execute your rules against sample data to verify behavior
              </p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-semibold">
              3
            </div>
            <div>
              <h3 className="font-semibold">Batch Process</h3>
              <p className="text-sm text-muted-foreground">
                Process multiple items efficiently using batch execution
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
