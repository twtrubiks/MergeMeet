-- 修復 users 表 schema - 添加缺少的欄位
-- 直接在 PostgreSQL 中執行此腳本

-- 添加 ban_reason 欄位（如果不存在）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'users' AND column_name = 'ban_reason'
    ) THEN
        ALTER TABLE users ADD COLUMN ban_reason TEXT;
    END IF;
END $$;

-- 添加 banned_until 欄位（如果不存在）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'users' AND column_name = 'banned_until'
    ) THEN
        ALTER TABLE users ADD COLUMN banned_until TIMESTAMP WITH TIME ZONE;
    END IF;
END $$;

-- 驗證結果
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'users'
AND column_name IN ('ban_reason', 'banned_until')
ORDER BY column_name;
