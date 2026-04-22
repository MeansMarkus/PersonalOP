# Backend (FastAPI)

## Run locally

```bash
cd backend
python -m venv .venv
. .venv/Scripts/Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open: http://127.0.0.1:8000/docs

Run background action worker in a second terminal:

```bash
cd backend
. .venv/Scripts/Activate.ps1
python -m app.worker
```


## IMPORTANT URLS
API home
http://127.0.0.1:8000/

Swagger UI (best way to test endpoints interactively)
http://127.0.0.1:8000/docs

Health check
http://127.0.0.1:8000/health

Task endpoints

GET http://127.0.0.1:8000/api/v1/tasks
POST http://127.0.0.1:8000/api/v1/tasks/plan
GET http://127.0.0.1:8000/api/v1/tasks/{task_id}
POST http://127.0.0.1:8000/api/v1/tasks/{task_id}/execute