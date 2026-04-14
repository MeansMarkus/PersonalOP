from uuid import uuid4

from fastapi import APIRouter

from app.schemas.task import TaskCreate, TaskResponse
from app.services.planner import plan_goal

router = APIRouter()


@router.post("/plan", response_model=TaskResponse)
def create_plan(payload: TaskCreate) -> TaskResponse:
    task_id = str(uuid4())
    steps = plan_goal(payload.goal)
    return TaskResponse(task_id=task_id, goal=payload.goal, steps=steps, summary="Plan generated")
