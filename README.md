# 📚 UPSC AI Learning Platform

A scalable, AI-powered learning platform for UPSC preparation with future support for JEE/NEET.

## 🏗️ Monorepo Structure

```
upsc-ai-platform/
├── apps/                          # Application packages
│   ├── web/                       # Next.js 14 frontend (App Router)
│   └── api/                       # FastAPI backend
│
├── packages/                      # Shared packages
│   ├── shared-types/              # Shared TypeScript types
│   ├── shared-utils/              # Shared utilities
│   └── ui-components/             # Shared React components
│
├── services/                      # AI Microservices
│   ├── rag-service/               # RAG (Retrieval Augmented Generation)
│   ├── quiz-generator/            # AI Quiz Generation Service
│   └── summarizer/                # Content Summarization Service
│
├── infrastructure/                # Infrastructure as Code
│   ├── docker/                    # Docker configurations
│   ├── kubernetes/                # K8s manifests
│   └── terraform/                 # Cloud infrastructure
│
├── docs/                          # Documentation
│   ├── api/                       # API documentation
│   ├── architecture/              # Architecture decisions
│   └── guides/                    # Developer guides
│
├── scripts/                       # Build & deployment scripts
├── .github/                       # GitHub Actions workflows
├── docker-compose.yml             # Local development setup
├── turbo.json                     # Turborepo configuration
└── package.json                   # Root package.json
```

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Python 3.11+
- PostgreSQL 15+
- Docker & Docker Compose

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd upsc-ai-platform

# Install dependencies
npm install

# Setup Python virtual environment
cd apps/api
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Setup database
alembic upgrade head

# Start development servers
npm run dev
```

## 📁 Folder Explanation

| Folder | Purpose |
|--------|---------|
| `apps/web` | Next.js 14 frontend with App Router, Tailwind CSS, shadcn/ui |
| `apps/api` | FastAPI backend with JWT auth, SQLAlchemy ORM, Alembic migrations |
| `packages/shared-types` | TypeScript types shared between frontend and other services |
| `packages/shared-utils` | Common utilities (validation, formatting, etc.) |
| `packages/ui-components` | Reusable React components library |
| `services/rag-service` | RAG service for intelligent Q&A using vector embeddings |
| `services/quiz-generator` | AI-powered quiz generation from study materials |
| `services/summarizer` | Content summarization for notes and articles |
| `infrastructure/` | DevOps configurations (Docker, K8s, Terraform) |
| `docs/` | Project documentation and API specs |
| `scripts/` | Automation scripts for CI/CD and local development |

## 🎯 Exam Support Roadmap

- [x] UPSC (Current)
- [ ] JEE (Planned)
- [ ] NEET (Planned)

## 📄 License

MIT License
