# 功能檢查表

> 審查時逐項確認前後端功能是否對應完整。

---

## 認證系統

| 功能 | 後端 | 前端 | 狀態 |
|-----|------|------|------|
| 用戶註冊 | `POST /api/auth/register` | Register.vue | ✅ |
| 用戶登入 | `POST /api/auth/login` | Login.vue | ✅ |
| Email 驗證 | `POST /api/auth/verify-email` | VerifyEmail.vue | ✅ |
| 忘記密碼 | `POST /api/auth/forgot-password` | ForgotPassword.vue | ✅ |
| 重設密碼 | `POST /api/auth/reset-password` | ResetPassword.vue | ✅ |
| 重設 Token 驗證 | `GET /api/auth/verify-reset-token` | ResetPassword.vue | ✅ |
| 重發驗證信 | `POST /api/auth/resend-verification` | VerifyEmail.vue | ✅ |
| 修改密碼 | `POST /api/auth/change-password`（需舊密碼，修改後 Token 失效） | Settings | ✅ |
| Token 刷新 | `POST /api/auth/refresh` | apiClient 攔截器 | ✅ |
| 登出 | `POST /api/auth/logout` | user.js | ✅ |
| 帳號刪除（30 天寬限） | `POST /api/auth/delete-account` | Settings | ✅ |
| 管理員登入 | `POST /api/auth/admin-login` | AdminLogin.vue | ✅ |

## 個人檔案

| 功能 | 後端 | 前端 |
|-----|------|------|
| 建立/獲取/更新檔案 | `POST/GET/PATCH /api/profile` | Profile.vue |
| 照片上傳 | `POST /api/profile/photos` | PhotoUploader |
| 興趣標籤 | `PUT /api/profile/interests` | InterestSelector |

## 探索配對

| 功能 | 後端 | 前端 | 狀態 |
|-----|------|------|------|
| 瀏覽候選人 | `GET /api/discovery/browse` | Discovery.vue | ✅ |
| 喜歡 | `POST /api/discovery/like/{user_id}` | Discovery.vue | ✅ |
| Pass 跳過 | `POST /api/discovery/pass/{user_id}`（matching 排除 24h 內 pass，背景清理 `pass_cleanup.py`） | Discovery.vue | ✅ |
| 每日 like 上限 | `FREE_DAILY_LIKE_LIMIT=50`，Redis 原子計數，超限回 HTTP 429（discovery.py:61,408,440） | Discovery.vue | ✅ |
| 配對列表 | `GET /api/discovery/matches` | Matches.vue | ✅ |

## 聊天系統

| 功能 | 後端 | 前端 |
|-----|------|------|
| 對話列表 | `GET /api/messages/conversations` | ChatList.vue |
| 聊天記錄 | `GET /api/messages/matches/{id}/messages` | Chat.vue |
| 即時訊息 | WebSocket `/ws` | useWebSocketStore |

## 安全功能

| 功能 | 後端 | 前端 |
|-----|------|------|
| 封鎖用戶 | `POST /api/safety/block/{id}` | ReportModal |
| 封鎖列表 | `GET /api/safety/blocked` | Blocked.vue |
| 舉報用戶 | `POST /api/safety/report` | ReportModal |
| 我的舉報 | `GET /api/safety/reports` | MyReports.vue |

## 安全 / 信任

| 功能 | 後端 | 前端 | 狀態 |
|-----|------|------|------|
| 內容/敏感詞審核 | `services/content_moderation.py` + 敏感詞 CRUD `GET/POST/PATCH/DELETE /api/moderation/sensitive-words` | AdminDashboard | ✅ |
| 審核日誌/統計 | `GET /api/moderation/logs`、`GET /api/moderation/stats` | AdminDashboard | ✅ |
| 申訴 appeals | `POST /api/moderation/appeals`、`GET /api/moderation/appeals\|appeals/my`、`POST /api/moderation/appeals/{id}/review`（照片申訴通過自動還原上架＋退信任分；同一內容限申訴一次） | AdminDashboard 申訴管理分頁 | ✅ |
| 信任分數系統 | `services/trust_score.py` + 每日恢復 `trust_score_recovery.py` + 配對加權 `matching_service.py` | — | ✅ |
| 帳號刪除 30 天寬限 | `POST /api/auth/delete-account`（auth.py:923）+ `services/account_cleanup.py` | Settings | ✅ |

## 通知系統

| 功能 | 後端 | 前端 |
|-----|------|------|
| 通知列表 | `GET /api/notifications` | Notifications.vue |
| 即時通知 | WebSocket | NotificationBell |

## 管理後台

| 功能 | 後端 | 前端 | 狀態 |
|-----|------|------|------|
| 統計數據 | `GET /api/admin/stats` | AdminDashboard | ✅ |
| 舉報處理 | `GET/POST /api/admin/reports` | AdminDashboard | ✅ |
| 照片審核 | `GET/POST /api/admin/photos/*`（pending/stats/{id}/review，駁回入隔離區；隔離照片預覽 `GET /api/admin/photos/quarantine/{user_id}/{filename}`） | AdminDashboard | ✅ |
| 用戶管理 | `GET /api/admin/users`（admin.py:270） | AdminDashboard | ✅ |
| 封禁/解封 | `POST /api/admin/users/ban\|unban`（admin.py:368,409） | AdminDashboard | ✅ |
| 信任分數歷史 | `GET /api/admin/users/{user_id}/trust-logs`（admin.py:330） | AdminDashboard「信任分數歷史」Modal | ✅ |

---

## 狀態標記

| 標記 | 說明 |
|-----|------|
| ✅ | 前後端皆完成 |
| ⚠️ | 部分實現 |
| ❌ | 功能缺失 |
