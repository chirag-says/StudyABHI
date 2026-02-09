# Next.js Frontend

Production-ready Next.js 14 frontend for UPSC AI Platform with App Router, Tailwind CSS, and shadcn/ui.

## Features

- ✅ Next.js 14 with App Router
- ✅ Tailwind CSS with shadcn/ui components
- ✅ Authentication-ready structure
- ✅ Protected routes with auth guards
- ✅ Zustand state management
- ✅ API service layer with Axios
- ✅ Form validation with Zod & React Hook Form
- ✅ Toast notifications
- ✅ SEO optimized

## Project Structure

```
apps/web/
├── src/
│   ├── app/                      # Next.js App Router
│   │   ├── (protected)/          # Protected routes (requires auth)
│   │   │   ├── dashboard/        # Dashboard pages
│   │   │   └── layout.tsx        # Protected layout with auth guard
│   │   ├── auth/                 # Authentication pages
│   │   │   ├── login/            # Login page
│   │   │   ├── register/         # Registration page
│   │   │   └── layout.tsx        # Auth layout
│   │   ├── globals.css           # Global styles
│   │   ├── layout.tsx            # Root layout
│   │   └── page.tsx              # Landing page
│   │
│   ├── components/               # React components
│   │   ├── auth/                 # Auth-related components
│   │   │   └── protected-route.tsx
│   │   └── ui/                   # shadcn/ui components
│   │       ├── button.tsx
│   │       ├── card.tsx
│   │       ├── input.tsx
│   │       ├── label.tsx
│   │       └── toast.tsx
│   │
│   ├── hooks/                    # Custom React hooks
│   │   └── use-toast.ts
│   │
│   ├── lib/                      # Utility functions
│   │   └── utils.ts
│   │
│   ├── providers/                # React context providers
│   │   └── auth-provider.tsx
│   │
│   ├── services/                 # API service layer
│   │   ├── api.ts                # Axios instance
│   │   ├── auth.service.ts       # Auth API methods
│   │   └── index.ts
│   │
│   └── stores/                   # Zustand stores
│       └── auth-store.ts
│
├── .env.example                  # Environment template
├── next.config.js                # Next.js config
├── package.json                  # Dependencies
├── postcss.config.js             # PostCSS config
├── tailwind.config.ts            # Tailwind config
└── tsconfig.json                 # TypeScript config
```

## Quick Start

### 1. Install Dependencies

```bash
cd apps/web
npm install
```

### 2. Configure Environment

```bash
cp .env.example .env.local
# Edit .env.local with your API URL
```

### 3. Run Development Server

```bash
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000)

## Pages

| Route | Description |
|-------|-------------|
| `/` | Landing page |
| `/auth/login` | Login page |
| `/auth/register` | Registration page |
| `/dashboard` | Main dashboard (protected) |
| `/dashboard/courses` | Courses page (protected) |
| `/dashboard/quiz` | Quiz page (protected) |
| `/dashboard/profile` | User profile (protected) |

## Adding New shadcn/ui Components

To add more shadcn/ui components, you can either:

1. Copy from the shadcn/ui website
2. Use the CLI: `npx shadcn@latest add [component]`

## License

MIT
