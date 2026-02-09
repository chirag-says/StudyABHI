# Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Next.js   │  │  Mobile App │  │  Admin Panel│             │
│  │     Web     │  │  (Future)   │  │  (Future)   │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                      │
└─────────┴────────────────┴────────────────┴─────────────────────┘
                           │
                    ┌──────▼──────┐
                    │  API Gateway │
                    │    (NGINX)   │
                    └──────┬──────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                       API Layer                                   │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   FastAPI   │  │ Quiz Service│  │ RAG Service │             │
│  │   Backend   │  │             │  │             │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                      │
└─────────┴────────────────┴────────────────┴─────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                      Data Layer                                   │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ PostgreSQL  │  │    Redis    │  │   Qdrant    │             │
│  │  (Primary)  │  │   (Cache)   │  │  (Vectors)  │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

## Key Architectural Decisions

### 1. Monorepo Structure
- **Decision**: Use Turborepo for monorepo management
- **Rationale**: Enables code sharing, unified CI/CD, and easy cross-package development

### 2. Backend Framework
- **Decision**: FastAPI with async SQLAlchemy
- **Rationale**: High performance, automatic OpenAPI docs, excellent Python async support

### 3. Frontend Framework
- **Decision**: Next.js 14 with App Router
- **Rationale**: Server-side rendering, file-based routing, React Server Components

### 4. Database
- **Decision**: PostgreSQL with async driver
- **Rationale**: Robust, proven, excellent async support with asyncpg

### 5. Authentication
- **Decision**: JWT with access/refresh token pattern
- **Rationale**: Stateless, scalable, standard industry practice

### 6. AI Services
- **Decision**: Separate microservices for AI features
- **Rationale**: Enables independent scaling, different compute requirements

## Data Flow

1. User interacts with Next.js frontend
2. Frontend makes API calls to FastAPI backend
3. Backend authenticates using JWT
4. Backend interacts with PostgreSQL for data persistence
5. AI services (RAG, Quiz) are called asynchronously
6. Responses are cached in Redis when appropriate
7. Vector operations use Qdrant for semantic search
