from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select
from jose import jwt, JWTError
from app.core.config import settings
from app.core.database import get_session
from app.models.user import User, UserRole, normalize_role

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(
    session: Session = Depends(get_session), token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") == "refresh":
            raise credentials_exception
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = session.get(User, user_id)
    if user is None:
        raise credentials_exception
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if normalize_role(current_user.role) != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough privileges")
    return current_user

def get_current_technician(current_user: User = Depends(get_current_user)) -> User:
    if normalize_role(current_user.role) != UserRole.TECHNICIAN:
        raise HTTPException(status_code=403, detail="Not enough privileges")
    return current_user


def get_current_customer(current_user: User = Depends(get_current_user)) -> User:
    role = normalize_role(current_user.role)
    if role not in (UserRole.CUSTOMER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Not enough privileges")
    return current_user
