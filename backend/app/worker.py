from app.db.store import init_db
from app.services.action_worker import run_action_worker


if __name__ == "__main__":
    init_db()
    run_action_worker()
