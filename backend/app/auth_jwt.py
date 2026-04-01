import time

import jwt

from app.config import jwt_secret, jwt_ttl_seconds

# Tight token binding: only this API should accept tokens it issued.
JWT_ISSUER = "ipovtich"
JWT_AUDIENCE = "ipovtich-v1"


def looks_like_jwt(token: str) -> bool:
    parts = token.split(".")
    return len(parts) == 3 and all(len(p) > 0 for p in parts)


def create_access_token() -> str:
    secret = jwt_secret()
    assert secret is not None
    ttl = jwt_ttl_seconds()
    now = int(time.time())
    payload = {
        "sub": "ipovtich",
        "iat": now,
        "exp": now + ttl,
        "typ": "access",
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_access_token(token: str) -> None:
    secret = jwt_secret()
    assert secret is not None
    jwt.decode(
        token,
        secret,
        algorithms=["HS256"],
        issuer=JWT_ISSUER,
        audience=JWT_AUDIENCE,
        options={"require": ["exp", "iat", "sub"]},
    )
