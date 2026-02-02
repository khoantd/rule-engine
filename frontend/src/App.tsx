import { useEffect } from 'react'
import { Outlet, useLocation, Link } from 'react-router-dom'
import { Toaster } from '@/components/ui/toaster'
import { Header } from '@/components/layout/Header'
import { Sidebar } from '@/components/layout/Sidebar'
import { useUIStore } from '@/stores'

function App() {
  const { theme } = useUIStore()
  const location = useLocation()

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [theme])

  const hideSidebar = location.pathname === '/' || location.pathname.startsWith('/execute')

  return (
    <div className="min-h-screen bg-background">
      <Link to="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground rounded">
        Skip to main content
      </Link>
      <Header />
      <div className="flex">
        {!hideSidebar && <Sidebar />}
        <main id="main-content" className="flex-1 p-6 overflow-auto">
          <Outlet />
        </main>
      </div>
      <Toaster />
    </div>
  )
}

export default App
