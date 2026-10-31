from typing import Optional
from app.core.config import settings


def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    attachment_bytes: Optional[bytes] = None,
    attachment_filename: Optional[str] = None,
) -> bool:
    """
    Sends transactional email via Resend API if RESEND_API_KEY is configured.
    Uses 'onboarding@resend.dev' by default for testing with any Resend free account.
    """
    if not settings.RESEND_API_KEY:
        print(f"[Email Sim] To: {to_email} | Subject: {subject}")
        return False

    try:
        import resend
        resend.api_key = settings.RESEND_API_KEY

        params: dict = {
            "from": "Brightloop Software <onboarding@resend.dev>",
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        }

        if attachment_bytes and attachment_filename:
            params["attachments"] = [
                {
                    "filename": attachment_filename,
                    "content": list(attachment_bytes),
                }
            ]

        resend.Emails.send(params)
        print(f"[Email Sent via Resend] To: {to_email} | Subject: {subject}")
        return True
    except Exception as e:
        print(f"[Email Warning] Could not send via Resend: {e}")
        return False
