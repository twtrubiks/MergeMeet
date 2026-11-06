# 變異測試（Mutation Testing）

> 覆蓋率只回答「這行有沒有被執行」，變異測試回答「這行**寫錯了**測試抓不抓得到」。

mutmut 會自動對程式碼做小幅修改（`<` 改成 `<=`、`and` 改成 `or`、刪掉一個參數…），
每個修改後的版本稱為一個**變異體（mutant）**，再對它跑測試：

| 結果 | 意義 |
|------|------|
| 🎉 killed | 有測試失敗 → 測試抓得到這個錯誤 |
| 🙁 survived | 測試全過 → 這種錯誤目前不會被發現 |
| 🫥 no tests | 沒有任何測試執行到這段程式碼 |

存活者不一定都是缺口：只改 log 文字這類與原碼語意等價的變異體，需要人工判讀後略過。

## 執行方式

前置需求：

- PostgreSQL + PostGIS、Redis（`docker compose up -d`），且資料庫使用者可 `CREATE DATABASE`
- `pip install -r requirements-dev.txt`（含 `mutmut>=3.8`）
- `backend/.env` 已設定 `TEST_DATABASE_URL`

```bash
cd backend

# 全部目標模組（約數小時，不建議放進 CI）
mutmut run --max-children 4

# 只跑特定模組 / 函式（支援 fnmatch 萬用字元）
mutmut run "app.services.login_limiter.*"

mutmut results            # 列出存活者
mutmut show <mutant 名稱>  # 顯示該變異體的 diff
mutmut browse             # 互動式瀏覽
```

結果存在 `backend/mutants/`（已加入 `.gitignore`），重新執行會跳過已有結果的變異體。
**修改測試或 `only_mutate` 之後請刪除 `mutants/`**，否則新加入的模組不會產生變異體。

### API 路由模組

mutmut 會跳過有裝飾器的函式，所以 `api/` 模組預設不會產生變異體。
`scripts/mutmut_unwrap_routes.py` 會建立一份 backend 副本，把路由改寫成「定義後再註冊」：

```bash
cd backend
python scripts/mutmut_unwrap_routes.py /tmp/mm-api app/api/safety.py app/api/messages.py
cd /tmp/mm-api && mutmut run --max-children 4
```

## 設定

`backend/pyproject.toml` 的 `[tool.mutmut]`：

| 設定 | 說明 |
|------|------|
| `only_mutate` | 目標模組 |
| `process_isolation = "forkserver"` | 每個 pytest session 都從乾淨行程 fork，避免單例的 Redis 連線綁在已關閉的 event loop |
| `pytest_add_cli_args` | 載入 `tests/mutmut_isolation.py`：每個 worker 使用獨立的測試庫 `<測試庫>_mm<slot>` 與 Redis db |
| `pytest_add_cli_args_test_selection` | 整個 `tests/`，排除 `test_rate_limit.py`（slowapi 在 import 時就綁定 Redis db 0，無法隔離） |

需要隔離是因為 mutmut 以多個 worker 平行跑測試，而本專案的測試共用同一個測試庫與 Redis，
平行執行會互相刪表、殺連線，把變異體誤判為 killed。

**檢查結果是否可信**：只改 log 文字的變異體不可能被測試抓到，若結果是 killed，代表有測試在隨機失敗。

## 寫測試時要避開的模式

以下測試在覆蓋率報告上都算「有測到」，但程式寫錯也不會失敗：

- **沒有斷言**，或斷言包在 `if` 裡（`if len(results) > 0: assert ...`）
- **弱斷言**：`"***" in 結果`、`"無效" in message`
- **`except Exception: pytest.skip`**：`AssertionError` 也被吞成 skip
- **離邊界太遠**：25 小時測不出 24 小時的期限、整數分數測不出四捨五入
- **授權只用「完全沒有資料的人」測**：要用「自己也有其他配對」的情境
- **時間邏輯沒有凍結時間**：要模擬非 UTC 主機，否則 `now()` 與 `now(UTC)` 的錯誤看不出來
- **不清除的共享狀態**：Redis 計數、class 屬性
