from datetime import datetime, timedelta, timezone

import httpx
from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token_value,
    get_password_hash,
    hash_refresh_token,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserRole, normalize_role
from app.schemas.auth_schema import TokenPair, UserCreate, UserLogin


def _issue_tokens(session: Session, user: User) -> TokenPair:
    access_token = create_access_token(user.id)
    refresh_plain = create_refresh_token_value()
    refresh_row = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_plain),
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    session.add(refresh_row)
    session.commit()
    return TokenPair(access_token=access_token, refresh_token=refresh_plain)


def register_user(session: Session, user_in: UserCreate) -> User:
    user = session.exec(select(User).where(User.email == user_in.email)).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )

    db_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=normalize_role(user_in.role).value,
    )
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def authenticate(session: Session, user_in: UserLogin) -> TokenPair:
    user = session.exec(select(User).where(User.email == user_in.email)).first()
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return _issue_tokens(session, user)


def refresh_access_token(session: Session, refresh_token: str) -> TokenPair:
    token_hash = hash_refresh_token(refresh_token)
    row = session.exec(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    ).first()
    if not row or row.revoked:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user = session.get(User, row.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    row.revoked = True
    session.add(row)
    session.commit()
    return _issue_tokens(session, user)


def revoke_refresh_token(session: Session, refresh_token: str) -> None:
    token_hash = hash_refresh_token(refresh_token)
    row = session.exec(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    ).first()
    if row:
        row.revoked = True
        session.add(row)
        session.commit()


def _google_profile_from_id_token(credential: str) -> dict:
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": credential},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid Google ID token")
    payload = resp.json()
    _verify_google_audience(payload.get("aud"))
    return payload


def _allowed_google_client_ids() -> set[str]:
    if not settings.GOOGLE_CLIENT_ID:
        return set()
    return {cid.strip() for cid in settings.GOOGLE_CLIENT_ID.split(",") if cid.strip()}


def _verify_google_audience(aud: str | None) -> None:
    allowed = _allowed_google_client_ids()
    if allowed and aud not in allowed:
        raise HTTPException(status_code=401, detail="Google token audience mismatch")


def _google_profile_from_access_token(credential: str) -> dict:
    with httpx.Client(timeout=10.0) as client:
        tokeninfo = client.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"access_token": credential},
        )
        if tokeninfo.status_code == 200:
            info = tokeninfo.json()
            _verify_google_audience(info.get("aud") or info.get("azp"))
            if info.get("email"):
                return {
                    "sub": info.get("sub") or info.get("user_id"),
                    "email": info.get("email"),
                    "name": info.get("name"),
                    "email_verified": info.get("email_verified", "false"),
                }

        resp = client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {credential}"},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid Google access token")
    data = resp.json()
    return {
        "sub": data.get("sub"),
        "email": data.get("email"),
        "name": data.get("name"),
        "email_verified": "true" if data.get("email_verified") else "false",
    }


def google_authenticate(session: Session, credential: str) -> TokenPair:
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth is not configured on the server.",
        )

    try:
        if credential.count(".") == 2:
            payload = _google_profile_from_id_token(credential)
        else:
            payload = _google_profile_from_access_token(credential)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Google token verification failed") from exc

    email = payload.get("email")
    google_sub = payload.get("sub")
    if not email or not google_sub:
        raise HTTPException(status_code=400, detail="Google account missing email")

    user = session.exec(select(User).where(User.google_id == google_sub)).first()
    if not user:
        user = session.exec(select(User).where(User.email == email)).first()
        if user:
            user.google_id = google_sub
            if payload.get("name") and not user.full_name:
                user.full_name = payload["name"]
            user.is_verified = payload.get("email_verified") == "true"
            session.add(user)
            session.commit()
            session.refresh(user)
        else:
            user = User(
                email=email,
                full_name=payload.get("name"),
                google_id=google_sub,
                hashed_password=None,
                role=UserRole.CUSTOMER.value,
                is_verified=payload.get("email_verified") == "true",
            )
            session.add(user)
            session.commit()
            session.refresh(user)

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    return _issue_tokens(session, user)
