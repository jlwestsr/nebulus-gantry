from pydantic import BaseModel, ConfigDict, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class UserResponse(BaseModel):
    """Response model for the authenticated user profile."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    display_name: str
    first_name: str | None = None
    username: str | None = None
    role: str
