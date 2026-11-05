from typing import Generator, List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.config import settings
from app.db.session import get_db
from app.core.security import decode_access_token
from app.models.user import User, UserRole
from app.core.exceptions import PermissionDeniedException

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/token",
    auto_error=False
)


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """
    Validates JWT token from Authorization header and returns current user.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate authentication credentials. Please login again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception

    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception

    user_id_str: str = payload.get("sub")
    if not user_id_str:
        raise credentials_exception

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise credentials_exception

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Verifies that the authenticated user account is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated. Contact an administrator."
        )
    return current_user


class RoleChecker:
    """
    Dependency callable that validates if the authenticated user has
    one of the allowed RBAC roles.
    """
    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in self.allowed_roles:
            role_names = ", ".join([r.value for r in self.allowed_roles])
            raise PermissionDeniedException(
                f"Access denied. Requires one of the following roles: [{role_names}]. "
                f"Your role is '{current_user.role.value}'."
            )
        return current_user


# Role presets for convenient route injection
require_admin = RoleChecker([UserRole.ADMIN])
require_hr_or_admin = RoleChecker([UserRole.ADMIN, UserRole.HR])
require_authenticated = get_current_active_user
