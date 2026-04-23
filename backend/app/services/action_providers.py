from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from app.schemas.action import ActionItem


@dataclass
class ProviderExecutionResult:
    succeeded: bool
    detail: str


def execute_action_with_provider(action: ActionItem) -> ProviderExecutionResult:
    if bool(action.payload.get("force_fail")):
        return ProviderExecutionResult(
            succeeded=False,
            detail=f"Execution failed for {action.action_type} on {action.target}",
        )

    supported_action_types = {"apply_internship", "send_connection_request", "follow_up_message"}
    if action.action_type not in supported_action_types:
        return ProviderExecutionResult(
            succeeded=False,
            detail=f"No provider configured for action type {action.action_type}",
        )

    return _execute_via_email_provider(action)


def _execute_via_email_provider(action: ActionItem) -> ProviderExecutionResult:
    recipient_email = (
        action.payload.get("recipient_email")
        or action.payload.get("to")
        or os.getenv("DEFAULT_APPLICATION_EMAIL", "applications@example.com")
    )
    subject = action.payload.get("subject") or f"PersonalOP action: {action.action_type}"
    message = action.payload.get("message") or f"Automated action target: {action.target}"

    if _is_dry_run_mode():
        return ProviderExecutionResult(
            succeeded=True,
            detail=f"Dry-run email provider: would send '{subject}' to {recipient_email}",
        )

    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    smtp_from = os.getenv("SMTP_FROM", "")

    if not smtp_host or not smtp_username or not smtp_password or not smtp_from:
        return ProviderExecutionResult(
            succeeded=False,
            detail="SMTP configuration missing; set SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, and SMTP_FROM",
        )

    email = EmailMessage()
    email["From"] = smtp_from
    email["To"] = recipient_email
    email["Subject"] = subject
    email.set_content(message)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as smtp:
            smtp.starttls()
            smtp.login(smtp_username, smtp_password)
            smtp.send_message(email)
    except Exception as exc:  # noqa: BLE001
        return ProviderExecutionResult(
            succeeded=False,
            detail=f"Email provider failure: {exc}",
        )

    return ProviderExecutionResult(
        succeeded=True,
        detail=f"Email provider sent '{subject}' to {recipient_email}",
    )


def _is_dry_run_mode() -> bool:
    return os.getenv("ACTION_DRY_RUN", "true").lower() == "true"
