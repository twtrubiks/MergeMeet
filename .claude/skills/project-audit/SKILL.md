---
name: project-audit
description: This skill should be used when evaluating the MergeMeet project's health status. It helps check feature completeness, frontend-backend consistency, potential bugs, and user flow logic. Use before developing new features or during sprint reviews.
---

# Project Audit

## Purpose

To comprehensively check the MergeMeet dating platform's health status, ensuring:
1. Feature completeness for a dating app
2. Frontend-backend API consistency
3. Bug detection
4. User flow logic

---

## Audit Checklist

### Core Dating App Features

| Category | Check Points |
|----------|-------------|
| Authentication | Registration, login, email verification, password reset |
| Profile | Edit, photo upload, moderation, interests |
| Discovery | Browse candidates, like/skip, preferences |
| Chat | Real-time messaging, read status, content moderation |
| Safety | Block, report, report history |
| Notifications | Real-time notifications, notification center |
| Admin | Dashboard, report handling, user management |

### Frontend-Backend Consistency

To check consistency between API endpoints and frontend calls:

```bash
# List all backend API endpoints
grep -r "@router\." backend/app/api/ --include="*.py"

# List all frontend API calls
grep -r "axios\." frontend/src/ --include="*.js" --include="*.vue"
```

### Testing

```bash
# Run backend tests with coverage
cd backend && pytest -v --cov=app

# Run frontend tests
cd frontend && npm run test
```

---

## Audit Process

### Step 1: Feature Completeness

```bash
# Check backend API modules
ls backend/app/api/

# Check frontend pages and components
ls frontend/src/views/
ls frontend/src/components/
ls frontend/src/stores/
```

### Step 2: Frontend-Backend Gap Analysis

Compare API endpoints with frontend calls to identify:
- Backend APIs without frontend implementation
- Frontend calls to non-existent APIs

### Step 3: User Flow Testing

Test complete user flows:
1. **Registration**: Register → Verify email → Create profile
2. **Matching**: Browse → Like → Match
3. **Chat**: Match list → Start chat → Send message
4. **Safety**: Block user → Report user

---

## References

| Topic | File |
|-------|------|
| Feature status | [feature-status.md](references/feature-status.md) |
| Frontend-backend gaps | [frontend-backend-gap.md](references/frontend-backend-gap.md) |
| Known issues | [known-issues.md](references/known-issues.md) |
| Improvement suggestions | [improvement-suggestions.md](references/improvement-suggestions.md) |
| E2E testing guide | [e2e-testing-guide.md](references/e2e-testing-guide.md) |

---

## Audit Report Template

```markdown
# MergeMeet Project Audit Report

## Date: YYYY-MM-DD

## 1. Feature Completeness (X/10)
- [x] Implemented features
- [ ] Missing features

## 2. Frontend-Backend Consistency
- Backend without frontend: X items
- Frontend without backend: X items

## 3. Issues Found
### Critical (P0)
- ...
### Medium (P1)
- ...
### Minor (P2)
- ...

## 4. Recommendations
1. ...
2. ...

## 5. Next Steps
- [ ] Task 1
- [ ] Task 2
```

---

## Related Skills

- **mergemeet-quickstart** - Development guide
- **backend-dev-fastapi** - Backend standards
- **frontend-dev-vue3** - Frontend standards
- **api-routing-standards** - API routing rules
