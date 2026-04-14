from fastapi import FastAPI

from app.api.v1.router import api_router

app = FastAPI(title="Personal AI Operator API", version="0.1.0")
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
