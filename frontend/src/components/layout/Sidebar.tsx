import { Home, BookOpen, PlaySquare, FileText, Settings, History, Layers, ListTree } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import { cn } from '@/lib/cn'
import { useUIStore } from '@/stores'

const navItems = [
  { icon: Home, label: 'Dashboard', path: '/' },
  {
    icon: PlaySquare,
    label: 'Execute',
    children: [
      { label: 'Single', path: '/execute' },
      { label: 'Batch', path: '/batch' },
      { label: 'Workflow', path: '/workflow' },
      { label: 'DMN', path: '/dmn' },
    ],
  },
  { icon: BookOpen, label: 'Rules', path: '/rules' },
  { icon: ListTree, label: 'Conditions', path: '/conditions' },
  { icon: FileText, label: 'Actions', path: '/actions' },
  { icon: Layers, label: 'Rulesets', path: '/rulesets' },
  { icon: History, label: 'History', path: '/history' },
  { icon: Settings, label: 'Settings', path: '/settings' },
]

export function Sidebar() {
  const { sidebarOpen } = useUIStore()
  const location = useLocation()

  return (
    <aside
      className={cn(
        'w-64 border-r bg-background flex flex-col transition-all duration-300',
        'fixed inset-y-0 left-0 z-40 lg:static lg:translate-x-0',
        !sidebarOpen && '-translate-x-full lg:block lg:opacity-100 lg:translate-x-0',
        sidebarOpen && 'translate-x-0',
      )}
    >
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = item.path === location.pathname

          if (item.children) {
            return (
              <div key={item.label} className="space-y-1">
                <div className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-muted-foreground">
                  <Icon className="h-4 w-4" />
                  {item.label}
                </div>
                {item.children.map((child) => {
                  const isChildActive = child.path === location.pathname
                  return (
                    <Link
                      key={child.path}
                      to={child.path}
                      className={cn(
                        'flex items-center gap-2 px-3 py-2 text-sm rounded-md ml-6',
                        isChildActive
                          ? 'bg-primary text-primary-foreground'
                          : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                      )}
                    >
                      {child.label}
                    </Link>
                  )
                })}
              </div>
            )
          }

          return (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                'flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          )
        })}
      </nav>
    </aside>
  )
}
