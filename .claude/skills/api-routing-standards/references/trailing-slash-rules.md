# 尾隨斜線規則詳細說明

> 基本規則已在 [SKILL.md](../SKILL.md) 說明。本文件提供檢查工具和測試方法。

---

## 檢查現有程式碼

### 後端：搜尋錯誤的路由定義

```bash
cd backend

# 搜尋 @router.get("/") 等錯誤模式
grep -rn '@router\.get\("\/"\)' app/api/
grep -rn '@router\.post\("\/"\)' app/api/
grep -rn '@router\.put\("\/"\)' app/api/

# 搜尋任何以 / 結尾的路由
grep -rn '@router\.\w*\(".*\/"\)' app/api/
```

### 前端：搜尋帶尾隨斜線的 API 呼叫

```bash
cd frontend

# 搜尋 axios 呼叫中的尾隨斜線
grep -rn "axios\.\w*('/api/.*/')" src/
grep -rn 'axios\.\w*("/api/.*/")' src/
```

---

## 快速測試

```bash
# 正確格式 - 應該返回 200
curl -w "\nHTTP: %{http_code}\n" -s -o /dev/null \
  http://localhost:8000/api/profile \
  -H "Authorization: Bearer $TOKEN"

# 錯誤格式 - 應該返回 404
curl -w "\nHTTP: %{http_code}\n" -s -o /dev/null \
  http://localhost:8000/api/profile/ \
  -H "Authorization: Bearer $TOKEN"
```

---

## 相關資源

- [SKILL.md](../SKILL.md) - 核心規則與範例
- [RESTful 原則](restful-principles.md)
