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
