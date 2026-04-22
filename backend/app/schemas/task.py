from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    goal: str = Field(min_length=5, max_length=500)


class TaskPlanStep(BaseModel):
    id: int
    description: str
    status: str = "pending"


class TaskResponse(BaseModel):
    task_id: str
    goal: str
    steps: list[TaskPlanStep]
    summary: str


class ExecutionLog(BaseModel):
    id: int
    action: str
    detail: str
    created_at: str


class TaskListItem(BaseModel):
    task_id: str
    goal: str
    summary: str
    created_at: str


class TaskDetail(TaskResponse):
    created_at: str
    logs: list[ExecutionLog]
