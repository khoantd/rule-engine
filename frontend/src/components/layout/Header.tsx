import { Menu, X, Moon, Sun } from 'lucide-react'
import { useUIStore } from '@/stores'
import { Button } from '@/components/ui/button'

export function Header() {
  const { sidebarOpen, theme, actions } = useUIStore()

  const toggleTheme = () => {
    actions.setTheme(theme === 'light' ? 'dark' : 'light')
  }

  return (
    <header className="h-16 border-b flex items-center px-6 bg-background">
      <button
        onClick={actions.toggleSidebar}
        className="p-2 hover:bg-accent rounded-md lg:hidden"
        aria-label="Toggle sidebar"
      >
        {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>
      <h1 className="text-xl font-semibold ml-4">Rule Engine</h1>
      <div className="ml-auto flex items-center gap-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={toggleTheme}
          aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
        >
          {theme === 'light' ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
        </Button>
        <span className="text-sm text-muted-foreground hidden sm:inline-block">
          v{import.meta.env.VITE_APP_VERSION || '1.0.0'}
        </span>
      </div>
    </header>
  )
}
