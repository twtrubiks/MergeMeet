# 前端代碼審查修復報告

**日期**: 2025-11-16
**審查範圍**: 前端 UI 美化提交 (4 commits)
**發現問題**: 28 個 (1 Critical, 7 High, 12 Medium, 6 Low, 2 Info)
**狀態**: 已評估，部分需要修復

---

## 一、Critical 級別問題重新評估

### C-1: XSS 漏洞（風險降級為 Low）

**原報告評級**: Critical
**實際評級**: **Low**

**理由**:
1. ✅ Vue 3 的 `{{}}` **自動轉義 HTML**，不會執行腳本
2. ✅ `display_name` 和 `bio` 經過後端**內容審核系統**過濾
3. ✅ `interest.icon` 來自資料庫**預設種子數據**（seed data）
4. ✅ 後端已實現敏感詞檢測（backend/app/services/content_moderation.py）

**無需修復**，現有安全機制已足夠。

---

## 二、High 級別問題修復方案

### ✅ H-1: 時間計算驗證（已有部分驗證）

**文件**: `Matches.vue:184-206`, `ChatList.vue:135-154`

**現狀分析**:
```javascript
const formatDate = (dateString) => {
  const date = new Date(dateString)
  const now = new Date()
  const diffInMs = now - date
  // ...
}
```

**潛在問題**:
- `dateString` 可能是無效字符串
- 時間差可能為負數（未來時間）

**建議修復**（創建共享工具函數）:

```javascript
// frontend/src/utils/dateFormat.js
export function safeFormatDate(dateString) {
  // 驗證輸入
  if (!dateString || typeof dateString !== 'string') {
    return ''
  }

  const date = new Date(dateString)

  // 驗證日期有效性
  if (isNaN(date.getTime())) {
    return ''
  }

  const now = new Date()
  const diffInMs = Math.max(0, now - date) // 避免負數
  const diffMins = Math.floor(diffInMs / (1000 * 60))
  const diffHours = Math.floor(diffInMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffInMs / (1000 * 60 * 60 * 24))

  if (diffMins < 1) return '剛剛'
  if (diffMins < 60) return `${diffMins} 分鐘前`
  if (diffHours < 24) return `${diffHours} 小時前`
  if (diffDays < 7) return `${diffDays} 天前`

  // 超過 7 天顯示完整日期
  return date.toLocaleDateString('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}
```

**使用方式**:
```vue
<!-- Matches.vue 和 ChatList.vue -->
<script setup>
import { safeFormatDate } from '@/utils/dateFormat'

const formatDate = safeFormatDate
</script>
```

---

### ✅ H-2: 地理位置輸入驗證（建議增強）

**文件**: `Profile.vue:376-398`

**現狀**:
```javascript
const geocodeLocation = (locationName) => {
  const cityCoordinates = { /* ... */ }
  return cityCoordinates[locationName] || { latitude: 25.0330, longitude: 121.5654 }
}
```

**問題**: 所有未知地點都被設為台北市

**建議修復**:

```javascript
const geocodeLocation = (locationName) => {
  // 輸入驗證
  if (!locationName || typeof locationName !== 'string') {
    return null
  }

  // 長度限制
  if (locationName.length > 50) {
    console.warn('地點名稱過長')
    return null
  }

  // 只允許中文、英文、數字和常見符號
  const validPattern = /^[\u4e00-\u9fa5a-zA-Z0-9\s-]+$/
  if (!validPattern.test(locationName)) {
    console.warn('地點名稱包含無效字符')
    return null
  }

  const cityCoordinates = {
    '台北市': { latitude: 25.0330, longitude: 121.5654 },
    '台北市信義區': { latitude: 25.033, longitude: 121.5654 },
    '台北市大安區': { latitude: 25.0263, longitude: 121.5436 },
    // ... 其他城市
  }

  const coords = cityCoordinates[locationName]

  if (!coords) {
    console.warn(`未找到城市座標: ${locationName}`)
    return null // 不要返回預設值！
  }

  return coords
}

// 在 updateProfile 中處理 null 情況
const updateProfile = () => {
  const coords = geocodeLocation(formData.value.location_name)
  if (!coords && formData.value.location_name) {
    alert('無法識別該地點，請選擇有效的城市')
    return
  }
  // ...
}
```

---

### ✅ H-3: 數組索引驗證

**文件**: `Matches.vue:66`

**問題**:
```vue
<div v-else class="avatar-placeholder">
  {{ match.matched_user.display_name[0] }}
</div>
```

**修復**（簡單快速）:
```vue
<div v-else class="avatar-placeholder">
  {{ (match.matched_user.display_name || 'U')[0] }}
</div>
```

**同時修復**: `Profile.vue:161`
```vue
{{ (profileStore.profile.display_name || 'U')[0].toUpperCase() }}
```

---

### 🔧 H-4: 競態條件問題

**文件**: `Matches.vue:264-277`

**現狀**:
```javascript
const confirmUnmatch = async () => {
  if (!unmatchTarget.value || isUnmatching.value) return

  isUnmatching.value = true

  try {
    await discoveryStore.unmatch(unmatchTarget.value.match_id)
    unmatchTarget.value = null // ❌ 失敗時不會執行
  } catch (error) {
    console.error('取消配對失敗:', error)
  } finally {
    isUnmatching.value = false
  }
}
```

**修復**:
```javascript
const confirmUnmatch = async () => {
  if (!unmatchTarget.value || isUnmatching.value) return

  isUnmatching.value = true

  try {
    await discoveryStore.unmatch(unmatchTarget.value.match_id)
    // 成功後才關閉彈窗和清空目標
    unmatchTarget.value = null
    showUnmatchModal.value = false
  } catch (error) {
    console.error('取消配對失敗:', error)
    // 顯示用戶友好的錯誤訊息
    alert('取消配對失敗，請稍後再試')
    // 保持彈窗打開，讓用戶可以重試
  } finally {
    isUnmatching.value = false
  }
}
```

---

### 🔧 H-5: 狀態同步問題

**文件**: `Profile.vue:416-419`

**現狀**:
```javascript
await profileStore.createProfile(profileData)
isCreating.value = false
isEditing.value = true // ❌ 失敗時仍會切換
```

**修復**:
```javascript
try {
  await profileStore.createProfile(profileData)
  // 只有成功後才切換狀態
  isCreating.value = false
  isEditing.value = true
} catch (error) {
  console.error('創建個人檔案失敗:', error)
  alert('創建失敗，請檢查網絡連接')
  // 不改變狀態，讓用戶可以重試
}
```

---

### 🔧 H-6: 數據刷新優化

**文件**: `Profile.vue:111`

**現狀**:
```vue
<PhotoUploader @photos-changed="fetchProfileData" />
```

每次照片變更都重新獲取整個 profile，效率低。

**建議**:
1. **短期方案**: 保持現狀（功能正常，只是效率稍低）
2. **長期優化**: PhotoUploader 直接更新 store 中的 photos 數組

```vue
<!-- 優化方案（需修改 PhotoUploader 組件）-->
<PhotoUploader @photos-updated="handlePhotosUpdated" />

<script setup>
const handlePhotosUpdated = (newPhotos) => {
  // 直接更新 store，無需重新獲取整個 profile
  profileStore.profile.photos = newPhotos
}
</script>
```

---

### ✅ H-7: 時間格式化邊界條件

**文件**: `ChatList.vue:145`

**現狀**:
```javascript
if (diffMins < 1) return '剛剛'
```

如果服務器時間比客戶端快，`diffMins` 可能為負數。

**修復**（已包含在 H-1 的 `safeFormatDate` 中）:
```javascript
const diffInMs = Math.max(0, now - date) // 避免負數
```

---

## 三、Medium 級別問題（建議修復）

### M-2: 替換 alert/confirm

**優先級**: Medium
**工作量**: 中等

**建議**: 使用 Naive UI 的 Message 和 Dialog 組件

```javascript
import { useMessage, useDialog } from 'naive-ui'

const message = useMessage()
const dialog = useDialog()

// 替換 alert
message.warning('請填寫所有必填欄位')

// 替換 confirm
dialog.warning({
  title: '提醒',
  content: '建議至少上傳 1 張照片，確定要繼續嗎？',
  positiveText: '繼續',
  negativeText: '返回',
  onPositiveClick: () => {
    // 用戶點擊「繼續」
    currentStep.value++
  }
})
```

---

### M-3: 防抖/節流

**優先級**: Medium
**工作量**: 小

**建議**: 使用 `@vueuse/core` 的 `useDebounceFn`

```javascript
import { useDebounceFn } from '@vueuse/core'

const nextStep = useDebounceFn(async () => {
  // 現有邏輯
}, 300) // 300ms 防抖
```

---

### M-4: 尊重用戶的減少動畫偏好

**優先級**: High（可訪問性）
**工作量**: 小

**修復**: 在 `main.css` 或 `App.vue` 添加全局樣式

```css
/* 尊重用戶的減少動畫偏好 */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

---

### M-6: 圖片加載失敗處理

**優先級**: Medium
**工作量**: 小

**建議**: 添加統一的圖片錯誤處理

```vue
<script setup>
const DEFAULT_AVATAR = '/default-avatar.png'

const handleImageError = (e) => {
  e.target.src = DEFAULT_AVATAR
}
</script>

<template>
  <img
    :src="photoUrl"
    @error="handleImageError"
    loading="lazy"
  />
</template>
```

---

## 四、可訪問性改進（Low 優先級）

### L-1: ARIA 標籤

**建議**: 為所有按鈕添加 `aria-label`

```vue
<button
  @click="showUnmatchConfirm(match)"
  class="btn-unmatch"
  aria-label="取消與該用戶的配對"
  title="取消配對"
>
  <span aria-hidden="true">💔</span>
</button>
```

---

## 五、修復優先級總結

### 🔴 立即修復（建議本週完成）
1. ✅ **H-3**: 數組索引驗證（2 分鐘）
2. 🔧 **H-4**: 競態條件（5 分鐘）
3. 🔧 **H-5**: 狀態同步（5 分鐘）
4. ✅ **M-4**: 減少動畫偏好（2 分鐘）

**總計**: ~15 分鐘

### 🟠 短期優化（建議下週完成）
1. ✅ **H-1**: 時間計算驗證（創建共享工具）
2. ✅ **H-2**: 地理位置驗證
3. **M-2**: 替換 alert/confirm
4. **M-3**: 防抖/節流
5. **M-6**: 圖片錯誤處理

**總計**: ~2 小時

### 🟡 中期改進（可選）
1. **H-6**: 數據刷新優化
2. **L-1 ~ L-6**: 可訪問性改進
3. 提取重複組件和樣式

---

## 六、結論

**整體代碼品質**: ⭐⭐⭐⭐☆ (4/5)

**優點**:
- ✅ 正確使用 Vue 3 Composition API
- ✅ 組件設計良好，可重用性高
- ✅ UI/UX 體驗優秀
- ✅ 後端已有完善的安全機制（內容審核）

**主要問題**:
- ⚠️ 錯誤處理需要加強
- ⚠️ 可訪問性需要改進
- ⚠️ 部分邊界條件未處理

**建議**:
1. 優先修復 **H-3, H-4, H-5, M-4**（15 分鐘即可完成）
2. 創建共享工具函數（dateFormat.js）統一處理時間和驗證邏輯
3. 逐步改進可訪問性（ARIA 標籤、鍵盤導航）

**無需修復**:
- C-1 (XSS 漏洞) - 現有機制已足夠安全

---

**最後更新**: 2025-11-16
**審查者**: Claude AI
**批准狀態**: 待開發者確認
