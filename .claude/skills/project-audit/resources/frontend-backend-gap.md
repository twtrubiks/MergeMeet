# 前後端功能對應檢查指南

本文件說明如何檢查前後端功能是否對應，以及常見的差異類型。

---

## 檢查流程

### 步驟 1：列出後端 API 端點

```bash
# 列出所有路由定義
grep -rh "@router\.\(get\|post\|put\|patch\|delete\)" backend/app/api/ \
  | grep -oE '@router\.[a-z]+\("[^"]*"' \
  | sort | uniq
```

### 步驟 2：列出前端 API 呼叫

```bash
# 列出所有 apiClient 呼叫
grep -rh "apiClient\.\(get\|post\|put\|patch\|delete\)" frontend/src/ \
  | grep -oE "apiClient\.[a-z]+\('[^']*'" \
  | sort | uniq
```

### 步驟 3：交叉比對

比較兩份清單，找出：
- 後端有但前端未使用的 API
- 前端呼叫但後端不存在的 API

---

## API 對應關係參考表

| 後端模組 | API 前綴 | 前端 Store/Component |
|---------|---------|---------------------|
| `auth.py` | `/api/auth/*` | `stores/user.js` |
| `profile.py` | `/api/profile/*` | `stores/profile.js` |
| `discovery.py` | `/api/discovery/*` | `stores/discovery.js` |
| `matches.py` | `/api/matches/*` | `stores/match.js` |
| `messages.py` | `/api/messages/*` | `stores/message.js` |
| `safety.py` | `/api/safety/*` | `stores/safety.js` |
| `notifications.py` | `/api/notifications/*` | `stores/notification.js` |
| `moderation.py` | `/api/moderation/*` | 相關組件（如 PhotoUploader） |
| `admin.py` | `/api/admin/*` | `views/admin/AdminDashboard.vue` |

---

## 常見差異類型

### 類型 1：後端有，前端未實現

**特徵**：後端 API 存在但前端沒有對應的 UI 或呼叫

**檢查方法**：
```bash
# 搜尋特定 API 是否被前端使用
grep -r "/api/some-endpoint" frontend/src/
```

**常見原因**：
- 功能尚未開發前端部分
- API 為內部使用（如管理功能）
- 預留給未來版本

### 類型 2：前端有，後端未實現

**特徵**：前端有 UI 但 API 呼叫會 404

**檢查方法**：
```bash
# 確認後端是否有對應路由
grep -r "some-endpoint" backend/app/api/
```

**常見原因**：
- 前端先行開發，後端未跟上
- API 路徑拼寫錯誤
- 路由註冊遺漏

### 類型 3：參數不一致

**特徵**：API 存在但請求/回應格式不匹配

**檢查方法**：
1. 查看後端 Pydantic schema
2. 對比前端發送的資料結構

**常見問題**：
- 欄位名稱大小寫不同（snake_case vs camelCase）
- 必填欄位遺漏
- 資料類型不匹配

---

## 重點檢查區域

### 用戶功能 API

| API | 用途 | 前端位置 |
|-----|------|---------|
| `GET /api/profile` | 獲取個人檔案 | stores/profile.js |
| `PATCH /api/profile` | 更新檔案（含偏好） | Settings.vue |
| `GET /api/notifications` | 通知列表 | Notifications.vue |
| `GET /api/safety/reports` | 我的舉報記錄 | MyReports.vue |
| `POST /api/moderation/appeals` | 提交申訴 | PhotoUploader.vue |

### 管理功能 API

| API | 用途 | 前端位置 |
|-----|------|---------|
| `GET /api/admin/users` | 用戶列表 | AdminDashboard 用戶管理 Tab |
| `POST /api/admin/users/ban` | 封禁用戶 | AdminDashboard 封禁按鈕 |
| `POST /api/admin/users/unban` | 解封用戶 | AdminDashboard 解封按鈕 |
| `GET /api/admin/stats` | 統計資料 | AdminDashboard 儀表板 |

---

## 自動化檢查腳本

可建立腳本自動比對：

```python
# scripts/check_api_coverage.py
import subprocess
import re

def get_backend_endpoints():
    """從後端程式碼提取所有 API 端點"""
    result = subprocess.run(
        ['grep', '-rh', '@router', 'backend/app/api/'],
        capture_output=True, text=True
    )
    endpoints = re.findall(r'@router\.\w+\("([^"]+)"', result.stdout)
    return set(endpoints)

def get_frontend_calls():
    """從前端程式碼提取所有 API 呼叫"""
    result = subprocess.run(
        ['grep', '-rh', 'apiClient', 'frontend/src/'],
        capture_output=True, text=True
    )
    calls = re.findall(r"apiClient\.\w+\('([^']+)'", result.stdout)
    return set(calls)

def compare():
    backend = get_backend_endpoints()
    frontend = get_frontend_calls()

    print("後端有但前端未使用:")
    for ep in backend - frontend:
        print(f"  - {ep}")

    print("\n前端呼叫但後端不存在:")
    for ep in frontend - backend:
        print(f"  - {ep}")
```

---

## 檢查清單

審查時確認以下項目：

- [ ] 所有後端 API 都有對應的前端呼叫或明確標記為「僅內部使用」
- [ ] 所有前端 API 呼叫都能正常回應（無 404）
- [ ] 請求/回應的資料結構一致
- [ ] 錯誤處理有對應的前端顯示
- [ ] WebSocket 事件有對應的前端處理器
