---
name: backend-dev-fastapi
description: FastAPI + SQLAlchemy 2.0 Async + PostgreSQL/PostGIS 開發指南。涵蓋路由設計、資料模型、Pydantic 驗證、JWT 認證、WebSocket、錯誤處理、TDD 測試等。適用於 MergeMeet 交友平台後端開發。
---

# FastAPI 後端開發指南

## 🎯 目的

建立 FastAPI + SQLAlchemy 2.0 Async 開發的一致性與最佳實踐。

---

## 📚 何時使用此 Skill

**自動觸發**:
- 編輯 `backend/app/**/*.py` 檔案
- 關鍵字: "backend", "fastapi", "api", "route", "model", "schema"
- 程式碼包含: `@router`, `async def`, `SQLAlchemy`, `BaseModel`

**手動使用**:
```bash
使用 Skill: backend-dev-fastapi
```

---

## 🏗️ 專案架構

```
backend/
├── app/
│   ├── api/              # API 路由（8 個模組）
│   │   ├── auth.py       # 認證系統
│   │   ├── profile.py    # 個人檔案
│   │   ├── discovery.py  # 探索配對
│   │   ├── messages.py   # 聊天訊息
│   │   ├── websocket.py  # WebSocket 即時聊天
│   │   ├── safety.py     # 安全功能
│   │   └── admin.py      # 管理後台
│   ├── core/             # 核心配置
│   │   ├── config.py     # 環境配置
│   │   ├── security.py   # JWT/密碼處理
│   │   └── deps.py       # 依賴注入
│   ├── models/           # SQLAlchemy 模型（8 個）
│   │   ├── user.py       # User, trust_score
│   │   ├── profile.py    # Profile, Photo, InterestTag
│   │   ├── match.py      # Like, Match, Message, BlockedUser
│   │   └── report.py     # Report
│   ├── schemas/          # Pydantic Schemas
│   ├── services/         # 業務邏輯
│   │   └── content_moderation.py  # 內容審核
│   ├── websocket/        # WebSocket 管理
│   │   └── manager.py    # 連接管理器
│   └── main.py           # FastAPI 主應用
├── tests/                # 測試（70+ 個測試）
└── alembic/              # 資料庫遷移
```

---

## ⚡ 快速檢查清單

創建新功能時：

- [ ] **路由定義** - 無尾隨斜線，使用 `APIRouter`
- [ ] **資料模型** - SQLAlchemy 2.0 Async 語法
- [ ] **Schema 驗證** - Pydantic `BaseModel`
- [ ] **錯誤處理** - `HTTPException` with 正確狀態碼
- [ ] **認證保護** - `Depends(get_current_user)`
- [ ] **資料庫 Session** - `Depends(get_db)` Async
- [ ] **回應模型** - `response_model` 參數
- [ ] **測試** - pytest 覆蓋率 >80%
- [ ] **文檔** - Docstring 說明

---

## 📖 資源檔案導覽

| 需要... | 閱讀此檔案 |
|--------|----------|
| 架構總覽 | [architecture-overview.md](resources/architecture-overview.md) |
| 路由與 API 設計 | [routing-patterns.md](resources/routing-patterns.md) |
| SQLAlchemy 模型 | [database-models.md](resources/database-models.md) |
| Pydantic 驗證 | [schema-validation.md](resources/schema-validation.md) |
| JWT 認證 | [authentication.md](resources/authentication.md) |
| WebSocket 管理 | [websocket-manager.md](resources/websocket-manager.md) |
| 錯誤處理 | [error-handling.md](resources/error-handling.md) |
| 測試策略 | [testing-guide.md](resources/testing-guide.md) |
| 內容審核 | [content-moderation.md](resources/content-moderation.md) |
| 完整範例 | [complete-examples.md](resources/complete-examples.md) |

---

## 🔍 查詢官方文檔 (Context7 MCP)

```bash
# FastAPI 文檔
context7: resolve-library-id "fastapi"
context7: get-library-docs "/fastapi" topic="async"
context7: get-library-docs "/fastapi" topic="dependencies"
context7: get-library-docs "/fastapi" topic="security"

# SQLAlchemy 文檔
context7: resolve-library-id "sqlalchemy"
context7: get-library-docs "/sqlalchemy" topic="async orm"
context7: get-library-docs "/sqlalchemy" topic="relationships"

# Pydantic 文檔
context7: resolve-library-id "pydantic"
context7: get-library-docs "/pydantic" topic="validation"

# PostGIS/GeoAlchemy
context7: resolve-library-id "geoalchemy2"
context7: get-library-docs "/geoalchemy2" topic="postgis"
```

---

## 🚀 核心模式

### 1. 路由定義模式
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/profile", tags=["Profile"])

@router.get("", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """獲取個人檔案"""
    if not current_user.profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="個人檔案不存在"
        )
    return current_user.profile
```

### 2. SQLAlchemy 2.0 Async 模式
```python
from sqlalchemy import Column, String, Integer, ForeignKey, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship

class Profile(Base):
    __tablename__ = "profiles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), unique=True)
    bio = Column(String(500))

    user = relationship("User", back_populates="profile")
    photos = relationship("Photo", back_populates="profile")

# Async 查詢
async def get_profile(user_id: str, db: AsyncSession):
    result = await db.execute(
        select(Profile).where(Profile.user_id == user_id)
    )
    return result.scalar_one_or_none()
```

### 3. Pydantic Schema 模式
```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime

class ProfileResponse(BaseModel):
    id: str
    name: str
    age: int
    bio: Optional[str] = None
    photos: List[str] = []
    interests: List[str] = []

    class Config:
        from_attributes = True  # Pydantic v2

class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    bio: Optional[str] = Field(None, max_length=500)

    @validator('bio')
    def bio_must_be_appropriate(cls, v):
        if v and has_inappropriate_content(v):
            raise ValueError('內容包含不當用語')
        return v
```

### 4. JWT 認證模式
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """從 JWT Token 獲取當前用戶"""
    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無效的認證憑證"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的認證憑證"
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用戶不存在"
        )

    return user
```

### 5. WebSocket 管理模式
```python
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    async def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_message(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str,
    db: AsyncSession = Depends(get_db)
):
    user = await get_user_from_token(token, db)
    await manager.connect(user.id, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            # 處理訊息...
    except WebSocketDisconnect:
        await manager.disconnect(user.id)
```

---

## 🧪 測試模式 (TDD)

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_profile(client: AsyncClient, auth_headers):
    """測試：創建個人檔案"""
    profile_data = {
        "name": "測試用戶",
        "bio": "這是我的個人簡介",
        "age": 25
    }

    response = await client.post(
        "/api/profile",
        json=profile_data,
        headers=auth_headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "測試用戶"
    assert "id" in data

@pytest.mark.asyncio
async def test_get_profile_unauthorized(client: AsyncClient):
    """測試：未認證無法獲取檔案"""
    response = await client.get("/api/profile")
    assert response.status_code == 401
```

---

## ⚠️ 常見錯誤

### 錯誤 1: 忘記 async/await
```python
# ❌ 錯誤 - 缺少 async/await
@router.get("")
def get_profile(db: AsyncSession = Depends(get_db)):
    profile = db.execute(select(Profile))  # ❌ 缺少 await

# ✅ 正確
@router.get("")
async def get_profile(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Profile))
    profile = result.scalar_one_or_none()
```

### 錯誤 2: 使用尾隨斜線
```python
# ❌ 錯誤
@router.get("/")  # 會導致 404

# ✅ 正確
@router.get("")
```

### 錯誤 3: 忘記 commit
```python
# ❌ 錯誤 - 忘記 commit
profile.bio = "新的簡介"
return profile  # 資料不會儲存！

# ✅ 正確
profile.bio = "新的簡介"
await db.commit()
await db.refresh(profile)
return profile
```

---

## 🔗 相關 Skills

- **api-routing-standards** - API 路由規範（必讀）
- **database-planning** - PostgreSQL + PostGIS 設計
- **testing-guide** - pytest 測試策略

---

## 📝 核心原則

1. **Async 優先** - 所有資料庫操作使用 async/await
2. **無尾隨斜線** - 所有路由不使用 `/` 結尾
3. **依賴注入** - 使用 `Depends()` 注入 DB session 和 user
4. **Schema 驗證** - 使用 Pydantic 驗證所有輸入
5. **明確錯誤** - HTTPException with 正確狀態碼
6. **測試覆蓋** - 每個功能都有 pytest 測試
7. **文檔完整** - Docstring + response_model

---

**Skill 狀態**: ✅ COMPLETE
**優先級**: HIGH
**行數**: < 400 行 ✅
