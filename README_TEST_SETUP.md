# 測試帳號快速設置工具

## 📝 說明

此工具可快速創建 Alice 和 Bob 測試帳號並自動配對，方便測試聊天功能。

## 🚀 使用方法

### 方式一：Python 腳本（推薦）

```bash
python3 setup_test_users_simple.py
```

**優點**：
- ✅ 簡單易用
- ✅ 無需額外依賴（僅需 requests 標準庫）
- ✅ 清晰的輸出格式
- ✅ 完整的錯誤處理

### 方式二：Shell 腳本

```bash
./setup_test_users.sh
```

**優點**：
- ✅ 純 Shell 腳本
- ✅ 不需要 Python

## 📋 前置要求

1. **後端 API 運行中**
   ```bash
   cd backend
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **資料庫容器運行中**
   ```bash
   docker compose up -d
   ```

## 🔐 創建的測試帳號

| 帳號 | Email | 密碼 | 性別 |
|------|-------|------|------|
| Alice | alice@example.com | Password123 | 女性 |
| Bob | bob@example.com | Password123 | 男性 |

## ✨ 腳本功能

腳本會自動完成以下步驟：

1. **清理現有資料** - 刪除舊的 Alice 和 Bob 帳號（如果存在）
2. **創建用戶帳號** - 註冊 Alice 和 Bob
3. **創建個人檔案** - 設置完整的個人資訊
4. **設置配對偏好** - 配置年齡、距離、性別偏好
5. **創建配對** - 自動讓 Alice 和 Bob 互相喜歡並配對
6. **驗證設置** - 檢查所有資料是否正確創建

## 🧪 測試聊天功能

執行腳本後，按照以下步驟測試：

### 1. 登入 Alice（瀏覽器 A）

```
URL: http://localhost:5173/login
Email: alice@example.com
密碼: Password123
```

### 2. 登入 Bob（瀏覽器 B 或無痕模式）

```
URL: http://localhost:5173/login
Email: bob@example.com
密碼: Password123
```

### 3. 進入訊息頁面

兩個瀏覽器都前往：`http://localhost:5173/messages`

### 4. 開始聊天測試

- ✅ 即時訊息收發
- ✅ 已讀狀態顯示（✓✓）
- ✅ 刪除訊息（右鍵選單）
- ✅ 聊天記錄分頁載入（向上滾動）
- ✅ 封鎖/舉報用戶（點擊 ⋮ 按鈕）
- ⚠️ 打字指示器（發送正常，接收有問題）

## 🔍 驗證腳本執行結果

腳本執行完成後會顯示：

1. **用戶和檔案表**
   ```
          email       | display_name | gender | is_complete
   -------------------+--------------+--------+-------------
    alice@example.com | Alice        | female | f
    bob@example.com   | Bob          | male   | f
   ```

2. **配對記錄**
   ```
                  match_id               |   user1_email   |    user2_email    | status
   --------------------------------------+-----------------+-------------------+--------
    xxxxx-xxxx-xxxx-xxxx-xxxxxxxxxx     | bob@example.com | alice@example.com | ACTIVE
   ```

## ⚠️ 注意事項

- **密碼格式**：必須包含至少一個大寫字母（Password123 而非 password123）
- **自動清理**：腳本會自動刪除現有的 Alice 和 Bob 帳號
- **配對狀態**：執行後兩個帳號立即處於配對狀態

## 🛠️ 故障排除

### 問題：後端 API 未運行

**解決方法**：
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 問題：資料庫容器未運行

**解決方法**：
```bash
docker compose up -d
```

### 問題：腳本執行失敗

**檢查事項**：
1. 確認後端 API 在 http://localhost:8000 運行
2. 確認資料庫容器名稱為 `mergemeet_postgres`
3. 查看腳本輸出的錯誤訊息

## 📚 相關文檔

- `MANUAL_TESTING_GUIDE.md` - 完整手動測試指南
- `BUG_FIXES_SUMMARY.md` - Bug 修復總結
- `WEEK4_CHAT_TEST_REPORT.md` - Week 4 聊天功能測試報告
- `WEEK5_SAFETY_TEST_REPORT.md` - Week 5 安全功能測試報告

## 🎯 下次測試時

只需要一行命令即可重新設置測試環境：

```bash
python3 setup_test_users_simple.py
```

腳本會自動清理舊資料並創建新的測試帳號！
