from fastapi.testclient import TestClient
from datetime import datetime, timedelta, timezone

from app.db.store import get_action, init_db, reset_db
from app.main import app
from app.services import action_worker
from app.services.action_worker import process_next_action


client = TestClient(app)


def setup_function() -> None:
    init_db()
    reset_db()


def _grant_consent(action_type: str, expires_in_hours: int = 12) -> None:
    expires_at = (datetime.now(tz=timezone.utc) + timedelta(hours=expires_in_hours)).isoformat()
    response = client.post(
        "/api/v1/actions/consents/grant",
        json={"action_type": action_type, "granted_by": "owner", "expires_at": expires_at},
    )
    assert response.status_code == 200


def _queue_and_approve_action(force_fail: bool = False, grant: bool = True) -> tuple[str, int]:
    task_response = client.post(
        "/api/v1/tasks/plan",
        json={"goal": "Apply to backend internships and connect with alumni"},
    )
    assert task_response.status_code == 200
    task_id = task_response.json()["task_id"]

    queue_response = client.post(
        "/api/v1/actions/queue",
        json={
            "task_id": task_id,
            "action_type": "apply_internship",
            "target": "ExampleCo Backend Internship",
            "payload": {"force_fail": force_fail},
        },
    )
    assert queue_response.status_code == 200
    action_id = queue_response.json()["action_id"]

    if grant:
        _grant_consent("apply_internship")

    approve_response = client.post(
        f"/api/v1/actions/{action_id}/approve",
        json={"reviewed_by": "mark", "note": "approved"},
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"

    return task_id, action_id


def test_worker_processes_approved_action_to_success() -> None:
    task_id, action_id = _queue_and_approve_action(force_fail=False)

    processed = process_next_action(max_attempts=3, base_delay_seconds=0)
    assert processed

    action = get_action(action_id)
    assert action is not None
    assert action.status == "succeeded"
    assert action.executed_at is not None

    timeline = client.get(f"/api/v1/tasks/{task_id}/timeline").json()
    assert any(event["action"] == "action_execution_started" for event in timeline)
    assert any(event["action"] == "action_executed" for event in timeline)


def test_worker_retries_then_fails_after_max_attempts() -> None:
    task_id, action_id = _queue_and_approve_action(force_fail=True)

    first = process_next_action(max_attempts=2, base_delay_seconds=0)
    assert first
    action_after_first = get_action(action_id)
    assert action_after_first is not None
    assert action_after_first.status == "approved"
    assert action_after_first.attempts == 1

    second = process_next_action(max_attempts=2, base_delay_seconds=0)
    assert second
    action_after_second = get_action(action_id)
    assert action_after_second is not None
    assert action_after_second.status == "failed"
    assert action_after_second.attempts == 2
    assert action_after_second.last_error is not None

    timeline = client.get(f"/api/v1/tasks/{task_id}/timeline").json()
    assert any(event["action"] == "action_retry_scheduled" for event in timeline)
    assert any(event["action"] == "action_failed" for event in timeline)


def test_worker_blocks_when_missing_consent() -> None:
    task_id, action_id = _queue_and_approve_action(force_fail=False, grant=False)

    processed = process_next_action(max_attempts=3, base_delay_seconds=0)
    assert processed

    action = get_action(action_id)
    assert action is not None
    assert action.status == "failed"
    assert action.last_error is not None
    assert "Missing active consent" in action.last_error

    timeline = client.get(f"/api/v1/tasks/{task_id}/timeline").json()
    assert any(event["action"] == "action_blocked" for event in timeline)


def test_worker_blocks_when_consent_expired() -> None:
    task_id, action_id = _queue_and_approve_action(force_fail=False, grant=False)
    _grant_consent("apply_internship", expires_in_hours=-1)

    processed = process_next_action(max_attempts=3, base_delay_seconds=0)
    assert processed

    action = get_action(action_id)
    assert action is not None
    assert action.status == "failed"
    assert action.last_error is not None
    assert "Missing active consent" in action.last_error


def test_worker_blocks_when_daily_cap_reached() -> None:
    original_cap = action_worker.DAILY_ACTION_CAPS["apply_internship"]
    action_worker.DAILY_ACTION_CAPS["apply_internship"] = 1
    try:
        first_task_id, first_action_id = _queue_and_approve_action(force_fail=False, grant=True)
        assert process_next_action(max_attempts=3, base_delay_seconds=0)
        first_action = get_action(first_action_id)
        assert first_action is not None
        assert first_action.status == "succeeded"

        second_task_id, second_action_id = _queue_and_approve_action(force_fail=False, grant=True)
        assert process_next_action(max_attempts=3, base_delay_seconds=0)
        second_action = get_action(second_action_id)
        assert second_action is not None
        assert second_action.status == "failed"
        assert second_action.last_error is not None
        assert "Daily cap reached" in second_action.last_error

        timeline = client.get(f"/api/v1/tasks/{second_task_id}/timeline").json()
        assert any(event["action"] == "action_blocked" for event in timeline)
    finally:
        action_worker.DAILY_ACTION_CAPS["apply_internship"] = original_cap
