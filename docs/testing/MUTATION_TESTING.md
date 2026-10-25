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

## 總覽

| 批次 | 模組 | 改善後變異體 | 基準線分數 | 改善後分數 |
|------|------|------:|-----:|-----:|
| 第一批 | 配對、信任分數、登入與 Email 限流、驗證碼、Token 黑名單、內容審核、密碼與 JWT（9 個） | 1528 | 66.0% | 87.2% |
| 第二批 | 認證依賴、Cookie、驗證碼嘗試限制、Token 全局失效、照片審核、清理任務、聊天／封鎖檢舉／照片審核 API（11 個） | 1845 | 66.4% | 92.8% |

兩批共修正 9 項問題（見各批的「找到的 bug」）與 14 項名不符實的測試；剩下的存活者逐一判讀過，
都是 log、語意等價、效能取捨或刻意保留的防禦性程式碼。

---

## 執行方式

### 前置需求

- PostgreSQL + PostGIS、Redis（`docker compose up -d`），且資料庫使用者可 `CREATE DATABASE`
- `pip install -r requirements-dev.txt`（含 `mutmut>=3.8`）
- `backend/.env` 已設定 `TEST_DATABASE_URL`

### 指令

```bash
cd backend

# 全部目標模組（只建議在修改這些模組時，針對該模組執行）
mutmut run --max-children 4

# 只跑特定模組 / 函式（支援 fnmatch 萬用字元；指定名稱時一律重跑）
mutmut run "app.services.login_limiter.*"

mutmut results            # 列出存活者
mutmut show <mutant 名稱>  # 顯示該變異體的 diff
mutmut browse             # 互動式瀏覽
```

結果存在 `backend/mutants/`（已加入 `.gitignore`）。中斷後重新執行 `mutmut run` 會跳過已有結果的變異體；
修改測試後若要重新驗證，請刪除 `mutants/` 或明確指定變異體名稱。

**修改 `only_mutate` 後請刪除 `mutants/`**：不在清單內的模組會被原樣複製進 `mutants/`，之後加入清單時，
mutmut 只要看到原始碼沒有比副本新，就不會重新產生變異體（結果裡完全不會出現該模組）；
舊的 `mutmut-stats.json` 也沒有這些函式的測試對應，會被誤判為 `no tests`。

### API 路由模組

mutmut 會跳過有裝飾器的函式（`@staticmethod`、`@classmethod` 除外），FastAPI 的路由函式都有
`@router.get(...)`，所以 `api/` 模組不會產生任何變異體。`scripts/mutmut_unwrap_routes.py` 會建立一份
backend 副本，把指定模組的路由改寫成語意相同的「定義後再註冊」（`f = router.get(...)(f)`），
並把副本的 `only_mutate` 設為這些模組：

```bash
cd backend
python scripts/mutmut_unwrap_routes.py /tmp/mm-api app/api/safety.py app/api/messages.py
cd /tmp/mm-api && mutmut run --max-children 4
```

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

測試本身也必須在重複執行時穩定：mutmut 會在同一個 slot 連續跑上百次測試。`conftest.py` 的 `client`
fixture 在每個測試前清除登入失敗、驗證碼嘗試、Email 發送次數等限流計數；否則固定 email 的計數會跨 session
累積（第 5 次就被鎖定回 429），測試隨機失敗，變異體被誤判為 killed。

**檢查誤判的方法**：只改 log 文字的變異體不可能被測試抓到，若結果是 killed，就代表有測試在隨機失敗。

---

## 範圍

分兩批進行。第一批是商業邏輯與安全性最關鍵、且多為純邏輯的 9 個模組；
第二批是認證依賴、照片審核、清理任務，以及聊天、封鎖與檢舉的 API（見「第二批」）。

第一批的 9 個模組：

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

## 第一批結果

- **基準線**：導入變異測試前的程式與測試，9 個模組共 1605 個變異體（已更正誤判，見「測量誤判與更正」）
- **改善後**：目前的程式與測試。依測量結果刪除冗餘程式碼後共 1528 個變異體。
  在 repo 跑過的變異體取 repo 結果；少數從未在 repo 重跑的（所在函式未改動、基準線已 killed，
  且涵蓋測試不含會隨機失敗的測試）沿用基準線結果
- 環境：4 核心、mutmut 3.8.0、`--max-children 4`

### 變異分數

| 模組 | 基準線 變異體 | killed / survived / no tests | 分數 | 改善後 變異體 | killed / survived / no tests | 分數 |
|------|------:|------|-----:|------:|------|-----:|
| `core.security` | 91 | 72 / 19 / 0 | 79.1% | 91 | 84 / 7 / 0 | 92.3% |
| `services.content_moderation` | 424 | 201 / 223 / 0 | 47.4% | 364 | 310 / 54 / 0 | 85.2% |
| `services.email_rate_limiter` | 66 | 49 / 17 / 0 | 74.2% | 66 | 64 / 2 / 0 | 97.0% |
| `services.login_limiter` | 85 | 66 / 19 / 0 | 77.6% | 85 | 81 / 4 / 0 | 95.3% |
| `services.matching_service` | 572 | 409 / 163 / 0 | 71.5% | 555 | 493 / 62 / 0 | 88.8% |
| `services.token_blacklist` | 105 | 50 / 29 / 26 | 63.3% | 105 | 73 / 32 / 0 | 69.5% |
| `services.trust_score` | 102 | 78 / 24 / 0 | 76.5% | 102 | 102 / 0 / 0 | 100.0% |
| `services.trust_score_recovery` | 94 | 51 / 17 / 26 | 75.0% | 94 | 73 / 21 / 0 | 77.7% |
| `services.verification_code` | 66 | 49 / 17 / 0 | 74.2% | 66 | 53 / 13 / 0 | 80.3% |
| **合計** | **1605** | 1025 / 528 / 52 | **66.0%** | **1528** | 1333 / 195 / 0 | **87.2%** |

分數 = killed ÷（killed + survived），timeout 算 killed，no tests 不計入。整體從 **66.0% → 87.2%**：
存活者從 528 個降到 195 個，沒有任何測試執行到的變異體從 52 個降到 0 個。
剩下的 195 個存活者逐一判讀過，歸類見「剩餘存活者」。

### 測量誤判與更正

第一版報告寫的是 68.6% → 88.1%，兩邊都高估了。原因是有些測試會隨機失敗，
存活的變異體因此被誤判為 killed：

1. **限流計數跨 session 累積**：測試用固定 email，登入失敗、驗證碼嘗試、Email 發送次數存在 Redis
   且不會清除。mutmut 在同一個 slot 重複跑同一批測試，第 5 次起 `test_login_wrong_password` 等測試
   就收到 429。一般開發時連續執行 `pytest tests/test_auth.py` 5 次也會失敗
2. **舊版 `test_redis_integration.py` 洩漏 Redis 連線**：把已關閉的連線留在 `ContentModerationService`
   的 class 屬性，排在它後面的測試跟著失敗

**怎麼發現的**：只改 log 文字的變異體不可能被測試抓到，卻被標成 killed（`clear_cache` 的 11 個變異體全數「killed」，另有 5 個只改 log 的變異體也是）。修正 `conftest.py` 後，
把涵蓋測試含這些測試檔的 killed 變異體全部重跑：基準線有 40 個、改善後有 19 個其實存活。
其中包括 `verify_password` 的例外分支和密碼長度上限，追查後又找到一個 bug（見下表第 3 項）。

### 找到的 bug（已修正）

| # | 位置 | 問題 | 怎麼發現的 |
|---|------|------|-----------|
| 1 | `api/moderation.py` 新增敏感詞 | 無條件 `.lower()`，正則也被轉小寫：`\S`（非空白）變成 `\s`（空白），`\D`、`\W` 語意反轉，`\Z` 變成無效的 `\z`。管理員新增的正則規則永遠比對不到 | `_match_sensitive_word` 正則分支的變異體全部存活，補測試時發現正則根本存不進去 |
| 2 | `matching_service._candidate_query` 年齡上限 | `date_of_birth >= today - (max_age + 1) 年` 會納入**今天剛滿 max_age + 1 歲**的人：偏好 30–35 歲會看到 36 歲的人。改為 `>` | `>=` → `>` 的變異體存活，追查後發現存活的那個才是正確版本 |
| 3 | `core/security.verify_password` | 登入 schema 沒限制密碼長度，超過 128 字元時預處理在 `try` 之外拋 `ValueError`，登入回 **500**。改為視為密碼錯誤（401） | 更正誤判後，密碼長度相關的變異體存活 |
| 4 | `content_moderation.check_profile_content` | 依欄位順序覆寫動作：簡介命中 `AUTO_BAN`、之後的興趣標籤命中 `REJECT`，結果被降級成 `REJECT`。改為取最嚴重者 | 動作判斷的條件變異體存活，追查時發現 |
| 5 | `schemas/moderation.py` 敏感詞輸入 | `severity`／`action` 接受任意字串；`severity` 打錯（例如 `high`）時嚴重度視為 0，該詞命中也照樣通過。改用 `Literal` 限制（回應 schema 不變，既有資料照常讀取） | 未知嚴重度預設權重的變異體存活 |
| 6 | `tests/conftest.py` | 限流計數不清除，連續執行測試會隨機失敗（見上節） | 只改 log 卻被 killed 的變異體 |

修正 1 之後，既有資料庫中已被轉成小寫的正則敏感詞需要由管理員重建。

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

### 補上的缺口

| 模組 | 原本沒有測到的行為 |
|------|-------------------|
| matching_service | 候選人過濾整段可刪除而不被發現：隱藏／未完成／停權用戶、自己、性別偏好、雙向封鎖、只排除「我」24 小時內跳過的人；年齡邊界；卡片內容（年齡、性別、自介、地點、距離與分數的四捨五入）；分數剛好等於門檻 15；「喜歡我」的排序加權與優先掃描；分批 offset；放寬建議只計多出來的人數；偏好為 NULL 時的預設 18–99 歲、50 公里；活躍度邊界與跳過期限以 UTC 計算（模擬 UTC+8 主機） |
| content_moderation | 審核日誌逐欄位；快取命中、TTL 過期、清除（含 Redis key、回退後不再呼叫 Redis）；正則與無效正則；Redis 快取讀寫與故障回退；多個詞命中時的嚴重度排序；個人檔案的 AUTO_BAN 與動作優先序；正常內容與未帶 user_id 不寫日誌；管理 API 拒絕未知的嚴重度／動作 |
| core/security | 密碼驗證：正確／錯誤、雜湊格式錯誤時不可放行、bcrypt 72 bytes 以外的差異、128／129 字元上限；Token 的 `exp`、`iat` 以 UTC 計算（模擬 UTC+8 主機）；自訂 `expires_delta` |
| trust_score | 分數剛好 20 不受限；今日尚未發訊；剩最後 1 則；記錄與檢查共用同一個當日 key 與 24h TTL，且以 UTC 日期命名；調整不存在的用戶要拋錯 |
| trust_score_recovery | 日期鎖以 UTC 日期命名、48h TTL；Redis 不可用時跳過；失敗時釋放鎖、釋放時 Redis 也故障仍拋出原本的錯誤；未注入 session 的正式環境路徑；背景任務的啟動／停止與每小時迴圈 |
| login_limiter | 鎖定時寫入的 key／值／TTL 與清除的計數 key；鎖定剩 1 秒仍有效；剩餘次數不會是負數；未鎖定時鎖定秒數為 0 |
| email_rate_limiter | 第 5 封仍允許；冷卻剩 1 秒仍擋下；cooldown key；距 UTC 午夜秒數（模擬 UTC+8 主機） |
| token_blacklist / verification_code | Redis 故障期間寫入內存的資料，Redis 恢復後仍有效；寫入 Redis 的值與 TTL；回退後刪除不再呼叫 Redis；剩不到 1 秒的 Token 不寫 Redis（`ex=0` 會讓黑名單永久回退）；清理迴圈 |

### 依測量結果整理的程式碼

**已刪除**（沒有任何作用的程式碼）：

- `ContentModerationService` 內存快取的 LRU 淘汰：快取只會存一份 `"words"`，永遠到不了 500 筆上限
- 傳給評分函式但沒被讀取的欄位：`user_data` 的偏好欄位、候選人的 `age`；敏感詞快取的 `description`
- `check_profile_content` 的重複邏輯、只可能在第一輪成立的條件、從未回傳的 `all_triggered_word_ids`
- `_log_moderation` 未使用的 `db` 參數（日誌一律以獨立 session 寫入）
- `fromisoformat` 前多餘的 `"Z"` 轉換（專案需求 Python 3.13+，3.11 起已支援）

**刻意保留**：

- `_candidate_query` 排除「已配對」的子查詢：目前已被「排除我喜歡過的人」涵蓋（配對必來自互相 Like，
  且 Like 從不刪除），但這是**刻意的防禦性排除**，`api/discovery.py` 的「誰喜歡我」使用同一套條件並註明
  「即使 like 記錄異常遺失也不洩漏」
- `min(score, 100)`、`func.least` 上限：防止日後調整權重或加分幅度時超出範圍
- 公開介面的預設值（`calculate_match_score` 的字典預設值、`content_type="TEXT"`、`ttl_minutes=10`）

**未修改（會破壞相容性）**：`create_access_token` 的 `expires_delta` 參數目前沒有呼叫端使用，
但刪除會改變公開函式簽名，改為補上測試。

### 剩餘存活者

| 類別 | 數量 | 說明與例子 |
|------|-----:|------|
| 日誌與錯誤訊息文字 | 91 | `logger.info(...)` 的內容與參數 |
| 語意等價 | 53 | SQL label／subquery 名稱、`join` 省略條件（由外鍵推得）、`EXISTS (SELECT NULL ...)`、初始值為 0 時 `=` 與 `+=`、`ensure_ascii=None`（falsy）、`"utf-8"` 與 `"UTF-8"`、Redis 鎖的值 `"1"`、`break` 與 `return`、`jwt.encode` 省略演算法（預設即 HS256）、輸入已驗證後不會出現的未知嚴重度／動作 |
| 冗餘但刻意保留 | 31 | 見上節「刻意保留」（其中 18 個是排除已配對的子查詢） |
| 效能或精度取捨 | 12 | 分批大小 `limit * 3` 與 `* 4`、湊滿後是否多掃一批、`use_spheroid`、公尺／公里換算 `1000` 與 `1001` |
| 微秒／次秒級時間邊界 | 7 | 過期判斷 `<` 與 `<=`（兩次 `now()` 不會剛好相等）、Redis TTL 剛好為 0 |
| 同分時的先後 | 1 | 兩個同嚴重度的敏感詞同時命中時取先命中或後命中者（規格未定義） |

這些不補測試：補了也只是把實作細節寫死在測試裡，無法多抓到真正的錯誤。

---

## 第二批：認證、照片審核、聊天、封鎖與檢舉

### 範圍

| 模組 | 職責 |
|------|------|
| `core/dependencies.py` | 取得目前用戶：Cookie + CSRF／Bearer 雙模式、黑名單、全局失效、停權、管理員 |
| `core/cookie_utils.py` | 認證 Cookie 的屬性與清除 |
| `core/utils.py` | Email 遮罩 |
| `services/verification_limiter.py` | 驗證碼嘗試限制（5 次鎖 15 分鐘） |
| `services/token_invalidator.py` | 密碼變更後使舊 Token 全局失效 |
| `services/photo_moderation.py` | 照片審核、統計、申訴還原 |
| `services/account_cleanup.py` | 刪除帳號寬限期到期後的清理 |
| `services/pass_cleanup.py` | 過期跳過記錄清理 |
| `api/messages.py` | 聊天 REST API（記錄、對話列表、已讀、刪除、上傳圖片） |
| `api/safety.py` | 封鎖與檢舉 |
| `api/photo_moderation.py` | 照片審核管理 API |

`api/` 三個模組要先用 `scripts/mutmut_unwrap_routes.py` 建立副本才能產生變異體（見「執行方式」）。

### 結果

- **基準線**：導入前的程式與測試；`api/` 三個模組以改寫路由的副本測量
- **改善後**：目前的程式與測試。刪除 `get_cookie_value`、移除不可能走到的分支與未使用參數後共 1845 個變異體
- 分數計算同第一批（timeout 算 killed：`api.messages` 改善後有 6 個 timeout，皆為迴圈條件被改壞後無法結束）

| 模組 | 基準線 變異體 | killed / survived / no tests | 分數 | 改善後 變異體 | killed / survived / no tests | 分數 |
|------|------:|------|-----:|------:|------|-----:|
| `core.dependencies` | 174 | 73 / 101 / 0 | 42.0% | 174 | 174 / 0 / 0 | 100.0% |
| `core.cookie_utils` | 109 | 32 / 70 / 7 | 31.4% | 102 | 98 / 4 / 0 | 96.1% |
| `core.utils` | 29 | 9 / 20 / 0 | 31.0% | 27 | 24 / 3 / 0 | 88.9% |
| `services.verification_limiter` | 85 | 55 / 30 / 0 | 64.7% | 85 | 81 / 4 / 0 | 95.3% |
| `services.token_invalidator` | 48 | 23 / 25 / 0 | 47.9% | 48 | 31 / 17 / 0 | 64.6% |
| `services.photo_moderation` | 407 | 262 / 130 / 15 | 66.8% | 405 | 366 / 24 / 15 | 93.8% |
| `services.account_cleanup` | 76 | 29 / 19 / 28 | 60.4% | 76 | 50 / 26 / 0 | 65.8% |
| `services.pass_cleanup` | 42 | 12 / 2 / 28 | 85.7% | 42 | 23 / 19 / 0 | 54.8% |
| `api.messages` | 541 | 423 / 118 / 0 | 78.2% | 538 | 508 / 30 / 0 | 94.4% |
| `api.safety` | 268 | 206 / 62 / 0 | 76.9% | 268 | 265 / 3 / 0 | 98.9% |
| `api.photo_moderation` | 80 | 59 / 21 / 0 | 73.8% | 80 | 78 / 2 / 0 | 97.5% |
| **合計** | **1859** | 1183 / 598 / 78 | **66.4%** | **1845** | 1698 / 132 / 15 | **92.8%** |

整體從 **66.4% → 92.8%**：存活者從 598 個降到 132 個，沒有任何測試執行到的從 78 個降到 15 個
（剩下的 15 個是沒有呼叫端的預留介面，見下方「刻意保留」）。

`pass_cleanup` 與 `account_cleanup` 的分數看起來沒有進步甚至下降，原因是基準線有 28 個 `no tests`
（背景任務的啟動、停止與迴圈完全沒有測試），不計入分數；補上測試後，這些函式裡只改 log 文字的變異體
都成為存活者計入分母。兩個模組剩下的 45 個存活者中，除了 5 個等價或微秒級邊界，其餘 40 個都是 log。

`core.dependencies` 基準線只有 42.0%：每個拒絕分支只測了狀態碼，訊息、`WWW-Authenticate` header、
CSRF 缺少 header 或缺少 Cookie 的區別都沒有測。

### 找到的 bug（已修正）

| # | 位置 | 問題 | 怎麼發現的 |
|---|------|------|-----------|
| 7 | 聊天 API 4 個端點、處理檢舉、查詢信任分數紀錄、刪除照片 | ID 以 `str` 接收後直接查資料庫，格式錯誤時 asyncpg 拋 `DataError`，回 **500**。改用 `uuid.UUID` 參數，由 FastAPI 回 422（有效 ID 行為不變） | 補聊天 API 授權測試時，以無效 ID 試打各端點 |
| 8 | `core/utils.mask_email`、`PhotoModerationService._mask_email` | `@` 前為空字串時 `local[0]` 拋 `IndexError`；docstring 的範例與實際輸出不符，且有多餘的條件（`len <= 1 or len <= 3`） | `mask_email` 的變異體全數存活，補測試時發現 |
| 9 | `docs/SECURITY.md` | 寫 CSRF 驗證在 `core/csrf.py`、且 GET/HEAD/OPTIONS 豁免。實際上 `csrf.py` 從未被使用，驗證在 `get_current_user`，Cookie 認證的 GET 也要驗證 | `csrf.py` 沒有任何呼叫端 |

### 名不符實的測試（已修正）

| 測試 | 問題 |
|------|------|
| `test_logout_clears_cookies` | 只有註解「驗證 Cookie 被清除」，**沒有任何斷言**；`clear_auth_cookies` 的 23 個變異體全數存活。refresh token 的 path 若寫錯，瀏覽器根本不會刪除該 Cookie |
| `test_approve_not_owned_photo_no_restore` | 測「申訴人不是照片擁有者時不還原」，但沒有 mock 隔離檔，實際是因「檔案不存在」才不還原；拿掉歸屬檢查也會通過 |
| 照片審核、CSRF、封鎖、檢舉、聊天的錯誤訊息 | `"無效" in message` 這類斷言，訊息被改成 `XX無效的審核狀態XX` 也會通過 |

### 補上的缺口

| 模組 | 原本沒有測到的行為 |
|------|-------------------|
| api/messages | **只能存取自己、且進行中的配對**：拿掉「配對 ID 相符」或「是配對成員」的條件時，原本的測試都不會失敗（只要自己有任何一個配對，就能讀取或標記別人配對的訊息）；已解除的配對；批次已讀只標記指定、未刪除的訊息；全部已讀只限本配對、不覆寫既有已讀時間、回條的時間帶時區；同一時間的訊息分頁；總數不含其他配對與已刪除訊息；對話列表各自的最後一則與未讀數、排序、主頭像、跳過停用的對方而不中斷；上傳超過一個區塊（64KB）的內容完整、WebP、大小上限邊界、儲存失敗 |
| api/safety | 只能解除**自己**的封鎖（拿掉條件可刪除別人的封鎖）；別人的封鎖或舉報不影響自己；配對中任一方封鎖都取消配對；封鎖列表內容與排序；五種舉報類型；只有處理中的舉報算重複 |
| api/photo_moderation | 分頁與篩選參數確實生效；記錄審核者；回應的 photo_id |
| core/dependencies | 每個拒絕分支的狀態碼、訊息與 `WWW-Authenticate`；Cookie 優先於 Bearer；CSRF header 或 Cookie 任一缺少；缺少 `iat` 的 Token 視為最早簽發 |
| core/cookie_utils | HttpOnly、Secure、SameSite、Domain、Max-Age，refresh token 只送往 `/api/auth`；清除時 path／domain 與設置時相同 |
| verification_limiter | 原本沒有單元測試：首次失敗才設 TTL（否則計數永不過期）、剩餘次數逐次扣減、鎖定的 key／值／TTL、驗證成功清除計數 |
| token_invalidator | 寫入帶 7 天 TTL（否則 key 永不過期）、同一秒簽發的 Token 仍有效、無 Redis 或故障時拒絕 |
| photo_moderation | 審核日誌逐欄位；統計與審核時間以 UTC 計算（模擬 UTC+8 主機）；「今日」從 00:00:00 起算；分頁依上傳時間；詳情欄位；申訴還原的歸屬檢查與完整度重算 |
| account_cleanup / pass_cleanup | 寬限期與保留期邊界，寬限期以 UTC 計算（在 UTC+8 主機誤用 `now()` 會提早 8 小時永久刪除帳號）；不論是配對的 user1 或 user2，聊天圖片目錄都清除；清除 Redis key；單筆失敗不影響其他帳號；未注入 session 的正式環境路徑；背景任務 |

### 依測量結果整理的程式碼

**已刪除**：`core/csrf.py`（從未被使用）、`cookie_utils.get_cookie_value`（從未被使用）、對話列表不可能走到的 `"Unknown"` 預設名稱、
`PhotoModerationService._log_moderation` 未使用的 `db` 參數（與第一批內容審核的情況相同）。
另外把已被 Starlette 標為棄用的 `HTTP_413_REQUEST_ENTITY_TOO_LARGE` 換成同值的 `HTTP_413_CONTENT_TOO_LARGE`

**刻意保留**：

- `PhotoModerationService.auto_moderate`、`process_auto_moderation_result`：沒有呼叫端（`no tests`），但註明為串接第三方圖片審核的預留介面
- `upload_chat_image` 以 64KB 分塊讀取：結果與一次讀完相同，用意是限制記憶體用量
- `mark_messages_as_read` 只在有更新時 commit：沒有更新時 commit 也不會改變任何資料

**建議但未修改**：

- `LoginLimiter` 與 `VerificationLimiter` 除了 key 前綴與 log 文字外完全相同，可以合併成一個參數化的類別
- `mask_email` 與 `PhotoModerationService._mask_email` 的遮罩規則不同（`us***r@` 與 `u***r@`），管理後台的舉報列表與照片審核列表顯示方式不一致

### 剩餘存活者

| 類別 | 數量 | 說明與例子 |
|------|-----:|------|
| 日誌與錯誤訊息文字 | 74 | `logger.info(...)` 的內容與參數；只決定要不要記 warning 的條件（檔案搬移失敗時） |
| 語意等價 | 40 | `func.count(None)` 即 `count(*)`；`join` 省略條件（由外鍵推得）；結果會再排序的 `order_by`；`split("@")` 與 `rsplit`（合法 email 只有一個 `@`）；空字串 Domain 本來就不會輸出；`httponly=None`（falsy）；naive `now().timestamp()` 與 UTC 相同；`break` 與 `return`；只在有更新時 commit；欄位預設值 `"PENDING"`；照片固定存成 `.jpg`，`FileResponse` 推得的 media type 相同；上傳的檔名不會用到（副檔名依 content type） |
| 效能或資源取捨 | 10 | 64KB 分塊讀取與一次讀完；`limit + 1` 與 `+ 2`；多查無關的資料再以 id 取用 |
| 防禦性程式碼 | 4 | `created_at` 為 NULL 的分支（有 server default）；照片的個人檔案不存在（外鍵 CASCADE） |
| 微秒／次秒級時間邊界 | 3 | 過期判斷 `<` 與 `<=`、Redis TTL 剛好為 0 |
| 公開介面的預設值 | 1 | `get_pending_photos` 的 `page_size=20`（API 一律明確傳入） |

同第一批，這些不補測試。

---

## 建議

- **不建議放進每次 CI**：第一批 9 個模組完整跑一次在 4 核心約 5 小時；第二批的認證依賴、Cookie、
  `mask_email` 幾乎每個 API 測試都會執行到，每個存活的變異體都要跑完 250–330 個測試。
  修改這些模組時，用 `mutmut run "app.services.<模組>.*"` 只跑該模組即可
- **測試速度**：測試改用 4 rounds 的 bcrypt（正式環境仍是 12），資料表每個 session 只建立一次、
  測試結束以 TRUNCATE 清空，API 測試約快 25%
- **先確認測試穩定**：結果裡若有「只改 log 卻被 killed」的變異體，代表有測試會隨機失敗，分數不可信
- **授權條件要用「自己也有其他資料」的情境測**：只用「完全沒有配對的人」測權限，拿掉「是不是這個配對」的條件也不會失敗
- **寫測試時避開這次找到的模式**：只用 `in`／`len > 0` 的弱斷言、包在 `if` 裡的斷言、`except Exception: skip`、
  只有註解沒有斷言、靠「檔案不存在」等其他條件才成立的前提、
  靠插入順序或隨機 UUID 才成立的前提、離邊界太遠的測試值（25 小時測不出 24 小時的期限、整數分數測不出四捨五入）、
  不清除的共享狀態（Redis 計數、class 屬性）
- **涉及時間的邏輯**：凍結 `datetime.now`，並模擬非 UTC 主機（例如 UTC+8），否則 `now()` 與 `now(UTC)` 的錯誤在 CI 上看不出來
