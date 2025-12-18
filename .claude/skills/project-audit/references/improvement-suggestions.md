# 改進建議與優化指南

本文件提供專案優化的方向和最佳實踐建議。

---

## 優化類別

| 類別 | 說明 |
|-----|------|
| **效能優化** | 載入速度、回應時間 |
| **程式碼品質** | 可維護性、可讀性 |
| **用戶體驗** | 操作流暢度、回饋 |
| **安全性** | 防護措施、資料保護 |

---

## 效能優化

### 前端優化

#### Bundle Size 優化

**問題**：主 bundle 過大導致首次載入慢

**解決方案**：

1. **Code Splitting**
```javascript
// vite.config.js
build: {
  rollupOptions: {
    output: {
      manualChunks: {
        'naive-ui': ['naive-ui'],
        'vendor': ['vue', 'vue-router', 'pinia']
      }
    }
  }
}
```

2. **路由懶載入**
```javascript
// router/index.js
const routes = [
  {
    path: '/settings',
    component: () => import('@/views/Settings.vue')
  }
]
```

3. **依賴分析**
```bash
# 分析 bundle 組成
npm run build -- --report
```

#### 圖片優化

**建議**：
- 使用 WebP 格式
- 實作懶載入
- 設定適當的圖片尺寸

```vue
<img
  :src="imageUrl"
  loading="lazy"
  :width="300"
  :height="300"
/>
```

### 後端優化

#### 資料庫查詢優化

**問題**：N+1 查詢

**解決方案**：使用 eager loading
```python
# 不好
users = await session.execute(select(User))
for user in users:
    photos = user.photos  # N+1

# 好
users = await session.execute(
    select(User).options(selectinload(User.photos))
)
```

#### 快取策略

**適合快取的資料**：
- 敏感詞列表
- 系統配置
- 熱門內容

```python
# 使用記憶體快取
from functools import lru_cache

@lru_cache(maxsize=100, ttl=300)
async def get_sensitive_words():
    ...
```

---

## 程式碼品質

### 前端最佳實踐

#### Store 模式統一

**建議**：統一使用 Composition API

```javascript
// stores/example.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useExampleStore = defineStore('example', () => {
  // state
  const items = ref([])
  const loading = ref(false)

  // getters
  const itemCount = computed(() => items.value.length)

  // actions
  async function fetchItems() {
    loading.value = true
    try {
      // ...
    } finally {
      loading.value = false
    }
  }

  return { items, loading, itemCount, fetchItems }
})
```

#### 錯誤處理標準化

**建議**：統一錯誤處理方式

```javascript
// utils/errorHandler.js
export function handleApiError(error, message) {
  const errorMessage = error.response?.data?.detail || message.error(errorMessage)
  logger.error(errorMessage, error)
}

// 使用
try {
  await apiClient.post('/api/something')
} catch (error) {
  handleApiError(error, message)
}
```

### 後端最佳實踐

#### 依賴注入模式

```python
# 使用 Depends 進行依賴注入
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    ...

@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_user)
):
    ...
```

#### 統一回應格式

```python
# schemas/response.py
class APIResponse(BaseModel):
    success: bool = True
    data: Any = None
    message: str = ""

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: str = ""
```

---

## 用戶體驗優化

### 載入狀態

**必要元素**：
- 骨架屏 (Skeleton)
- 載入指示器
- 錯誤狀態

```vue
<template>
  <div v-if="loading">
    <n-skeleton text :repeat="3" />
  </div>
  <div v-else-if="error">
    <n-result status="error" :description="error" />
  </div>
  <div v-else>
    <!-- 內容 -->
  </div>
</template>
```

### 操作回饋

**必要回饋**：
- 操作成功提示
- 操作失敗提示
- 確認對話框（危險操作）

```javascript
// 成功
message.success('儲存成功')

// 失敗
message.error('操作失敗，請稍後再試')

// 確認
dialog.warning({
  title: '確認刪除',
  content: '此操作無法復原',
  positiveText: '確認',
  negativeText: '取消',
  onPositiveClick: () => handleDelete()
})
```

### 表單驗證

**建議**：即時驗證 + 提交驗證

```vue
<n-form :rules="rules" :model="form">
  <n-form-item label="Email" path="email">
    <n-input v-model:value="form.email" />
  </n-form-item>
</n-form>
```

---

## 安全性加強

### 前端安全

- [ ] XSS 防護：避免 v-html 使用未過濾內容
- [ ] CSRF Token 處理
- [ ] 敏感資料不存 localStorage

### 後端安全

- [ ] 輸入驗證（Pydantic）
- [ ] SQL 注入防護（ORM）
- [ ] Rate Limiting
- [ ] 密碼加密儲存

---

## 測試覆蓋

### 建議覆蓋率

| 類型 | 目標 |
|-----|------|
| 單元測試 | > 80% |
| 整合測試 | 關鍵流程 |
| E2E 測試 | 核心功能 |

### 測試重點

**後端**：
- API 端點
- 業務邏輯
- 資料驗證

**前端**：
- Store 邏輯
- 關鍵組件
- 用戶流程

---

## 可選功能建議

### 交友軟體進階功能

| 功能 | 複雜度 | 說明 |
|-----|:-----:|------|
| 超級喜歡 | 中 | 特殊互動功能 |
| 回顧功能 | 低 | 查看跳過的用戶 |
| 每日推薦 | 高 | 需要推薦演算法 |
| 用戶在線狀態 | 中 | 需要狀態追蹤 |
| 視訊通話 | 高 | 需要 WebRTC |

---

## 參考資源

- **Skill: backend-dev-fastapi** - 後端開發規範
- **Skill: frontend-dev-vue3** - 前端開發規範
- **Skill: api-routing-standards** - API 設計規範
