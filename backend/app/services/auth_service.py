from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.user import User, UserRole
from app.schemas.auth import UserCreate, Token
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.exceptions import DuplicateResourceException, PayrollException


class AuthService:
    @staticmethod
    def authenticate_user(db: Session, username_or_email: str, password: str) -> Optional[User]:
        """Validates credentials against email or username and verifies password."""
        user = db.query(User).filter(
            or_(
                User.username == username_or_email.strip(),
                User.email == username_or_email.strip().lower()
            )
        ).first()

        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    @staticmethod
    def create_user(db: Session, user_in: UserCreate) -> User:
        """Registers a new user, checking for existing username/email collisions."""
        existing_user = db.query(User).filter(
            or_(
                User.username == user_in.username.strip(),
                User.email == user_in.email.strip().lower()
            )
        ).first()

        if existing_user:
            if existing_user.username == user_in.username.strip():
                raise DuplicateResourceException(f"Username '{user_in.username}' is already taken.")
            raise DuplicateResourceException(f"Email '{user_in.email}' is already registered.")

        db_user = User(
            username=user_in.username.strip(),
            email=user_in.email.strip().lower(),
            password_hash=get_password_hash(user_in.password),
            role=user_in.role,
            is_active=user_in.is_active
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def generate_token_for_user(user: User) -> Token:
        """Generates a signed JWT bearer token with embedded role claims."""
        access_token = create_access_token(
            subject=user.id,
            role=user.role.value
        )
        return Token(
            access_token=access_token,
            token_type="bearer",
            role=user.role.value,
            user_id=user.id,
            username=user.username,
            email=user.email
        )

    @staticmethod
    def change_password(db: Session, user: User, current_password: str, new_password: str) -> bool:
        """Updates the password after verifying the old password."""
        if not verify_password(current_password, user.password_hash):
            raise PayrollException("Current password provided does not match.", status_code=400)
        user.password_hash = get_password_hash(new_password)
        db.commit()
        return True
