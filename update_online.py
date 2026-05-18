from app.core.database import engine
from sqlmodel import text

def main():
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(text("UPDATE technician_profiles SET is_online = true, current_status = 'online'"))
            print('Updated technicians')

if __name__ == '__main__':
    main()
