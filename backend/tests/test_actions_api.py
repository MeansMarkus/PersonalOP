from fastapi.testclient import TestClient

from app.db.store import init_db, reset_db
from app.main import app


client = TestClient(app)


def setup_function() -> None:
    init_db()
    reset_db()


def _create_task() -> str:
    response = client.post("/api/v1/tasks/plan", json={"goal": "Apply to backend internships and connect with alumni"})
    assert response.status_code == 200
    return response.json()["task_id"]


def test_queue_action_and_list_pending() -> None:
    task_id = _create_task()

    queue_response = client.post(
        "/api/v1/actions/queue",
        json={
            "task_id": task_id,
            "action_type": "apply_internship",
            "target": "ExampleCo Backend Internship",
            "payload": {"job_url": "https://example.com/job/123"},
        },
    )
    assert queue_response.status_code == 200
    queued = queue_response.json()
    assert queued["status"] == "queued"

    pending_response = client.get("/api/v1/actions/pending")
    assert pending_response.status_code == 200
    pending = pending_response.json()
    assert len(pending) == 1
    assert pending[0]["action_id"] == queued["action_id"]


def test_approve_action_executes_and_updates_timeline() -> None:
    task_id = _create_task()
    queued = client.post(
        "/api/v1/actions/queue",
        json={
            "task_id": task_id,
            "action_type": "send_connection_request",
            "target": "alumni_profile_42",
            "payload": {"message": "Hi! I would love to connect."},
        },
    ).json()

    approve_response = client.post(
        f"/api/v1/actions/{queued['action_id']}/approve",
        json={"reviewed_by": "mark", "note": "Looks good"},
    )
    assert approve_response.status_code == 200
    approved = approve_response.json()
    assert approved["status"] == "executed"
    assert approved["reviewed_by"] == "mark"

    timeline_response = client.get(f"/api/v1/tasks/{task_id}/timeline")
    assert timeline_response.status_code == 200
    timeline = timeline_response.json()
    assert any(event["action"] == "action_executed" for event in timeline)
    assert any(event["source"] == "execution" for event in timeline)


def test_reject_action_and_not_found_paths() -> None:
    task_id = _create_task()
    queued = client.post(
        "/api/v1/actions/queue",
        json={
            "task_id": task_id,
            "action_type": "apply_internship",
            "target": "AnotherCo Internship",
            "payload": {},
        },
    ).json()

    reject_response = client.post(
        f"/api/v1/actions/{queued['action_id']}/reject",
        json={"reviewed_by": "mark", "note": "Not a fit"},
    )
    assert reject_response.status_code == 200
    rejected = reject_response.json()
    assert rejected["status"] == "rejected"

    missing_action = client.post("/api/v1/actions/9999/approve", json={"reviewed_by": "mark", "note": "x"})
    assert missing_action.status_code == 404

    missing_task_timeline = client.get("/api/v1/tasks/does-not-exist/timeline")
    assert missing_task_timeline.status_code == 404
