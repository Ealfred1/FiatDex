import httpx
import logging
from app.config import settings
from typing import Optional

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
logger = logging.getLogger(__name__)

class BrevoService:
    def __init__(self):
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": getattr(settings, "BREVO_API_KEY", "dummy"),
        }

    async def send_otp_email(self, email: str, full_name: str, otp_code: str) -> bool:
        payload = {
            "sender": {"name": getattr(settings, "BREVO_SENDER_NAME", "FiatDex"), "email": getattr(settings, "BREVO_SENDER_EMAIL", "noreply@fiatdex.app")},
            "to": [{"email": email, "name": full_name}],
            "subject": f"Your FiatDex verification code: {otp_code}",
            "htmlContent": self._otp_email_html(full_name, otp_code),
        }
        # If template configured, use template instead
        template_id = getattr(settings, "BREVO_OTP_TEMPLATE_ID", None)
        if template_id:
            payload = {
                "sender": {"name": settings.BREVO_SENDER_NAME, "email": settings.BREVO_SENDER_EMAIL},
                "to": [{"email": email, "name": full_name}],
                "templateId": template_id,
                "params": {"NAME": full_name, "OTP": otp_code},
            }

        async with httpx.AsyncClient() as client:
            try:
                logger.info(f"Sending OTP email to {email}")
                response = await client.post(BREVO_API_URL, json=payload, headers=self.headers)
                if response.status_code == 201:
                    logger.info(f"OTP email sent to {email}")
                    return True
                logger.warning(f"Brevo OTP email failed: {response.status_code}")
                return False
            except Exception as e:
                logger.error(f"Failed to send OTP email to {email}: {e}")
                return False

    async def send_password_reset_email(self, email: str, full_name: str, reset_token: str) -> bool:
        frontend_url = getattr(settings, "FRONTEND_BASE_URL", "https://app.fiatdex.app")
        reset_link = f"{frontend_url}/reset-password?token={reset_token}"
        payload = {
            "sender": {"name": getattr(settings, "BREVO_SENDER_NAME", "FiatDex"), "email": getattr(settings, "BREVO_SENDER_EMAIL", "noreply@fiatdex.app")},
            "to": [{"email": email, "name": full_name}],
            "subject": "Reset your FiatDex password",
            "htmlContent": self._password_reset_html(full_name, reset_link),
        }
        async with httpx.AsyncClient() as client:
            try:
                logger.info(f"Sending password reset email to {email}")
                response = await client.post(BREVO_API_URL, json=payload, headers=self.headers)
                if response.status_code == 201:
                    logger.info(f"Password reset email sent to {email}")
                    return True
                logger.warning(f"Brevo reset email failed: {response.status_code}")
                return False
            except Exception as e:
                logger.error(f"Failed to send reset email to {email}: {e}")
                return False

    async def send_welcome_email(self, email: str, full_name: str) -> bool:
        payload = {
            "sender": {"name": getattr(settings, "BREVO_SENDER_NAME", "FiatDex"), "email": getattr(settings, "BREVO_SENDER_EMAIL", "noreply@fiatdex.app")},
            "to": [{"email": email, "name": full_name}],
            "subject": "Welcome to FiatDex 🚀",
            "htmlContent": self._welcome_html(full_name),
        }
        async with httpx.AsyncClient() as client:
            try:
                logger.info(f"Sending welcome email to {email}")
                response = await client.post(BREVO_API_URL, json=payload, headers=self.headers)
                if response.status_code == 201:
                    logger.info(f"Welcome email sent to {email}")
                    return True
                logger.warning(f"Brevo welcome email failed: {response.status_code}")
                return False
            except Exception as e:
                logger.error(f"Failed to send welcome email to {email}: {e}")
                return False

    def _otp_email_html(self, name: str, otp: str) -> str:
        return f"""
        <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px">
          <h2 style="color:#1a1a2e">FiatDex Verification</h2>
          <p>Hi {name}, here is your verification code:</p>
          <div style="font-size:42px;font-weight:bold;letter-spacing:8px;
                      text-align:center;padding:24px;background:#f4f4f8;
                      border-radius:12px;color:#1a1a2e">{otp}</div>
          <p style="color:#888;margin-top:16px">Expires in <strong>10 minutes</strong>.</p>
          <p style="color:#bbb;font-size:12px">If you didn't request this, ignore this email.</p>
        </div>
        """

    def _password_reset_html(self, name: str, link: str) -> str:
        return f"""
        <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px">
          <h2>Reset your FiatDex password</h2>
          <p>Hi {name},</p>
          <p>Click the button below to reset your password. This link expires in 1 hour.</p>
          <a href="{link}" style="display:inline-block;padding:14px 28px;
             background:#1a1a2e;color:white;border-radius:8px;
             text-decoration:none;font-weight:bold">Reset Password</a>
          <p style="color:#bbb;font-size:12px;margin-top:24px">
            If you didn't request this, your account is safe — ignore this email.
          </p>
        </div>
        """

    def _welcome_html(self, name: str) -> str:
        return f"""
        <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px">
          <h2>Welcome to FiatDex, {name}! 🚀</h2>
          <p>Your email is verified. You can now fund your account and buy any 
             Injective token with your local currency.</p>
          <p style="color:#888">Built for Africa. Powered by Injective.</p>
        </div>
        """

brevo_service = BrevoService()
