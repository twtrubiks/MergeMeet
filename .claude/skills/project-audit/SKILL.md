---
name: project-audit
description: 評估 MergeMeet 專案健康狀態時使用此 skill。協助檢查功能完整性、前後端一致性、潛在錯誤和用戶流程邏輯。適用於開發新功能前或 sprint 審查時。
---

# 專案審查

## 目的

檢查 MergeMeet 交友平台的健康狀態：功能完整性、前後端一致性、用戶流程邏輯。

---

## 快速檢查指令

```bash
# 後端 API 端點
grep -rh "@router\.\(get\|post\|put\|patch\|delete\)" backend/app/api/ \
  | grep -oE '@router\.[a-z]+\("[^"]*"' | sort | uniq

# 前端 API 呼叫
grep -rh "apiClient\.\(get\|post\|put\|patch\|delete\)" frontend/src/ \
  | grep -oE "apiClient\.[a-z]+\('[^']*'" | sort | uniq

# 執行測試
cd backend && pytest -v --cov=app
```

---

## 審查檢查清單

| 類別 | 檢查點 |
|------|--------|
| 認證 | 註冊、登入、Email 驗證、密碼重設 |
| 個人檔案 | 編輯、照片上傳、審核、興趣 |
| 探索 | 瀏覽候選人、喜歡/跳過、偏好設定 |
| 聊天 | 即時訊息、已讀狀態、內容審核 |
| 安全 | 封鎖、舉報、舉報記錄 |
| 通知 | 即時通知、通知中心 |
| 管理後台 | 儀表板、舉報處理、用戶管理 |

---

## 參考資料

| 主題 | 檔案 |
|------|------|
| 功能檢查表 | [feature-status.md](references/feature-status.md) |
| 前後端差異檢查 | [frontend-backend-gap.md](references/frontend-backend-gap.md) |
| E2E 測試指南 | [e2e-testing-guide.md](references/e2e-testing-guide.md) |

---

## 相關 Skills

- **mergemeet-quickstart** - 開發指南
- **backend-dev-fastapi** - 後端標準
- **frontend-dev-vue3** - 前端標準
