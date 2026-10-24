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

# 全部目標模組（4 核心約需 3–4 小時）
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

<!-- RESULTS -->
