from fastapi import APIRouter, HTTPException

from app.db.store import (
    append_log,
    decide_action,
    get_action,
    get_task,
    list_pending_actions,
    queue_action,
)
from app.schemas.action import ActionDecision, ActionItem, ActionQueueCreate

router = APIRouter()


@router.post("/queue", response_model=ActionItem)
def create_action(payload: ActionQueueCreate) -> ActionItem:
    task = get_task(payload.task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    action = queue_action(
        task_id=payload.task_id,
        action_type=payload.action_type,
        target=payload.target,
        payload=payload.payload,
    )
    append_log(
        task_id=payload.task_id,
        action="action_queued",
        detail=f"Queued action {payload.action_type} for target {payload.target}",
    )
    return action


@router.get("/pending", response_model=list[ActionItem])
def get_pending_actions() -> list[ActionItem]:
    return list_pending_actions()


@router.post("/{action_id}/approve", response_model=ActionItem)
def approve_action(action_id: int, payload: ActionDecision) -> ActionItem:
    action = get_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.status != "queued":
        raise HTTPException(status_code=400, detail="Only queued actions can be approved")

    approved = decide_action(
        action_id,
        status="approved",
        reviewed_by=payload.reviewed_by,
        note=payload.note,
        expected_status="queued",
    )
    if approved is None:
        raise HTTPException(status_code=500, detail="Failed to approve action")

    append_log(
        task_id=approved.task_id,
        action="action_approved",
        detail=f"Action #{approved.action_id} approved by {payload.reviewed_by}",
    )
    return approved


@router.post("/{action_id}/reject", response_model=ActionItem)
def reject_action(action_id: int, payload: ActionDecision) -> ActionItem:
    action = get_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.status != "queued":
        raise HTTPException(status_code=400, detail="Only queued actions can be rejected")

    rejected = decide_action(
        action_id,
        status="rejected",
        reviewed_by=payload.reviewed_by,
        note=payload.note,
        expected_status="queued",
    )
    if rejected is None:
        raise HTTPException(status_code=500, detail="Failed to reject action")

    append_log(
        task_id=rejected.task_id,
        action="action_rejected",
        detail=f"Action #{rejected.action_id} rejected by {payload.reviewed_by}",
    )
    return rejected
