#!/usr/bin/env python3
"""測試內容審核機制"""
import sys
import os

# 動態設定路徑，指向 backend 目錄
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, '../..'))
sys.path.insert(0, backend_dir)

from app.services.content_moderation import ContentModerationService

# 測試案例
test_cases = [
    {
        "content": "你好，很高興認識你！",
        "expected": True,
        "description": "正常訊息"
    },
    {
        "content": "想要看色情影片嗎？",
        "expected": False,
        "description": "包含敏感詞：色情"
    },
    {
        "content": "加我LINE: abc123",
        "expected": False,
        "description": "包含 LINE ID"
    },
    {
        "content": "我的電話是 0912345678",
        "expected": False,
        "description": "包含電話號碼"
    },
    {
        "content": "請匯款到這個帳號",
        "expected": False,
        "description": "包含敏感詞：匯款"
    },
    {
        "content": "點擊這個連結 http://scam.com",
        "expected": False,
        "description": "包含 URL"
    },
    {
        "content": "這是正常的對話內容，沒有任何問題",
        "expected": True,
        "description": "正常訊息"
    }
]

print("=" * 60)
print("內容審核機制測試")
print("=" * 60)

passed = 0
failed = 0

for i, test in enumerate(test_cases, 1):
    content = test["content"]
    expected = test["expected"]
    description = test["description"]

    is_safe, violations = ContentModerationService.check_content(content)

    status = "✅ PASS" if is_safe == expected else "❌ FAIL"
    if is_safe == expected:
        passed += 1
    else:
        failed += 1

    print(f"\n測試 {i}: {description}")
    print(f"  內容: {content}")
    print(f"  預期安全: {expected}, 實際安全: {is_safe}")
    if violations:
        print(f"  違規項目: {', '.join(violations)}")
    print(f"  結果: {status}")

print("\n" + "=" * 60)
print(f"測試結果: {passed} 通過, {failed} 失敗")
print("=" * 60)
