# FastAPI Trailing Slash 重構計劃

## 問題現狀

目前 API 尾隨斜線使用**不一致**：

### 有斜線（/）
- Profile API: `/`, `/interests/`, `/photos/`, `/interest-tags/`
- Messages API: `/conversations/`, `/messages/read/`, `/messages/{message_id}/`

### 無斜線
- Discovery API: `/browse`, `/like/{user_id}`, `/matches`
- Safety API: `/block/{user_id}`, `/blocked`, `/report`
- Admin API: `/stats`, `/reports`, `/users`
- Auth API: `/register`, `/login`, `/refresh`

## 推薦方案：統一**不使用**尾隨斜線

### 理由
1. ✅ 符合 RESTful API 業界標準
2. ✅ 與主流框架一致（GitHub, Stripe, Twitter API）
3. ✅ 前端客戶端（axios/fetch）預設不加斜線
4. ✅ 更簡潔、易讀、易記
5. ✅ 減少 307 重定向錯誤

## 需要修改的檔案

### 後端 API Routes

#### 1. Profile API (`backend/app/api/profile.py`)
```python
# 修改前 → 修改後
@router.post("/", ...)          → @router.post("", ...)
@router.get("/", ...)           → @router.get("", ...)
@router.patch("/", ...)         → @router.patch("", ...)
@router.put("/interests/", ...) → @router.put("/interests", ...)
@router.post("/photos/", ...)   → @router.post("/photos", ...)
@router.delete("/photos/{photo_id}/", ...) → @router.delete("/photos/{photo_id}", ...)
@router.get("/interest-tags/", ...) → @router.get("/interest-tags", ...)
@router.post("/interest-tags/", ...) → @router.post("/interest-tags", ...)
```

#### 2. Messages API (`backend/app/api/messages.py`)
```python
# 修改前 → 修改後
@router.get("/matches/{match_id}/messages/", ...) → @router.get("/matches/{match_id}/messages", ...)
@router.get("/conversations/", ...) → @router.get("/conversations", ...)
@router.post("/messages/read/", ...) → @router.post("/messages/read", ...)
@router.delete("/messages/{message_id}/", ...) → @router.delete("/messages/{message_id}", ...)
```

### 前端 API 呼叫

#### 1. Profile 相關 (`frontend/src/stores/profile.ts`, `frontend/src/api/profile.ts`)
```javascript
// 修改前 → 修改後
POST   '/api/profile/'              → '/api/profile'
GET    '/api/profile/'              → '/api/profile'
PATCH  '/api/profile/'              → '/api/profile'
PUT    '/api/profile/interests/'    → '/api/profile/interests'
POST   '/api/profile/photos/'       → '/api/profile/photos'
DELETE '/api/profile/photos/{id}/'  → '/api/profile/photos/{id}'
GET    '/api/profile/interest-tags/' → '/api/profile/interest-tags'
```

#### 2. Messages 相關 (`frontend/src/stores/messages.ts`, `frontend/src/api/messages.ts`)
```javascript
// 修改前 → 修改後
GET    '/api/messages/conversations/' → '/api/messages/conversations'
GET    '/api/messages/matches/{id}/messages/' → '/api/messages/matches/{id}/messages'
POST   '/api/messages/read/' → '/api/messages/read'
DELETE '/api/messages/{id}/' → '/api/messages/{id}'
```

### 測試檔案

#### 1. 後端測試 (`backend/tests/`)
搜尋並更新所有包含以下模式的測試：
```python
# 修改模式
client.post("/api/profile/", ...)
client.get("/api/profile/", ...)
client.put("/api/profile/interests/", ...)
# ... 等等
```

#### 2. 前端測試（如果有）
同樣更新所有 API 呼叫路徑

### 文檔更新

#### 1. `CLAUDE.md`
- 更新 "API Routing 重要規範" 章節
- 統一說明：**所有 API 端點不使用尾隨斜線**

#### 2. `TESTING_GUIDE.md`
- 已在前面更新完成（Discovery API 部分）
- 需要更新 Profile 和 Messages 相關的測試命令

#### 3. API 文檔註解
更新所有 docstring 中的 API 路徑範例

## 實施步驟

### Phase 1: 後端修改
1. [ ] 修改 `backend/app/api/profile.py`
2. [ ] 修改 `backend/app/api/messages.py`
3. [ ] 更新 `backend/tests/test_profile.py`
4. [ ] 更新 `backend/tests/test_messages.py`
5. [ ] 運行所有測試確保通過

### Phase 2: 前端修改
1. [ ] 修改 `frontend/src/api/profile.ts`（或相關檔案）
2. [ ] 修改 `frontend/src/api/messages.ts`
3. [ ] 更新所有 Pinia stores 中的 API 呼叫
4. [ ] 測試前端功能

### Phase 3: 文檔和測試腳本
1. [ ] 更新 `CLAUDE.md`
2. [ ] 更新 `TESTING_GUIDE.md`
3. [ ] 更新 `test_matching_chat.sh` 和其他測試腳本
4. [ ] 更新 API 文檔註解

### Phase 4: 驗證
1. [ ] 運行完整的 E2E 測試
2. [ ] 檢查 Swagger UI 文檔
3. [ ] 手動測試所有功能
4. [ ] 確認沒有 307 重定向

## 風險評估

### 低風險
- 這是破壞性變更，但影響範圍明確
- 所有錯誤會在測試階段被捕捉（404 或 307）
- FastAPI 的 Swagger UI 會自動更新

### 緩解措施
1. 在開發分支進行修改
2. 完整的測試覆蓋
3. 一次性完成所有修改（避免部分遷移狀態）

## 替代方案

### 方案 A: 保持現狀
- ❌ 不推薦
- 持續困擾開發者
- 增加維護成本

### 方案 B: 使用 FastAPI 的 `redirect_slashes`
```python
app = FastAPI(redirect_slashes=True)
```
- ⚠️ 不完全解決問題
- 效能損失（額外的重定向）
- 不符合 REST 最佳實踐

### 方案 C: 統一使用尾隨斜線
- 可行但不推薦
- 與業界慣例不符
- 需要修改更多檔案（Discovery, Auth, Safety, Admin API）

## 結論

**推薦立即執行 Phase 1-4**，將所有 API 統一為**不使用尾隨斜線**。

- 估計工時: 2-3 小時
- 影響範圍: 明確且可控
- 長期收益: 顯著提升開發體驗和維護性

## 參考資料

- [FastAPI Path Parameters](https://fastapi.tiangolo.com/tutorial/path-params/)
- [RESTful API Design Best Practices](https://stackoverflow.blog/2020/03/02/best-practices-for-rest-api-design/)
- [GitHub API Documentation](https://docs.github.com/en/rest)
