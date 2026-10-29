import os
import time

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://matrix:matrix@postgres:5432/matrix")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def update_task_status(task_id: int, status: str, result: str):
    db = SessionLocal()
    try:
        db.execute(
            text(
                """
                UPDATE tasks
                SET status = :status,
                    result = :result,
                    updated_at = NOW()
                WHERE id = :task_id
                """
            ),
            {"status": status, "result": result, "task_id": task_id},
        )
        db.commit()
    finally:
        db.close()


def ssh_check(task_id: int, host: str):
    update_task_status(task_id, "running", f"Checking {host}")
    time.sleep(3)

    result = {
        "host": host,
        "status": "reachable",
        "mode": "demo-check",
    }

    update_task_status(task_id, "done", str(result))
    return result
