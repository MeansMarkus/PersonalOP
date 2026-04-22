import sqlite3
from datetime import datetime, timezone
from datetime import timedelta
import json

from app.db.session import get_database_url
from app.schemas.action import ActionExecutionLog, ActionItem, TimelineEvent
from app.schemas.consent import ConsentRecord
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
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS action_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                target TEXT NOT NULL,
                payload TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                reviewed_by TEXT,
                note TEXT,
                attempts INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                locked_at TEXT,
                executed_at TEXT,
                next_retry_at TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
            """
        )
        _ensure_action_queue_columns(cursor)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS action_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_id INTEGER NOT NULL,
                task_id TEXT NOT NULL,
                status TEXT NOT NULL,
                detail TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (action_id) REFERENCES action_queue(id),
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS consents (
                action_type TEXT PRIMARY KEY,
                granted_by TEXT NOT NULL,
                granted_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            )
            """
        )


def reset_db() -> None:
    with _connect() as connection:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM consents")
        cursor.execute("DELETE FROM action_executions")
        cursor.execute("DELETE FROM action_queue")
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


def queue_action(task_id: str, action_type: str, target: str, payload: dict) -> ActionItem:
    now = _utc_now()
    with _connect() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO action_queue (task_id, action_type, target, payload, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (task_id, action_type, target, json.dumps(payload), "queued", now, now),
        )
        action_id = cursor.lastrowid

    return ActionItem(
        action_id=action_id,
        task_id=task_id,
        action_type=action_type,
        target=target,
        payload=payload,
        status="queued",
        created_at=now,
        updated_at=now,
    )


def list_pending_actions(limit: int = 100) -> list[ActionItem]:
    with _connect() as connection:
        cursor = connection.cursor()
        rows = cursor.execute(
            """
                 SELECT id, task_id, action_type, target, payload, status, created_at, updated_at, reviewed_by, note,
                     attempts, last_error, locked_at, executed_at, next_retry_at
            FROM action_queue
            WHERE status = 'queued'
            ORDER BY id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [_action_row_to_item(row) for row in rows]


def get_action(action_id: int) -> ActionItem | None:
    with _connect() as connection:
        cursor = connection.cursor()
        row = cursor.execute(
            """
                 SELECT id, task_id, action_type, target, payload, status, created_at, updated_at, reviewed_by, note,
                     attempts, last_error, locked_at, executed_at, next_retry_at
            FROM action_queue
            WHERE id = ?
            """,
            (action_id,),
        ).fetchone()
    if row is None:
        return None

    return _action_row_to_item(row)


def decide_action(
    action_id: int,
    status: str,
    reviewed_by: str,
    note: str = "",
    expected_status: str | None = None,
) -> ActionItem | None:
    now = _utc_now()
    with _connect() as connection:
        cursor = connection.cursor()
        if expected_status is None:
            cursor.execute(
                """
                UPDATE action_queue
                SET status = ?, reviewed_by = ?, note = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, reviewed_by, note, now, action_id),
            )
        else:
            cursor.execute(
                """
                UPDATE action_queue
                SET status = ?, reviewed_by = ?, note = ?, updated_at = ?
                WHERE id = ? AND status = ?
                """,
                (status, reviewed_by, note, now, action_id, expected_status),
            )
        if cursor.rowcount == 0:
            return None

    return get_action(action_id)


def log_action_execution(action_id: int, task_id: str, status: str, detail: str) -> ActionExecutionLog:
    created_at = _utc_now()
    with _connect() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO action_executions (action_id, task_id, status, detail, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (action_id, task_id, status, detail, created_at),
        )
        execution_id = cursor.lastrowid

    return ActionExecutionLog(
        execution_id=execution_id,
        action_id=action_id,
        task_id=task_id,
        status=status,
        detail=detail,
        created_at=created_at,
    )


def get_task_timeline(task_id: str) -> list[TimelineEvent]:
    with _connect() as connection:
        cursor = connection.cursor()
        task_rows = cursor.execute(
            "SELECT action, detail, created_at FROM task_logs WHERE task_id = ?",
            (task_id,),
        ).fetchall()
        action_rows = cursor.execute(
            """
            SELECT action_type, target, status, created_at
            FROM action_queue
            WHERE task_id = ?
            """,
            (task_id,),
        ).fetchall()
        execution_rows = cursor.execute(
            """
            SELECT action_id, status, detail, created_at
            FROM action_executions
            WHERE task_id = ?
            """,
            (task_id,),
        ).fetchall()

    events: list[TimelineEvent] = []
    events.extend(
        TimelineEvent(source="task", action=row["action"], detail=row["detail"], created_at=row["created_at"])
        for row in task_rows
    )
    events.extend(
        TimelineEvent(
            source="action",
            action=f"queued:{row['action_type']}",
            detail=f"Target: {row['target']} (status={row['status']})",
            created_at=row["created_at"],
        )
        for row in action_rows
    )
    events.extend(
        TimelineEvent(
            source="execution",
            action=f"execution:{row['status']}",
            detail=f"Action #{row['action_id']}: {row['detail']}",
            created_at=row["created_at"],
        )
        for row in execution_rows
    )
    return sorted(events, key=lambda event: event.created_at)


def claim_next_approved_action() -> ActionItem | None:
    now = _utc_now()
    with _connect() as connection:
        cursor = connection.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        row = cursor.execute(
            """
            SELECT id
            FROM action_queue
            WHERE status = 'approved'
              AND (next_retry_at IS NULL OR next_retry_at <= ?)
            ORDER BY id ASC
            LIMIT 1
            """,
            (now,),
        ).fetchone()
        if row is None:
            connection.commit()
            return None

        cursor.execute(
            """
            UPDATE action_queue
            SET status = 'executing', locked_at = ?, updated_at = ?
            WHERE id = ? AND status = 'approved'
            """,
            (now, now, row["id"]),
        )
        if cursor.rowcount == 0:
            connection.commit()
            return None
        connection.commit()

    return get_action(row["id"])


def mark_action_succeeded(action_id: int) -> ActionItem | None:
    now = _utc_now()
    with _connect() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE action_queue
            SET status = 'succeeded',
                updated_at = ?,
                executed_at = ?,
                locked_at = NULL,
                next_retry_at = NULL,
                last_error = NULL
            WHERE id = ?
            """,
            (now, now, action_id),
        )
        if cursor.rowcount == 0:
            return None
    return get_action(action_id)


def mark_action_failed_or_retry(action_id: int, error_detail: str, max_attempts: int, base_delay_seconds: int) -> ActionItem | None:
    action = get_action(action_id)
    if action is None:
        return None

    next_attempts = action.attempts + 1
    now = datetime.now(tz=timezone.utc)
    with _connect() as connection:
        cursor = connection.cursor()
        if next_attempts >= max_attempts:
            cursor.execute(
                """
                UPDATE action_queue
                SET status = 'failed',
                    attempts = ?,
                    last_error = ?,
                    updated_at = ?,
                    locked_at = NULL,
                    next_retry_at = NULL
                WHERE id = ?
                """,
                (next_attempts, error_detail, now.isoformat(), action_id),
            )
        else:
            delay_seconds = base_delay_seconds * (2 ** (next_attempts - 1))
            retry_at = (now + timedelta(seconds=delay_seconds)).isoformat()
            cursor.execute(
                """
                UPDATE action_queue
                SET status = 'approved',
                    attempts = ?,
                    last_error = ?,
                    updated_at = ?,
                    locked_at = NULL,
                    next_retry_at = ?
                WHERE id = ?
                """,
                (next_attempts, error_detail, now.isoformat(), retry_at, action_id),
            )

        if cursor.rowcount == 0:
            return None

    return get_action(action_id)


def grant_consent(action_type: str, granted_by: str, expires_at: str) -> ConsentRecord:
    now = _utc_now()
    with _connect() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO consents (action_type, granted_by, granted_at, expires_at, is_active)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(action_type)
            DO UPDATE SET
                granted_by = excluded.granted_by,
                granted_at = excluded.granted_at,
                expires_at = excluded.expires_at,
                is_active = 1
            """,
            (action_type, granted_by, now, expires_at),
        )
    return get_consent(action_type)


def revoke_consent(action_type: str) -> ConsentRecord | None:
    with _connect() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE consents
            SET is_active = 0
            WHERE action_type = ?
            """,
            (action_type,),
        )
        if cursor.rowcount == 0:
            return None

    return get_consent(action_type)


def get_consent(action_type: str) -> ConsentRecord | None:
    with _connect() as connection:
        cursor = connection.cursor()
        row = cursor.execute(
            """
            SELECT action_type, granted_by, granted_at, expires_at, is_active
            FROM consents
            WHERE action_type = ?
            """,
            (action_type,),
        ).fetchone()
    if row is None:
        return None

    return ConsentRecord(
        action_type=row["action_type"],
        granted_by=row["granted_by"],
        granted_at=row["granted_at"],
        expires_at=row["expires_at"],
        is_active=bool(row["is_active"]),
    )


def list_consents() -> list[ConsentRecord]:
    with _connect() as connection:
        cursor = connection.cursor()
        rows = cursor.execute(
            """
            SELECT action_type, granted_by, granted_at, expires_at, is_active
            FROM consents
            ORDER BY action_type ASC
            """
        ).fetchall()

    return [
        ConsentRecord(
            action_type=row["action_type"],
            granted_by=row["granted_by"],
            granted_at=row["granted_at"],
            expires_at=row["expires_at"],
            is_active=bool(row["is_active"]),
        )
        for row in rows
    ]


def has_valid_consent(action_type: str) -> bool:
    consent = get_consent(action_type)
    if consent is None or not consent.is_active:
        return False

    try:
        expires_at = datetime.fromisoformat(consent.expires_at)
    except ValueError:
        return False
    return expires_at > datetime.now(tz=timezone.utc)


def count_successful_actions_today_by_type(action_type: str) -> int:
    now = datetime.now(tz=timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    start_of_next_day = (now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)).isoformat()

    with _connect() as connection:
        cursor = connection.cursor()
        row = cursor.execute(
            """
            SELECT COUNT(*) AS count
            FROM action_executions ae
            JOIN action_queue aq ON aq.id = ae.action_id
            WHERE ae.status = 'succeeded'
              AND aq.action_type = ?
              AND ae.created_at >= ?
              AND ae.created_at < ?
            """,
            (action_type, start_of_day, start_of_next_day),
        ).fetchone()

    return int(row["count"]) if row is not None else 0


def _ensure_action_queue_columns(cursor: sqlite3.Cursor) -> None:
    table_info = cursor.execute("PRAGMA table_info(action_queue)").fetchall()
    existing_columns = {row[1] for row in table_info}
    required_columns = {
        "attempts": "ALTER TABLE action_queue ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0",
        "last_error": "ALTER TABLE action_queue ADD COLUMN last_error TEXT",
        "locked_at": "ALTER TABLE action_queue ADD COLUMN locked_at TEXT",
        "executed_at": "ALTER TABLE action_queue ADD COLUMN executed_at TEXT",
        "next_retry_at": "ALTER TABLE action_queue ADD COLUMN next_retry_at TEXT",
    }

    for name, statement in required_columns.items():
        if name not in existing_columns:
            cursor.execute(statement)


def _action_row_to_item(row: sqlite3.Row) -> ActionItem:
    return ActionItem(
        action_id=row["id"],
        task_id=row["task_id"],
        action_type=row["action_type"],
        target=row["target"],
        payload=json.loads(row["payload"]),
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        reviewed_by=row["reviewed_by"],
        note=row["note"],
        attempts=row["attempts"],
        last_error=row["last_error"],
        locked_at=row["locked_at"],
        executed_at=row["executed_at"],
        next_retry_at=row["next_retry_at"],
    )
