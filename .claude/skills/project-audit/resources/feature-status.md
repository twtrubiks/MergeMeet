# 交友軟體核心功能狀態

> 最後更新: 2025-12-16

## 功能狀態總覽

| 類別 | 功能 | 後端 | 前端 | 狀態 |
|-----|------|:----:|:----:|:----:|
| **認證** | 用戶註冊 | O | O | COMPLETE |
| | 用戶登入 | O | O | COMPLETE |
| | Email 驗證 | O | O | COMPLETE |
| | 忘記密碼 | O | O | COMPLETE |
| | 密碼修改 | O | O | COMPLETE |
| | Token 安全存儲 | O | O | COMPLETE |
| **個人檔案** | 建立/編輯檔案 | O | O | COMPLETE |
| | 照片上傳 | O | O | COMPLETE |
| | 照片審核狀態 | O | O | COMPLETE |
| | 興趣標籤 | O | O | COMPLETE |
| | 地理位置 | O | O | COMPLETE |
| **探索配對** | 瀏覽候選人 | O | O | COMPLETE |
| | 配對分數計算 | O | O | COMPLETE |
| | 喜歡/跳過 | O | O | COMPLETE |
| | 滑動卡片 UI | - | O | COMPLETE |
| | 配對成功通知 | O | O | COMPLETE |
| **聊天** | 配對列表 | O | O | COMPLETE |
| | 即時訊息 (WS) | O | O | COMPLETE |
| | 訊息已讀狀態 | O | O | COMPLETE |
| | 內容審核 | O | - | PARTIAL |
| **安全** | 封鎖用戶 | O | O | COMPLETE |
| | 解除封鎖 | O | O | COMPLETE |
| | 舉報用戶 | O | O | COMPLETE |
| | 信任分數 | O | - | BACKEND ONLY |
| **通知** | 即時通知 (WS) | O | O | COMPLETE |
| | 持久化通知 | O | O | PARTIAL |
| | 通知中心頁面 | O | X | MISSING |
| **管理後台** | 儀表板統計 | O | O | COMPLETE |
| | 舉報處理 | O | O | COMPLETE |
| | 內容審核 | O | O | COMPLETE |
| | 照片審核 | O | O | COMPLETE |
| | 用戶管理 | O | X | MISSING |

## 圖例

- O = 已實現
- X = 未實現
- \- = 不適用
- COMPLETE = 功能完整
- PARTIAL = 部分實現
- MISSING = 缺失
- BACKEND ONLY = 僅後端實現

---

## 詳細說明

### COMPLETE 功能

#### 認證系統
- **用戶註冊**: Email + 密碼註冊，含年齡驗證 (18+)
- **用戶登入**: JWT Token 認證，HttpOnly Cookie 存儲
- **Email 驗證**: 發送驗證連結，驗證後啟用帳號
- **忘記密碼**: 發送重設連結，設定新密碼
- **密碼修改**: 驗證舊密碼後更新
- **Token 安全**: HttpOnly Cookie + CSRF 防護

#### 個人檔案
- **建立/編輯**: 顯示名稱、性別、自我介紹
- **照片上傳**: 最多 6 張，支援 JPG/PNG/GIF/WEBP
- **照片審核**: PENDING/APPROVED/REJECTED 狀態顯示
- **興趣標籤**: 3-10 個標籤選擇
- **地理位置**: PostGIS 支援距離計算

#### 探索配對
- **瀏覽候選人**: 根據偏好篩選，計算配對分數
- **喜歡/跳過**: 操作記錄，避免重複顯示
- **配對成功**: 互相喜歡時觸發配對

#### 聊天
- **配對列表**: 顯示所有配對，最後訊息預覽
- **即時訊息**: WebSocket 即時傳送接收
- **已讀狀態**: 標記訊息已讀時間

#### 安全
- **封鎖用戶**: 封鎖後不再顯示該用戶
- **解除封鎖**: 可解除封鎖恢復
- **舉報用戶**: 多種舉報類型（騷擾、詐騙等）

#### 管理後台
- **儀表板**: 用戶、配對、訊息、舉報統計
- **舉報處理**: 批准/拒絕，警告/封禁用戶
- **內容審核**: 敏感詞管理，申訴處理
- **照片審核**: 審核待審照片，拒絕理由

---

### PARTIAL 功能

#### 訊息內容審核
- 後端: 有敏感詞過濾服務
- 前端: 未顯示訊息被過濾的提示

#### 持久化通知
- 後端: 有完整 CRUD API
- 前端: 有 store 但無專門頁面查看歷史

---

### MISSING 功能

#### 通知中心頁面
- 後端 API: `GET /api/notifications` 已實現
- 前端: 缺少 `/notifications` 頁面
- 用戶無法查看和管理歷史通知

#### 管理員用戶管理
- 後端 API: `GET /admin/users`, `POST /admin/users/ban`, `POST /admin/users/unban` 已實現
- 前端: AdminDashboard 缺少用戶管理 Tab
- 管理員無法直接搜尋和管理用戶

---

## 待評估功能

這些功能是交友軟體常見但本專案尚未實現的：

| 功能 | 優先級 | 說明 |
|-----|:------:|------|
| 用戶詳情頁面 | HIGH | 點擊查看完整個人檔案 |
| 配對偏好設定 UI | HIGH | 調整年齡、距離、性別偏好 |
| 用戶申訴介面 | MEDIUM | 一般用戶提交內容審核申訴 |
| 我的舉報記錄 | MEDIUM | 查看自己提交的舉報狀態 |
| 超級喜歡 | LOW | 特殊互動功能 |
| 回顧功能 | LOW | 重新查看跳過的用戶 |
| 每日推薦 | LOW | 精選推薦用戶 |

---

## 下次審查重點

1. 檢查 PARTIAL 功能是否已補全
2. 確認 MISSING 功能的開發計劃
3. 評估新功能需求的優先級
