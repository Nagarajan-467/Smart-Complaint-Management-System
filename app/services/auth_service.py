"""
Authentication service handling passwords and JWTs.
"""

from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.user import User
from app.schemas.user import UserCreate

# Password hashing context setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hashed version."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def get_user_by_username(db: Session, username: str) -> User | None:
    """Fetch a user by their username."""
    stmt = select(User).where(User.username == username)
    return db.scalars(stmt).first()


def get_user_by_email(db: Session, email: str) -> User | None:
    """Fetch a user by their email address."""
    stmt = select(User).where(User.email == email)
    return db.scalars(stmt).first()


def create_user(db: Session, user_in: UserCreate) -> User:
    """Create a new user with a hashed password."""
    db_user = User(
        username=user_in.username,
        email=user_in.email,
        full_name=user_in.full_name,
        password_hash=get_password_hash(user_in.password),
        role=user_in.role,
        phone=user_in.phone,
        department_id=user_in.department_id,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """Verify credentials and return the user if valid."""
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Generate a JWT access token."""
    settings = get_settings()
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )
        
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt
