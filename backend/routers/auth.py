from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session as DBSession

from backend.dependencies import get_db
from backend.services.auth_service import AuthService, hash_password, verify_password
from backend.schemas.auth import ChangePasswordRequest, LoginRequest, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_auth_service(db: DBSession = Depends(get_db)) -> AuthService:
    return AuthService(db)


def get_current_user(request: Request, auth: AuthService = Depends(get_auth_service)):
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = auth.validate_session(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return user


@router.post("/login")
def login(data: LoginRequest, response: Response, auth: AuthService = Depends(get_auth_service)):
    user = auth.authenticate(data.email, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = auth.create_session(user.id)
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=86400  # 24 hours
    )
    return {"message": "Login successful"}


@router.post("/logout")
def logout(request: Request, response: Response, auth: AuthService = Depends(get_auth_service)):
    token = request.cookies.get("session_token")
    if token:
        auth.delete_session(token)
    response.delete_cookie("session_token")
    return {"message": "Logout successful"}


@router.get("/me", response_model=UserResponse)
def get_me(user=Depends(get_current_user)):
    return user


@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    user=Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Change the current user's password.

    Requires the current password for verification.
    """
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.password_hash = hash_password(data.new_password)
    db.commit()
    return {"message": "Password changed successfully"}
