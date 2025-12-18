---
name: api-routing-standards
description: This skill should be used when creating or modifying API routes in the MergeMeet project. It enforces the "no trailing slash" standard to prevent 404 errors. Use this skill when working with FastAPI routers, fixing 404 errors, or reviewing API endpoint definitions.
---

# API Routing Standards

## Purpose

To prevent common 404 errors by ensuring all FastAPI routes follow the project's "no trailing slash" convention.

---

## Critical Rule: No Trailing Slash

All API endpoints in this project must NOT use trailing slashes. This is enforced by the FastAPI configuration.

### Correct Examples

```python
# Backend routes - no trailing slash
@router.get("")                      # GET /api/profile
@router.post("")                     # POST /api/profile
@router.put("/interests")            # PUT /api/profile/interests
@router.get("/browse")               # GET /api/discovery/browse
@router.post("/like/{user_id}")      # POST /api/discovery/like/{id}
```

```javascript
// Frontend axios calls - no trailing slash
await axios.get('/api/profile')
await axios.put('/api/profile/interests', data)
await axios.post('/api/profile/photos', formData)
```

### Incorrect Examples (Will Cause 404)

```python
# These will cause 404 errors
@router.post("/")                    # 404
@router.put("/interests/")           # 404
@router.post("/like/{user_id}/")     # 404
```

```javascript
// These will cause 404 errors
await axios.get('/api/profile/')     // 404
await axios.put('/api/profile/interests/', data)  // 404
```

---

## Why This Matters

The FastAPI application is configured with `redirect_slashes=False`:

```python
# backend/app/main.py
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    redirect_slashes=False,  # No automatic redirect
)
```

This means:
- `/api/profile` returns HTTP 200 (correct)
- `/api/profile/` returns HTTP 404 (incorrect)
- Authorization headers are lost during redirects

---

## Quick Checklist

When creating or modifying API routes:

- [ ] Route definition has no trailing slash
- [ ] HTTP method is correct (GET/POST/PUT/PATCH/DELETE)
- [ ] Path parameters use `{param}` format
- [ ] Response model is defined with `response_model`
- [ ] Error handling uses `HTTPException`
- [ ] Frontend axios calls match backend routes exactly

---

## References

For detailed information, refer to these reference files:

| Topic | File |
|-------|------|
| Trailing slash rules | [trailing-slash-rules.md](references/trailing-slash-rules.md) |
| RESTful principles | [restful-principles.md](references/restful-principles.md) |
| HTTP status codes | [status-codes.md](references/status-codes.md) |
| Complete examples | [complete-examples.md](references/complete-examples.md) |

---

## Related Skills

- **backend-dev-fastapi** - FastAPI development guide
- **frontend-dev-vue3** - Vue 3 development guide
