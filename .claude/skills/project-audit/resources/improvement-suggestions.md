# 改進建議和優先級

> 最後更新: 2025-12-16

## 優先級分類

- **P0 (Critical)**: 影響核心功能，必須立即修復
- **P1 (High)**: 重要功能缺失，應優先處理
- **P2 (Medium)**: 用戶體驗改善，計劃性處理
- **P3 (Low)**: 錦上添花，有空再做

---

## P0: 必須修復

### 1. 修復 Blocked.vue 的 logger 錯誤

**問題**: 未 import logger 導致 ReferenceError

**修復**:
```javascript
// frontend/src/views/Blocked.vue
import { logger } from '@/utils/logger'
```

**工作量**: < 5 分鐘

---

## P1: 優先處理

### 2. 新增配對偏好設定 UI

**位置**: `frontend/src/views/Settings.vue`

**需求**:
- 年齡範圍滑桿 (18-99)
- 最大距離選擇 (1-500 km)
- 性別偏好 (男/女/不限)

**工作量**: 2-4 小時

**相關**:
- 後端 API: `PATCH /api/profile` 已支援
- Schema: `ProfileUpdateRequest`

---

### 3. 新增管理員用戶管理功能

**位置**: `frontend/src/views/admin/AdminDashboard.vue`

**需求**:
- 新增「用戶管理」Tab
- 用戶搜尋（Email）
- 用戶列表（分頁）
- 封禁/解封操作
- 查看信任分數

**工作量**: 4-6 小時

**相關**:
- 後端 API: `GET /admin/users`, `POST /admin/users/ban`, `POST /admin/users/unban`
- Schema: `UserManagementResponse`, `BanUserRequest`, `UnbanUserRequest`

---

### 4. 統一前後端檔案大小限制

**問題**: 前端 10MB，後端可能 5MB

**修復**:
1. 確認後端 `settings.MAX_UPLOAD_SIZE` 值
2. 在前端使用環境變數或 API 獲取限制
3. 統一錯誤訊息

**工作量**: 1-2 小時

---

## P2: 計劃性處理

### 5. 新增通知中心頁面

**位置**: 新建 `frontend/src/views/Notifications.vue`

**需求**:
- 通知列表（分頁）
- 標記已讀/全部已讀
- 刪除通知
- 通知類型圖標

**工作量**: 4-6 小時

**相關**:
- 後端 API: `/api/notifications/*`
- Store: `stores/notification.js`

---

### 6. 新增用戶詳情頁面

**位置**: 新建 `frontend/src/views/UserDetail.vue`

**需求**:
- 完整個人檔案展示
- 所有照片輪播
- 完整興趣標籤
- 完整自我介紹
- 配對分數

**工作量**: 4-6 小時

**相關**:
- 後端 API: 可能需要新增 `GET /api/users/{user_id}/profile`
- 或使用現有 discovery 資料

---

### 7. 新增用戶申訴介面

**位置**: 可在 `PhotoUploader.vue` 或新建組件

**需求**:
- 照片被拒絕時顯示申訴按鈕
- 申訴理由輸入
- 查看申訴狀態

**工作量**: 3-4 小時

**相關**:
- 後端 API: `POST /api/moderation/appeals`, `GET /api/moderation/appeals/my`

---

### 8. 新增我的舉報記錄

**位置**: `frontend/src/views/Settings.vue` 或新頁面

**需求**:
- 舉報列表
- 舉報狀態（待處理/已處理）
- 處理結果

**工作量**: 2-3 小時

**相關**:
- 後端 API: `GET /api/safety/reports`
- Store: 需在 `safety.js` 新增 `fetchMyReports`

---

## P3: 未來考慮

### 9. 超級喜歡功能

**說明**: 特殊互動，讓對方知道你特別喜歡

**需求**:
- 後端: 新增 SuperLike 模型和 API
- 前端: 新增「超級喜歡」按鈕

**工作量**: 6-8 小時

---

### 10. 回顧功能

**說明**: 重新查看已跳過的用戶

**需求**:
- 後端: 修改跳過邏輯，保留記錄
- 前端: 新增「回顧」按鈕

**工作量**: 4-6 小時

---

### 11. 每日推薦

**說明**: 系統精選推薦用戶

**需求**:
- 後端: 推薦演算法
- 前端: 推薦用戶展示區

**工作量**: 8-12 小時

---

### 12. 用戶在線狀態

**說明**: 顯示用戶是否在線或最後活躍時間

**需求**:
- 後端: 追蹤在線狀態
- 前端: 在線指示器

**工作量**: 4-6 小時

---

## 實施路線圖建議

### 第一階段（立即）
1. 修復 Blocked.vue logger 錯誤 (P0)
2. 統一檔案大小限制 (P1)

### 第二階段（本週）
3. 配對偏好設定 UI (P1)
4. 管理員用戶管理 (P1)

### 第三階段（下週）
5. 通知中心頁面 (P2)
6. 用戶詳情頁面 (P2)

### 第四階段（後續）
7. 用戶申訴介面 (P2)
8. 我的舉報記錄 (P2)

### 未來版本
9-12. P3 功能根據用戶反饋決定

---

## 技術債務

### 需要重構的部分

1. **Store 模式統一**
   - 部分 store 使用 Options API
   - 建議統一使用 Composition API

2. **錯誤處理標準化**
   - 統一錯誤訊息格式
   - 統一錯誤顯示方式

3. **API 呼叫抽象**
   - 考慮使用 composables 封裝常用 API 操作
   - 減少重複程式碼

4. **測試覆蓋率**
   - 前端測試覆蓋率需提升
   - 增加 E2E 測試

---

## 參考資源

- **Skill: backend-dev-fastapi** - 後端開發規範
- **Skill: frontend-dev-vue3** - 前端開發規範
- **Skill: api-routing-standards** - API 設計規範
- **Skill: testing-guide** - 測試策略
