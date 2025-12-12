"""Email 發送服務

使用 aiosmtplib 進行非同步 Email 發送。
開發環境使用 Mailpit (localhost:1025)，生產環境可切換至 SendGrid/AWS SES。

使用範例：
    from app.services.email import EmailService

    # 發送密碼重置郵件
    await EmailService.send_password_reset_email(
        to_email="user@example.com",
        username="User",
        reset_token="abc123..."
    )
"""
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Email 發送服務"""

    @staticmethod
    async def send_email(
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        發送郵件

        Args:
            to_email: 收件人 Email
            subject: 郵件主旨
            html_content: HTML 內容
            text_content: 純文字內容 (選填，作為備用)

        Returns:
            bool: 是否成功發送

        Raises:
            不會拋出異常，失敗時會記錄錯誤並返回 False
        """
        try:
            # 建立 MIME 郵件
            message = MIMEMultipart("alternative")
            message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            message["To"] = to_email
            message["Subject"] = subject

            # 添加純文字版本 (備用)
            if text_content:
                part1 = MIMEText(text_content, "plain", "utf-8")
                message.attach(part1)

            # 添加 HTML 版本
            part2 = MIMEText(html_content, "html", "utf-8")
            message.attach(part2)

            # 發送郵件
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER if settings.SMTP_USER else None,
                password=settings.SMTP_PASSWORD if settings.SMTP_PASSWORD else None,
                use_tls=settings.SMTP_TLS,
            )

            logger.info(f"Email sent successfully to {to_email}: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}", exc_info=True)
            return False

    @staticmethod
    async def send_password_reset_email(
        to_email: str,
        username: str,
        reset_token: str
    ) -> bool:
        """
        發送密碼重置郵件

        Args:
            to_email: 收件人 Email
            username: 用戶名稱（用於個性化郵件）
            reset_token: 密碼重置 Token (32+ 字符)

        Returns:
            bool: 是否成功發送
        """
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        expire_minutes = settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES

        # HTML 郵件模板
        html_content = f"""  # noqa: E501
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f5f5f5; }}
        .container {{ max-width: 600px; margin: 20px auto; padding: 0; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 30px; text-align: center; border-radius: 12px 12px 0 0; }}
        .header h1 {{ margin: 0; font-size: 28px; font-weight: 600; }}
        .content {{ background: white; padding: 40px 30px; border-radius: 0 0 12px 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }}
        .button {{ display: inline-block; padding: 16px 32px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white !important; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px; margin: 24px 0; }}
        .button:hover {{ opacity: 0.9; }}
        .url-box {{ background: #f8f9fa; padding: 12px; border-radius: 6px; word-break: break-all; font-size: 14px; color: #666; margin: 16px 0; border: 1px solid #e9ecef; }}
        .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 16px; margin: 24px 0; border-radius: 0 8px 8px 0; }}
        .warning strong {{ color: #856404; }}
        .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 30px; padding: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 密碼重置</h1>
        </div>
        <div class="content">
            <p>Hi <strong>{username}</strong>,</p>
            <p>我們收到了您的密碼重置請求。請點擊下方按鈕重置您的密碼：</p>

            <div style="text-align: center;">
                <a href="{reset_url}" class="button">重置密碼</a>
            </div>

            <p>或複製以下鏈接到瀏覽器：</p>
            <div class="url-box">{reset_url}</div>

            <div class="warning">
                <p><strong>⚠️ 安全提醒：</strong></p>
                <ul style="margin: 8px 0; padding-left: 20px;">
                    <li>此鏈接將在 <strong>{expire_minutes} 分鐘</strong>後失效</li>
                    <li>如果您沒有請求重置密碼，請忽略此郵件</li>
                    <li>請勿將此鏈接分享給他人</li>
                </ul>
            </div>
        </div>
        <div class="footer">
            <p>© 2025 MergeMeet. All rights reserved.</p>
            <p>這是系統自動發送的郵件，請勿直接回覆。</p>
        </div>
    </div>
</body>
</html>
        """

        # 純文字版本
        text_content = f"""
Hi {username},

我們收到了您的密碼重置請求。

請複製以下鏈接到瀏覽器重置密碼：
{reset_url}

⚠️ 安全提醒：
- 此鏈接將在 {expire_minutes} 分鐘後失效
- 如果您沒有請求重置密碼，請忽略此郵件
- 請勿將此鏈接分享給他人

© 2025 MergeMeet
這是系統自動發送的郵件，請勿直接回覆。
        """

        return await EmailService.send_email(
            to_email=to_email,
            subject="🔐 MergeMeet - 密碼重置請求",
            html_content=html_content,
            text_content=text_content
        )

    @staticmethod
    async def send_verification_email(
        to_email: str,
        username: str,
        verification_code: str
    ) -> bool:
        """
        發送 Email 驗證郵件

        Args:
            to_email: 收件人 Email
            username: 用戶名稱
            verification_code: 6 位數驗證碼

        Returns:
            bool: 是否成功發送
        """
        html_content = f"""  # noqa: E501
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f5f5f5; }}
        .container {{ max-width: 600px; margin: 20px auto; padding: 0; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 30px; text-align: center; border-radius: 12px 12px 0 0; }}
        .header h1 {{ margin: 0; font-size: 28px; }}
        .content {{ background: white; padding: 40px 30px; border-radius: 0 0 12px 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }}
        .code {{ font-size: 36px; font-weight: bold; letter-spacing: 8px; text-align: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; padding: 24px; margin: 24px 0; border: 2px dashed #667eea; border-radius: 12px; }}
        .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 30px; padding: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✉️ Email 驗證</h1>
        </div>
        <div class="content">
            <p>Hi <strong>{username}</strong>,</p>
            <p>歡迎加入 MergeMeet！請使用以下驗證碼完成註冊：</p>
            <div class="code">{verification_code}</div>
            <p><strong>⚠️ 注意：</strong></p>
            <ul style="margin: 8px 0; padding-left: 20px;">
                <li>此驗證碼將在 <strong>10 分鐘</strong>後失效</li>
                <li>請勿將驗證碼分享給他人</li>
            </ul>
        </div>
        <div class="footer">
            <p>© 2025 MergeMeet. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
        """

        text_content = f"""
Hi {username},

歡迎加入 MergeMeet！

您的驗證碼是：{verification_code}

⚠️ 此驗證碼將在 10 分鐘後失效，請勿分享給他人。

© 2025 MergeMeet
        """

        return await EmailService.send_email(
            to_email=to_email,
            subject="✉️ MergeMeet - Email 驗證碼",
            html_content=html_content,
            text_content=text_content
        )
