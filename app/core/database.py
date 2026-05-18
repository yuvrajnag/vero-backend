from sqlmodel import SQLModel, Session, create_engine
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=10,
    max_overflow=20
)

def get_session():
    with Session(engine) as session:
        yield session

def init_db():
    import app.models  # Ensure all models are registered
    SQLModel.metadata.create_all(engine)
    from app.core.migrations import run_sql_migrations

    run_sql_migrations()

