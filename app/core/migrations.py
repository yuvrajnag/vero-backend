"""Apply idempotent SQL migrations from backend/migrations/*.sql on startup."""

from pathlib import Path

from sqlalchemy import text
from sqlmodel import Session

from app.core.database import engine
from app.utils.logger import logger

_MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def run_sql_migrations() -> None:
    if not _MIGRATIONS_DIR.is_dir():
        return

    sql_files = sorted(_MIGRATIONS_DIR.glob("*.sql"))
    if not sql_files:
        return

    with Session(engine) as session:
        for path in sql_files:
            raw = path.read_text(encoding="utf-8")
            statements = []
            for chunk in raw.split(";"):
                lines = [
                    line
                    for line in chunk.splitlines()
                    if line.strip() and not line.strip().startswith("--")
                ]
                stmt = "\n".join(lines).strip()
                if stmt:
                    statements.append(stmt)
            for stmt in statements:
                try:
                    session.exec(text(stmt))
                    session.commit()
                except Exception as exc:
                    session.rollback()
                    logger.warning("Migration skipped (%s): %s — %s", path.name, stmt[:80], exc)

    logger.info("SQL migrations applied from %s", _MIGRATIONS_DIR)
