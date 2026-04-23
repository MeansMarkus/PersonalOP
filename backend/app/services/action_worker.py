from __future__ import annotations

from time import sleep

from app.db.store import (
    append_log,
    claim_next_approved_action,
    count_successful_actions_today_by_type,
    has_valid_consent,
    log_action_execution,
    mark_action_failed_or_retry,
    mark_action_succeeded,
)
from app.services.action_providers import execute_action_with_provider
from app.schemas.action import ActionItem

DAILY_ACTION_CAPS: dict[str, int] = {
    "apply_internship": 10,
    "send_connection_request": 20,
    "follow_up_message": 30,
}


def _check_preconditions(action: ActionItem) -> str | None:
    if not has_valid_consent(action.action_type):
        return f"Missing active consent for action type {action.action_type}"

    daily_cap = DAILY_ACTION_CAPS.get(action.action_type)
    if daily_cap is None:
        return None

    succeeded_today = count_successful_actions_today_by_type(action.action_type)
    if succeeded_today >= daily_cap:
        return f"Daily cap reached for {action.action_type} ({daily_cap})"

    return None


def process_next_action(max_attempts: int = 3, base_delay_seconds: int = 5) -> bool:
    action = claim_next_approved_action()
    if action is None:
        return False

    precondition_error = _check_preconditions(action)
    if precondition_error is not None:
        mark_action_failed_or_retry(
            action_id=action.action_id,
            error_detail=precondition_error,
            max_attempts=1,
            base_delay_seconds=0,
        )
        log_action_execution(action.action_id, action.task_id, "failed_precondition", precondition_error)
        append_log(action.task_id, "action_blocked", f"Action #{action.action_id} blocked: {precondition_error}")
        return True

    append_log(action.task_id, "action_execution_started", f"Action #{action.action_id} entered worker")
    provider_result = execute_action_with_provider(action)
    succeeded = provider_result.succeeded
    detail = provider_result.detail

    if succeeded:
        updated = mark_action_succeeded(action.action_id)
        if updated is None:
            return False
        log_action_execution(action.action_id, action.task_id, "succeeded", detail)
        append_log(action.task_id, "action_executed", f"Action #{action.action_id} succeeded")
        return True

    updated = mark_action_failed_or_retry(
        action_id=action.action_id,
        error_detail=detail,
        max_attempts=max_attempts,
        base_delay_seconds=base_delay_seconds,
    )
    if updated is None:
        return False

    if updated.status == "failed":
        log_action_execution(action.action_id, action.task_id, "failed", detail)
        append_log(action.task_id, "action_failed", f"Action #{action.action_id} failed after retries")
    else:
        log_action_execution(action.action_id, action.task_id, "retry_scheduled", detail)
        append_log(action.task_id, "action_retry_scheduled", f"Action #{action.action_id} scheduled for retry")

    return True


def run_action_worker(poll_interval_seconds: int = 2, max_attempts: int = 3, base_delay_seconds: int = 5) -> None:
    while True:
        processed = process_next_action(max_attempts=max_attempts, base_delay_seconds=base_delay_seconds)
        if not processed:
            sleep(poll_interval_seconds)
