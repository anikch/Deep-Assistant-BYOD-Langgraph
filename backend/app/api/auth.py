import uuid
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token, get_current_user
from app.db.session import get_db
from app.models.users import User
from app.schemas.auth import SignupRequest, LoginRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(request: SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == request.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )

    user = User(
        id=str(uuid.uuid4()),
        username=request.username,
        password_hash=hash_password(request.password),
        is_active=True,
        is_admin=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(
        {"sub": user.id},
        expires_delta=timedelta(minutes=settings.jwt_expire_minutes),
    )
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
        is_admin=user.is_admin,
    )


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == request.username, User.is_active == True).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = create_access_token(
        {"sub": user.id},
        expires_delta=timedelta(minutes=settings.jwt_expire_minutes),
    )
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
        is_admin=user.is_admin,
    )


@router.post("/logout")
def logout():
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
