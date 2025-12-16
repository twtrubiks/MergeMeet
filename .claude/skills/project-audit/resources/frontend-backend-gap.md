# 前後端功能差異分析

> 最後更新: 2025-12-16

## 後端有實現，前端未完全使用的功能

### 1. 用戶管理 API (管理後台)

**後端 API** (`backend/app/api/admin.py`):
```python
@router.get("/users")           # 獲取用戶列表（含搜尋、篩選）
@router.post("/users/ban")      # 封禁用戶
@router.post("/users/unban")    # 解封用戶
```

**前端狀態**: AdminDashboard.vue 缺少「用戶管理」Tab

**影響**: 管理員無法直接在後台搜尋和管理用戶

**建議**: 在 AdminDashboard 新增用戶管理功能

---

### 2. 通知中心

**後端 API** (`backend/app/api/notifications.py`):
```python
@router.get("")                           # 獲取通知列表
@router.put("/{notification_id}/read")    # 標記已讀
@router.put("/read-all")                  # 全部標記已讀
@router.delete("/{notification_id}")       # 刪除通知
```

**前端狀態**:
- `stores/notification.js` 有基本實現
- 缺少專門的 `/notifications` 頁面

**影響**: 用戶無法查看和管理歷史通知

**建議**: 新增通知中心頁面，顯示所有通知歷史

---

### 3. 用戶申訴介面

**後端 API** (`backend/app/api/moderation.py`):
```python
@router.post("/appeals")         # 提交申訴
@router.get("/appeals/my")       # 查看我的申訴
```

**前端狀態**: 僅管理後台有申訴「處理」功能，一般用戶無法「提交」申訴

**影響**: 用戶內容被審核拒絕後無法申訴

**建議**: 在照片或訊息被拒絕時，提供申訴入口

---

### 4. 我的舉報記錄

**後端 API** (`backend/app/api/safety.py`):
```python
@router.get("/reports")          # 獲取我提交的舉報記錄
```

**前端狀態**: `stores/safety.js` 沒有 `fetchMyReports` 方法

**影響**: 用戶無法追蹤舉報處理進度

**建議**: 在設定頁或專門頁面顯示舉報記錄

---

### 5. 配對偏好設定

**後端 API** (`backend/app/api/profile.py`):
```python
# ProfileUpdateRequest 支援以下偏好設定:
min_age_preference: int
max_age_preference: int
max_distance_km: int
gender_preference: str
```

**前端狀態**: Profile.vue 和 Settings.vue 沒有偏好設定 UI

**影響**: 用戶無法調整配對篩選條件

**建議**: 在設定頁新增「配對偏好」區塊

---

## 檢查腳本

### 列出後端所有 API 端點

```bash
# 在專案根目錄執行
grep -rh "@router\.\(get\|post\|put\|patch\|delete\)" backend/app/api/ \
  | grep -oE '@router\.[a-z]+\("[^"]*"' \
  | sort | uniq
```

### 列出前端所有 API 呼叫

```bash
grep -rh "apiClient\.\(get\|post\|put\|patch\|delete\)" frontend/src/ \
  | grep -oE "apiClient\.[a-z]+\('[^']*'" \
  | sort | uniq
```

### 對比差異

```bash
# 產生後端端點清單
grep -rh "@router" backend/app/api/*.py | grep -oE '"[^"]*"' | sort | uniq > /tmp/backend_endpoints.txt

# 產生前端呼叫清單
grep -rh "apiClient" frontend/src/**/*.{js,vue} 2>/dev/null | grep -oE "'/[^']*'" | sort | uniq > /tmp/frontend_calls.txt

# 手動比較
```

---

## 對應關係表

| 後端 API | 前端 Store/Component | 狀態 |
|---------|---------------------|------|
| `/api/auth/*` | `stores/user.js` | COMPLETE |
| `/api/profile/*` | `stores/profile.js` | COMPLETE |
| `/api/discovery/*` | `stores/discovery.js` | COMPLETE |
| `/api/matches/*` | `stores/match.js` | COMPLETE |
| `/api/messages/*` | `stores/message.js` | COMPLETE |
| `/api/safety/*` | `stores/safety.js` | PARTIAL |
| `/api/notifications/*` | `stores/notification.js` | PARTIAL |
| `/api/moderation/*` (用戶) | - | MISSING |
| `/api/admin/*` | `AdminDashboard.vue` | PARTIAL |

---

## 優先修復建議

### P0 (高優先級)
1. **配對偏好設定 UI** - 影響用戶體驗
2. **管理員用戶管理** - 管理員核心功能

### P1 (中優先級)
3. **通知中心頁面** - 完善通知系統
4. **用戶申訴介面** - 公平性保障

### P2 (低優先級)
5. **我的舉報記錄** - 增強透明度
