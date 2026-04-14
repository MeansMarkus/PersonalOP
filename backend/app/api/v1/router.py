from fastapi import APIRouter

from app.api.v1.endpoints.tasks import router as tasks_router

api_router = APIRouter()
api_router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
