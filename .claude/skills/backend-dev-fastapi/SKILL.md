---
name: backend-dev-fastapi
description: This skill should be used when developing backend features for MergeMeet. It provides guidance on FastAPI + SQLAlchemy 2.0 Async + PostgreSQL/PostGIS patterns including routing, models, Pydantic validation, JWT authentication, WebSocket, and error handling.
---

# FastAPI Backend Development Guide

## Purpose

To establish consistent patterns for FastAPI + SQLAlchemy 2.0 Async development in the MergeMeet project.

---

## Project Structure

```
backend/
├── app/
│   ├── api/              # API routes
│   │   ├── auth.py       # Authentication
│   │   ├── profile.py    # User profiles
│   │   ├── discovery.py  # Discovery/matching
│   │   ├── messages.py   # Chat messages
│   │   ├── websocket.py  # Real-time chat
│   │   ├── safety.py     # Safety features
│   │   └── admin.py      # Admin dashboard
│   ├── core/             # Core configuration
│   │   ├── config.py     # Environment config
│   │   ├── security.py   # JWT/password handling
│   │   └── deps.py       # Dependency injection
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   └── main.py           # FastAPI application
├── tests/                # pytest tests
└── alembic/              # Database migrations
```

---

## Quick Checklist

When creating new features:

- [ ] Route has no trailing slash (see api-routing-standards skill)
- [ ] Use `async def` for all route handlers
- [ ] Use `AsyncSession` for database operations
- [ ] Define Pydantic `response_model`
- [ ] Add `Depends(get_current_user)` for protected routes
- [ ] Use `HTTPException` for error handling
- [ ] Add docstring for API documentation
- [ ] Keep function complexity <= 10 (C901)

---

## Core Patterns

### Route Definition

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/profile", tags=["Profile"])

@router.get("", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user profile."""
    if not current_user.profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    return current_user.profile
```

### SQLAlchemy 2.0 Async Query

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

async def get_profile(user_id: str, db: AsyncSession):
    result = await db.execute(
        select(Profile).where(Profile.user_id == user_id)
    )
    return result.scalar_one_or_none()
```

### Pydantic Schema

```python
from pydantic import BaseModel, Field
from typing import Optional, List

class ProfileResponse(BaseModel):
    id: str
    name: str
    age: int
    bio: Optional[str] = None
    photos: List[str] = []

    class Config:
        from_attributes = True  # Pydantic v2
```

### JWT Authentication

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Extract user from JWT token."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user
```

---

## Common Mistakes

### Missing async/await

```python
# Wrong
@router.get("")
def get_profile(db: AsyncSession = Depends(get_db)):
    profile = db.execute(select(Profile))  # Missing await

# Correct
@router.get("")
async def get_profile(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Profile))
    profile = result.scalar_one_or_none()
```

### Trailing slash (causes 404)

```python
# Wrong
@router.get("/")  # Will cause 404

# Correct
@router.get("")
```

### Missing commit

```python
# Wrong - data won't persist
profile.bio = "New bio"
return profile

# Correct
profile.bio = "New bio"
await db.commit()
await db.refresh(profile)
return profile
```

---

## Testing

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_profile(client: AsyncClient, auth_headers):
    response = await client.get("/api/profile", headers=auth_headers)
    assert response.status_code == 200
    assert "id" in response.json()

@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient):
    response = await client.get("/api/profile")
    assert response.status_code == 401
```

---

## Related Skills

- **api-routing-standards** - API routing rules (required reading)
- **frontend-dev-vue3** - Frontend integration
