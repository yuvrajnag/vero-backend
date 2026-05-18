from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlmodel import Session

from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.models.user import User, normalize_role
from app.schemas.auth_schema import (
    GoogleAuthRequest,
    RefreshTokenRequest,
    TokenPair,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse)
def register(user_in: UserCreate, session: Session = Depends(get_session)):
    """Register a new user (Customer, Technician, or Admin)"""
    return auth_service.register_user(session, user_in)


@router.post("/login", response_model=TokenPair)
def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    """Login to get access and refresh tokens"""
    user_in = UserLogin(email=form_data.username, password=form_data.password)
    return auth_service.authenticate(session, user_in)


@router.post("/google", response_model=TokenPair)
def google_login(body: GoogleAuthRequest, session: Session = Depends(get_session)):
    """Exchange Google ID token for platform JWT tokens"""
    return auth_service.google_authenticate(session, body.credential)


@router.post("/refresh", response_model=TokenPair)
def refresh_tokens(body: RefreshTokenRequest, session: Session = Depends(get_session)):
    """Rotate refresh token and issue a new access token"""
    return auth_service.refresh_access_token(session, body.refresh_token)


@router.post("/logout")
def logout(body: RefreshTokenRequest, session: Session = Depends(get_session)):
    """Revoke refresh token"""
    auth_service.revoke_refresh_token(session, body.refresh_token)
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current user details"""
    return current_user


class CompleteOnboardingRequest(BaseModel):
    role: str


@router.post("/complete-onboarding", response_model=UserResponse)
def complete_onboarding(
    data: CompleteOnboardingRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Complete onboarding and update user role"""
    current_user.role = normalize_role(data.role).value
    current_user.onboarding_completed = True
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user
