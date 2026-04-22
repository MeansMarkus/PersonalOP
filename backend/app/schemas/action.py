from typing import Any

from pydantic import BaseModel, Field


class ActionQueueCreate(BaseModel):
    task_id: str
    action_type: str = Field(min_length=3, max_length=64)
    target: str = Field(min_length=1, max_length=255)
    payload: dict[str, Any] = Field(default_factory=dict)


class ActionDecision(BaseModel):
    reviewed_by: str = Field(min_length=2, max_length=64)
    note: str = Field(default="")


class ActionItem(BaseModel):
    action_id: int
    task_id: str
    action_type: str
    target: str
    payload: dict[str, Any]
    status: str
    created_at: str
    updated_at: str
    reviewed_by: str | None = None
    note: str | None = None


class ActionExecutionLog(BaseModel):
    execution_id: int
    action_id: int
    task_id: str
    status: str
    detail: str
    created_at: str


class TimelineEvent(BaseModel):
    source: str
    action: str
    detail: str
    created_at: str
