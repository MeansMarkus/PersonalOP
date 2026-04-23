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

Action safety endpoints

GET http://127.0.0.1:8000/api/v1/actions/pending
POST http://127.0.0.1:8000/api/v1/actions/consents/grant
GET http://127.0.0.1:8000/api/v1/actions/consents
POST http://127.0.0.1:8000/api/v1/actions/consents/{action_type}/revoke

Note: the worker now requires active consent per action type and enforces daily action caps.

Execution provider behavior

- The worker now executes supported actions through an email provider abstraction.
- Supported action types: `apply_internship`, `send_connection_request`, `follow_up_message`.
- Default mode is dry-run (`ACTION_DRY_RUN=true`) so no external email is sent.
- To enable live sending, set `ACTION_DRY_RUN=false` and configure SMTP settings in `.env`.