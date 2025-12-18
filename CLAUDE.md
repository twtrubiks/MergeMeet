# MergeMeet Development Guide

> For detailed development workflow, use **Skill: mergemeet-quickstart**

---

## Project Info

- **Project**: MergeMeet Dating Platform
- **Tech Stack**: FastAPI + Vue 3 + PostgreSQL + PostGIS + Redis
- **Stage**: MVP (Week 1-6)
- **Test Coverage**: >80%

---

## Quick Start (3 Steps)

```bash
# 1. Start infrastructure
docker compose up -d

# 2. Start backend (http://localhost:8000/docs)
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 3. Start frontend (http://localhost:5173)
cd frontend && npm run dev
```

---

## Available Skills

| Skill | Purpose |
|-------|---------|
| **api-routing-standards** | API routing rules - enforces "no trailing slash" to prevent 404 errors |
| **backend-dev-fastapi** | FastAPI + SQLAlchemy 2.0 Async development patterns |
| **frontend-dev-vue3** | Vue 3 Composition API + Pinia development patterns |
| **mergemeet-quickstart** | Complete development workflow, commands, and troubleshooting |
| **project-audit** | Project health check - feature completeness and consistency |

### Skills Structure

```
.claude/skills/
├── api-routing-standards/
│   ├── SKILL.md
│   └── references/           # Trailing slash rules, RESTful principles
├── backend-dev-fastapi/
│   └── SKILL.md
├── frontend-dev-vue3/
│   └── SKILL.md
├── mergemeet-quickstart/
│   ├── SKILL.md
│   └── references/           # Commands, tools, troubleshooting
└── project-audit/
    ├── SKILL.md
    └── references/           # Feature status, known issues
```

---

## Critical Rule: No Trailing Slash

All API endpoints must NOT use trailing slashes. This is enforced by `redirect_slashes=False`.

```python
# Correct
@router.get("")                  # GET /api/profile
@router.put("/interests")        # PUT /api/profile/interests

# Wrong (causes 404)
@router.get("/")                 # 404
@router.put("/interests/")       # 404
```

```javascript
// Frontend must also have no trailing slash
await axios.get('/api/profile')          // Correct
await axios.get('/api/profile/')         // 404
```

For details, use **Skill: api-routing-standards**

---

## Project Structure

```
mergemeet/
├── backend/              # FastAPI
│   ├── app/api/         # API routes
│   ├── app/models/      # SQLAlchemy models
│   └── tests/           # pytest tests
├── frontend/            # Vue 3
│   └── src/
│       ├── views/       # Page components
│       ├── components/  # Reusable components
│       └── stores/      # Pinia stores
└── .claude/skills/      # Claude Code skills
```

---

## Common Commands

```bash
# Database
docker exec -it mergemeet-db psql -U mergemeet -d mergemeet

# Testing
cd backend && pytest -v --cov=app

# Reset
docker compose down -v && docker compose up -d
```

For complete command list, use **Skill: mergemeet-quickstart**

---

## Related Documentation

- **README.md** - Project overview
- **ARCHITECTURE.md** - Technical architecture
- **QUICKSTART.md** - Quick start guide
- **docs/INDEX.md** - Documentation index

---

## Core Principles

1. **No trailing slash** - All API endpoints without `/` suffix
2. **Async first** - Backend uses async/await
3. **Composition API** - Frontend uses `<script setup>`
4. **Test driven** - TDD development workflow
5. **Use Skills** - Reference skills during development
