# 功能檢查表

> 審查時逐項確認前後端功能是否對應完整。

---

## 認證系統

| 功能 | 後端 | 前端 |
|-----|------|------|
| 用戶註冊 | `POST /api/auth/register` | Register.vue |
| 用戶登入 | `POST /api/auth/login` | Login.vue |
| Email 驗證 | `POST /api/auth/verify-email` | VerifyEmail.vue |
| 忘記密碼 | `POST /api/auth/forgot-password` | ForgotPassword.vue |
| 重設密碼 | `POST /api/auth/reset-password` | ResetPassword.vue |

## 個人檔案

| 功能 | 後端 | 前端 |
|-----|------|------|
| 建立/獲取/更新檔案 | `POST/GET/PATCH /api/profile` | Profile.vue |
| 照片上傳 | `POST /api/profile/photos` | PhotoUploader |
| 興趣標籤 | `PUT /api/profile/interests` | InterestSelector |

## 探索配對

| 功能 | 後端 | 前端 |
|-----|------|------|
| 瀏覽候選人 | `GET /api/discovery/browse` | Discovery.vue |
| 喜歡/跳過 | `POST /api/discovery/like\|pass` | Discovery.vue |
| 配對列表 | `GET /api/discovery/matches` | Matches.vue |

## 聊天系統

| 功能 | 後端 | 前端 |
|-----|------|------|
| 對話列表 | `GET /api/messages/conversations` | ChatList.vue |
| 聊天記錄 | `GET /api/messages/matches/{id}/messages` | Chat.vue |
| 即時訊息 | WebSocket `/ws` | useWebSocket |

## 安全功能

| 功能 | 後端 | 前端 |
|-----|------|------|
| 封鎖用戶 | `POST /api/safety/block/{id}` | ReportModal |
| 封鎖列表 | `GET /api/safety/blocked` | Blocked.vue |
| 舉報用戶 | `POST /api/safety/report` | ReportModal |
| 我的舉報 | `GET /api/safety/reports` | MyReports.vue |

## 通知系統

| 功能 | 後端 | 前端 |
|-----|------|------|
| 通知列表 | `GET /api/notifications` | Notifications.vue |
| 即時通知 | WebSocket | NotificationBell |

## 管理後台

| 功能 | 後端 | 前端 |
|-----|------|------|
| 統計數據 | `GET /api/admin/stats` | AdminDashboard |
| 舉報處理 | `GET/POST /api/admin/reports` | AdminDashboard |
| 照片審核 | `GET/POST /api/admin/photos` | AdminDashboard |

---

## 狀態標記

| 標記 | 說明 |
|-----|------|
| ✅ | 前後端皆完成 |
| ⚠️ | 部分實現 |
| ❌ | 功能缺失 |
