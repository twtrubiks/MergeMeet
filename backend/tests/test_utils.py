"""通用工具函數測試"""

import pytest

from app.core.utils import mask_email


@pytest.mark.parametrize(
    ("email", "expected"),
    [
        ("longname@domain.com", "lo***e@domain.com"),
        ("user@example.com", "us***r@example.com"),
        ("abc@test.com", "a***@test.com"),
        ("a@test.com", "a***@test.com"),
        ("@test.com", "***@test.com"),
        ("", "***@***"),
        ("not-an-email", "***@***"),
    ],
)
def test_mask_email(email, expected):
    assert mask_email(email) == expected
