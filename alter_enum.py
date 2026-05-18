from app.core.database import engine
from sqlmodel import text

def alter_enum():
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(text("ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'pending'"))
            conn.execute(text("ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'matched'"))
            conn.execute(text("ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'negotiating'"))
            conn.execute(text("ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'accepted'"))
            conn.execute(text("ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'in_progress'"))
            conn.execute(text("ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'completed'"))
            conn.execute(text("ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'cancelled'"))
            conn.execute(text("ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'PENDING'"))
            conn.execute(text("ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'MATCHED'"))
            conn.execute(text("ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'NEGOTIATING'"))
            conn.execute(text("ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'ACCEPTED'"))
            conn.execute(text("ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'IN_PROGRESS'"))
            conn.execute(text("ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'COMPLETED'"))
            conn.execute(text("ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'CANCELLED'"))
            print("Enum altered successfully!")

if __name__ == '__main__':
    alter_enum()
