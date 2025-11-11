-- 快速修復 is_active 欄位問題
-- 直接在 PostgreSQL 中執行此腳本

-- 1. 將所有現有用戶的 is_active 設為 TRUE（如果是 NULL）
UPDATE users SET is_active = TRUE WHERE is_active IS NULL;

-- 2. 設置 is_active 欄位的預設值為 TRUE
ALTER TABLE users ALTER COLUMN is_active SET DEFAULT TRUE;
ALTER TABLE users ALTER COLUMN is_active SET NOT NULL;

-- 3. 同樣處理 email_verified 欄位
UPDATE users SET email_verified = FALSE WHERE email_verified IS NULL;
ALTER TABLE users ALTER COLUMN email_verified SET DEFAULT FALSE;
ALTER TABLE users ALTER COLUMN email_verified SET NOT NULL;

-- 4. 處理 is_admin 欄位
UPDATE users SET is_admin = FALSE WHERE is_admin IS NULL;
ALTER TABLE users ALTER COLUMN is_admin SET DEFAULT FALSE;
ALTER TABLE users ALTER COLUMN is_admin SET NOT NULL;

-- 驗證結果
SELECT id, email, is_active, email_verified, is_admin
FROM users
ORDER BY created_at DESC
LIMIT 10;
