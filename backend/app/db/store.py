import sqlite3
from datetime import datetime, timezone

from app.db.session import get_database_url
from app.schemas.task import ExecutionLog, TaskListItem, TaskPlanStep


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _resolve_db_path(database_url: str) -> str:
    if not database_url.startswith("sqlite:///"):
        raise ValueError("Only sqlite DATABASE_URL values are supported for MVP")
    return database_url.replace("sqlite:///", "", 1)


def _connect() -> sqlite3.Connection:
    path = _resolve_db_path(get_database_url())
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with _connect() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                goal TEXT NOT NULL,
                summary TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS task_steps (
                task_id TEXT NOT NULL,
                step_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                PRIMARY KEY (task_id, step_id),
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS task_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                action TEXT NOT NULL,
                detail TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
            """
        )


def reset_db() -> None:
    with _connect() as connection:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM task_logs")
        cursor.execute("DELETE FROM task_steps")
        cursor.execute("DELETE FROM tasks")


def create_task(task_id: str, goal: str, summary: str, steps: list[TaskPlanStep]) -> None:
    created_at = _utc_now()
    with _connect() as connection:
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO tasks (id, goal, summary, created_at) VALUES (?, ?, ?, ?)",
            (task_id, goal, summary, created_at),
        )
        cursor.executemany(
            "INSERT INTO task_steps (task_id, step_id, description, status) VALUES (?, ?, ?, ?)",
            [(task_id, step.id, step.description, step.status) for step in steps],
        )


def append_log(task_id: str, action: str, detail: str) -> None:
    with _connect() as connection:
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO task_logs (task_id, action, detail, created_at) VALUES (?, ?, ?, ?)",
            (task_id, action, detail, _utc_now()),
        )


def list_tasks(limit: int = 50) -> list[TaskListItem]:
    with _connect() as connection:
        cursor = connection.cursor()
        rows = cursor.execute(
            """
            SELECT id, goal, summary, created_at
            FROM tasks
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [
        TaskListItem(task_id=row["id"], goal=row["goal"], summary=row["summary"], created_at=row["created_at"])
        for row in rows
    ]


def get_task(task_id: str) -> dict | None:
    with _connect() as connection:
        cursor = connection.cursor()
        task_row = cursor.execute(
            "SELECT id, goal, summary, created_at FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
        if task_row is None:
            return None

        step_rows = cursor.execute(
            """
            SELECT step_id, description, status
            FROM task_steps
            WHERE task_id = ?
            ORDER BY step_id ASC
            """,
            (task_id,),
        ).fetchall()

        log_rows = cursor.execute(
            """
            SELECT id, action, detail, created_at
            FROM task_logs
            WHERE task_id = ?
            ORDER BY id ASC
            """,
            (task_id,),
        ).fetchall()

    return {
        "task_id": task_row["id"],
        "goal": task_row["goal"],
        "summary": task_row["summary"],
        "created_at": task_row["created_at"],
        "steps": [
            TaskPlanStep(id=row["step_id"], description=row["description"], status=row["status"])
            for row in step_rows
        ],
        "logs": [
            ExecutionLog(id=row["id"], action=row["action"], detail=row["detail"], created_at=row["created_at"])
            for row in log_rows
        ],
    }


def set_steps_status(task_id: str, status: str) -> None:
    with _connect() as connection:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE task_steps SET status = ? WHERE task_id = ?",
            (status, task_id),
        )
