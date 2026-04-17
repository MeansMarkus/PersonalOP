from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    goal: str = Field(min_length=5, max_length=500)


class TaskIntake(BaseModel):
    task_type: str
    focus_area: str
    keywords: list[str] = Field(default_factory=list)
    next_best_action: str


class TaskPlanStep(BaseModel):
    id: int
    description: str
    status: str = "pending"


class TaskResponse(BaseModel):
    task_id: str
    goal: str
    intake: TaskIntake
    steps: list[TaskPlanStep]
    summary: str
