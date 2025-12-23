# MergeMeet 文檔索引

文檔已整理至結構化目錄，方便查找和維護。

## 文檔結構總覽

```
mergemeet/
├── README.md                  # 項目總覽（含快速開始）
├── CLAUDE.md                  # 開發指南（API routing、Git 規範等）
└── docs/
    ├── INDEX.md               # 本索引
    ├── ARCHITECTURE.md        # 系統架構文檔
    ├── SECURITY.md            # 安全策略與防護機制
    ├── KNOWN_ISSUES.md        # 已知問題與技術債務
    ├── ROADMAP.md             # 技術路線圖
    ├── testing/               # 測試相關指南
    └── 管理員設置指南.md       # 管理員帳號設置
```

---

## 快速導航

### 新手入門（必讀）
1. [README.md](../README.md) - 了解項目概況與快速開始
2. [CLAUDE.md](../CLAUDE.md) - 開發規範與注意事項
3. [ARCHITECTURE.md](ARCHITECTURE.md) - 系統架構深入解析

---

## 專案管理

- [KNOWN_ISSUES.md](KNOWN_ISSUES.md) - 已知問題與技術債務
- [ROADMAP.md](ROADMAP.md) - 技術路線圖

---

## 測試文檔

- [TESTING_GUIDE.md](testing/TESTING_GUIDE.md) - 自動化測試指南
- [MANUAL_TESTING_GUIDE.md](testing/MANUAL_TESTING_GUIDE.md) - 手動測試指南
- [README_TEST_SETUP.md](testing/README_TEST_SETUP.md) - 測試環境設置

---

## 技術參考文檔

- [TRUST_SCORE_SYSTEM.md](TRUST_SCORE_SYSTEM.md) - 信任分數系統
- [CURSOR_PAGINATION.md](CURSOR_PAGINATION.md) - Cursor 分頁技術說明
- [MATCHING_ALGORITHM.md](MATCHING_ALGORITHM.md) - 配對算法說明

---

## 安全與管理文檔

- [SECURITY.md](SECURITY.md) - 安全策略與防護機制
- [管理員設置指南.md](管理員設置指南.md) - 管理員帳號創建與密碼設置

---

## 文檔統計

- **核心文檔**: 2 份（根目錄：README、CLAUDE）
- **架構與安全**: 2 份（ARCHITECTURE、SECURITY）
- **專案管理**: 2 份（KNOWN_ISSUES、ROADMAP）
- **技術參考**: 3 份
- **測試指南**: 3 份
- **管理文檔**: 1 份
- **總計**: 13 份

---

## 文檔使用建議

### 對於新加入的開發者
1. 閱讀 README.md 了解項目並啟動開發環境
2. 查看 CLAUDE.md 學習開發規範
3. 需要深入了解架構時參考 ARCHITECTURE.md

### 對於測試人員
1. 查看 `docs/testing/` 下的測試指南

### 對於系統管理員
1. 查看 [管理員設置指南.md](管理員設置指南.md) 設置管理員帳號

---

最後更新：2025-12-23
