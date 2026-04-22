from fastapi.testclient import TestClient

from app.db.store import get_action, init_db, reset_db
from app.main import app
from app.services.action_worker import process_next_action


client = TestClient(app)


def setup_function() -> None:
    init_db()
    reset_db()


def _queue_and_approve_action(force_fail: bool = False) -> tuple[str, int]:
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
