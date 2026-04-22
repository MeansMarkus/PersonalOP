from __future__ import annotations

from time import sleep

from app.db.store import (
    append_log,
    claim_next_approved_action,
    log_action_execution,
    mark_action_failed_or_retry,
    mark_action_succeeded,
)
from app.schemas.action import ActionItem


def _execute_action(action: ActionItem) -> tuple[bool, str]:
    # Mock executor for MVP. Real connectors can replace this per action_type.
    if bool(action.payload.get("force_fail")):
        return False, f"Execution failed for {action.action_type} on {action.target}"
    return True, f"Executed {action.action_type} for {action.target}"


def process_next_action(max_attempts: int = 3, base_delay_seconds: int = 5) -> bool:
    action = claim_next_approved_action()
    if action is None:
        return False

    append_log(action.task_id, "action_execution_started", f"Action #{action.action_id} entered worker")
    succeeded, detail = _execute_action(action)

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
