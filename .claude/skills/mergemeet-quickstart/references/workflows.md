# 開發工作流程

> 僅列出專案規範。通用 Git/TDD 知識請直接詢問 Claude。

---

## 分支命名

```
feature/   - 新功能      例: feature/user-profile-photos
fix/       - 錯誤修復    例: fix/login-404-error
refactor/  - 重構        例: refactor/auth-service
docs/      - 文檔更新    例: docs/api-guide
test/      - 測試相關    例: test/profile-coverage
```

---

## Commit Message

使用 Conventional Commits 格式：

```
<type>: <subject>

類型:
feat      新功能
fix       錯誤修復
refactor  重構
style     格式調整
test      測試相關
docs      文檔更新
chore     維護任務
perf      效能優化
```

範例：
```bash
git commit -m "feat: 新增照片上傳功能"
git commit -m "fix: 修復 API 尾隨斜線導致的 404 錯誤"
git commit -m "feat!: 更新認證機制為 JWT（破壞性變更）"
```

---

## 測試目標

| 指標 | 目標 |
|------|------|
| 總體覆蓋率 | >80% |
| 關鍵業務邏輯 | >90% |

```bash
# 後端
pytest --cov=app --cov-report=term-missing

# 前端
npm run test:coverage
```
