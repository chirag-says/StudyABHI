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
- Redis (optional, for caching)
- Docker & Docker Compose (recommended)

---

## Option 1: Run with Docker (Recommended)

The easiest way to get started is using Docker Compose, which sets up all services automatically.

```bash
# Clone the repository
git clone https://github.com/chirag-says/StudyABHI.git
cd StudyABHI

# Start all services (PostgreSQL, Redis, Qdrant, API, Web)
docker-compose up -d

# View logs
docker-compose logs -f
```

**Services will be available at:**
- 🌐 **Frontend**: http://localhost:3000
- 🔧 **Backend API**: http://localhost:8000
- 📚 **API Docs**: http://localhost:8000/docs
- 🗄️ **PostgreSQL**: localhost:5432
- 📦 **Redis**: localhost:6379
- 🔍 **Qdrant**: localhost:6333

---

## Option 2: Manual Setup (Development)

### Step 1: Clone & Install Dependencies

```bash
# Clone the repository
git clone https://github.com/chirag-says/StudyABHI.git
cd StudyABHI

# Install Node.js dependencies (for web app and turbo)
npm install
```

### Step 2: Setup PostgreSQL Database

Make sure PostgreSQL is running locally, then create a database:

```sql
-- Connect to PostgreSQL and run:
CREATE USER upsc_user WITH PASSWORD 'upsc_password';
CREATE DATABASE upsc_db OWNER upsc_user;
GRANT ALL PRIVILEGES ON DATABASE upsc_db TO upsc_user;
```

Or use Docker for just the database:

```bash
docker run -d --name upsc_postgres \
  -e POSTGRES_USER=upsc_user \
  -e POSTGRES_PASSWORD=upsc_password \
  -e POSTGRES_DB=upsc_db \
  -p 5432:5432 \
  postgres:15-alpine
```

### Step 3: Setup Backend (FastAPI)

```bash
# Navigate to the API directory
cd apps/api

# Create Python virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Copy environment file and configure
cp .env.example .env
# Edit .env file with your database credentials

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn app.main:app --reload --port 8000
```

**Backend will be available at:** http://localhost:8000
**API Documentation:** http://localhost:8000/docs

### Step 4: Setup Frontend (Next.js)

Open a new terminal:

```bash
# Navigate to the web directory
cd apps/web

# Copy environment file
cp .env.example .env.local

# Install dependencies (if not already done via root npm install)
npm install

# Start the development server
npm run dev
```

**Frontend will be available at:** http://localhost:3000

---

## 🔧 Environment Configuration

### Backend (`apps/api/.env`)

```env
# Application
APP_NAME="UPSC AI Platform"
DEBUG=true
ENVIRONMENT=development

# Server
HOST=0.0.0.0
PORT=8000
ALLOWED_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]

# Database (PostgreSQL)
DATABASE_URL=postgresql+asyncpg://upsc_user:upsc_password@localhost:5432/upsc_db

# Redis (optional)
REDIS_URL=redis://localhost:6379

# JWT Authentication (CHANGE IN PRODUCTION!)
SECRET_KEY=your-super-secret-key-change-this-in-production-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Frontend (`apps/web/.env.local`)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME="UPSC AI Platform"
NEXT_PUBLIC_ENABLE_AI_FEATURES=true
```

---

## 📝 Available Scripts

Run these commands from the **root directory**:

| Command | Description |
|---------|-------------|
| `npm run dev` | Start all services (web + api) with Turbo |
| `npm run dev:web` | Start only the Next.js frontend |
| `npm run dev:api` | Start only the FastAPI backend |
| `npm run build` | Build all packages |
| `npm run lint` | Lint all packages |
| `npm run db:migrate` | Run database migrations |
| `npm run db:generate` | Generate a new migration |

---

## 🐳 Docker Commands

```bash
# Start all services in background
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f

# Rebuild containers (after code changes)
docker-compose up -d --build

# Remove all data (fresh start)
docker-compose down -v
```

---

## 🧪 Testing

```bash
# Run backend tests
cd apps/api
pytest

# Run frontend tests
cd apps/web
npm run test
```

---

## 📱 API Endpoints

Once the backend is running, explore the API at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

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
