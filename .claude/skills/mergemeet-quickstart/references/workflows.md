# Git 與測試工作流程

## 目錄

- [Git 工作流程](#git-工作流程)
- [測試工作流程](#測試工作流程)
- [CI/CD 流程](#cicd-流程)
- [發布流程](#發布流程)

---

## Git 工作流程

### 分支策略

```
main (生產環境)
  │
  ├── develop (開發主線)
  │     │
  │     ├── feature/user-profile (功能分支)
  │     ├── feature/matching-algorithm (功能分支)
  │     └── feature/chat-system (功能分支)
  │
  └── hotfix/fix-login-bug (緊急修復)
```

### 標準開發流程

#### 1. 創建功能分支

```bash
# 1. 確保在最新的 main 分支
git checkout main
git pull origin main

# 2. 創建功能分支（使用語義化命名）
git checkout -b feature/user-profile-photos

# 命名規範:
# feature/   - 新功能
# fix/       - 錯誤修復
# refactor/  - 重構
# docs/      - 文檔更新
# test/      - 測試相關
```

#### 2. 開發與提交

```bash
# 查看變更
git status
git diff

# 添加變更
git add backend/app/api/profile.py
git add frontend/src/views/Profile.vue

# 或添加所有變更
git add .

# 提交（使用語義化 commit message）
git commit -m "feat: 新增個人檔案照片上傳功能

- 實作照片上傳 API 端點
- 新增照片驗證和壓縮
- 更新前端照片上傳組件
- 新增相關測試"
```

#### 3. 提交規範

使用 **Conventional Commits** 格式：

```bash
# 格式
<type>(<scope>): <subject>

<body>

<footer>

# 類型 (type):
feat:     新功能
fix:      錯誤修復
refactor: 重構（不改變外部行為）
style:    格式調整（不影響程式碼）
test:     測試相關
docs:     文檔更新
chore:    維護任務（依賴更新等）
perf:     效能優化

# 範例 1: 簡單功能
git commit -m "feat: 新增照片上傳功能"

# 範例 2: 錯誤修復
git commit -m "fix: 修復登入頁面 404 錯誤

修復了 URL 尾隨斜線導致的 404 問題。
所有 API 端點已統一為無尾隨斜線格式。"

# 範例 3: 破壞性變更
git commit -m "feat!: 更新 API 認證機制

BREAKING CHANGE: 從 session 改為 JWT Token 認證。
需要更新所有前端 API 請求加入 Authorization header。"

# 範例 4: 包含 issue 引用
git commit -m "fix: 修復配對演算法錯誤

修復了距離計算不準確的問題。

Closes #123"
```

#### 4. 推送與 Pull Request

```bash
# 推送分支
git push origin feature/user-profile-photos

# 如果遠端分支不存在，使用 -u
git push -u origin feature/user-profile-photos

# 在 GitHub/GitLab 創建 Pull Request
# 填寫 PR 描述:
```

**PR 模板**:
```markdown
## 變更說明
簡述此 PR 的主要變更

## 變更類型
- [ ] 新功能
- [ ] 錯誤修復
- [ ] 重構
- [ ] 文檔更新

## 測試
- [ ] 單元測試通過
- [ ] 整合測試通過
- [ ] 手動測試完成

## 檢查清單
- [ ] API URL 無尾隨斜線
- [ ] 測試覆蓋率 >80%
- [ ] 無 linting 錯誤
- [ ] 更新相關文檔

## 截圖（若適用）
[添加截圖]

## 相關 Issue
Closes #123
```

#### 5. Code Review 與合併

```bash
# Code Review 通過後，合併到 main

# 選項 A: Merge commit（保留完整歷史）
git checkout main
git merge --no-ff feature/user-profile-photos

# 選項 B: Squash and merge（合併為單一 commit）
git merge --squash feature/user-profile-photos
git commit -m "feat: 新增個人檔案照片上傳功能"

# 選項 C: Rebase and merge（線性歷史）
git checkout feature/user-profile-photos
git rebase main
git checkout main
git merge feature/user-profile-photos

# 推送
git push origin main

# 刪除功能分支
git branch -d feature/user-profile-photos
git push origin --delete feature/user-profile-photos
```

---

## 測試工作流程

### TDD (Test-Driven Development) 流程

#### 步驟 1: 寫測試（Red）

```python
# tests/test_profile.py
import pytest
from httpx import AsyncClient

async def test_upload_photo(client: AsyncClient, auth_headers):
    """測試上傳個人檔案照片"""
    # 準備測試資料
    files = {"file": ("test.jpg", open("tests/fixtures/test.jpg", "rb"), "image/jpeg")}

    # 發送請求
    response = await client.post(
        "/api/profile/photos",
        files=files,
        headers=auth_headers
    )

    # 斷言
    assert response.status_code == 201
    assert "photo_id" in response.json()
    assert response.json()["url"].startswith("http")
```

```bash
# 執行測試（會失敗 ❌）
pytest tests/test_profile.py::test_upload_photo -v
```

#### 步驟 2: 寫程式碼（Green）

```python
# backend/app/api/profile.py
from fastapi import APIRouter, UploadFile, Depends
from app.services.photo_service import PhotoService

router = APIRouter()

@router.post("/photos", status_code=201)
async def upload_photo(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    photo_service: PhotoService = Depends()
):
    """上傳個人檔案照片"""
    # 驗證檔案
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "只接受圖片檔案")

    # 處理上傳
    photo = await photo_service.upload_photo(current_user.id, file)

    return {
        "photo_id": photo.id,
        "url": photo.url
    }
```

```bash
# 執行測試（應該通過 ✅）
pytest tests/test_profile.py::test_upload_photo -v
```

#### 步驟 3: 重構（Refactor）

```python
# 重構 PhotoService
class PhotoService:
    async def upload_photo(self, user_id: str, file: UploadFile):
        # 壓縮圖片
        compressed = await self._compress_image(file)

        # 上傳到雲端儲存
        url = await self._upload_to_storage(compressed)

        # 儲存到資料庫
        photo = await self._save_to_database(user_id, url)

        return photo

    async def _compress_image(self, file: UploadFile):
        # 壓縮邏輯
        pass

    async def _upload_to_storage(self, file):
        # 上傳邏輯
        pass

    async def _save_to_database(self, user_id: str, url: str):
        # 資料庫邏輯
        pass
```

```bash
# 再次執行測試（應該仍然通過 ✅）
pytest tests/test_profile.py::test_upload_photo -v
```

### 測試層級

#### 1. 單元測試 (Unit Tests)

測試單一函數或類別：

```python
# tests/unit/test_photo_service.py
import pytest
from app.services.photo_service import PhotoService

@pytest.mark.asyncio
async def test_compress_image():
    """測試圖片壓縮"""
    service = PhotoService()
    original_size = 5 * 1024 * 1024  # 5MB

    # 模擬檔案
    file = create_test_image(size=original_size)

    # 壓縮
    compressed = await service._compress_image(file)

    # 驗證
    assert compressed.size < original_size
    assert compressed.size < 1 * 1024 * 1024  # < 1MB
```

```bash
# 執行單元測試
pytest tests/unit/ -v
```

#### 2. 整合測試 (Integration Tests)

測試多個組件的交互：

```python
# tests/integration/test_profile_api.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_profile_workflow(client: AsyncClient):
    """測試完整的個人檔案工作流程"""
    # 1. 註冊
    response = await client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "password123"
    })
    assert response.status_code == 201

    # 2. 登入
    response = await client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    })
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. 更新個人檔案
    response = await client.put("/api/profile", json={
        "bio": "Hello world"
    }, headers=headers)
    assert response.status_code == 200

    # 4. 上傳照片
    files = {"file": ("test.jpg", open("tests/fixtures/test.jpg", "rb"))}
    response = await client.post("/api/profile/photos", files=files, headers=headers)
    assert response.status_code == 201

    # 5. 查看個人檔案
    response = await client.get("/api/profile", headers=headers)
    assert response.status_code == 200
    assert response.json()["bio"] == "Hello world"
    assert len(response.json()["photos"]) == 1
```

```bash
# 執行整合測試
pytest tests/integration/ -v
```

#### 3. E2E 測試 (End-to-End Tests)

測試完整的使用者流程（前端 + 後端）：

```javascript
// frontend/tests/e2e/profile.spec.js
import { test, expect } from '@playwright/test'

test('用戶可以更新個人檔案', async ({ page }) => {
  // 1. 登入
  await page.goto('http://localhost:5173/login')
  await page.fill('input[name="email"]', 'test@example.com')
  await page.fill('input[name="password"]', 'password123')
  await page.click('button[type="submit"]')

  // 2. 前往個人檔案頁面
  await page.goto('http://localhost:5173/profile')

  // 3. 更新個人簡介
  await page.fill('textarea[name="bio"]', 'Hello world')
  await page.click('button:has-text("儲存")')

  // 4. 驗證更新成功
  await expect(page.locator('.success-message')).toBeVisible()

  // 5. 重新載入頁面
  await page.reload()

  // 6. 驗證資料已儲存
  await expect(page.locator('textarea[name="bio"]')).toHaveValue('Hello world')
})
```

```bash
# 執行 E2E 測試
npm run test:e2e
```

### 測試覆蓋率

```bash
# 後端覆蓋率
cd backend
pytest --cov=app --cov-report=html --cov-report=term-missing

# 查看覆蓋率報告
open htmlcov/index.html

# 前端覆蓋率
cd frontend
npm run test:coverage

# 查看覆蓋率報告
open coverage/index.html
```

**覆蓋率目標**:
- 總體覆蓋率: >80%
- 關鍵業務邏輯: >90%
- 配置檔案: 可以較低

---

## CI/CD 流程

### GitHub Actions 範例

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  backend-test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgis/postgis:15-3.3
        env:
          POSTGRES_USER: mergemeet
          POSTGRES_PASSWORD: password
          POSTGRES_DB: mergemeet_test
        ports:
          - 5432:5432
      redis:
        image: redis:alpine
        ports:
          - 6379:6379

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'

    - name: Install dependencies
      run: |
        cd backend
        pip install -r requirements.txt
        pip install -r requirements-dev.txt

    - name: Run linting
      run: |
        cd backend
        flake8 app/
        black --check app/
        mypy app/

    - name: Run tests
      run: |
        cd backend
        pytest --cov=app --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: backend/coverage.xml

  frontend-test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'

    - name: Install dependencies
      run: |
        cd frontend
        npm ci

    - name: Run linting
      run: |
        cd frontend
        npm run lint

    - name: Run tests
      run: |
        cd frontend
        npm run test

    - name: Build
      run: |
        cd frontend
        npm run build
```

### Pre-commit Hooks

```bash
# 安裝 pre-commit
pip install pre-commit

# 創建 .pre-commit-config.yaml
cat > .pre-commit-config.yaml <<EOF
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3.12

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
EOF

# 安裝 hooks
pre-commit install

# 現在每次 git commit 都會自動執行檢查
```

---

## 發布流程

### 版本號規範

使用 **Semantic Versioning** (SemVer):

```
MAJOR.MINOR.PATCH

例如: 1.2.3
  │   │   │
  │   │   └─ PATCH: 錯誤修復（向下相容）
  │   └───── MINOR: 新功能（向下相容）
  └───────── MAJOR: 破壞性變更（不相容）
```

### 發布步驟

```bash
# 1. 確保所有測試通過
pytest
npm run test

# 2. 更新版本號
# 編輯 backend/app/__init__.py
__version__ = "1.2.3"

# 編輯 frontend/package.json
"version": "1.2.3"

# 3. 更新 CHANGELOG.md
cat >> CHANGELOG.md <<EOF
## [1.2.3] - 2024-01-15

### Added
- 新增個人檔案照片上傳功能

### Fixed
- 修復登入頁面 404 錯誤

### Changed
- 優化配對演算法效能
EOF

# 4. 提交版本變更
git add .
git commit -m "chore: bump version to 1.2.3"

# 5. 創建 Git tag
git tag -a v1.2.3 -m "Release version 1.2.3"

# 6. 推送
git push origin main
git push origin v1.2.3

# 7. 部署到生產環境
# (根據你的部署流程)
```

---

**提示**: 一個良好的工作流程能大幅提升團隊協作效率和程式碼品質！
