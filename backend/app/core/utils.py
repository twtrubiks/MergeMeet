"""通用工具函數"""


def mask_email(email: str) -> str:
    """
    Email 脫敏處理，保護用戶隱私

    示例:
    - user@example.com -> us***@example.com
    - a@test.com -> a***@test.com
    - longname@domain.com -> lo***e@domain.com

    Args:
        email: 原始 email 地址

    Returns:
        脫敏後的 email 地址
    """
    if not email or '@' not in email:
        return '***@***'

    local, domain = email.split('@', 1)

    if len(local) <= 1:
        masked_local = local[0] + '***'
    elif len(local) <= 3:
        masked_local = local[0] + '***'
    else:
        # 保留前兩個和最後一個字符，中間替換為 ***
        masked_local = local[:2] + '***' + local[-1]

    return f"{masked_local}@{domain}"
