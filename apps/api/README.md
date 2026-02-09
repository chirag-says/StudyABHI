# FastAPI Backend

Production-ready FastAPI backend for the UPSC AI Platform.

## Features

- ✅ JWT Authentication (Access + Refresh tokens)
- ✅ Environment-based Configuration
- ✅ Async SQLAlchemy ORM
- ✅ PostgreSQL with Alembic Migrations
- ✅ Modular Architecture
- ✅ Pydantic Validation
- ✅ CORS Support
- ✅ Health Check Endpoints

## Project Structure

```
apps/api/
├── alembic/                  # Database migrations
│   ├── versions/             # Migration files
│   ├── env.py               # Alembic environment
│   └── script.py.mako       # Migration template
├── app/
│   ├── api/                  # API routes
│   │   └── v1/
│   │       ├── endpoints/    # Route handlers
│   │       │   ├── auth.py   # Authentication routes
│   │       │   ├── users.py  # User management
│   │       │   └── health.py # Health checks
│   │       └── router.py     # v1 router
│   ├── core/                 # Core modules
│   │   ├── config.py         # Settings
│   │   ├── database.py       # DB connection
│   │   ├── security.py       # JWT & hashing
│   │   └── dependencies.py   # FastAPI deps
│   ├── models/               # SQLAlchemy models
│   │   └── user.py          # User model
│   ├── schemas/              # Pydantic schemas
│   │   ├── user.py          # User schemas
│   │   └── auth.py          # Auth schemas
│   ├── services/             # Business logic
│   │   ├── user_service.py  # User operations
│   │   └── auth_service.py  # Auth operations
│   └── main.py              # Application entry
├── .env.example             # Environment template
├── alembic.ini              # Alembic config
├── Dockerfile               # Production container
└── requirements.txt         # Dependencies
```

## Quick Start

### 1. Setup Virtual Environment

```bash
cd apps/api
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your values
```

### 4. Setup Database

```bash
# Create PostgreSQL database
createdb upsc_db

# Run migrations
alembic upgrade head
```

### 5. Run Development Server

```bash
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login user |
| POST | `/api/v1/auth/refresh` | Refresh tokens |
| POST | `/api/v1/auth/logout` | Logout user |
| GET | `/api/v1/auth/me` | Get current user |

### Users

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/users/me` | Get profile |
| PATCH | `/api/v1/users/me` | Update profile |
| POST | `/api/v1/users/me/change-password` | Change password |
| DELETE | `/api/v1/users/me` | Deactivate account |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/health/live` | Liveness probe |
| GET | `/api/v1/health/ready` | Readiness probe |

## Environment Variables

See `.env.example` for all available configuration options.

## License

MIT
