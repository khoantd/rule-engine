import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import App from './App'
import { Dashboard, ExecutePage } from './pages'

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'rules', element: <div>Rules Page - Coming Soon</div> },
      { path: 'conditions', element: <div>Conditions Page - Coming Soon</div> },
      { path: 'actions', element: <div>Actions Page - Coming Soon</div> },
      { path: 'rulesets', element: <div>Rulesets Page - Coming Soon</div> },
      { path: 'execute', element: <ExecutePage /> },
      { path: 'batch', element: <div>Batch Execution Page - Coming Soon</div> },
      { path: 'workflow', element: <div>Workflow Page - Coming Soon</div> },
      { path: 'dmn', element: <div>DMN Page - Coming Soon</div> },
      { path: 'history', element: <div>History Page - Coming Soon</div> },
      { path: 'settings', element: <div>Settings Page - Coming Soon</div> },
    ],
  },
])

export default function Router() {
  return <RouterProvider router={router} />
}
