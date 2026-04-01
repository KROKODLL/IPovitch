from fastapi import APIRouter, Depends, HTTPException, status

from app.auth_jwt import create_access_token
from app.auth_password import verify_login_password
from app.auth_rate_limit import enforce_login_rate_limit
from app.config import auth_required, jwt_auth_configured, jwt_ttl_seconds
from app.domain.models import AuthStatusResponse, LoginRequest, TokenResponse

router = APIRouter(prefix="/v1")


@router.get("/auth/status", response_model=AuthStatusResponse)
def auth_status() -> AuthStatusResponse:
    return AuthStatusResponse(
        token_login=jwt_auth_configured(),
        requires_auth=auth_required(),
    )


@router.post(
    "/auth/token",
    response_model=TokenResponse,
    dependencies=[Depends(enforce_login_rate_limit)],
)
def auth_token(body: LoginRequest) -> TokenResponse:
    if not jwt_auth_configured():
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="TOKEN_LOGIN_DISABLED")
    if not verify_login_password(body.password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    return TokenResponse(
        access_token=create_access_token(),
        token_type="bearer",
        expires_in=jwt_ttl_seconds(),
    )
