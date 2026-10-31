"""Transactional email. Logs to stdout until SMTP credentials are configured."""

from __future__ import annotations

import logging

logger = logging.getLogger("brightloop.email")


def send_email(*, to: str, subject: str, body: str) -> None:
    """Single seam to replace with SMTP / SES / Postmark later.

    The scaffold intentionally logs instead of talking to a mail server so that
    local runs need no credentials.
    """
    logger.info("email to=%s subject=%s\n%s", to, subject, body)


def send_password_reset(*, to: str, full_name: str, reset_url: str) -> None:
    send_email(
        to=to,
        subject="Reset your Brightloop password",
        body=(
            f"Hello {full_name},\n\n"
            f"Use the link below to choose a new password. It expires shortly.\n\n"
            f"{reset_url}\n\n"
            "If you did not request this, you can ignore this email."
        ),
    )
