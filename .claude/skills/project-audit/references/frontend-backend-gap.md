# 前後端差異檢查

> 檢查前後端 API 是否對應完整。

---

## 檢查指令

### 列出後端 API

```bash
grep -rh "@router\.\(get\|post\|put\|patch\|delete\)" backend/app/api/ \
  | grep -oE '@router\.[a-z]+\("[^"]*"' | sort | uniq
```

### 列出前端 API 呼叫

```bash
grep -rh "apiClient\.\(get\|post\|put\|patch\|delete\)" frontend/src/ \
  | grep -oE "apiClient\.[a-z]+\('[^']*'" | sort | uniq
```

### 搜尋特定 API

```bash
# 後端是否有此端點
grep -rn "/api/some-endpoint" backend/app/api/

# 前端是否有呼叫
grep -rn "/api/some-endpoint" frontend/src/
```

---

## API 對應表

| 後端模組 | API 前綴 | 前端 Store/Component |
|---------|---------|---------------------|
| auth.py | `/api/auth/*` | user.js |
| profile.py | `/api/profile/*` | profile.js |
| discovery.py | `/api/discovery/*` | discovery.js |
| messages.py | `/api/messages/*` | chat.js |
| safety.py | `/api/safety/*` | safety.js |
| notifications.py | `/api/notifications/*` | notification.js |
| moderation.py | `/api/moderation/*` | 相關組件 |
| photo_moderation.py | `/api/admin/photos/*` | AdminDashboard.vue |
| websocket.py | `/ws/*` | websocket.js |
| admin.py | `/api/admin/*` | AdminDashboard.vue |

---

## 常見問題

| 類型 | 說明 |
|------|------|
| 後端有，前端無 | API 存在但前端未實現 |
| 前端有，後端無 | 前端呼叫但 API 不存在（404） |
| 參數不一致 | 欄位名稱或類型不匹配 |
