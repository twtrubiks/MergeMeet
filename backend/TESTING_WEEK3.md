# Week 3 探索與配對功能測試指南

## 前置準備

### 1. 確保 Docker 服務運行
```bash
cd mergemeet
docker-compose up -d
```

檢查服務狀態：
```bash
docker ps
# 應該看到 mergemeet_postgres 和 mergemeet_redis 運行中
```

### 2. 啟動 Python 虛擬環境
```bash
cd backend
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate  # Windows
```

### 3. 執行資料庫遷移
```bash
# 查看當前遷移狀態
alembic current

# 執行遷移（創建 Match 相關表格）
alembic upgrade head

# 確認遷移成功
alembic current
# 應該顯示: 002 (head)
```

### 4. 啟動後端 API
```bash
# 方法 1：使用 uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 方法 2：直接執行
python -m app.main
```

API 文檔：http://localhost:8000/docs

---

## 測試場景

### 場景 1：註冊測試用戶（建立測試資料）

我們需要至少 2 個用戶來測試配對功能。

#### 1.1 註冊用戶 A
```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@example.com",
    "password": "Alice1234",
    "date_of_birth": "1995-06-15"
  }'
```

保存回應中的 `access_token`（記為 `TOKEN_A`）

#### 1.2 建立用戶 A 的個人檔案
```bash
curl -X POST "http://localhost:8000/api/profile" \
  -H "Authorization: Bearer TOKEN_A" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "Alice",
    "gender": "female",
    "bio": "喜歡旅遊和美食",
    "location": {
      "lat": 25.0330,
      "lng": 121.5654
    },
    "location_name": "台北市信義區",
    "min_age_preference": 25,
    "max_age_preference": 35,
    "max_distance_km": 50,
    "gender_preference": "male"
  }'
```

#### 1.3 新增用戶 A 的興趣標籤
```bash
# 先取得所有興趣標籤
curl -X GET "http://localhost:8000/api/profile/interests/all"

# 選擇 3-10 個興趣的 ID，然後更新
curl -X PUT "http://localhost:8000/api/profile/interests" \
  -H "Authorization: Bearer TOKEN_A" \
  -H "Content-Type: application/json" \
  -d '{
    "interest_ids": ["興趣ID1", "興趣ID2", "興趣ID3"]
  }'
```

#### 1.4 重複步驟註冊用戶 B、C、D...
```bash
# 用戶 B (Bob)
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "bob@example.com",
    "password": "Bob12345",
    "date_of_birth": "1990-03-20"
  }'
# 保存 TOKEN_B

# 建立 Bob 的檔案（位置稍微不同，有共同興趣）
curl -X POST "http://localhost:8000/api/profile" \
  -H "Authorization: Bearer TOKEN_B" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "Bob",
    "gender": "male",
    "bio": "熱愛運動和旅遊",
    "location": {
      "lat": 25.0500,
      "lng": 121.5500
    },
    "location_name": "台北市大安區",
    "min_age_preference": 22,
    "max_age_preference": 32,
    "max_distance_km": 30,
    "gender_preference": "female"
  }'
```

---

### 場景 2：瀏覽可配對用戶

#### 2.1 用戶 A 瀏覽候選人
```bash
curl -X GET "http://localhost:8000/api/discovery/browse?limit=10" \
  -H "Authorization: Bearer TOKEN_A"
```

**預期結果：**
- 返回符合 Alice 偏好的用戶列表
- 每個用戶包含：基本資訊、距離、興趣、配對分數
- 按配對分數排序
- 排除 Alice 自己

#### 2.2 檢查配對分數計算
返回的每個用戶應該有 `match_score` 欄位：
- 共同興趣越多，分數越高（最多 50 分）
- 距離越近，分數越高（最多 20 分）
- 最近活躍，分數越高（最多 20 分）
- 照片和自我介紹完整，分數越高（最多 10 分）

---

### 場景 3：喜歡用戶（Like）

#### 3.1 Alice 喜歡 Bob
```bash
curl -X POST "http://localhost:8000/api/discovery/like/BOB_USER_ID" \
  -H "Authorization: Bearer TOKEN_A"
```

**預期結果：**
```json
{
  "liked": true,
  "is_match": false,
  "match_id": null
}
```
- `is_match` 為 `false`（Bob 還沒喜歡 Alice）

#### 3.2 Bob 喜歡 Alice（互相喜歡，觸發配對！）
```bash
curl -X POST "http://localhost:8000/api/discovery/like/ALICE_USER_ID" \
  -H "Authorization: Bearer TOKEN_B"
```

**預期結果：**
```json
{
  "liked": true,
  "is_match": true,
  "match_id": "配對ID"
}
```
- `is_match` 為 `true`（配對成功！）
- 返回 `match_id`

#### 3.3 測試重複喜歡（應該失敗）
```bash
curl -X POST "http://localhost:8000/api/discovery/like/BOB_USER_ID" \
  -H "Authorization: Bearer TOKEN_A"
```

**預期結果：**
- HTTP 400 錯誤
- 錯誤訊息："已經喜歡過此用戶"

---

### 場景 4：跳過用戶（Pass）

#### 4.1 Alice 跳過某個用戶
```bash
curl -X POST "http://localhost:8000/api/discovery/pass/USER_ID" \
  -H "Authorization: Bearer TOKEN_A"
```

**預期結果：**
```json
{
  "passed": true,
  "message": "已跳過此用戶"
}
```

---

### 場景 5：查看配對列表

#### 5.1 Alice 查看所有配對
```bash
curl -X GET "http://localhost:8000/api/discovery/matches" \
  -H "Authorization: Bearer TOKEN_A"
```

**預期結果：**
- 返回所有配對列表
- 包含配對對象的基本資訊
- 按配對時間排序（最新在前）

---

### 場景 6：取消配對（Unmatch）

#### 6.1 Alice 取消與 Bob 的配對
```bash
curl -X DELETE "http://localhost:8000/api/discovery/unmatch/MATCH_ID" \
  -H "Authorization: Bearer TOKEN_A"
```

**預期結果：**
```json
{
  "message": "已取消配對"
}
```

#### 6.2 再次查看配對列表（應該不包含 Bob）
```bash
curl -X GET "http://localhost:8000/api/discovery/matches" \
  -H "Authorization: Bearer TOKEN_A"
```

---

## 測試檢查表

### 功能測試
- [ ] 可以瀏覽候選人
- [ ] 配對分數計算正確
- [ ] 喜歡用戶功能正常
- [ ] 互相喜歡自動配對
- [ ] 跳過用戶功能正常
- [ ] 查看配對列表
- [ ] 取消配對功能正常

### 篩選測試
- [ ] 性別篩選生效
- [ ] 年齡篩選生效
- [ ] 距離篩選生效
- [ ] 排除已喜歡的用戶
- [ ] 排除已配對的用戶
- [ ] 排除已封鎖的用戶

### 錯誤處理
- [ ] 重複喜歡返回錯誤
- [ ] 不能喜歡自己
- [ ] 不能跳過自己
- [ ] 無效的 user_id 返回錯誤
- [ ] 無效的 match_id 返回錯誤

### 邊界測試
- [ ] 檔案未完成無法瀏覽
- [ ] 未設定位置無法瀏覽
- [ ] 沒有候選人時返回空陣列
- [ ] limit 參數正確限制返回數量

---

## 使用 Swagger UI 測試（推薦）

訪問 http://localhost:8000/docs

### 優點：
- 視覺化介面
- 自動處理 Authorization
- 可以直接看到 Schema
- 方便測試各種參數

### 步驟：
1. 先執行 `/api/auth/register` 和 `/api/auth/login` 取得 token
2. 點擊右上角 "Authorize" 按鈕
3. 輸入 token: `Bearer YOUR_TOKEN`
4. 現在可以測試所有需要認證的 API

---

## 常見問題

### Q1: 遷移失敗 "relation already exists"
```bash
# 重置資料庫（會刪除所有資料！）
alembic downgrade base
alembic upgrade head
```

### Q2: 找不到候選人
- 確認至少有 2 個用戶完成檔案
- 確認兩個用戶的位置、年齡、性別符合彼此的偏好
- 確認距離在偏好範圍內

### Q3: 配對分數都是 0
- 確認用戶有設定興趣標籤
- 確認用戶有設定位置
- 確認用戶有上傳照片和自我介紹

### Q4: PostGIS 錯誤
```bash
# 進入 PostgreSQL 容器
docker exec -it mergemeet_postgres bash

# 連接資料庫
psql -U mergemeet -d mergemeet

# 確認 PostGIS 擴展已安裝
\dx

# 如果沒有，安裝它
CREATE EXTENSION IF NOT EXISTS postgis;
```

---

## 下一步

測試通過後：
1. 開發前端探索頁面 (Discovery.vue)
2. 開發配對成功彈窗 (MatchModal.vue)
3. 開發配對列表頁面 (Matches.vue)
4. 整合前後端
5. 端到端測試
