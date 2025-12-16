# 已知問題和潛在 Bug

> 最後更新: 2025-12-16

## 嚴重問題 (P0)

### 1. Blocked.vue 中 logger 未定義

**檔案**: `frontend/src/views/Blocked.vue:120`

**問題**: 使用了 `logger.error` 但沒有 import logger

```javascript
// 第 120 行
} catch (error) {
  logger.error('載入封鎖列表失敗:', error)  // logger 未定義
}
```

**影響**: 執行時會報 ReferenceError

**修復方案**:
```javascript
import { logger } from '@/utils/logger'
```

---

## 中等問題 (P1)

### 2. 前後端檔案大小驗證不一致

**檔案**:
- `frontend/src/components/PhotoUploader.vue:107` - 驗證 10MB
- `backend/app/core/config.py` - MAX_UPLOAD_SIZE 設定

**問題**:
```javascript
// 前端 PhotoUploader.vue
if (file.size > 10 * 1024 * 1024) {  // 10MB
  error.value = '圖片大小不能超過 10MB'
}
```

```python
# 後端 config.py
MAX_UPLOAD_SIZE: int = 5 * 1024 * 1024  # 5MB (可能的設定)
```

**影響**: 前端允許上傳的檔案可能被後端拒絕，造成困惑

**修復方案**: 統一前後端大小限制，建議使用環境變數配置

---

### 3. Discovery.vue 缺少用戶詳情查看功能

**檔案**: `frontend/src/views/Discovery.vue`

**問題**: 用戶只能看到候選人的卡片摘要，無法點擊查看完整個人檔案

**影響**: 用戶無法獲取足夠資訊做出配對決策

**修復方案**:
1. 新增 `UserDetail.vue` 頁面
2. 在卡片上新增「查看詳情」按鈕
3. 或點擊照片進入詳情頁

---

### 4. AdminDashboard 缺少用戶管理功能

**檔案**: `frontend/src/views/admin/AdminDashboard.vue`

**問題**: 後端有完整的用戶管理 API，但前端缺少對應的 Tab

**影響**: 管理員無法直接管理用戶（搜尋、封禁、解封）

**修復方案**: 新增「用戶管理」Tab，包含：
- 用戶搜尋
- 用戶列表（分頁）
- 封禁/解封操作

---

## 輕微問題 (P2)

### 5. Settings.vue 缺少配對偏好設定

**檔案**: `frontend/src/views/Settings.vue`

**問題**: 用戶無法在 UI 中調整配對偏好

**影響**: 用戶需要手動調用 API 才能修改偏好

**修復方案**: 新增配對偏好設定區塊：
- 年齡範圍滑桿
- 最大距離選擇
- 性別偏好選擇

---

### 6. 通知頁面缺失

**檔案**: 缺少 `frontend/src/views/Notifications.vue`

**問題**: 用戶無法查看和管理歷史通知

**影響**: 通知只能即時看到，無法回顧

**修復方案**:
1. 新增 `/notifications` 路由
2. 建立 `Notifications.vue` 頁面
3. 顯示通知列表，支援已讀/刪除操作

---

### 7. 照片審核被拒絕時缺少申訴入口

**檔案**: `frontend/src/components/PhotoUploader.vue`

**問題**: 顯示了拒絕原因但沒有申訴選項

**影響**: 用戶認為照片被錯誤拒絕時無法申訴

**修復方案**: 在被拒絕的照片卡片上新增「申訴」按鈕

---

## 潛在問題（需驗證）

### 8. WebSocket 重連機制

**相關檔案**:
- `frontend/src/stores/message.js`
- `frontend/src/stores/notification.js`

**疑慮**: WebSocket 斷線後的重連邏輯是否完善？

**驗證方法**:
1. 開啟聊天頁面
2. 斷開網路連線
3. 重新連線
4. 檢查 WebSocket 是否自動重連

---

### 9. 並發操作處理

**相關檔案**: `frontend/src/views/Discovery.vue`

**疑慮**: 快速連續點擊喜歡/跳過時，是否正確處理並發？

**驗證方法**:
1. 快速連續點擊「喜歡」按鈕
2. 檢查 API 請求數量
3. 確認候選人列表狀態正確

**現狀**: 有使用 throttle（500ms），但需確認效果

---

### 10. 圖片載入錯誤處理

**檔案**: `frontend/src/views/Discovery.vue:47`

**現狀**:
```javascript
@error="(e) => e.target.src = defaultAvatar"
```

**疑慮**: `defaultAvatar` 指向 `/default-avatar.png`，需確認此檔案存在

**驗證方法**: 檢查 `frontend/public/default-avatar.png` 是否存在

---

## 待驗證清單

使用 Chrome DevTools MCP 或手動測試驗證以下項目：

- [ ] Blocked.vue logger 錯誤是否影響功能
- [ ] 上傳超過 5MB 但小於 10MB 的照片會發生什麼
- [ ] WebSocket 斷線重連測試
- [ ] 快速操作並發測試
- [ ] 預設頭像檔案是否存在

---

## 修復追蹤

| 問題 ID | 狀態 | 修復日期 | PR |
|--------|------|---------|-----|
| #1 | OPEN | - | - |
| #2 | OPEN | - | - |
| #3 | OPEN | - | - |
| #4 | OPEN | - | - |
| #5 | OPEN | - | - |
| #6 | OPEN | - | - |
| #7 | OPEN | - | - |
