from pydantic import BaseModel, ConfigDict, EmailStr


class UserListResponse(BaseModel):
    users: list["UserAdminResponse"]


class UserAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    display_name: str
    role: str


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str
    role: str = "user"


class UpdateUserRequest(BaseModel):
    display_name: str | None = None
    role: str | None = None
    password: str | None = None


class DeleteUserResponse(BaseModel):
    message: str


class ServiceStatus(BaseModel):
    name: str
    status: str  # running, stopped, error
    container_id: str | None = None


class ServiceListResponse(BaseModel):
    services: list[ServiceStatus]


class RestartServiceResponse(BaseModel):
    message: str
    service: str


class ModelInfo(BaseModel):
    id: str
    name: str
    active: bool


class ModelListResponse(BaseModel):
    models: list[ModelInfo]


class SwitchModelRequest(BaseModel):
    model_id: str


class SwitchModelResponse(BaseModel):
    message: str
    model_id: str


class UnloadModelResponse(BaseModel):
    message: str
