from fastapi.testclient import TestClient

from app.db.store import init_db, reset_db
from app.main import app


client = TestClient(app)


def setup_function() -> None:
    init_db()
    reset_db()


def test_plan_persists_and_returns_task() -> None:
    response = client.post("/api/v1/tasks/plan", json={"goal": "Apply to three backend internships in NYC"})

    assert response.status_code == 200
    data = response.json()
    assert data["task_id"]
    assert data["goal"] == "Apply to three backend internships in NYC"
    assert len(data["steps"]) == 4
    assert "Plan generated" in data["summary"]


def test_task_list_and_detail_endpoints() -> None:
    created = client.post("/api/v1/tasks/plan", json={"goal": "Build my weekly networking target list"}).json()
    task_id = created["task_id"]

    list_response = client.get("/api/v1/tasks")
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert len(list_payload) == 1
    assert list_payload[0]["task_id"] == task_id

    detail_response = client.get(f"/api/v1/tasks/{task_id}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["task_id"] == task_id
    assert len(detail_payload["logs"]) >= 1
    assert detail_payload["logs"][0]["action"] == "plan_created"


def test_execute_marks_steps_done_and_logs_action() -> None:
    created = client.post("/api/v1/tasks/plan", json={"goal": "Prepare for my backend interview this month"}).json()
    task_id = created["task_id"]

    execute_response = client.post(f"/api/v1/tasks/{task_id}/execute")
    assert execute_response.status_code == 200

    payload = execute_response.json()
    assert all(step["status"] == "done" for step in payload["steps"])
    assert payload["logs"][-1]["action"] == "task_executed"


def test_task_not_found_paths() -> None:
    missing_task_id = "does-not-exist"

    detail_response = client.get(f"/api/v1/tasks/{missing_task_id}")
    assert detail_response.status_code == 404

    execute_response = client.post(f"/api/v1/tasks/{missing_task_id}/execute")
    assert execute_response.status_code == 404
