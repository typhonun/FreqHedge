# backend/app/services/mail_service.py
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from config.settings import (
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
    SMTP_FROM, SMTP_FROM_NAME, FRONTEND_URL,
)

conf = ConnectionConfig(
    MAIL_USERNAME=SMTP_USER,
    MAIL_PASSWORD=SMTP_PASSWORD,
    MAIL_FROM=SMTP_FROM,
    MAIL_FROM_NAME=SMTP_FROM_NAME,
    MAIL_PORT=SMTP_PORT,
    MAIL_SERVER=SMTP_HOST,
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)


class MailService:

    @staticmethod
    async def _send(to: str, subject: str, html: str):
        msg = MessageSchema(
            subject=subject,
            recipients=[to],
            body=html,
            subtype=MessageType.html,
        )
        await FastMail(conf).send_message(msg)

    @staticmethod
    async def send_reset_email(to: str, token: str):   # ★ async
        link = f"{FRONTEND_URL}/reset-password?token={token}"
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 520px;">
          <h2>重置密码</h2>
          <p>你正在请求重置密码，点击下方链接（30 分钟内有效）：</p>
          <p><a href="{link}" style="background:#2bbdf6;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;">重置密码</a></p>
          <p style="color:#888;font-size:12px;">如果这不是你的操作，请忽略此邮件。</p>
        </div>
        """
        await MailService._send(to, "重置密码 - DcaTp", html)

    @staticmethod
    async def send_verify_email(to: str, token: str):   # ★ async
        link = f"{FRONTEND_URL}/verify-email?token={token}"
        html = f"""
        <div style="font-family: Arial, sans-serif;">
          <h2>欢迎注册 DcaTp</h2>
          <p>点击验证邮箱：<a href="{link}">立即验证</a></p>
        </div>
        """
        await MailService._send(to, "验证邮箱 - DcaTp", html)