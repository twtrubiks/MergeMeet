# MergeMeet 安全策略文檔

## 認證與授權

### 雙重認證機制（HttpOnly Cookie + Bearer Token）

MergeMeet 支援兩種認證方式，優先使用 HttpOnly Cookie 提供更高安全性。

**主要認證方式：HttpOnly Cookie（推薦）**
- Access Token: 180 分鐘（3 小時）有效期
- Refresh Token: 30 天有效期
- 存儲位置: HttpOnly Cookie（防止 XSS 攻擊）
- 傳輸方式: 瀏覽器自動攜帶 Cookie + CSRF Token Header
- CSRF 防護: Double Submit Cookie Pattern

**備用認證方式：Bearer Token**
- 存儲位置: localStorage（向下相容）
- 傳輸方式: HTTP Authorization Header (`Bearer <token>`)
- CSRF 防護: 不需要（Token 本身即防護）

**技術實現位置：**
- Cookie 工具: `backend/app/core/cookie_utils.py`
- CSRF 驗證: `backend/app/core/csrf.py`
- 前端整合: `frontend/src/stores/user.js`

**JWT Token Payload：**
| 欄位 | 說明 | 範例 |
|------|------|------|
| `sub` | 用戶 ID | `"958dfaec-93a2-4988-a45a-aea93f9d2df6"` |
| `email` | 用戶 Email | `"user@example.com"` |
| `email_verified` | Email 驗證狀態 | `true` |
| `is_admin` | 管理員權限（僅管理員登入時包含） | `true` |
| `exp` | Token 過期時間 | `1766576028` |
| `type` | Token 類型 | `"access"` |

> **安全設計**：`is_admin` 直接從 JWT Token 解析，而非存儲在 localStorage，防止用戶偽造管理員權限。

---

## CSRF (Cross-Site Request Forgery) 防護

### Double Submit Cookie Pattern

當使用 HttpOnly Cookie 認證時，系統自動啟用 CSRF 防護：

**運作流程：**
1. **登入時**
   - 後端生成 CSRF Token (32 字元隨機字串)
   - 設置為非 HttpOnly Cookie (`csrf_token`)
   - 前端可讀取此 Cookie

2. **發送請求時**
   - 前端從 Cookie 讀取 `csrf_token`
   - 將 Token 放入 `X-CSRF-Token` Header
   - 瀏覽器自動附加 `csrf_token` Cookie

3. **後端驗證**
   - 比對 Header 和 Cookie 中的 Token
   - 兩者一致才允許請求

**防護原理：**
```
攻擊者網站 → 誘導用戶點擊 → 瀏覽器發送 Cookie
                            → ❌ 無法讀取 Cookie 內容
                            → ❌ 無法設置正確的 X-CSRF-Token Header
                            → 驗證失敗 (403 Forbidden)
```

**豁免情況：**
- GET/HEAD/OPTIONS 等安全方法（不修改資料）
- 使用 Bearer Token 認證（Token 本身即防護）

**實作位置：**
- CSRF 生成: `backend/app/core/cookie_utils.py:generate_csrf_token()`
- CSRF 驗證: `backend/app/core/csrf.py:verify_csrf_token()`

---

## Cookie 安全配置

### 開發環境
```python
COOKIE_SECURE = False        # 允許 HTTP（本地測試）
COOKIE_SAMESITE = "lax"      # 允許跨站 GET 請求
COOKIE_DOMAIN = ""           # 當前域名
```

### 生產環境（建議）
```python
COOKIE_SECURE = True         # 強制 HTTPS
COOKIE_SAMESITE = "strict"   # 嚴格同站策略
COOKIE_DOMAIN = ".mergemeet.com"  # 允許子域名
```

**安全屬性：**
- `HttpOnly`: 防止 JavaScript 讀取 Cookie（XSS 防護）
- `Secure`: 僅透過 HTTPS 傳輸（中間人攻擊防護）
- `SameSite`: 防止跨站請求攜帶 Cookie（CSRF 防護）

---

## XSS (Cross-Site Scripting) 保護

### 已實施措施

1. **輸入驗證與清理**
   - Pydantic schemas 驗證所有輸入
   - 內容審核系統過濾惡意內容
   - 文件: `backend/app/services/content_moderation.py`

2. **輸出編碼**
   - FastAPI 自動 JSON 編碼
   - 防止 HTML/JavaScript 注入

3. **HttpOnly Cookie**
   - Token 存儲在 HttpOnly Cookie
   - JavaScript 無法讀取（即使發生 XSS）

4. **Content Security Policy（建議）**
   ```python
   # TODO: 添加 CSP header
   response.headers["Content-Security-Policy"] = (
       "default-src 'self'; "
       "script-src 'self'; "
       "style-src 'self' 'unsafe-inline';"
   )
   ```

---

## SQL 注入防護

### 已實施措施

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
   - 搜索參數清理: `backend/app/api/admin.py:283`
   ```python
   # 只允許安全字符：字母、數字、@、.、-、_
   safe_search = re.sub(r'[^\w@.\-]', '', search)
   ```

---

## 敏感資料保護

### 密碼安全

1. **密碼雜湊**
   - 使用 bcrypt 演算法
   - 自動加鹽 (salt)
   - SHA256 預處理避免 bcrypt 72 bytes 限制
   - 密碼最大長度 128 字元（防 DoS）
   - 文件: `backend/app/core/security.py`

2. **密碼強度要求**
   - 最少 8 個字元
   - 必須包含大寫、小寫、數字
   - 拒絕常見弱密碼
   - 文件: `backend/app/schemas/auth.py`

### 個人資訊保護

1. **Email 脫敏**
   - 管理後台顯示時自動脫敏
   - 範例: `user@example.com` → `us***@example.com`
   - 函數定義: `backend/app/core/utils.py:4` (`mask_email`)
   - 使用位置: `backend/app/api/admin.py:155,157`

2. **最小權限原則**
   - 普通用戶無法查看其他用戶的完整 email
   - 只有管理員可以查看（且經過脫敏）

---

## WebSocket 安全

### Token 驗證

1. **連接時驗證**
   - 支援 Cookie 或 Bearer Token
   - 檢查 Token 類型（必須是 access token）
   - 檢查 Token 過期時間
   - 檢查 Token 是否在黑名單中（已登出）
   - 文件: `backend/app/websocket/manager.py:78-129`

2. **異常連接清理**
   - 30 秒心跳間隔發送 ping
   - 90 秒無回應超時檢測
   - 自動清理異常斷線
   - 防止資源洩漏
   - 文件: `backend/app/websocket/manager.py:317-354`

---

## 速率限制（Rate Limiting）

### 已實施措施

1. **登入失敗限制**
   - 使用 Redis 追蹤失敗次數
   - 5 次失敗後鎖定 15 分鐘
   - 文件: `backend/app/services/login_limiter.py`

2. **低信任用戶訊息限制**
   - 信任分數 < 20 的用戶每日限 20 則訊息
   - 使用 Redis 追蹤發送次數
   - 文件: `backend/app/services/trust_score.py`

### 待改進

- [ ] API 全域速率限制（需實作）
- [ ] IP 黑名單機制
- [ ] 防止暴力破解

---

## 信任分數系統

### 自動行為監控

MergeMeet 使用信任分數系統自動追蹤用戶行為，維護平台安全。

**核心機制：**
- 分數範圍: 0-100（預設 50）
- 正向行為加分：Email 驗證 +5、被喜歡 +1、配對 +2
- 負向行為扣分：被舉報 -5、違規內容 -3、被封鎖 -2
- 管理員確認舉報額外扣分 -10

**安全應用：**

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

**實作位置：**
- 服務層: `backend/app/services/trust_score.py`
- 測試: `backend/tests/test_trust_score.py` (22 個測試案例)
- 文檔: `docs/TRUST_SCORE_SYSTEM.md`

---

## 資料庫安全

### 索引優化

**性能索引** (Migration 006, 007)
- blocked_users: 封鎖查詢優化
- moderation_logs: 審核日誌查詢優化
- sensitive_words: 敏感詞分類查詢優化
- matches: 配對狀態查詢優化
- messages: 未讀訊息查詢優化

### 防止 DoS

- 查詢超時設定
- 分頁限制（max 100 items）
- 輸入長度限制

---

## 安全配置清單

### ✅ 已實施

- [x] HttpOnly Cookie 認證（防 XSS）
- [x] CSRF Token 防護（Double Submit Cookie）
- [x] SameSite Cookie 屬性
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
- [ ] 全域 API 速率限制
- [ ] IP 黑名單機制
- [ ] 安全 header (HSTS, X-Frame-Options, X-Content-Type-Options)
- [ ] 檔案上傳安全掃描（病毒掃描）

---

## 安全事件回應

### 報告安全問題

如果發現安全漏洞，請聯繫：
- Email: security@mergemeet.com
- 不要在公開 issue 中討論安全漏洞

### 安全更新策略

1. **Critical**: 24 小時內修復
2. **High**: 7 天內修復
3. **Medium**: 30 天內修復
4. **Low**: 90 天內修復或下次版本

---

## 參考資源

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [SQLAlchemy Security](https://docs.sqlalchemy.org/en/14/faq/security.html)

---

**最後更新**: 2025-12-25
**版本**: 2.2.0（修正行號引用、更新心跳超時時間、補充密碼預處理說明）
