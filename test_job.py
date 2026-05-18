import asyncio
from app.core.database import engine
from sqlmodel import Session
from app.services.job_service import create_job
from app.schemas.job_schema import JobCreate
import uuid

def main():
    try:
        session = Session(engine)
        user_id = uuid.uuid4()
        job_in = JobCreate(title='test', required_role='test', budget=100)
        job = create_job(session, user_id, job_in)
        print("Success:", job.id)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
