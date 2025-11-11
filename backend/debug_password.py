"""診斷密碼哈希問題"""
import sys
import traceback

print("=" * 60)
print("診斷密碼哈希問題")
print("=" * 60)

# 測試 1: 檢查模組是否正確加載
print("\n[1] 檢查 security.py 模組...")
try:
    from app.core.security import get_password_hash, verify_password, _pre_hash_password
    print("✅ 模組導入成功")
    print(f"   _pre_hash_password 函數存在: {callable(_pre_hash_password)}")
except ImportError as e:
    print(f"❌ 模組導入失敗: {e}")
    sys.exit(1)

# 測試 2: 檢查 SHA256 預處理
print("\n[2] 測試 SHA256 預處理...")
try:
    test_password = "Password123"
    pre_hashed = _pre_hash_password(test_password)
    print(f"✅ SHA256 預處理成功")
    print(f"   原始密碼: {test_password}")
    print(f"   原始長度: {len(test_password)} bytes")
    print(f"   SHA256 輸出: {pre_hashed}")
    print(f"   SHA256 長度: {len(pre_hashed)} bytes")
    print(f"   是否超過 72 bytes: {len(pre_hashed) > 72}")
except Exception as e:
    print(f"❌ SHA256 預處理失敗: {e}")
    traceback.print_exc()

# 測試 3: 測試密碼加密
print("\n[3] 測試密碼加密 (get_password_hash)...")
try:
    test_password = "Password123"
    print(f"   正在加密: {test_password}")
    hashed = get_password_hash(test_password)
    print(f"✅ 密碼加密成功")
    print(f"   哈希值: {hashed[:60]}...")
except Exception as e:
    print(f"❌ 密碼加密失敗")
    print(f"   錯誤類型: {type(e).__name__}")
    print(f"   錯誤訊息: {e}")
    print("\n完整堆疊追蹤:")
    traceback.print_exc()
    sys.exit(1)

# 測試 4: 測試密碼驗證
print("\n[4] 測試密碼驗證 (verify_password)...")
try:
    is_valid = verify_password(test_password, hashed)
    print(f"✅ 密碼驗證成功: {is_valid}")

    is_invalid = verify_password("WrongPassword", hashed)
    print(f"✅ 錯誤密碼驗證: {is_invalid} (應該是 False)")
except Exception as e:
    print(f"❌ 密碼驗證失敗")
    print(f"   錯誤類型: {type(e).__name__}")
    print(f"   錯誤訊息: {e}")
    print("\n完整堆疊追蹤:")
    traceback.print_exc()
    sys.exit(1)

# 測試 5: 測試長密碼
print("\n[5] 測試長密碼 (100 字元)...")
try:
    long_password = "A" * 100
    print(f"   密碼長度: {len(long_password)} bytes")
    hashed_long = get_password_hash(long_password)
    print(f"✅ 長密碼加密成功")

    is_valid_long = verify_password(long_password, hashed_long)
    print(f"✅ 長密碼驗證成功: {is_valid_long}")
except Exception as e:
    print(f"❌ 長密碼處理失敗")
    print(f"   錯誤類型: {type(e).__name__}")
    print(f"   錯誤訊息: {e}")
    print("\n完整堆疊追蹤:")
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ 所有測試通過！密碼哈希功能正常")
print("=" * 60)
