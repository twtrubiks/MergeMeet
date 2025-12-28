# MergeMeet 配對演算法文檔

**實現位置**: `backend/app/services/matching_service.py`

---

## 📊 演算法概述

MergeMeet 使用**多因素評分系統**計算配對分數（0-100 分），綜合考慮興趣匹配、地理距離、用戶活躍度、檔案完整度和信任分數，為用戶推薦最合適且安全的配對對象。

**設計理念**: 簡單但有效，採用業界常見的多因素評分模式，同時整合信任分數保障平台安全。

---

## 🎯 評分系統（總分 100 分）

### 評分因素權重（v2.0）

| 因素 | 權重 | 最高分 | 說明 |
|------|------|--------|------|
| **興趣匹配** | 50% | 50 分 | 共同興趣數量 |
| **地理距離** | 20% | 20 分 | 物理距離遠近 |
| **活躍度** | 20% | 20 分 | 最後上線時間 |
| **檔案完整度** | 5% | 5 分 | 照片數量和 Bio（v1.0 為 10 分） |
| **信任分數** | 5% | 5 分 | 用戶信譽評分（v2.0 新增） |

---

## 📐 詳細評分規則

### 1. 興趣匹配（50 分）

**計算方式**: 每個共同興趣 10 分，最多 5 個共同興趣

```python
user_interests = {"旅遊", "攝影", "美食"}
candidate_interests = {"旅遊", "攝影", "健身"}
common_interests = {"旅遊", "攝影"}  # 2 個

score = min(2 * 10, 50) = 20 分
```

**評分表**:
```
0 個共同興趣 → 0 分（不太適合）
1 個共同興趣 → 10 分
2 個共同興趣 → 20 分
3 個共同興趣 → 30 分（良好）
4 個共同興趣 → 40 分（很好）
5+ 個共同興趣 → 50 分（完美）
```

**實現代碼**:
```python
# backend/app/services/matching_service.py:130-133
user_interests = set(user_profile.get("interests", []))
candidate_interests = set(candidate.get("interests", []))
common_interests = user_interests & candidate_interests
score += min(len(common_interests) * 10, 50)
```

---

### 2. 地理距離（20 分）

**計算方式**: 使用 PostGIS 計算球面距離（公里）

```python
distance_km = 3.5  # PostGIS 自動計算

if distance_km < 5:     score = 20 分  # 非常近
elif distance_km < 10:  score = 15 分  # 近
elif distance_km < 25:  score = 10 分  # 中等
elif distance_km < 50:  score = 5 分   # 遠
else:                   score = 0 分   # 太遠（不會出現）
```

**評分表**:
```
0-5 km    → 20 分（同區域，約會方便）
5-10 km   → 15 分（鄰近區域）
10-25 km  → 10 分（同城市）
25-50 km  → 5 分（不同區域）
> 50 km   → 0 分（根據偏好設定，不會顯示）
```

**實現代碼**:
```python
# backend/app/services/matching_service.py:6-23 (_calculate_distance_score 函數)
def _calculate_distance_score(distance_km: float) -> float:
    if distance_km < 5:
        return 20
    if distance_km < 10:
        return 15
    if distance_km < 25:
        return 10
    if distance_km < 50:
        return 5
    return 0
```

**PostGIS 計算**（在查詢時完成）:
```python
# backend/app/api/discovery.py:105-111
distance_label = (
    func.ST_Distance(
        Profile.location,
        my_profile.location,
        True  # use_spheroid=True（球面計算）
    ) / 1000  # 轉換為公里
).label('distance_km')
```

---

### 3. 活躍度（20 分）

**計算方式**: 根據最後上線時間（last_active）

```python
last_active = datetime.now() - timedelta(hours=5)  # 5 小時前上線
hours_ago = 5

if hours_ago < 1:       score = 20 分  # 剛上線
elif hours_ago < 24:    score = 15 分  # 今天活躍
elif hours_ago < 72:    score = 10 分  # 3 天內活躍
elif hours_ago < 168:   score = 5 分   # 7 天內活躍
else:                   score = 0 分   # 不活躍
```

**評分表**:
```
< 1 小時   → 20 分（線上中，極可能回應）
< 24 小時  → 15 分（今日活躍，很可能回應）
< 3 天     → 10 分（本週活躍，可能回應）
< 7 天     → 5 分（上週活躍，較慢回應）
> 7 天     → 0 分（不活躍，可能不回應）
```

**實現代碼**:
```python
# backend/app/services/matching_service.py:26-51 (_calculate_activity_score 函數)
def _calculate_activity_score(last_active) -> float:
    if not last_active:
        return 0
    hours_ago = (datetime.now(timezone.utc) - last_active).total_seconds() / 3600

    if hours_ago < 1:
        return 20
    if hours_ago < 24:
        return 15
    if hours_ago < 72:
        return 10
    if hours_ago < 168:  # 7天
        return 5
    return 0
```

---

### 4. 檔案完整度（5 分）- v2.0 更新

**計算方式**: 照片數量 + Bio（權重調整）

```python
photo_count = 4
has_bio = True

照片分數 = min(4 * 0.5, 3) = 2 分  # 每張照片 0.5 分，最多 3 分
Bio 分數 = 2 分（有）或 0 分（無）

總分 = 2 + 2 = 4 分
```

**評分表**:
```
0 張照片 + 無 Bio  → 0 分（檔案空）
1-2 張照片 + 無 Bio → 0.5-1 分（檔案不完整）
3-4 張照片 + 無 Bio → 1.5-2 分（還行）
任意照片 + 有 Bio  → +2 分
6 張照片 + 有 Bio  → 5 分（完美檔案）
```

**實現代碼**:
```python
# backend/app/services/matching_service.py:67-71
photo_count = candidate.get("photo_count", 0)
score += min(photo_count * 0.5, 3)  # 照片：最多 3 分
if candidate.get("bio"):
    score += 2                       # Bio：2 分
```

---

### 5. 信任分數（5 分）- v2.0 新增

**計算方式**: 根據用戶信任分數映射到權重

```python
trust_score = 65  # 用戶當前信任分數（0-100）

if trust_score >= 70:    weight = 5.0 分  # 高度信任
elif trust_score >= 50:  weight = 4.0 分  # 正常
elif trust_score >= 30:  weight = 2.5 分  # 需關注
elif trust_score >= 20:  weight = 1.0 分  # 受限
else:                    weight = 0.0 分  # 高度可疑
```

**評分表**:
```
trust_score = 75  → 5.0 分（優先推薦）
trust_score = 55  → 4.0 分（正常推薦）
trust_score = 35  → 2.5 分（降低推薦）
trust_score = 22  → 1.0 分（極少推薦）
trust_score = 10  → 0.0 分（幾乎不推薦）
```

**目的**:
- 優先推薦高信任度用戶（減少詐騙、騷擾）
- 降低低信任用戶曝光（保護平台安全）
- 配合訊息限制（< 20 分用戶每日 20 則上限）

**實現代碼**:
```python
# backend/app/services/matching_service.py:145-146
trust_score = candidate.get("trust_score", 50)  # 預設 50 分
score += _calculate_trust_score_weight(trust_score)
```

**函數定義**: `_calculate_trust_score_weight()` 在第 75-99 行

**信任分數如何變化**: 參見 [TRUST_SCORE_SYSTEM.md](TRUST_SCORE_SYSTEM.md)

---

## 🔍 篩選條件（browse API）

在計算分數前，候選人必須通過以下篩選：

### 基本篩選

```python
# backend/app/api/discovery.py:121-146
1. ✅ 排除自己
2. ✅ 檔案可見且完整
3. ✅ 帳號啟用中
4. ✅ 符合年齡偏好（用戶設定的 min_age ~ max_age）
5. ✅ 符合距離偏好（PostGIS 範圍查詢）
6. ✅ 符合性別偏好（male/female/both/all）
```

### 排除已互動用戶

```python
# backend/app/api/discovery.py:148-187
7. ✅ 排除已喜歡的用戶（likes 表）
8. ✅ 排除已配對的用戶（matches 表）
9. ✅ 排除已封鎖的用戶（blocked_users 表）
10. ✅ 排除封鎖我的用戶（blocked_users 表）
11. ✅ 排除 24 小時內跳過的用戶（passes 表）
```

### 配對分數門檻

```python
# backend/app/api/discovery.py:52-53
MIN_MATCH_SCORE = 15.0  # 最低配對分數門檻

# 計算分數後過濾（第 248-250 行）
12. ✅ 配對分數 >= 15% 才會顯示
```

**設計理由**:
- 低於 15% 的配對幾乎沒有共同點，顯示無意義
- 提升推薦品質，避免用戶滑過一堆不相關的人
- 若無符合條件的候選人，返回空列表（前端顯示「沒有更多候選人」）

---

## 📈 實際範例

### 範例 1：高分配對（v2.0）

**用戶 A**:
- 興趣：旅遊、攝影、美食、健身
- 位置：台北市中正區
- 偏好：25-35 歲，50km 內

**候選人 B**:
- 興趣：旅遊、攝影、美食（3 個共同）
- 位置：台北市大安區（距離 3km）
- 活躍度：2 小時前上線
- 檔案：5 張照片 + Bio
- 信任分數：75（高度信任）

**評分計算**:
```
興趣匹配：3 × 10 = 30 分
地理距離：3km < 5km = 20 分
活躍度：2h < 24h = 15 分
檔案完整度：2.5 + 2 = 4.5 分
信任分數：75 ≥ 70 = 5 分
───────────────────────────
總分：74.5 分（高配對度）
```

---

### 範例 2：中等配對（v2.0）

**用戶 A**:
- 興趣：閱讀、音樂、電影
- 位置：台北市

**候選人 C**:
- 興趣：音樂、健身（1 個共同）
- 位置：新北市（距離 15km）
- 活躍度：5 天前上線
- 檔案：2 張照片，無 Bio
- 信任分數：55（正常）

**評分計算**:
```
興趣匹配：1 × 10 = 10 分
地理距離：15km → 10 分
活躍度：5 天 → 5 分
檔案完整度：1 + 0 = 1 分
信任分數：55 ≥ 50 = 4 分
───────────────────────────
總分：30 分（中低配對度）
```

---

### 範例 3：低分配對（v2.0）

**候選人 D**:
- 興趣：運動、遊戲（0 個共同）
- 位置：40km 遠
- 活躍度：10 天前上線
- 檔案：1 張照片，無 Bio
- 信任分數：15（受限用戶）

**評分計算**:
```
興趣匹配：0 分
地理距離：40km → 5 分
活躍度：10 天 → 0 分
檔案完整度：0.5 + 0 = 0.5 分
信任分數：15 < 20 = 0 分
───────────────────────────
總分：5.5 分（極低配對度，幾乎不推薦）
```

---

## 🚀 API 使用流程

### 瀏覽候選人流程

```
1. 用戶請求: GET /api/discovery/browse?limit=20

2. 後端處理:
   a. 取得用戶檔案和偏好設定
   b. PostGIS 地理查詢（距離篩選）
   c. 排除已互動用戶（喜歡、配對、封鎖、跳過）
   d. 取 limit × 3 個候選人
   e. 計算每個候選人的配對分數
   f. 依分數排序
   g. 返回 top limit 個

3. 前端顯示:
   - 卡片堆疊（顯示前 3 張）
   - 顯示配對分數百分比
   - 用戶可滑動喜歡或跳過
```

### 分數計算流程

```
用戶檔案 + 候選人檔案
    ↓
MatchingService.calculate_match_score()
    ↓
計算 5 個因素分數（興趣、距離、活躍度、完整度、信任）
    ↓
加總（最高 100 分）
    ↓
返回配對分數
```

---

## 📖 相關文檔

- [技術架構](./ARCHITECTURE.md) - 系統整體架構
- [開發路線圖](./ROADMAP.md) - 未來規劃（含配對演算法優化）
- [API 文檔](http://localhost:8000/docs) - FastAPI Swagger UI

