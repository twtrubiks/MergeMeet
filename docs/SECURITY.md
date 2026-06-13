# MergeMeet 安全策略文檔

## 認證與授權

### 雙重認證機制（HttpOnly Cookie + Bearer Token）

MergeMeet 支援兩種認證方式，優先使用 HttpOnly Cookie 提供更高安全性。

**主要認證方式：HttpOnly Cookie（推薦）**
- Access Token: 30 分鐘有效期（預設，可透過環境變數調整）
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
| `iat` | Token 簽發時間（用於全局失效檢查） | `1766576000` |
| `exp` | Token 過期時間（iat + 30 分鐘） | `1766577800` |
| `type` | Token 類型 | `"access"` |

> **安全設計**：`is_admin` 直接從 JWT Token 解析，而非存儲在 localStorage，防止用戶偽造管理員權限。

---

## CSRF (Cross-Site Request Forgery) 防護

### Double Submit Cookie Pattern

當使用 HttpOnly Cookie 認證時，系統自動啟用 CSRF 防護：

**運作流程：**
1. **登入時**
   - 後端生成 CSRF Token (32 bytes 亂數，Base64 URL-safe 編碼後約 43 字元)
   - 設置為非 HttpOnly Cookie (`csrf_token`)
   - 前端可讀取此 Cookie

2. **發送請求時**
   - 前端從 Cookie 讀取 `csrf_token`
   - 將 Token 放入 `X-CSRF-Token` Header
   - 瀏覽器自動附加 `csrf_token` Cookie

3. **後端驗證**
   - 比對 Header 和 Cookie 中的 Token
   - 兩者一致才允許請求

**豁免情況：**
- GET/HEAD/OPTIONS 等安全方法（不修改資料）
- 使用 Bearer Token 認證（Token 本身即防護）

**實作位置：**
- CSRF 生成: `backend/app/core/cookie_utils.py:generate_csrf_token()`
- CSRF 驗證: `backend/app/core/csrf.py:verify_csrf_token()`

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

4. **Content Security Policy**
   - API 響應採最嚴格策略：`default-src 'none'; img-src 'self'; frame-ancestors 'none'`
   - `/docs`、`/redoc` 豁免（Swagger UI / ReDoc 需載入 CDN 腳本）
   - 同時設置 HSTS、X-Content-Type-Options、X-Frame-Options、Referrer-Policy
   - 文件: `backend/app/middleware/security_headers.py`

---

## SQL 注入防護

### 已實施措施

1. **使用 SQLAlchemy ORM**
   - 自動參數化查詢
   - 防止 SQL 注入

2. **輸入清理**
   - 搜索參數清理: `backend/app/api/admin.py`
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
   - 範例: `user@example.com` → `us***r@example.com`
   - 函數: `backend/app/core/utils.py` (`mask_email`)
   - 使用: `backend/app/api/admin.py`

2. **Email 枚舉防護**
   - 驗證碼錯誤與用戶不存在返回相同錯誤訊息
   - 重新發送驗證碼無論用戶是否存在都返回成功
   - 已驗證的 Email 重新發送也返回成功（不洩露驗證狀態）
   - 防止攻擊者透過錯誤訊息探測有效 Email

3. **密碼重置後 Token 全局失效**
   - 密碼變更後使該用戶所有現有 Token 失效
   - 使用 Redis 記錄失效時間戳（TTL: 7 天）
   - Token 驗證時檢查 `iat` 是否早於失效時間
   - 文件: `backend/app/services/token_invalidator.py`

4. **最小權限原則**
   - 普通用戶無法查看其他用戶的完整 email
   - 只有管理員可以查看（且經過脫敏）
   - 密碼重置驗證返回遮罩 email（如 `us***r@example.com`）

---

## WebSocket 安全

### Token 驗證

1. **連接時驗證**
   - 支援 Cookie 或 Bearer Token
   - 檢查 Token 類型（必須是 access token）
   - 檢查 Token 過期時間
   - 檢查 Token 是否在黑名單中（已登出）
   - 文件: `backend/app/websocket/manager.py`

2. **異常連接清理**
   - 30 秒心跳間隔發送 ping
   - 90 秒無回應超時檢測
   - 自動清理異常斷線
   - 防止資源洩漏
   - 文件: `backend/app/websocket/manager.py`

---

## 速率限制（Rate Limiting）

### 已實施措施

0. **全域 IP 速率限制（slowapi + Redis）**
   - 所有 API 端點共用 60 次/分鐘 per IP（application-level 共享計數）
   - 登入/註冊/管理員登入另設 10 次/5 分鐘 per IP（裝飾器獨立計數，與下方 email-based 限制互補）
   - `/health` 健康檢查豁免（供監控輪詢）；`/uploads` 靜態檔案不計入
   - Redis 不可用時自動回退內存計數（單實例部署下行為一致）
   - 429 回應帶 `Retry-After` 與 `X-RateLimit-*` headers（已加入 CORS expose_headers）
   - ⚠️ 反向代理部署時 uvicorn 需以 `--proxy-headers --forwarded-allow-ips='<代理 IP>'` 啟動，才能取得真實用戶 IP
   - 文件: `backend/app/core/rate_limit.py`、測試: `backend/tests/test_rate_limit.py`

1. **登入失敗限制**
   - 使用 Redis 追蹤失敗次數
   - 5 次失敗後鎖定 15 分鐘
   - 文件: `backend/app/services/login_limiter.py`

2. **驗證碼暴力破解防護**
   - 使用 Redis 追蹤驗證失敗次數
   - 5 次失敗後鎖定 15 分鐘
   - 成功驗證後自動清除計數
   - 文件: `backend/app/services/verification_limiter.py`

3. **低信任用戶訊息限制**
   - 見「信任分數系統」章節

4. **每日喜歡次數限制**
   - 使用 Redis 追蹤每日喜歡次數（`like:daily:{user_id}:{date}`，TTL 24h）
   - 免費用戶 50 次/日，超限回傳 429 Too Many Requests
   - Redis 不可用時放行（不阻斷核心功能）
   - 文件: `backend/app/api/discovery.py`

---

## 信任分數系統

### 自動行為監控

MergeMeet 使用信任分數系統自動追蹤用戶行為，維護平台安全。

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
- 測試: `backend/tests/test_trust_score.py`
- 文檔: [TRUST_SCORE_SYSTEM.md](./TRUST_SCORE_SYSTEM.md)

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
- [x] 驗證碼暴力破解防護（Redis，5 次/15 分鐘）
- [x] 密碼重置後 Token 全局失效（Redis）
- [x] Email 枚舉防護
- [x] 驗證碼使用加密安全隨機數生成（secrets.choice）
- [x] 信任分數系統（自動行為監控 + 功能限制）
- [x] Redis 密碼認證（requirepass + 端口僅綁定 127.0.0.1）
- [x] HTTP 安全 Headers（HSTS、CSP、X-Frame-Options、X-Content-Type-Options、Referrer-Policy）
- [x] 照片 EXIF 元資料去除（重新編碼去除 GPS / 設備資訊，並先套用 Orientation 轉正）
- [x] Docker Compose 密碼可由環境變數覆寫（根目錄 `.env`，見 `.env.example`）
- [x] 全域 IP 速率限制（slowapi + Redis，60 次/分鐘 per IP；認證端點 10 次/5 分鐘）

### ⚠️ 建議改進

詳見 [ROADMAP.md](./ROADMAP.md) Phase 2 安全相關項目。
