# Rule Engine Frontend

Modern React frontend for the Rule Engine backend application.

## Tech Stack

- React 18 with TypeScript
- Vite 5
- React Router v6
- React Query (TanStack Query)
- Zustand (State Management)
- Tailwind CSS
- shadcn/ui (Component Library)
- Axios (HTTP Client)

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Installation

```bash
cd frontend
npm install
```

### Configuration

Create a `.env` file in the root directory:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_API_KEY=
VITE_APP_TITLE=Rule Engine
VITE_APP_VERSION=1.0.0
```

### Development

```bash
npm run dev
```

The application will be available at `http://localhost:3000`

### Build

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

## Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript type checking
- `npm run test` - Run unit tests
- `npm run test:coverage` - Run tests with coverage
- `npm run test:e2e` - Run E2E tests
- `npm run format` - Format code with Prettier

## Features

- Dashboard with stats and quick actions
- Rule management (CRUD)
- Condition management
- Action management
- Ruleset management
- Single rule execution
- Batch execution
- Workflow execution
- DMN support
- Execution history
- Settings

## Project Structure

```
frontend/
├── src/
│   ├── components/     # React components
│   ├── pages/          # Page components
│   ├── hooks/          # Custom React hooks
│   ├── services/       # API services
│   ├── stores/         # Zustand stores
│   ├── types/          # TypeScript types
│   ├── lib/            # Utilities
│   ├── config/         # Configuration
│   ├── App.tsx         # Main app component
│   ├── main.tsx        # Entry point
│   └── Router.tsx      # React Router configuration
├── public/             # Static assets
└── package.json
```

## Documentation

See [FRONTEND_SPEC.md](./FRONTEND_SPEC.md) for detailed specification.

## License

MIT
