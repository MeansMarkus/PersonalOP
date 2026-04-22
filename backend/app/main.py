from fastapi import FastAPI

from app.api.v1.router import api_router
from app.db.store import init_db

app = FastAPI(title="Personal AI Operator API", version="0.1.0")
app.include_router(api_router, prefix="/api/v1")
init_db()


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "Personal AI Operator API",
        "docs": "/docs",
        "health": "/health",
        "tasks": "/api/v1/tasks",
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
