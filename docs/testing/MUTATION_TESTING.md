# 變異測試（Mutation Testing）

> 覆蓋率只回答「這行有沒有被執行」，變異測試回答「這行**寫錯了**測試抓不抓得到」。

變異測試會自動對程式碼做小幅修改（把 `<` 改成 `<=`、`and` 改成 `or`、刪掉一個參數、把字串換成 `None`…），
每個修改後的版本稱為一個**變異體（mutant）**，再對它跑測試：

| 結果 | 意義 |
|------|------|
| 🎉 killed | 有測試失敗 → 測試抓得到這個錯誤 |
| 🙁 survived | 測試全過 → **這種錯誤目前不會被發現** |
| 🫥 no tests | 沒有任何測試執行到這段程式碼 |

**變異分數** = killed ÷（killed + survived）。存活者不一定都是缺口：有些修改在語意上與原碼等價
（例如把 log 訊息換掉），稱為**等價變異體**，需要人工判讀。

---

## 執行方式

### 前置需求

- PostgreSQL + PostGIS、Redis（`docker compose up -d`），且資料庫使用者可 `CREATE DATABASE`
- `pip install -r requirements-dev.txt`（含 `mutmut>=3.8`）
- `backend/.env` 已設定 `TEST_DATABASE_URL`

### 指令

```bash
cd backend

# 全部目標模組（4 核心約需 5 小時）
mutmut run --max-children 4

# 只跑特定模組 / 函式（支援 fnmatch 萬用字元；指定名稱時一律重跑）
mutmut run "app.services.login_limiter.*"

mutmut results            # 列出存活者
mutmut show <mutant 名稱>  # 顯示該變異體的 diff
mutmut browse             # 互動式瀏覽
```

結果存在 `backend/mutants/`（已加入 `.gitignore`）。中斷後重新執行 `mutmut run` 會跳過已有結果的變異體；
修改測試後若要重新驗證，請刪除 `mutants/` 或明確指定變異體名稱。

### 設定（`backend/pyproject.toml` 的 `[tool.mutmut]`）

| 設定 | 說明 |
|------|------|
| `only_mutate` | 目標模組（見下方「範圍」） |
| `process_isolation = "forkserver"` | 每個 pytest session 都從只做過 collect 的乾淨行程 fork |
| `pytest_add_cli_args` | 載入 `tests/mutmut_isolation.py` 隔離 plugin |
| `pytest_add_cli_args_test_selection` | 整個 `tests/`，排除 `test_rate_limit.py` |

### 為什麼需要隔離 plugin

mutmut 以多個 worker 平行跑測試，但本專案的測試：

1. 共用同一個 PostgreSQL 測試庫，每個測試都 `create_all` / `drop_all`；
   session fixture 還會 `pg_terminate_backend` 同一個庫的其他連線
2. 共用同一個 Redis（登入限制、驗證碼、黑名單等 key）

平行執行會互相刪表、殺連線，把變異體誤判為 killed。`tests/mutmut_isolation.py` 讓每個 pytest session
以 `flock` 取得獨佔 slot，改用 `<測試庫>_mm<slot>`（不存在時自動建立）與 Redis db `<slot + 1>`。

另外兩個設定也是為了避免誤判：

- **forkserver**：預設的 fork 模式會在同一行程連續跑多個 pytest session，`ContentModerationService`
  等 class 層級單例持有的 Redis 連線會綁在上一個 session 已關閉的 event loop 上（`Event loop is closed`）
- **排除 `test_rate_limit.py`**：slowapi 的 storage 在 import 時就綁定 Redis db 0，無法隔離

---

## 範圍

挑選商業邏輯與安全性最關鍵、且多為純邏輯的 9 個模組：

| 模組 | 職責 |
|------|------|
| `core/security.py` | 密碼雜湊、JWT 簽發與解碼 |
| `services/matching_service.py` | 5 維度配對評分、候選人篩選、分批瀏覽、放寬建議 |
| `services/trust_score.py` | 信任分數調整、低信任訊息限流 |
| `services/trust_score_recovery.py` | 每日信任分數恢復（Redis 日期鎖） |
| `services/login_limiter.py` | 登入失敗鎖定（防暴力破解） |
| `services/email_rate_limiter.py` | Email 發送冷卻與每日上限 |
| `services/verification_code.py` | 驗證碼存取（Redis + 內存回退） |
| `services/token_blacklist.py` | 登出 Token 黑名單（Redis + 內存回退） |
| `services/content_moderation.py` | 敏感詞審核、可疑模式、審核日誌、快取 |

---

## 結果

- **基準線**：導入變異測試前的測試，對 9 個模組全部 1605 個變異體執行
- **改善後**：補完測試後，重跑基準線中 survived 與 no tests 的 540 個變異體
  （基準線已 killed 的變異體未重跑：這段期間對既有測試的修改都是加嚴斷言或改得更貼近邊界，沒有拿掉會殺死它們的斷言）
- 環境：4 核心、mutmut 3.8.0、`--max-children 4`

### 變異分數

| 模組 | 變異體 | 基準線 killed / survived / no tests | 分數 | 改善後 killed / survived / no tests | 分數 |
|------|-------:|------|-----:|------|-----:|
| `core.security` | 91 | 86 / 5 / 0 | 94.5% | 89 / 2 / 0 | 97.8% |
| `services.content_moderation` | 424 | 212 / 212 / 0 | 50.0% | 371 / 53 / 0 | 87.5% |
| `services.email_rate_limiter` | 66 | 50 / 16 / 0 | 75.8% | 64 / 2 / 0 | 97.0% |
| `services.login_limiter` | 85 | 76 / 9 / 0 | 89.4% | 83 / 2 / 0 | 97.6% |
| `services.matching_service` | 572 | 409 / 163 / 0 | 71.5% | 491 / 81 / 0 | 85.8% |
| `services.token_blacklist` | 105 | 54 / 25 / 26 | 68.4% | 70 / 22 / 13 | 76.1% |
| `services.trust_score` | 102 | 78 / 24 / 0 | 76.5% | 99 / 3 / 0 | 97.1% |
| `services.trust_score_recovery` | 94 | 51 / 17 / 26 | 75.0% | 61 / 7 / 26 | 89.7% |
| `services.verification_code` | 66 | 49 / 17 / 0 | 74.2% | 52 / 14 / 0 | 78.8% |
| **合計** | **1605** | 1065 / 488 / 52 | **68.6%** | 1380 / 186 / 39 | **88.1%** |

分數 = killed ÷（killed + survived），no tests 不計入。整體從 **68.6% → 88.1%**，存活者從 488 個降到 186 個；剩下的存活者逐一判讀過，都屬於下方「剩餘存活者」的類別。

### 找到的 bug（已修正）

| 位置 | 問題 | 怎麼發現的 |
|------|------|-----------|
| `api/moderation.py` 新增敏感詞 | 無條件 `.lower()`，正則也被轉小寫：`\S`（非空白）變成 `\s`（空白），`\D`、`\W` 語意反轉，`\Z` 變成無效的 `\z`。管理員新增的正則規則因此永遠比對不到 | `_match_sensitive_word` 正則分支的變異體全部存活 → 補測試時發現正則根本存不進去 |
| `matching_service._candidate_query` 年齡上限 | `date_of_birth >= today - (max_age + 1) 年` 會納入**今天剛滿 max_age + 1 歲**的人：偏好 30–35 歲會看到卡片顯示 36 歲的人。改為 `>` | `>=` → `>` 的變異體存活，追查後發現存活的那個才是正確版本 |

修正 1 之後，既有資料庫中已被轉成小寫的正則敏感詞需要由管理員重建。

### 潛在問題（未修正，記錄供評估）

- **`check_profile_content` 的動作可能被降級**：簡介命中 `AUTO_BAN`、之後某個興趣標籤命中 `REJECT` 時，
  `max_action` 會被覆寫成 `REJECT`。目前所有呼叫端只傳 `bio`，觸發不到。
- **敏感詞的 `severity` / `action` 沒有列舉驗證**：管理 API 接受任意字串。`severity` 打錯（例如 `high`）時，
  該詞命中後嚴重度視為 0，動作停在 `APPROVED`，等於沒有作用。

### 名不符實的測試（已修正）

這些測試在覆蓋率報告上都算「有測到」，但程式寫錯也不會失敗：

| 測試 | 問題 |
|------|------|
| `test_moderation_log_created` | 查詢日誌後丟棄結果，**沒有任何斷言** |
| `test_cache_mechanism` | 只比較兩次結果相同，完全不快取也成立 |
| 內容清理測試 | `"***" in 結果`：替換成 `XX***XX` 也會通過 |
| 個人檔案審核測試 | `any("個人簡介" in v ...)`：前綴改壞也會通過；`AUTO_BAN`、WARN 標籤、多欄位優先序都沒有測試 |
| `test_browse_users_success` | 斷言包在 `if len(...) > 0:` 內，回傳空陣列也會通過 |
| `test_browse_fills_limit_when_first_batch_is_low_score` | 依插入順序假設「低分在前段」，但 browse 依 user_id 分批，約 19% 機率根本不會走到第二批 |
| `test_expired_token_auto_remove` | 經 `add()` 加入過期 Token，但 `add()` 會直接略過過期 Token，從未走到「內存過期自動移除」的路徑 |
| `test_redis_integration.py` | 整段包在 `except Exception: pytest.skip`，`AssertionError` 也被吞成 skip。每次執行有 2 個被跳過，原因其實是共用連線池跨 event loop，不是 Redis 不可用，因此黑名單與驗證碼的真實 Redis 整合測試**從未真正執行** |
| 跳過紀錄測試 | 只檢查「被跳過者不出現」；子查詢壞掉變成 `NOT IN (NULL)` 會排除所有人，仍然通過 |
| `test_passed_user_reappears_after_24_hours` | 把跳過時間設成 25 小時前，期限寫成 25 小時也會通過（改為 24 小時 1 分） |
| `test_browse_liked_me_candidate_ranked_first_among_equal_scores` | 同分時靠 DB 掃描順序就排第一，拿掉排序加權也會通過 |

另外，以不同順序執行測試時發現 `test_cache_to_redis` 會把已關閉的 Redis 連線留在
`ContentModerationService` 的 class 屬性上，讓排在它之後的內容審核測試失敗（已改用 monkeypatch 還原）。

### 補上的缺口

| 模組 | 原本沒有測到的行為 |
|------|-------------------|
| matching_service | 候選人過濾整段可刪除而不被發現（74 個存活者）：隱藏／未完成／停權用戶、自己、性別偏好（male / female / both / all）、雙向封鎖、只排除「我」24 小時內跳過的人；年齡邊界；卡片內容（年齡、性別、自介、地點、距離與分數的四捨五入）由候選人實際資料算出；分數剛好等於門檻 15 算合格；「喜歡我」的排序加權與優先掃描（只看喜歡我、不含喜歡別人的人）；分批 offset；放寬建議只計多出來的人數；活躍度 1h / 24h / 168h 邊界（凍結時間）；照片逐張計分 |
| content_moderation | 審核日誌逐欄位；快取命中、TTL 過期、清除（含 Redis key）；正則敏感詞與無效正則；Redis 快取讀寫與故障回退（之後不再重試）；多個詞命中時的嚴重度排序；個人檔案的 AUTO_BAN、WARN 標籤、REJECT 不被降級；正常內容與未帶 user_id 不寫日誌 |
| trust_score | 分數剛好 20 不受限；今日尚未發訊；剩最後 1 則；記錄與檢查共用同一個當日計數 key 與 24h TTL |
| trust_score_recovery | 日期鎖 key 以 UTC 日期命名、48h TTL；Redis 不可用時跳過；失敗時釋放鎖以便重試；未注入 session 的正式環境路徑 |
| login_limiter | 鎖定時寫入的 key / 值 / TTL 與清除的計數 key（原本只驗證「有呼叫 set」） |
| email_rate_limiter | 第 5 封仍允許（`>` vs `>=`）；冷卻剩 1 秒仍擋下；cooldown key；距 UTC 午夜秒數（模擬 UTC+8 主機） |
| token_blacklist / verification_code | Redis 故障期間寫入內存的資料，Redis 恢復後仍有效；寫入 Redis 的值與 TTL |
| core/security | access / refresh Token 的 `exp`、`iat` 以 UTC 計算（模擬 UTC+8 主機；PyJWT 把 naive datetime 當 UTC，誤用 `now()` 會讓 Token 多活 8 小時） |

### 剩餘存活者

186 個存活者逐一判讀後的分類。這些不補測試：補了也只是把實作細節寫死在測試裡，無法多抓到真正的錯誤。

| 類別 | 數量 | 例子 |
|------|-----:|------|
| 日誌與錯誤訊息文字 | 56 | `logger.info(...)` 的內容、`ValueError` 的訊息 |
| 冗餘或不可達的程式碼 | 58 | 見下方說明 |
| 語意等價 | 44 | SQL label／subquery 名稱、`join` 省略條件（由外鍵推得）、`EXISTS (SELECT NULL ...)`、初始值為 0 時 `=` 與 `+=`、`ensure_ascii=None`（falsy）、`"utf-8"` 與 `"UTF-8"`、Redis 鎖的值 `"1"`、Python 3.11 起 `fromisoformat` 已支援 `Z` |
| 效能或精度取捨 | 12 | 分批大小 `limit * 3` 與 `* 4`、湊滿後是否多掃一批、`use_spheroid`、公尺／公里換算 `1000` 與 `1001` |
| 微秒級時間邊界 | 7 | 過期判斷 `<` 與 `<=`（兩次 `now()` 不會剛好相等） |
| 時區（主機為 UTC 時等價） | 4 | 日期字串的 `datetime.now(UTC)` 與 `now(None)`；JWT 與 Email 冷卻的同類問題已用模擬 UTC+8 的測試蓋住 |
| Redis 雙重故障 | 3 | Redis 已回退時刪除失敗、釋放鎖時 Redis 又故障 |
| 輸入未驗證／排序未定義 | 2 | 未知 `severity` 的預設權重（見「潛在問題」）、同嚴重度時取先命中或後命中者 |

**冗餘或不可達的程式碼（58）**，可考慮直接簡化：

- `_candidate_query` 排除「已配對」的子查詢（18）：配對必然來自雙方互相 Like，而 Like 從不刪除（解除配對也不刪），
  已被「排除我喜歡過的人」涵蓋
- `ContentModerationService` 內存快取的 LRU 淘汰（8）：快取 key 只有 `"words"` 一個，永遠到不了 500 筆上限
- 傳給評分函式但沒被讀取的欄位（12）：`user_data` 的偏好欄位、候選人的 `age`、敏感詞的 `description`
- 不會用到的預設值（11）：`or 18 / 99 / 50`（資料庫欄位已有預設）、`get("distance_km", 999)` 等字典預設值、`content_type="TEXT"` 與 `ttl_minutes=10`（呼叫端都有傳）
- 其他（9）：`min(score, 100)`（權重總和剛好 100）、`func.least` 上限（WHERE 已限定低於預設分數，且每次只 +1）、
  個人檔案審核中只可能在第一輪成立的條件、只有測試會呼叫的 `reset_session_factory` 等

**no tests（39）**：Token 黑名單清理迴圈 `_periodic_cleanup`、信任分數恢復的 `_periodic_recovery` 與
`start_recovery_task` / `stop_recovery_task`。它們是 `while True: sleep()` 的背景任務外殼，
實際工作（`cleanup_expired`、`run_daily_recovery_once`）都已有測試。

---

## 建議

- **不建議放進每次 CI**：9 個模組完整跑一次在 4 核心約 5 小時（內容審核與配對的變異體會觸發大量 API 整合測試）。
  修改這些模組時，用 `mutmut run "app.services.<模組>.*"` 只跑該模組即可
- **寫測試時避開這次找到的模式**：只用 `in`／`len > 0` 的弱斷言、包在 `if` 裡的斷言、`except Exception: skip`、
  靠插入順序或隨機 UUID 才成立的前提、離邊界太遠的測試值（25 小時測不出 24 小時的期限、整數分數測不出四捨五入）
- **涉及時間的邏輯**：凍結 `datetime.now`，並模擬非 UTC 主機（例如 UTC+8），否則 `now()` 與 `now(UTC)` 的錯誤在 CI 上看不出來
