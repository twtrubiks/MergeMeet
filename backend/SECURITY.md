# MergeMeet 安全策略文檔

## 認證與授權

### JWT Token 認證機制

MergeMeet 使用 JWT (JSON Web Token) Bearer token 認證，而非 session cookie。

**技術實現**:
- Access Token: 30 分鐘有效期
- Refresh Token: 7 天有效期
- 存儲位置: 前端 localStorage
- 傳輸方式: HTTP Authorization Header (`Bearer <token>`)

**安全優勢**:
```
✅ Token 不會自動隨請求發送（不像 cookie）
✅ 必須由前端 JavaScript 主動添加到 Authorization header
✅ 有效防止 CSRF (Cross-Site Request Forgery) 攻擊
✅ 支援跨域認證
```

### CSRF 保護策略

#### 當前狀態: 受 JWT Bearer Token 保護

**為什麼不需要額外的 CSRF token**:

1. **Bearer Token 特性**
   - 存儲在 localStorage，不是 cookie
   - 不會被瀏覽器自動附加到請求中
   - 惡意網站無法讀取或發送我們的 token

2. **CSRF 攻擊原理**
   ```
   攻擊者網站 → 誘導用戶點擊 → 瀏覽器自動發送 cookie → 成功偽造請求
   ```

   **在我們的系統中**:
   ```
   攻擊者網站 → 誘導用戶點擊 → ❌ 沒有 Authorization header → 認證失敗 (401)
   ```

3. **實際防護範例**

   正常請求（成功）:
   ```javascript
   // 前端代碼
   await axios.get('/api/profile', {
     headers: {
       'Authorization': `Bearer ${localStorage.getItem('access_token')}`
     }
   })
   ```

   CSRF 攻擊（失敗）:
   ```html
   <!-- 攻擊者的網站 -->
   <form action="https://mergemeet.com/api/profile" method="POST">
     <!-- ❌ 無法讀取 localStorage -->
     <!-- ❌ 無法添加 Authorization header -->
     <input type="submit" value="點我領獎">
   </form>
   ```
   結果: 401 Unauthorized（缺少 Authorization header）

#### ⚠️ 未來安全考慮

**如果改用 Cookie 存儲 Token，必須實施以下措施**:

1. **啟用 SameSite Cookie**
   ```python
   response.set_cookie(
       "access_token",
       value=token,
       httponly=True,      # 防止 XSS
       secure=True,        # 僅 HTTPS
       samesite="Strict"   # 防止 CSRF
   )
   ```

2. **添加 CSRF Token 機制**
   - 使用雙重提交 Cookie (Double Submit Cookie) 模式
   - 或實施同步 Token 模式 (Synchronizer Token Pattern)

3. **CORS 配置強化**
   ```python
   # 嚴格限制允許的來源
   allow_origins=["https://mergemeet.com"],
   allow_credentials=True
   ```

## XSS (Cross-Site Scripting) 保護

### 現有防護措施

1. **輸入驗證與清理**
   - Pydantic schemas 驗證所有輸入
   - 內容審核系統過濾惡意內容
   - 文件: `app/services/content_moderation.py`

2. **輸出編碼**
   - FastAPI 自動 JSON 編碼
   - 防止 HTML/JavaScript 注入

3. **Content Security Policy (建議)**
   ```python
   # TODO: 添加 CSP header
   response.headers["Content-Security-Policy"] = (
       "default-src 'self'; "
       "script-src 'self'; "
       "style-src 'self' 'unsafe-inline';"
   )
   ```

## SQL 注入保護

### 現有防護措施

1. **使用 SQLAlchemy ORM**
   - 自動參數化查詢
   - 防止 SQL 注入

   ✅ 安全範例:
   ```python
   result = await db.execute(
       select(User).where(User.email == user_email)
   )
   ```

   ❌ 不安全範例（已禁止）:
   ```python
   # 絕對不要這樣做
   query = f"SELECT * FROM users WHERE email = '{user_email}'"
   ```

2. **輸入清理**
   - `app/api/admin.py:283`: 搜索參數清理
   ```python
   # 只允許安全字符：字母、數字、@、.、-、_
   safe_search = re.sub(r'[^\w@.\-]', '', search)
   ```

## 敏感資料保護

### 密碼安全

1. **密碼雜湊**
   - 使用 bcrypt 演算法
   - 自動加鹽 (salt)
   - 文件: `app/core/security.py`

2. **密碼強度要求**
   - 最少 8 個字元
   - 必須包含大寫、小寫、數字
   - 拒絕常見弱密碼
   - 文件: `app/schemas/auth.py`

### 個人資訊保護

1. **Email 脫敏**
   - 管理後台顯示時自動脫敏
   - 範例: `user@example.com` → `us***@example.com`
   - 文件: `app/api/admin.py:28`

2. **最小權限原則**
   - 普通用戶無法查看其他用戶的完整 email
   - 只有管理員可以查看（且經過脫敏）

## WebSocket 安全

### Token 驗證

1. **連接時驗證**
   - 檢查 Token 類型（必須是 access token）
   - 檢查 Token 過期時間
   - 文件: `app/websocket/manager.py:39-68`

2. **異常連接清理**
   - 5 分鐘心跳超時檢測
   - 自動清理異常斷線
   - 防止資源洩漏
   - 文件: `app/websocket/manager.py:200-247`

## 資料庫安全

### 索引優化

1. **性能索引** (Migration 007)
   - blocked_users: 封鎖查詢優化
   - moderation_logs: 審核日誌查詢優化
   - sensitive_words: 敏感詞分類查詢優化
   - matches: 配對狀態查詢優化
   - messages: 未讀訊息查詢優化

2. **防止 DoS**
   - 查詢超時設定
   - 分頁限制（max 100 items）
   - 輸入長度限制

## 信任分數系統（2025-12-14 新增）

### 自動行為監控

MergeMeet 使用信任分數系統自動追蹤用戶行為，維護平台安全。

**核心機制**:
- 分數範圍: 0-100（預設 50）
- 正向行為加分：Email 驗證 +5、被喜歡 +1、配對 +2
- 負向行為扣分：被舉報 -5、違規內容 -3、被封鎖 -2
- 管理員確認舉報額外扣分 -10

**安全應用**:

1. **配對排序整合**
   - 高信任用戶優先推薦（5 分權重）
   - 低信任用戶（< 20 分）幾乎不被推薦

2. **自動功能限制**
   - 低信任用戶（< 20 分）每日訊息上限 20 則
   - 使用 Redis 追蹤每日發送次數
   - 防止垃圾訊息和騷擾行為

3. **並發安全**
   - 使用資料庫事務保證分數更新原子性
   - 分數邊界保護（0-100）

**實作位置**:
- 服務層: `app/services/trust_score.py`
- 測試: `tests/test_trust_score.py` (22 個測試案例)

## 安全配置清單

### ✅ 已實施

- [x] JWT Bearer token 認證
- [x] CORS 配置
- [x] 密碼雜湊 (bcrypt)
- [x] 密碼強度驗證
- [x] SQL 注入防護 (ORM)
- [x] XSS 輸入驗證
- [x] WebSocket token 驗證
- [x] 異常連接清理
- [x] 資料庫索引優化
- [x] Email 脫敏
- [x] 內容審核系統
- [x] 輸入長度限制
- [x] 登入失敗次數限制（Redis，5 次/15 分鐘）
- [x] 信任分數系統（自動行為監控 + 功能限制）

### ⚠️ 建議改進

- [ ] Content Security Policy (CSP) header
- [ ] Rate limiting（API 速率限制，全局）
- [ ] IP 黑名單機制
- [ ] 安全 header (HSTS, X-Frame-Options, etc.)

### 🔴 未來必須實施（如果改用 Cookie）

- [ ] CSRF token 機制
- [ ] SameSite cookie 屬性
- [ ] HttpOnly cookie 屬性

## 安全事件回應

### 報告安全問題

如果發現安全漏洞，請聯繫:
- Email: security@mergemeet.com
- 不要在公開 issue 中討論安全漏洞

### 安全更新策略

1. **Critical**: 24 小時內修復
2. **High**: 7 天內修復
3. **Medium**: 30 天內修復
4. **Low**: 90 天內修復或下次版本

## 參考資源

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [SQLAlchemy Security](https://docs.sqlalchemy.org/en/14/faq/security.html)

---

**最後更新**: 2025-12-14
**版本**: 1.1.0（新增信任分數系統）
