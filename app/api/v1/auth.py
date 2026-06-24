"""
Authentication API endpoints.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.database import get_db
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserResponse
from app.services import auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    user_in: UserCreate,
    db: Annotated[Session, Depends(get_db)]
):
    """
    Register a new user.
    """
    # Check if username or email already exists
    if auth_service.get_user_by_username(db, username=user_in.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this username already exists in the system",
        )
    if auth_service.get_user_by_email(db, email=user_in.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email already exists in the system",
        )
        
    return auth_service.create_user(db, user_in=user_in)


@router.post("/login", response_model=Token)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)]
):
    """
    OAuth2 compatible token login, getting an access token for future requests.
    """
    user = auth_service.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
        
    access_token = auth_service.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Get current user details.
    """
    return current_user
