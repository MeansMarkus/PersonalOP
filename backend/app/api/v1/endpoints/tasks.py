from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.db.store import append_log, create_task, get_task, get_task_timeline, list_tasks, set_steps_status
from app.schemas.action import TimelineEvent
from app.schemas.task import TaskCreate, TaskDetail, TaskListItem, TaskResponse
from app.services.executor import execute_steps
from app.services.planner import build_task_intake, plan_goal
from app.tools.internship_search import search_internships

router = APIRouter()


@router.post("/plan", response_model=TaskResponse)
def create_plan(payload: TaskCreate) -> TaskResponse:
    task_id = str(uuid4())
    intake = build_task_intake(payload.goal)
    steps = plan_goal(payload.goal)
    internships = search_internships(payload.goal)
    summary = f"Plan generated with {len(steps)} steps and {len(internships)} sample internship matches"

    create_task(task_id=task_id, goal=payload.goal, summary=summary, steps=steps)
    append_log(task_id=task_id, action="plan_created", detail=f"Created plan for goal: {payload.goal}")

    return TaskResponse(task_id=task_id, goal=payload.goal, intake=intake, steps=steps, summary=summary)


@router.get("", response_model=list[TaskListItem])
def get_tasks() -> list[TaskListItem]:
    return list_tasks()


@router.get("/{task_id}", response_model=TaskDetail)
def get_task_detail(task_id: str) -> TaskDetail:
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    task["intake"] = build_task_intake(task["goal"])
    return TaskDetail(**task)


@router.post("/{task_id}/execute", response_model=TaskDetail)
def execute_task(task_id: str) -> TaskDetail:
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    done_steps = execute_steps(task["steps"])
    if done_steps:
        set_steps_status(task_id=task_id, status="done")

    append_log(task_id=task_id, action="task_executed", detail="All task steps marked done")
    updated_task = get_task(task_id)
    if updated_task is None:
        raise HTTPException(status_code=500, detail="Task missing after execution")

    updated_task["intake"] = build_task_intake(updated_task["goal"])
    return TaskDetail(**updated_task)


@router.get("/{task_id}/timeline", response_model=list[TimelineEvent])
def get_timeline(task_id: str) -> list[TimelineEvent]:
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return get_task_timeline(task_id)
