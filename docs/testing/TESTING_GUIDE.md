# MergeMeet 測試指南

**測試範圍**: Week 1-6 功能
**最後更新**: 2025-12-26

---

## 目錄

1. [環境準備](#1-環境準備)
2. [測試帳號資訊](#2-測試帳號資訊)
3. [功能測試流程](#3-功能測試流程)
4. [測試檢查清單](#4-測試檢查清單)
5. [API 測試命令](#5-api-測試命令)
6. [常見問題排查](#6-常見問題排查)

---

## 1. 環境準備

### 1.1 啟動開發環境

```bash
# 1. 啟動資料庫和 Redis
docker compose up -d

# 2. 啟動後端（新終端）
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 3. 啟動前端（新終端）
cd frontend
npm run dev
```

### 1.2 驗證服務狀態

| 服務 | 網址 | 預期結果 |
|------|------|----------|
| 後端 API | http://localhost:8000/api/hello | JSON 回應 |
| API 文檔 | http://localhost:8000/docs | Swagger UI |
| 前端應用 | http://localhost:5173 | Vue 應用 |

### 1.3 瀏覽器要求

- Chrome 100+ / Edge 100+ / Firefox 100+ / Safari 15+
- 需啟用：JavaScript、Cookies、LocalStorage、WebSocket

### 1.4 測試前準備

開啟瀏覽器開發者工具（`F12`）：

- **Console**：查看錯誤訊息
- **Network**：監控 API 請求
- **Application**：查看 LocalStorage

---

## 2. 測試帳號資訊

### 預設測試帳號

| 帳號 | Email | 密碼 | 性別 |
|------|-------|------|------|
| Alice | alice@example.com | Password123 | 女性 |
| Bob | bob@example.com | Password123 | 男性 |
| Carol | carol@example.com | Password123 | 女性 |
| David | david@example.com | Password123 | 男性 |

> **注意**: 密碼必須包含至少一個大寫字母。如果帳號不存在，需要先自行註冊。

### 測試資料範例

**個人檔案：**

- 顯示名稱：Alice / Bob
- 性別：女性 / 男性
- 生日：1995-06-15 / 1990-03-20
- 位置：台北市信義區 (25.0330, 121.5654)

**興趣標籤：** 選擇 3-10 個（旅遊、美食、運動、音樂等）

---

## 3. 功能測試流程

### 3.1 用戶註冊與登入

#### 測試案例：新用戶註冊

1. 訪問 http://localhost:5173/register
2. 填寫表單：

   ```text
   Email: test_user@example.com
   密碼: TestPass123!
   姓名: 測試用戶
   性別: 男性
   生日: 1995-06-15
   ```

3. 點擊「註冊」

**預期結果：**

- 註冊成功，自動跳轉
- Network: `POST /api/auth/register` 返回 `201`

#### 測試案例：用戶登入

1. 訪問 http://localhost:5173/login
2. 填寫 Email 和密碼
3. 點擊「登入」

**預期結果：**

- 登入成功，跳轉到首頁
- LocalStorage 儲存 `access_token`
- Network: `POST /api/auth/login` 返回 `200`

---

### 3.2 個人檔案管理

#### 測試案例：建立/編輯個人檔案

1. 訪問 http://localhost:5173/profile
2. 填寫：顯示名稱、性別、個人簡介、地理位置
3. 點擊「儲存」

**預期結果：**

- Network: `POST /api/profile` 返回 `201` 或 `PATCH /api/profile` 返回 `200`

#### 測試案例：上傳照片

1. 在個人檔案頁面點擊「上傳照片」
2. 選擇 1-6 張照片（JPG/PNG，< 5MB）
3. 上傳

**預期結果：**

- 照片顯示在個人檔案中
- 第一張自動設為主頭像
- Network: `POST /api/profile/photos` 返回 `201`

#### 測試案例：設定興趣標籤

1. 點擊「編輯興趣」
2. 選擇 3-10 個標籤
3. 儲存

**預期結果：**

- Network: `PUT /api/profile/interests` 返回 `200`

---

### 3.3 探索與配對

#### 測試案例：瀏覽候選人

1. 訪問 http://localhost:5173/discovery
2. 觀察顯示的候選人卡片

**預期結果：**

- 顯示：照片、姓名、年齡、距離、共同興趣、配對分數
- 候選人符合偏好設定
- Network: `GET /api/discovery/browse` 返回 `200`

#### 測試案例：喜歡候選人

1. 點擊「❤️」按鈕或向右滑動

**預期結果：**

- 卡片滑出，顯示下一位
- Network: `POST /api/discovery/like/{user_id}` 返回 `200`
- 若雙方互相喜歡：顯示「配對成功」彈窗

#### 測試案例：跳過候選人

1. 點擊「✖️」按鈕或向左滑動

**預期結果：**

- 卡片滑出，該用戶 24 小時內不再出現
- Network: `POST /api/discovery/pass/{user_id}` 返回 `200`

---

### 3.4 即時聊天

#### 測試案例：進入聊天室

1. 從配對列表點擊一個配對

**預期結果：**

- 跳轉到 `/messages/{match_id}`
- WebSocket 連接成功（Console 顯示 "WebSocket connected"）
- Network: WebSocket 連接到 `ws://localhost:8000/ws`

#### 測試案例：即時訊息（需兩個瀏覽器）

1. **視窗 A**：Alice 登入，進入與 Bob 的聊天室
2. **視窗 B**：Bob 登入（無痕模式），進入與 Alice 的聊天室
3. Alice 發送訊息

**預期結果：**

- Alice 視窗：訊息立即顯示在右側
- Bob 視窗：**即時**收到訊息（不需刷新），顯示在左側

#### 測試案例：已讀狀態（即時更新）

1. **視窗 A**：Alice 發送訊息給 Bob
2. **視窗 B**：Bob 進入聊天室查看訊息

**預期結果：**

- Alice 視窗的訊息**即時**從「✓ 已送達」變成「✓✓ 已讀」（不需刷新）
- Network: `POST /api/messages/matches/{match_id}/read-all` 返回 `204`
- WebSocket: Alice 收到 `read_receipt` 事件，觸發 UI 即時更新

#### 測試案例：刪除訊息

1. 右鍵點擊自己的訊息
2. 選擇「刪除」

**預期結果：**

- 訊息消失
- Network: `DELETE /api/messages/messages/{message_id}` 返回 `204`

---

### 3.5 安全功能

#### 測試案例：封鎖用戶

1. 在聊天室點擊「⋮」按鈕
2. 選擇「封鎖」並確認

**預期結果：**

- 該用戶從探索列表消失
- 配對狀態變為 BLOCKED
- Network: `POST /api/safety/block/{user_id}` 返回 `201`

#### 測試案例：查看/解除封鎖

1. 訪問 http://localhost:5173/blocked
2. 點擊「解除封鎖」

**預期結果：**

- Network: `DELETE /api/safety/block/{user_id}` 返回 `200`

#### 測試案例：舉報用戶

1. 點擊「舉報」按鈕
2. 選擇類型（INAPPROPRIATE / HARASSMENT / FAKE_PROFILE / SCAM / OTHER）
3. 填寫原因並提交

**預期結果：**

- Network: `POST /api/safety/report` 返回 `201`

---

## 4. 測試檢查清單

### 用戶認證（Week 1）

- [ ] 新用戶註冊成功
- [ ] 用戶登入成功
- [ ] Token 正確儲存
- [ ] 登出功能正常

### 個人檔案（Week 2）

- [ ] 建立個人檔案
- [ ] 上傳 1-6 張照片
- [ ] 設定 3-10 個興趣標籤
- [ ] 編輯/刪除功能正常
- [ ] 檔案完整度檢查正確

### 探索與配對（Week 3）

- [ ] 瀏覽候選人（符合偏好）
- [ ] Like / Pass 功能正常
- [ ] 配對成功提示
- [ ] 配對列表正確顯示

### 即時聊天（Week 4）

- [ ] WebSocket 連接成功
- [ ] 發送/接收訊息即時
- [ ] 已讀狀態更新
- [ ] 刪除訊息功能
- [ ] 聊天記錄載入

### 安全功能（Week 5）

- [ ] 封鎖/解除封鎖用戶
- [ ] 舉報用戶（5 種類型）
- [ ] 封鎖列表查看

### 效能與穩定性

- [ ] 頁面載入 < 2 秒
- [ ] API 回應 < 500ms
- [ ] Console 無紅色錯誤
- [ ] WebSocket 穩定連接

---

## 5. API 測試命令

```bash
# 取得 Token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"Password123"}' | jq -r '.access_token')

# 瀏覽候選人
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/discovery/browse?limit=10"

# 喜歡用戶
curl -X POST -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/discovery/like/{USER_ID}"

# 查看配對
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/discovery/matches"

# 查看對話列表
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/messages/conversations"

# 查看聊天記錄
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/messages/matches/{MATCH_ID}/messages"
```

---

## 6. 常見問題排查

### 問題 1：配對列表一直轉圈圈

**排查：**

1. Console 查看錯誤訊息
2. Network 檢查 `/api/discovery/matches` 狀態碼：
   - `200` ✅ 正常
   - `401` ❌ Token 失效
   - `307` ❌ URL 格式錯誤（檢查尾隨斜線）

**解決：** 重新登入或 `localStorage.clear()`

---

### 問題 2：WebSocket 無法連接

**排查：**

1. Console 檢查 WebSocket 狀態
2. Network > WS 標籤，確認 `101 Switching Protocols`
3. 確認後端運行：`curl http://localhost:8000/health`

**解決：** 重新整理頁面或重啟後端

---

### 問題 3：訊息沒有即時更新

**排查：**

1. 確認 WebSocket 連接狀態
2. 確認在正確的聊天室（URL 包含正確的 match_id）

**解決：** 重新整理頁面

---

### 問題 4：307 重定向錯誤

**原因：** API URL 尾隨斜線格式錯誤

**確認：**

- ✅ 正確: `/api/profile`
- ❌ 錯誤: `/api/profile/`

**解決：** 清除瀏覽器快取

---

### 問題 5：圖片無法上傳

**可能原因：**

- 檔案過大（> 5MB）
- 格式不支援（只支援 JPG/PNG）
- 已達 6 張上限

**解決：** 壓縮圖片或刪除舊照片

---

## 自動化測試

```bash
# 運行 pytest 測試
cd backend
pytest tests/ -v

# 查看測試覆蓋率
pytest --cov=app --cov-report=html
```

---

## 進階測試場景

### 場景 1：多人配對

1. 創建 4 個用戶（Alice, Bob, Carol, Dave）
2. Alice 喜歡 Bob 和 Dave
3. 測試多個配對同時聊天

### 場景 2：配對後封鎖

1. Alice 和 Bob 配對成功並開始聊天
2. Alice 封鎖 Bob
3. 驗證配對解除、無法發送訊息

### 場景 3：壓力測試

1. 創建 10+ 個用戶
2. 同時在多個聊天室發送訊息
3. 測試 WebSocket 穩定性
