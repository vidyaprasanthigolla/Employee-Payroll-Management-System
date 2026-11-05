from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.auth import UserLogin, UserCreate, UserResponse, Token, PasswordChange
from app.services.auth_service import AuthService
from app.core.dependencies import get_current_active_user, require_admin
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token, summary="User login with JSON credentials")
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user with username or email and password.
    Returns signed JWT access token and user metadata.
    """
    user = AuthService.authenticate_user(
        db=db,
        username_or_email=credentials.username_or_email,
        password=credentials.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact your system administrator."
        )

    return AuthService.generate_token_for_user(user)


@router.post("/token", response_model=Token, summary="OAuth2 compatible token login (form-data)")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """OAuth2 password flow endpoint enabling Swagger UI 'Authorize' lock button."""
    user = AuthService.authenticate_user(
        db=db,
        username_or_email=form_data.username,
        password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive."
        )

    return AuthService.generate_token_for_user(user)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Create a new user account (Admin only)")
def register_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin)
):
    """
    Creates a new user account with specified RBAC role.
    Protected: Only administrators can register new user accounts.
    """
    return AuthService.create_user(db=db, user_in=user_in)


@router.get("/me", response_model=UserResponse, summary="Retrieve current authenticated user profile")
def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Returns the authenticated user's profile and active role."""
    return current_user


@router.post("/change-password", summary="Change password for current logged-in user")
def change_password(
    payload: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Allows authenticated user to update their account password."""
    AuthService.change_password(
        db=db,
        user=current_user,
        current_password=payload.current_password,
        new_password=payload.new_password
    )
    return {"message": "Password changed successfully."}
