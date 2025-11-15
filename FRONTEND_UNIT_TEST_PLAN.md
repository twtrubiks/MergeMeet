# 前端單元測試規劃

**建立日期**: 2025-11-15
**測試框架**: Vitest + Vue Test Utils
**目標覆蓋率**: 70%+
**預計工時**: 2-3 小時

---

## 📋 測試範圍總覽

### 優先級分類
- **P0 (必須)**: 核心業務邏輯，影響主要功能
- **P1 (重要)**: 重要功能，但有替代方案
- **P2 (可選)**: 輔助功能，對核心流程影響較小

---

## 🏗️ Phase 1: 環境設置（15-20分鐘）

### 1.1 創建測試配置文件

**檔案**: `frontend/vitest.config.js`

```javascript
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  test: {
    globals: true,
    environment: 'jsdom',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/main.js',
        'src/router/',
        '**/*.config.js'
      ]
    },
    setupFiles: ['./tests/setup.js']
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  }
})
```

### 1.2 創建測試設置文件

**檔案**: `frontend/tests/setup.js`

```javascript
import { vi } from 'vitest'

// Mock localStorage
global.localStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn()
}

// Mock WebSocket
global.WebSocket = vi.fn(() => ({
  send: vi.fn(),
  close: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn()
}))

// Mock console methods to reduce test noise
global.console = {
  ...console,
  log: vi.fn(),
  error: vi.fn(),
  warn: vi.fn()
}
```

### 1.3 安裝測試依賴

```bash
npm install -D @vitest/ui @vitest/coverage-v8 jsdom happy-dom
```

---

## 🧪 Phase 2: Pinia Stores 測試（60-80分鐘）

### 2.1 User Store 測試 (P0 - 必須)

**檔案**: `frontend/tests/stores/user.spec.js`

**測試覆蓋**:
- ✅ 初始狀態驗證
- ✅ `register()` - 成功註冊
- ✅ `register()` - 失敗處理
- ✅ `login()` - 成功登入
- ✅ `login()` - 失敗處理
- ✅ `logout()` - 清除狀態
- ✅ `saveTokens()` - Token 儲存
- ✅ `clearTokens()` - Token 清除
- ✅ `initializeFromToken()` - JWT 解析
- ✅ `isAuthenticated` computed 屬性

**預計時間**: 15-20分鐘

### 2.2 Chat Store 測試 (P0 - 必須)

**檔案**: `frontend/tests/stores/chat.spec.js`

**測試覆蓋**:
- ✅ `fetchConversations()` - 獲取對話列表
- ✅ `fetchChatHistory()` - 獲取聊天記錄（分頁）
- ✅ `sendMessage()` - 發送訊息
- ✅ `deleteMessage()` - 刪除訊息
- ✅ `markAsRead()` - 標記已讀
- ✅ `handleNewMessage()` - 新訊息事件處理
- ✅ `handleMessageDeleted()` - 刪除訊息事件處理
- ✅ `handleTypingIndicator()` - 打字指示器
- ✅ `handleReadReceipt()` - 已讀回條
- ✅ `joinMatchRoom()` / `leaveMatchRoom()` - 聊天室管理
- ✅ `unreadCount` computed 屬性

**預計時間**: 25-30分鐘

### 2.3 Discovery Store 測試 (P0 - 必須)

**檔案**: `frontend/tests/stores/discovery.spec.js`

**測試覆蓋**:
- ✅ `fetchCandidates()` - 獲取候選人
- ✅ `likeUser()` - 喜歡用戶
- ✅ `passUser()` - 跳過用戶
- ✅ `fetchMatches()` - 獲取配對列表
- ✅ 狀態更新邏輯

**預計時間**: 10-15分鐘

### 2.4 Profile Store 測試 (P1 - 重要)

**檔案**: `frontend/tests/stores/profile.spec.js`

**測試覆蓋**:
- ✅ `fetchProfile()` - 獲取個人檔案
- ✅ `createProfile()` - 創建檔案
- ✅ `updateProfile()` - 更新檔案
- ✅ `updateInterests()` - 更新興趣
- ✅ `uploadPhoto()` / `deletePhoto()` - 照片管理

**預計時間**: 10-15分鐘

### 2.5 Safety Store 測試 (P1 - 重要)

**檔案**: `frontend/tests/stores/safety.spec.js`

**測試覆蓋**:
- ✅ `blockUser()` - 封鎖用戶
- ✅ `unblockUser()` - 解除封鎖
- ✅ `fetchBlockedUsers()` - 獲取封鎖列表
- ✅ `reportUser()` - 舉報用戶

**預計時間**: 10分鐘

---

## 🎯 Phase 3: Composables 測試（30-40分鐘）

### 3.1 useWebSocket 測試 (P0 - 必須)

**檔案**: `frontend/tests/composables/useWebSocket.spec.js`

**測試覆蓋**:
- ✅ `connect()` - 建立連接
- ✅ `disconnect()` - 斷開連接
- ✅ `send()` - 發送訊息
- ✅ `sendChatMessage()` - 發送聊天訊息
- ✅ `sendTypingIndicator()` - 發送打字指示
- ✅ `sendReadReceipt()` - 發送已讀回條
- ✅ `joinMatch()` / `leaveMatch()` - 加入/離開聊天室
- ✅ `onMessage()` - 註冊訊息處理器
- ✅ `handleMessage()` - 處理收到的訊息
- ✅ 自動重連邏輯
- ✅ `isConnected` / `isConnecting` computed 屬性

**預計時間**: 30-40分鐘

---

## 🎨 Phase 4: Vue 組件測試（40-50分鐘）

### 4.1 MessageBubble.vue 測試 (P0 - 必須)

**檔案**: `frontend/tests/components/chat/MessageBubble.spec.js`

**測試覆蓋**:
- ✅ 渲染自己的訊息（右側）
- ✅ 渲染對方的訊息（左側）
- ✅ 顯示已讀狀態（✓✓）
- ✅ 右鍵選單（只有自己的訊息可以刪除）
- ✅ 刪除訊息事件發射
- ✅ 時間格式化顯示

**預計時間**: 15-20分鐘

### 4.2 InterestSelector.vue 測試 (P1 - 重要)

**檔案**: `frontend/tests/components/InterestSelector.spec.js`

**測試覆蓋**:
- ✅ 渲染興趣列表
- ✅ 選擇/取消選擇興趣
- ✅ 興趣數量限制
- ✅ 事件發射

**預計時間**: 10-15分鐘

### 4.3 MatchModal.vue 測試 (P1 - 重要)

**檔案**: `frontend/tests/components/MatchModal.spec.js`

**測試覆蓋**:
- ✅ 配對成功時顯示
- ✅ 顯示對方資訊
- ✅ 「開始聊天」按鈕
- ✅ Modal 關閉

**預計時間**: 10分鐘

### 4.4 PhotoUploader.vue 測試 (P2 - 可選)

**檔案**: `frontend/tests/components/PhotoUploader.spec.js`

**測試覆蓋**:
- ✅ 選擇檔案
- ✅ 檔案格式驗證
- ✅ 檔案大小限制
- ✅ 上傳事件發射

**預計時間**: 5-10分鐘

---

## 📊 測試示例

### 範例 1: User Store 測試

```javascript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUserStore } from '@/stores/user'
import { authAPI } from '@/api/auth'

// Mock authAPI
vi.mock('@/api/auth', () => ({
  authAPI: {
    register: vi.fn(),
    login: vi.fn(),
    verifyEmail: vi.fn(),
    resendVerification: vi.fn()
  }
}))

describe('User Store', () => {
  beforeEach(() => {
    // 每次測試前創建新的 Pinia 實例
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('應該初始化為未登入狀態', () => {
    const store = useUserStore()

    expect(store.user).toBeNull()
    expect(store.isAuthenticated).toBe(false)
    expect(store.isLoading).toBe(false)
    expect(store.error).toBeNull()
  })

  it('應該成功註冊用戶', async () => {
    const store = useUserStore()
    const mockResponse = {
      access_token: 'mock_access_token',
      refresh_token: 'mock_refresh_token'
    }

    authAPI.register.mockResolvedValue(mockResponse)

    const result = await store.register({
      email: 'test@example.com',
      password: 'Password123',
      date_of_birth: '1995-01-01'
    })

    expect(result).toBe(true)
    expect(store.accessToken).toBe('mock_access_token')
    expect(store.isAuthenticated).toBe(true)
    expect(localStorage.setItem).toHaveBeenCalledWith('access_token', 'mock_access_token')
  })

  it('應該處理註冊失敗', async () => {
    const store = useUserStore()
    const mockError = {
      response: {
        data: {
          detail: '電子郵件已被使用'
        }
      }
    }

    authAPI.register.mockRejectedValue(mockError)

    const result = await store.register({
      email: 'test@example.com',
      password: 'Password123'
    })

    expect(result).toBe(false)
    expect(store.error).toBe('電子郵件已被使用')
    expect(store.isAuthenticated).toBe(false)
  })

  it('應該正確登出並清除狀態', () => {
    const store = useUserStore()

    // 設置已登入狀態
    store.accessToken = 'test_token'
    store.user = { id: '123', email: 'test@example.com' }

    store.logout()

    expect(store.user).toBeNull()
    expect(store.accessToken).toBeNull()
    expect(store.isAuthenticated).toBe(false)
    expect(localStorage.removeItem).toHaveBeenCalledWith('access_token')
  })
})
```

### 範例 2: useWebSocket 測試

```javascript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useWebSocket } from '@/composables/useWebSocket'
import { setActivePinia, createPinia } from 'pinia'
import { useUserStore } from '@/stores/user'

describe('useWebSocket', () => {
  let mockWebSocket

  beforeEach(() => {
    setActivePinia(createPinia())

    // Mock WebSocket
    mockWebSocket = {
      send: vi.fn(),
      close: vi.fn(),
      readyState: WebSocket.OPEN,
      onopen: null,
      onmessage: null,
      onclose: null,
      onerror: null
    }

    global.WebSocket = vi.fn(() => mockWebSocket)

    // 設置已登入用戶
    const userStore = useUserStore()
    userStore.user = { id: 'user123', email: 'test@example.com' }
    userStore.accessToken = 'test_token'
  })

  it('應該成功建立 WebSocket 連接', () => {
    const ws = useWebSocket()

    ws.connect()

    expect(WebSocket).toHaveBeenCalled()
    expect(ws.connectionState.value).toBe('connecting')

    // 模擬連接成功
    mockWebSocket.onopen()

    expect(ws.connectionState.value).toBe('connected')
    expect(ws.isConnected.value).toBe(true)
  })

  it('應該正確發送聊天訊息', () => {
    const ws = useWebSocket()
    ws.connect()
    mockWebSocket.onopen()

    const result = ws.sendChatMessage('match123', 'Hello!', 'TEXT')

    expect(result).toBe(true)
    expect(mockWebSocket.send).toHaveBeenCalledWith(
      JSON.stringify({
        type: 'chat_message',
        match_id: 'match123',
        content: 'Hello!',
        message_type: 'TEXT'
      })
    )
  })

  it('應該註冊並調用訊息處理器', () => {
    const ws = useWebSocket()
    const handler = vi.fn()

    ws.onMessage('new_message', handler)

    // 模擬收到訊息
    const messageData = {
      type: 'new_message',
      message: { id: '123', content: 'Test' }
    }

    mockWebSocket.onmessage({ data: JSON.stringify(messageData) })

    expect(handler).toHaveBeenCalledWith(messageData)
  })

  it('應該在連接失敗時嘗試重連', () => {
    vi.useFakeTimers()
    const ws = useWebSocket()

    ws.connect()

    // 模擬連接關閉（非正常關閉）
    mockWebSocket.onclose({ code: 1006, reason: 'Abnormal closure' })

    expect(ws.reconnectAttempts.value).toBe(1)

    // 快進到重連時間
    vi.advanceTimersByTime(3000)

    expect(WebSocket).toHaveBeenCalledTimes(2) // 初始連接 + 重連

    vi.useRealTimers()
  })
})
```

### 範例 3: MessageBubble.vue 測試

```javascript
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import MessageBubble from '@/components/chat/MessageBubble.vue'
import { NDropdown } from 'naive-ui'

describe('MessageBubble', () => {
  const mockMessage = {
    id: 'msg123',
    content: 'Hello World!',
    sent_at: '2025-11-15T10:00:00Z',
    is_read: true,
    sender_id: 'user123'
  }

  it('應該渲染訊息內容', () => {
    const wrapper = mount(MessageBubble, {
      props: {
        message: mockMessage,
        isOwn: true
      }
    })

    expect(wrapper.text()).toContain('Hello World!')
  })

  it('應該顯示自己的訊息在右側', () => {
    const wrapper = mount(MessageBubble, {
      props: {
        message: mockMessage,
        isOwn: true
      }
    })

    const bubble = wrapper.find('.message-bubble')
    expect(bubble.classes()).toContain('own-message')
  })

  it('應該顯示對方的訊息在左側', () => {
    const wrapper = mount(MessageBubble, {
      props: {
        message: mockMessage,
        isOwn: false
      }
    })

    const bubble = wrapper.find('.message-bubble')
    expect(bubble.classes()).toContain('other-message')
  })

  it('應該顯示已讀狀態', () => {
    const wrapper = mount(MessageBubble, {
      props: {
        message: { ...mockMessage, is_read: true },
        isOwn: true
      }
    })

    expect(wrapper.text()).toContain('✓✓')
  })

  it('應該只在自己的訊息上顯示刪除選項', async () => {
    const wrapper = mount(MessageBubble, {
      props: {
        message: mockMessage,
        isOwn: true
      },
      global: {
        components: { NDropdown }
      }
    })

    // 右鍵點擊
    await wrapper.find('.message-bubble').trigger('contextmenu')

    // 檢查是否有刪除選項
    expect(wrapper.html()).toContain('刪除訊息')
  })

  it('應該發射刪除事件', async () => {
    const wrapper = mount(MessageBubble, {
      props: {
        message: mockMessage,
        isOwn: true
      }
    })

    await wrapper.vm.$emit('delete', mockMessage.id)

    expect(wrapper.emitted('delete')).toBeTruthy()
    expect(wrapper.emitted('delete')[0]).toEqual([mockMessage.id])
  })
})
```

---

## 🚀 執行計劃

### Step 1: 環境設置（第1天，15-20分鐘）
1. 創建 `vitest.config.js`
2. 創建 `tests/setup.js`
3. 安裝依賴
4. 執行測試確保環境正常：`npm run test`

### Step 2: Store 測試（第1天，60-80分鐘）
1. 創建 `tests/stores/` 目錄
2. 依優先級實現測試：
   - User Store (P0)
   - Chat Store (P0)
   - Discovery Store (P0)
   - Profile Store (P1)
   - Safety Store (P1)

### Step 3: Composables 測試（第2天，30-40分鐘）
1. 創建 `tests/composables/` 目錄
2. 實現 useWebSocket 測試 (P0)

### Step 4: 組件測試（第2天，40-50分鐘）
1. 創建 `tests/components/` 目錄
2. 依優先級實現測試：
   - MessageBubble (P0)
   - InterestSelector (P1)
   - MatchModal (P1)
   - PhotoUploader (P2)

### Step 5: 驗證與優化（第2天，10-15分鐘）
1. 執行完整測試套件：`npm run test`
2. 檢查覆蓋率報告：`npm run test:coverage`
3. 修復失敗的測試
4. 優化慢速測試

---

## 📈 成功標準

### 測試通過率
- ✅ 所有測試通過（100%）
- ✅ 無 console.error 輸出

### 覆蓋率目標
- ✅ **Stores**: 80%+ 覆蓋率
- ✅ **Composables**: 75%+ 覆蓋率
- ✅ **Components**: 60%+ 覆蓋率
- ✅ **整體**: 70%+ 覆蓋率

### 測試品質
- ✅ 每個測試獨立運行（無順序依賴）
- ✅ 清晰的測試描述（it('應該...')）
- ✅ 適當的 setup 和 cleanup
- ✅ Mock 外部依賴（API, WebSocket）
- ✅ 測試關鍵邏輯和邊緣情況

---

## 🎯 預期收益

### 1. 代碼信心
- 重構時不怕破壞現有功能
- 新功能開發時確保不影響舊功能

### 2. Bug 預防
- 提早發現邏輯錯誤
- 避免上線後的緊急修復

### 3. 文檔作用
- 測試即文檔，展示如何使用各個模組
- 新成員快速理解代碼邏輯

### 4. 開發效率
- 減少手動測試時間
- CI/CD 自動化測試

---

## 📝 注意事項

### Mock 策略
1. **API 調用**: 使用 `vi.mock()` mock 整個 API 模組
2. **WebSocket**: 使用 Mock 物件替代真實 WebSocket
3. **LocalStorage**: 在 `tests/setup.js` 中 mock
4. **Router**: 使用 `createMemoryHistory()` 創建測試用 router

### 測試隔離
- 每個測試前重置 Pinia 狀態：`setActivePinia(createPinia())`
- 清除所有 mock：`vi.clearAllMocks()`
- 清除 localStorage：`localStorage.clear()`

### 常見陷阱
1. ❌ 測試實作細節（如內部變數名稱）
2. ❌ 測試依賴執行順序
3. ❌ 過度 mock 導致測試失去意義
4. ✅ 測試公開 API 和行為
5. ✅ 測試關鍵的業務邏輯
6. ✅ 適度 mock，保留核心邏輯

---

## 🔧 工具與資源

### 文檔
- [Vitest 官方文檔](https://vitest.dev/)
- [Vue Test Utils 文檔](https://test-utils.vuejs.org/)
- [Testing Pinia](https://pinia.vuejs.org/cookbook/testing.html)

### VSCode 擴展
- **Vitest**: 測試運行器整合
- **Coverage Gutters**: 顯示代碼覆蓋率

### 指令速查
```bash
npm run test              # 執行測試
npm run test:ui           # 開啟 UI 介面
npm run test:coverage     # 生成覆蓋率報告
npm run test -- --watch   # 監聽模式
npm run test -- MessageBubble  # 執行特定測試
```

---

**規劃人員**: Claude Code
**規劃日期**: 2025-11-15
**最後更新**: 2025-11-15
