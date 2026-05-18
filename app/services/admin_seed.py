from sqlmodel import Session, select

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.utils.logger import logger


def seed_admin_user(session: Session) -> None:
    if not settings.ADMIN_EMAIL or not settings.ADMIN_PASSWORD:
        return

    existing = session.exec(select(User).where(User.email == settings.ADMIN_EMAIL)).first()
    if existing:
        if existing.role != UserRole.ADMIN.value:
            existing.role = UserRole.ADMIN.value
            existing.onboarding_completed = True
            session.add(existing)
            session.commit()
        return

    admin = User(
        email=settings.ADMIN_EMAIL,
        full_name="Platform Admin",
        hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
        role=UserRole.ADMIN.value,
        onboarding_completed=True,
        is_verified=True,
    )
    session.add(admin)
    session.commit()
    logger.info("Admin user seeded: %s", settings.ADMIN_EMAIL)
