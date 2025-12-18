---
name: mergemeet-quickstart
description: This skill should be used when setting up the MergeMeet development environment, running services, troubleshooting issues, or learning the development workflow. It covers Docker, FastAPI, Vue 3, PostgreSQL, Redis, testing, and common commands.
---

# MergeMeet Quick Start Guide

## Purpose

To provide a complete development workflow guide for the MergeMeet project, including environment setup, common commands, and troubleshooting.

---

## Quick Start (3 Steps)

### Step 1: Start Infrastructure

```bash
# Start PostgreSQL and Redis
docker compose up -d

# Verify services
docker compose ps
# Expected: mergemeet-db (Up), mergemeet-redis (Up)
```

### Step 2: Start Backend

```bash
cd backend

# Install dependencies (first time)
pip install -r requirements.txt

# Start FastAPI
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API documentation: http://localhost:8000/docs

### Step 3: Start Frontend

```bash
cd frontend

# Install dependencies (first time)
npm install

# Start dev server
npm run dev
```

Application: http://localhost:5173/

---

## Common Commands

### Database

```bash
# Connect to PostgreSQL
docker exec -it mergemeet-db psql -U mergemeet -d mergemeet

# Common SQL commands
\dt                    # List tables
\d+ users              # Describe table
\q                     # Quit
```

### Database Migrations (Alembic)

```bash
cd backend

alembic revision --autogenerate -m "Add new field"
alembic upgrade head
alembic downgrade -1
alembic history
```

### Testing

```bash
cd backend

pytest                           # Run all tests
pytest -v                        # Verbose output
pytest --cov=app                 # With coverage
pytest tests/test_profile.py    # Specific file
```

### Docker

```bash
docker compose ps                # Status
docker compose logs -f postgres  # Follow logs
docker compose down              # Stop
docker compose down -v           # Stop and remove volumes
```

---

## Troubleshooting

### Backend Cannot Start

**Error**: `sqlalchemy.exc.OperationalError: could not connect to server`

```bash
# Check if database is running
docker compose ps

# Restart database
docker compose restart postgres

# Test connection
docker exec -it mergemeet-db psql -U mergemeet -d mergemeet -c "SELECT 1;"
```

### Frontend Cannot Connect to Backend

**Error**: `Network Error` or `CORS Error`

```bash
# Verify backend is running
curl http://localhost:8000/health

# Check CORS settings in backend/app/core/config.py
# Ensure CORS_ORIGINS includes "http://localhost:5173"
```

### API Returns 404

**Most common cause**: URL has trailing slash

```python
# Wrong
@router.get("/")           # 404

# Correct
@router.get("")
```

```javascript
// Wrong
await axios.get('/api/profile/')   // 404

// Correct
await axios.get('/api/profile')
```

See **api-routing-standards** skill for details.

---

## References

For detailed information:

| Topic | File |
|-------|------|
| All commands | [commands.md](references/commands.md) |
| Troubleshooting | [troubleshooting.md](references/troubleshooting.md) |
| Development tools | [tools.md](references/tools.md) |
| Git workflow | [workflows.md](references/workflows.md) |

---

## Related Skills

- **api-routing-standards** - API routing rules
- **backend-dev-fastapi** - Backend development
- **frontend-dev-vue3** - Frontend development
- **project-audit** - Project health check
