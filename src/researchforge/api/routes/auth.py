"""Authentication endpoints — register, login, and current user."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator

from researchforge.auth.dependencies import AuthenticatedUser
from researchforge.auth.jwt import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

_bearer_scheme = HTTPBearer(auto_error=False)
_bearer_security = Security(_bearer_scheme)


def _normalize_email(value: object) -> object:
    # Phone keyboards capitalise the first letter and autofill can add spaces;
    # without this the same person gets "Invalid email or password".
    return value.strip().lower() if isinstance(value, str) else value


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=6, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        return _normalize_email(value)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        return _normalize_email(value)


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


class UserResponse(BaseModel):
    id: str
    email: str
    name: str


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(body: RegisterRequest, request: Request) -> AuthResponse:
    from researchforge.auth.postgres_user_store import PostgresUserStore

    user_store: PostgresUserStore | None = getattr(request.app.state, "user_store", None)
    if user_store is None:
        raise HTTPException(status_code=503, detail="Registration unavailable")

    if await user_store.email_exists(body.email):
        raise HTTPException(status_code=409, detail="Email already registered")

    user = await user_store.create_user(body.email, body.name, body.password)
    token = create_access_token(user.id, user.email, user.name)
    return AuthResponse(
        token=token,
        user=UserResponse(id=user.id, email=user.email, name=user.name),
    )


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, request: Request) -> AuthResponse:
    from researchforge.auth.postgres_user_store import PostgresUserStore

    user_store: PostgresUserStore | None = getattr(request.app.state, "user_store", None)
    if user_store is None:
        raise HTTPException(status_code=503, detail="Login unavailable")

    user = await user_store.authenticate(body.email, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user.id, user.email, user.name)
    return AuthResponse(
        token=token,
        user=UserResponse(id=user.id, email=user.email, name=user.name),
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = _bearer_security,
) -> UserResponse:
    from researchforge.auth.dependencies import AuthDependency

    auth: AuthDependency = request.app.state.auth_dependency
    user: AuthenticatedUser = await auth(request, credentials)
    return UserResponse(id=user.id, email=user.email, name=user.name)
