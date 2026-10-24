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

測試本身也必須在重複執行時穩定：mutmut 會在同一個 slot 連續跑上百次測試。`conftest.py` 的 `client`
fixture 在每個測試前清除登入失敗、驗證碼嘗試、Email 發送次數等限流計數；否則固定 email 的計數會跨 session
累積（第 5 次就被鎖定回 429），測試隨機失敗，變異體被誤判為 killed。

**檢查誤判的方法**：只改 log 文字的變異體不可能被測試抓到，若結果是 killed，就代表有測試在隨機失敗。

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

## 建議

- **不建議放進每次 CI**：9 個模組完整跑一次在 4 核心約 5 小時（內容審核與配對的變異體會觸發大量 API 整合測試）。
  修改這些模組時，用 `mutmut run "app.services.<模組>.*"` 只跑該模組即可
- **先確認測試穩定**：結果裡若有「只改 log 卻被 killed」的變異體，代表有測試會隨機失敗，分數不可信
- **寫測試時避開這次找到的模式**：只用 `in`／`len > 0` 的弱斷言、包在 `if` 裡的斷言、`except Exception: skip`、
  靠插入順序或隨機 UUID 才成立的前提、離邊界太遠的測試值（25 小時測不出 24 小時的期限、整數分數測不出四捨五入）、
  不清除的共享狀態（Redis 計數、class 屬性）
- **涉及時間的邏輯**：凍結 `datetime.now`，並模擬非 UTC 主機（例如 UTC+8），否則 `now()` 與 `now(UTC)` 的錯誤在 CI 上看不出來
