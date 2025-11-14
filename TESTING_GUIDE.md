# MergeMeet 探索配對與即時聊天測試指南

## 快速開始

### 方法 1: 使用自動化腳本 ⚡（推薦）

```bash
cd /home/twtrubiks/下載/merge_meet/mergemeet
./test_matching_chat.sh
```

這個腳本會自動：
- ✅ 創建 2 個測試用戶（Alice & Bob）
- ✅ 完成個人檔案設置
- ✅ 設定興趣標籤
- ✅ 完成互相喜歡（配對）
- ✅ 準備好聊天環境

**執行時間**: ~5 秒

---

### 方法 2: 手動測試流程 🖱️

## 步驟 1: 準備環境

### 1.1 啟動所有服務

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

### 1.2 確認服務運行

```bash
# 檢查後端
curl http://localhost:8000/api/hello

# 檢查前端
curl http://localhost:5173
```

---

## 步驟 2: 創建測試用戶

### 2.1 註冊用戶 Alice

1. 訪問: http://localhost:5173/register
2. 填寫資料：
   - **Email**: `alice.test@example.com`
   - **密碼**: `Alice1234`
   - **生日**: `1995-06-15`
3. 點擊「註冊」
4. 註冊成功後會自動登入

### 2.2 完成 Alice 的個人檔案

1. 自動導向個人檔案頁面
2. 填寫基本資訊：
   - **暱稱**: Alice
   - **性別**: 女性
   - **自我介紹**: "喜歡旅遊和美食，熱愛生活！"
3. 設定位置：
   - **位置名稱**: 台北市信義區
   - **緯度**: 25.0330
   - **經度**: 121.5654
4. 配對偏好：
   - **年齡範圍**: 25-35 歲
   - **最大距離**: 50 公里
   - **性別偏好**: 男性
5. 選擇興趣標籤（至少 3 個）：
   - 旅遊、美食、攝影等
6. 點擊「儲存」

### 2.3 註冊用戶 Bob

1. **登出 Alice 帳號**（右上角）
2. 訪問: http://localhost:5173/register
3. 填寫資料：
   - **Email**: `bob.test@example.com`
   - **密碼**: `Bob12345`
   - **生日**: `1990-03-20`
4. 點擊「註冊」

### 2.4 完成 Bob 的個人檔案

1. 填寫基本資訊：
   - **暱稱**: Bob
   - **性別**: 男性
   - **自我介紹**: "熱愛運動和旅遊，喜歡交朋友！"
2. 設定位置：
   - **位置名稱**: 台北市大安區
   - **緯度**: 25.0500
   - **經度**: 121.5500
3. 配對偏好：
   - **年齡範圍**: 22-32 歲
   - **最大距離**: 30 公里
   - **性別偏好**: 女性
4. 選擇興趣標籤（至少 3 個，與 Alice 有共同興趣）
5. 點擊「儲存」

---

## 步驟 3: 測試探索與配對功能

### 3.1 Alice 瀏覽候選人

1. 以 Alice 帳號登入
2. 點擊導航欄的「探索」
3. 應該會看到 Bob 的個人資料卡片：
   - 顯示 Bob 的照片、暱稱、年齡
   - 顯示距離（約 3 公里）
   - 顯示共同興趣
   - 顯示配對分數

### 3.2 Alice 喜歡 Bob

1. 在 Bob 的卡片上點擊「❤️ 喜歡」按鈕
2. 卡片會消失，顯示下一位候選人
3. 此時配對狀態：
   - ✅ Alice → Bob: 已喜歡
   - ❌ Bob → Alice: 未喜歡
   - ❌ 尚未配對

### 3.3 Bob 喜歡 Alice（觸發配對）

1. 登出 Alice，以 Bob 帳號登入
2. 點擊「探索」
3. 應該會看到 Alice 的個人資料卡片
4. 點擊「❤️ 喜歡」按鈕
5. **配對成功彈窗出現！** 🎉
   - 顯示「配對成功」訊息
   - 顯示 Alice 的資訊
   - 提供「開始聊天」按鈕

### 3.4 查看配對列表

1. 點擊導航欄的「配對」
2. 應該會看到：
   - Alice 和 Bob 的配對卡片
   - 配對時間
   - 最後訊息預覽（如果有）
   - 未讀訊息數量（如果有）

---

## 步驟 4: 測試即時聊天功能

### 4.1 開啟聊天室

**方法 1: 從配對列表**
1. 在「配對」頁面
2. 點擊對方的頭像或名稱
3. 自動導向聊天頁面

**方法 2: 從配對成功彈窗**
1. 配對成功後點擊「開始聊天」按鈕
2. 直接進入聊天頁面

### 4.2 測試即時訊息（WebSocket）

1. **Alice 發送訊息**：
   - 以 Alice 帳號開啟聊天室
   - 在輸入框輸入: "Hi Bob! 很高興認識你"
   - 點擊「發送」或按 Enter
   - 訊息立即顯示在聊天記錄

2. **Bob 接收訊息（即時）**：
   - 開啟另一個瀏覽器視窗（或無痕模式）
   - 以 Bob 帳號登入
   - 進入與 Alice 的聊天室
   - **無需刷新**，應該立即看到 Alice 的訊息

3. **Bob 回覆訊息**：
   - Bob 輸入: "Hi Alice! 我也很高興認識妳"
   - 點擊「發送」
   - Alice 的視窗應該**即時**收到訊息

4. **驗證 WebSocket 連接**：
   - 打開瀏覽器開發者工具（F12）
   - 切換到「Network」標籤
   - 篩選「WS」（WebSocket）
   - 應該看到 `ws://localhost:8000/ws` 連接
   - 狀態應該是「101 Switching Protocols」

### 4.3 測試訊息功能

#### 4.3.1 已讀狀態
- 當 Bob 查看訊息時
- Alice 的訊息應該顯示「已讀」標記
- 未讀訊息數量更新

#### 4.3.2 刪除訊息
1. 長按或右鍵點擊自己的訊息
2. 選擇「刪除」
3. 確認刪除
4. 訊息從聊天記錄中移除

#### 4.3.3 訊息通知
- 當收到新訊息時
- 配對列表的未讀數字應該增加
- 聊天列表顯示最新訊息預覽

---

## 步驟 5: 測試其他功能

### 5.1 跳過用戶

1. 在「探索」頁面
2. 對不感興趣的用戶點擊「❌ 跳過」
3. 該用戶不會再出現在候選列表

### 5.2 取消配對

1. 在「配對」頁面
2. 點擊配對卡片的「...」選單
3. 選擇「取消配對」
4. 確認後：
   - 配對關係解除
   - 聊天記錄保留（但無法繼續聊天）
   - 可以重新喜歡並配對

### 5.3 封鎖用戶

1. 在聊天頁面或個人資料頁面
2. 點擊「封鎖」按鈕
3. 確認封鎖後：
   - 配對關係解除
   - 不會再出現在探索列表
   - 無法發送訊息
   - 可在「設定」→「封鎖列表」查看

### 5.4 舉報用戶

1. 在個人資料頁面或聊天頁面
2. 點擊「舉報」按鈕
3. 選擇舉報原因：
   - 騷擾
   - 不當內容
   - 詐騙
   - 假帳號
   - 其他
4. 填寫詳細說明
5. 提交舉報
6. 管理員可在後台查看並處理

---

## 測試檢查清單

### 探索與配對 ✅
- [ ] 註冊並完成個人檔案
- [ ] 瀏覽候選人列表
- [ ] 配對分數正確顯示
- [ ] 距離計算正確
- [ ] 共同興趣顯示
- [ ] 喜歡用戶功能
- [ ] 跳過用戶功能
- [ ] 互相喜歡觸發配對
- [ ] 配對成功彈窗顯示
- [ ] 配對列表正確顯示

### 即時聊天 ✅
- [ ] WebSocket 連接成功
- [ ] 發送文字訊息
- [ ] 即時接收訊息（無需刷新）
- [ ] 訊息時間戳正確
- [ ] 已讀狀態更新
- [ ] 未讀訊息數量
- [ ] 訊息刪除功能
- [ ] 聊天記錄載入
- [ ] 多個聊天室切換

### 安全功能 ✅
- [ ] 取消配對
- [ ] 封鎖用戶
- [ ] 解除封鎖
- [ ] 舉報用戶
- [ ] 查看封鎖列表
- [ ] 查看舉報記錄

---

## 常見問題

### Q1: 找不到候選人？
**原因**:
- 偏好設定不符合（年齡、距離、性別）
- 沒有其他已完成檔案的用戶
- 已經喜歡或跳過所有用戶

**解決**:
- 調整偏好設定（增加年齡範圍、距離）
- 創建更多測試用戶
- 使用自動化腳本創建用戶

### Q2: WebSocket 連接失敗？
**原因**:
- 後端未啟動
- JWT Token 過期
- CORS 配置問題

**解決**:
```bash
# 檢查後端運行
curl http://localhost:8000/api/hello

# 查看後端日誌
# 應該看到 WebSocket 連接日誌

# 重新登入獲取新 Token
```

### Q3: 訊息沒有即時更新？
**原因**:
- WebSocket 連接中斷
- 瀏覽器標籤頁在背景

**解決**:
- F12 開發者工具 → Network → WS，檢查連接狀態
- 刷新頁面重新建立 WebSocket 連接
- 查看 Console 是否有錯誤訊息

### Q4: 配對後無法聊天？
**原因**:
- 配對狀態不正確
- WebSocket 權限問題

**解決**:
```bash
# 檢查配對狀態
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/discovery/matches/

# 檢查對話列表
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/messages/conversations/
```

---

## API 測試命令

### 瀏覽候選人
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/discovery/browse?limit=10"
```

### 喜歡用戶
```bash
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/discovery/like/USER_ID"
```

### 查看配對
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/discovery/matches"
```

### 查看對話列表
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/messages/conversations"
```

### 查看聊天記錄
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/messages/matches/MATCH_ID/messages"
```

---

## 進階測試場景

### 場景 1: 多人配對
1. 創建 4 個用戶（Alice, Bob, Carol, Dave）
2. Alice 喜歡 Bob 和 Dave
3. Bob 喜歡 Alice 和 Carol
4. 測試多個配對同時聊天

### 場景 2: 配對後封鎖
1. Alice 和 Bob 配對成功
2. 開始聊天
3. Alice 封鎖 Bob
4. 驗證配對解除、無法發送訊息

### 場景 3: 壓力測試
1. 創建 10+ 個用戶
2. 完成多個配對
3. 同時在多個聊天室發送訊息
4. 測試 WebSocket 穩定性

---

## 自動化測試

```bash
# 運行 pytest 測試
cd backend
pytest tests/test_discovery.py -v
pytest tests/test_safety.py -v

# 查看測試覆蓋率
pytest --cov=app --cov-report=html
```

---

**祝測試順利！** 🚀

如有問題請參考 `README.md` 或 `QUICKSTART.md`
