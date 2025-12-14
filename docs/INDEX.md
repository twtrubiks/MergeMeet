# MergeMeet 文檔索引

文檔已整理至結構化目錄，方便查找和維護。

## 📂 文檔結構總覽

```
mergemeet/
├── README.md                  # 項目總覽
├── QUICKSTART.md              # 快速啟動指南
├── CLAUDE.md                  # 開發指南（API routing、Git 規範等）
├── ARCHITECTURE.md            # 系統架構文檔
├── backend/SECURITY.md        # 安全策略
└── docs/
    ├── testing/               # 測試相關指南
    ├── reports/               # 測試報告
    └── archived/              # 歷史文檔歸檔
        ├── bug-fixes/         # Bug 修復記錄
        └── reviews/           # 代碼審查報告
```

---

## 🚀 快速導航

### 新手入門（必讀）
1. [README.md](../README.md) - 了解項目概況
2. [QUICKSTART.md](../QUICKSTART.md) - 5 分鐘快速啟動
3. [CLAUDE.md](../CLAUDE.md) - 開發規範與注意事項
4. [ARCHITECTURE.md](../ARCHITECTURE.md) - 系統架構深入解析

---

## 🧪 測試文檔

### 測試指南
- [TESTING_GUIDE.md](testing/TESTING_GUIDE.md) - 自動化測試指南
- [MANUAL_TESTING_GUIDE.md](testing/MANUAL_TESTING_GUIDE.md) - 手動測試指南
- [README_TEST_SETUP.md](testing/README_TEST_SETUP.md) - 測試環境設置
- [FRONTEND_UNIT_TEST_PLAN.md](testing/FRONTEND_UNIT_TEST_PLAN.md) - 前端單元測試計劃
- [COVERAGE_SUMMARY.md](testing/COVERAGE_SUMMARY.md) - 測試覆蓋率總結

### 功能規劃文檔
- [NOTIFICATION_PERSISTENCE_PLAN.md](NOTIFICATION_PERSISTENCE_PLAN.md) - 通知持久化功能 ✅ 已完成

### 測試報告
- [MANUAL_TEST_REPORT_2025-11-14.md](reports/MANUAL_TEST_REPORT_2025-11-14.md) - 手動測試報告
- [FRONTEND_MANUAL_TEST_REPORT_2025-11-14.md](reports/FRONTEND_MANUAL_TEST_REPORT_2025-11-14.md) - 前端手動測試
- [WEEK4_CHAT_TEST_REPORT.md](reports/WEEK4_CHAT_TEST_REPORT.md) - Week 4 聊天功能測試
- [WEEK4_ADVANCED_FEATURES_TEST_REPORT_2025-11-14.md](reports/WEEK4_ADVANCED_FEATURES_TEST_REPORT_2025-11-14.md) - Week 4 高級功能測試
- [WEEK5_SAFETY_TEST_REPORT.md](reports/WEEK5_SAFETY_TEST_REPORT.md) - Week 5 安全功能測試
- [WEEK5_BROWSER_TEST_REPORT_2025-11-16.md](reports/WEEK5_BROWSER_TEST_REPORT_2025-11-16.md) - Week 5 瀏覽器測試

---

## 🗄️ 歷史文檔歸檔

### Bug 修復記錄（12 份）
存放於 [archived/bug-fixes/](archived/bug-fixes/)

主要內容：
- Trailing Slash 修復系列
- WebSocket 修復驗證
- Vitest 升級與修復
- 訊息刪除同步修復
- SQLAlchemy DetachedInstance 修復
- 配對功能調試指南

### 代碼審查報告（4 份）
存放於 [archived/reviews/](archived/reviews/)

- Code Review Report 2025-11-16
- Deep Analysis Report 2025-11-16
- Git Commit Analysis 2025-11-16
- Git Pull Review Report 2025-11-16

---

## 🔒 安全文檔

- [backend/SECURITY.md](../backend/SECURITY.md) - CSRF 保護策略

---

## 📊 文檔統計

- **核心文檔**: 4 份（根目錄）
- **測試指南**: 5 份
- **測試報告**: 6 份
- **Bug 修復記錄**: 12 份
- **審查報告**: 4 份
- **總計**: 31 份文檔

---

## 💡 文檔使用建議

### 對於新加入的開發者
1. 閱讀 README.md 了解項目
2. 按照 QUICKSTART.md 啟動項目
3. 查看 CLAUDE.md 學習開發規範
4. 需要深入了解架構時參考 ARCHITECTURE.md

### 對於測試人員
1. 查看 `docs/testing/` 下的測試指南
2. 參考 `docs/reports/` 下的歷史測試報告

### 對於維護人員
1. 歷史 Bug 修復記錄在 `docs/archived/bug-fixes/`
2. 代碼審查報告在 `docs/archived/reviews/`

---

## 📝 文檔維護原則

1. **核心文檔保持簡潔**：根目錄只保留必要的核心文檔
2. **測試文檔分類存放**：指南與報告分開
3. **歷史文檔及時歸檔**：Bug 修復和審查報告歸檔保存
4. **命名規範統一**：使用 `PURPOSE_YYYY-MM-DD.md` 格式
5. **及時更新索引**：新增文檔後更新本索引

---

最後更新：2025-12-14
