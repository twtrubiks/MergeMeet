---
name: backend-dev-fastapi
description: 在 MergeMeet 開發後端功能時使用此 skill。提供 FastAPI + SQLAlchemy 2.0 Async + PostgreSQL/PostGIS 的開發模式指南，包含路由、模型、Pydantic 驗證、JWT 認證、WebSocket 和錯誤處理。
---

# FastAPI 後端開發指南

## 目的

建立 MergeMeet 專案中 FastAPI + SQLAlchemy 2.0 Async 開發的一致模式。

---

## 專案結構

```
backend/
├── app/
│   ├── api/              # API 路由
│   │   ├── auth.py       # 認證
│   │   ├── profile.py    # 用戶檔案
│   │   ├── discovery.py  # 探索/配對
│   │   ├── messages.py   # 聊天訊息
│   │   ├── websocket.py  # 即時聊天
│   │   ├── safety.py     # 安全功能
│   │   └── admin.py      # 管理後台
│   ├── core/             # 核心配置
│   │   ├── config.py     # 環境設定
│   │   ├── security.py   # JWT/密碼處理
│   │   └── deps.py       # 依賴注入
│   ├── models/           # SQLAlchemy 模型
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # 業務邏輯
│   └── main.py           # FastAPI 應用程式
├── tests/                # pytest 測試
└── alembic/              # 資料庫遷移
```

---

## 快速檢查清單

建立新功能時：

- [ ] 路由無尾隨斜線（參考 api-routing-standards skill）
- [ ] 所有路由處理器使用 `async def`
- [ ] 資料庫操作使用 `AsyncSession`
- [ ] 定義 Pydantic `response_model`
- [ ] 受保護路由加上 `Depends(get_current_user)`
- [ ] 錯誤處理使用 `HTTPException`
- [ ] 為 API 文件加上 docstring
- [ ] 保持函數複雜度 <= 10 (C901)

---

## 核心模式

### 路由定義

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/profile", tags=["Profile"])

@router.get("", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """獲取用戶檔案。"""
    if not current_user.profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    return current_user.profile
```

### SQLAlchemy 2.0 非同步查詢

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

### JWT 認證

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """從 JWT token 提取用戶。"""
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

## 常見錯誤

### 缺少 async/await

```python
# 錯誤
@router.get("")
def get_profile(db: AsyncSession = Depends(get_db)):
    profile = db.execute(select(Profile))  # 缺少 await

# 正確
@router.get("")
async def get_profile(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Profile))
    profile = result.scalar_one_or_none()
```

### 尾隨斜線（導致 404）

```python
# 錯誤
@router.get("/")  # 會導致 404

# 正確
@router.get("")
```

### 缺少 commit

```python
# 錯誤 - 資料不會持久化
profile.bio = "New bio"
return profile

# 正確
profile.bio = "New bio"
await db.commit()
await db.refresh(profile)
return profile
```

---

## 測試

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

## 相關 Skills

- **api-routing-standards** - API 路由規則（必讀）
- **frontend-dev-vue3** - 前端整合
