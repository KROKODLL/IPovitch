import secrets
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth_jwt import looks_like_jwt, verify_access_token
from app.config import api_key as configured_api_key
from app.config import auth_required, jwt_auth_configured

_optional_bearer = HTTPBearer(auto_error=False)


def _extract_bearer_token(
    authorization: str | None,
    x_api_key: str | None,
    credentials: HTTPAuthorizationCredentials | None,
) -> str | None:
    if credentials is not None and credentials.scheme.lower() == "bearer":
        return credentials.credentials
    if x_api_key is not None and x_api_key.strip() != "":
        return x_api_key.strip()
    if authorization is not None and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


async def require_v1_auth(
    authorization: Annotated[str | None, Header(include_in_schema=False)] = None,
    x_api_key: Annotated[str | None, Header(alias="X-Api-Key", include_in_schema=False)] = None,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_optional_bearer),
    ] = None,
) -> None:
    if not auth_required():
        return
    token = _extract_bearer_token(authorization, x_api_key, credentials)
    if token is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    if jwt_auth_configured() and looks_like_jwt(token):
        try:
            verify_access_token(token)
        except jwt.PyJWTError:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            ) from None
        return
    expected = configured_api_key()
    if expected is not None and secrets.compare_digest(token, expected):
        return
    raise HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication",
    )
