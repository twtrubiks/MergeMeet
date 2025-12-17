# 交友軟體核心功能檢查清單

本文件列出交友軟體應具備的核心功能，用於審查時逐項確認。

---

## 功能檢查表

### 認證系統

| 功能 | 後端檢查點 | 前端檢查點 |
|-----|-----------|-----------|
| 用戶註冊 | `POST /api/auth/register` | 註冊表單、驗證邏輯 |
| 用戶登入 | `POST /api/auth/login` | 登入表單、Token 處理 |
| Email 驗證 | `POST /api/auth/verify-email` | 驗證頁面、重發連結 |
| 忘記密碼 | `POST /api/auth/forgot-password` | 重設流程頁面 |
| 密碼修改 | `POST /api/auth/change-password` | 設定頁密碼區塊 |
| Token 安全 | HttpOnly Cookie 設定 | CSRF Token 處理 |

### 個人檔案

| 功能 | 後端檢查點 | 前端檢查點 |
|-----|-----------|-----------|
| 建立/編輯檔案 | `GET/PATCH /api/profile` | Profile.vue 編輯表單 |
| 照片上傳 | `POST /api/profile/photos` | PhotoUploader 組件 |
| 照片審核狀態 | Photo model status 欄位 | 審核狀態顯示 |
| 照片申訴 | `POST /api/moderation/appeals` | 申訴按鈕和表單 |
| 興趣標籤 | `PUT /api/profile/interests` | 標籤選擇器 |
| 地理位置 | PostGIS 整合 | 位置更新邏輯 |

### 探索配對

| 功能 | 後端檢查點 | 前端檢查點 |
|-----|-----------|-----------|
| 瀏覽候選人 | `GET /api/discovery/candidates` | Discovery.vue 卡片列表 |
| 用戶詳情查看 | 候選人資料 API | UserDetailModal 組件 |
| 配對分數計算 | matching 演算法 | 分數顯示 |
| 喜歡/跳過 | `POST /api/discovery/like|skip` | 滑動/按鈕操作 |
| 配對成功通知 | Match 建立 + 通知 | 配對成功彈窗 |
| 配對偏好設定 | ProfileUpdateRequest 偏好欄位 | Settings.vue 偏好區塊 |

### 聊天系統

| 功能 | 後端檢查點 | 前端檢查點 |
|-----|-----------|-----------|
| 配對列表 | `GET /api/matches` | ChatList.vue |
| 即時訊息 | WebSocket `/ws/chat` | message store |
| 訊息已讀狀態 | read_at 欄位更新 | 已讀標記顯示 |
| 內容審核提示 | 敏感詞過濾服務 | 錯誤訊息顯示 |

### 安全功能

| 功能 | 後端檢查點 | 前端檢查點 |
|-----|-----------|-----------|
| 封鎖用戶 | `POST /api/safety/block` | 封鎖按鈕 |
| 解除封鎖 | `DELETE /api/safety/block/{id}` | Blocked.vue 解封按鈕 |
| 舉報用戶 | `POST /api/safety/reports` | 舉報表單 |
| 我的舉報記錄 | `GET /api/safety/reports` | MyReports.vue |
| 信任分數 | TrustScore 計算邏輯 | （僅管理後台顯示） |

### 通知系統

| 功能 | 後端檢查點 | 前端檢查點 |
|-----|-----------|-----------|
| 即時通知 | WebSocket `/ws/notifications` | notification store |
| 持久化通知 | Notification model | 通知列表 API 呼叫 |
| 通知中心頁面 | `GET /api/notifications` | Notifications.vue |
| 標記已讀 | `PUT /api/notifications/{id}/read` | 已讀操作 |

### 管理後台

| 功能 | 後端檢查點 | 前端檢查點 |
|-----|-----------|-----------|
| 儀表板統計 | `GET /api/admin/stats` | AdminDashboard 統計卡片 |
| 舉報處理 | `GET/POST /api/admin/reports` | 舉報管理 Tab |
| 內容審核 | `GET/POST /api/admin/moderation` | 內容審核 Tab |
| 照片審核 | `GET/POST /api/admin/photos` | 照片審核 Tab |
| 用戶管理 | `GET /api/admin/users`, ban/unban | 用戶管理 Tab |

---

## 審查方法

### 後端檢查

```bash
# 列出所有 API 端點
grep -rh "@router\.\(get\|post\|put\|patch\|delete\)" backend/app/api/ \
  | grep -oE '@router\.[a-z]+\("[^"]*"' \
  | sort | uniq

# 執行測試確認功能正常
cd backend && pytest -v --cov=app
```

### 前端檢查

```bash
# 列出所有 API 呼叫
grep -rh "apiClient\.\(get\|post\|put\|patch\|delete\)" frontend/src/ \
  | grep -oE "apiClient\.[a-z]+\('[^']*'" \
  | sort | uniq

# Build 確認無錯誤
cd frontend && npm run build
```

---

## 狀態標記說明

審查時使用以下標記：

| 標記 | 說明 |
|-----|------|
| ✅ COMPLETE | 前後端皆已實現 |
| ⚠️ PARTIAL | 部分實現，需補全 |
| ❌ MISSING | 功能缺失 |
| 🔧 BACKEND ONLY | 僅後端實現 |
| 🎨 FRONTEND ONLY | 僅前端實現 |

---

## 待評估功能（可選）

交友軟體常見但非必要的功能：

| 功能 | 說明 |
|-----|------|
| 超級喜歡 | 特殊互動功能 |
| 回顧功能 | 重新查看跳過的用戶 |
| 每日推薦 | 精選推薦用戶 |
| 用戶在線狀態 | 顯示是否在線 |
