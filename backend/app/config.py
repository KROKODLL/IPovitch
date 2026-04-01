import os
from urllib.parse import urlparse

MAX_UPLOAD_BYTES_DEFAULT = 10 * 1024 * 1024
MAX_UPLOAD_BYTES_HARD_CAP = 100 * 1024 * 1024
TABULAR_MAPPING_JSON_MAX_LEN = 16_384
GRAPH_VALIDATE_MAX_NODES = 50_000
GRAPH_VALIDATE_MAX_EDGES = 200_000

CORS_ORIGINS_DEFAULT = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


def max_upload_bytes() -> int:
    raw = os.environ.get("MAX_UPLOAD_BYTES")
    if raw is None or raw.strip() == "":
        return MAX_UPLOAD_BYTES_DEFAULT
    try:
        n = int(raw.strip())
    except ValueError:
        return MAX_UPLOAD_BYTES_DEFAULT
    return max(1, min(n, MAX_UPLOAD_BYTES_HARD_CAP))


def _valid_cors_origin(origin: str) -> bool:
    if origin.strip() == "*" or "*" in origin:
        return False
    parsed = urlparse(origin)
    if parsed.scheme not in ("http", "https"):
        return False
    if parsed.netloc == "":
        return False
    return True


def api_key() -> str | None:
    raw = os.environ.get("IPOVITCH_API_KEY", "").strip()
    return raw or None


def jwt_secret() -> str | None:
    raw = os.environ.get("IPOVITCH_JWT_SECRET", "").strip()
    if raw == "":
        return None
    if len(raw) < 32:
        raise ValueError("IPOVITCH_JWT_SECRET must be at least 32 characters")
    return raw


def login_password_plain() -> str | None:
    raw = os.environ.get("IPOVITCH_LOGIN_PASSWORD", "").strip()
    return raw or None


def login_password_hash() -> str | None:
    raw = os.environ.get("IPOVITCH_LOGIN_PASSWORD_HASH", "").strip()
    return raw or None


def jwt_ttl_seconds() -> int:
    raw = os.environ.get("IPOVITCH_JWT_TTL_SECONDS", "").strip()
    if raw == "":
        return 8 * 3600
    try:
        n = int(raw)
    except ValueError:
        return 8 * 3600
    return max(60, min(n, 86400 * 7))


def jwt_auth_configured() -> bool:
    return jwt_secret() is not None


def auth_required() -> bool:
    return api_key() is not None or jwt_auth_configured()


def validate_auth_env() -> None:
    j_raw = os.environ.get("IPOVITCH_JWT_SECRET", "").strip()
    has_login = bool(os.environ.get("IPOVITCH_LOGIN_PASSWORD", "").strip()) or bool(
        os.environ.get("IPOVITCH_LOGIN_PASSWORD_HASH", "").strip()
    )
    if has_login != bool(j_raw):
        if has_login:
            raise ValueError(
                "Set IPOVITCH_JWT_SECRET when using IPOVITCH_LOGIN_PASSWORD(_HASH)",
            )
        raise ValueError(
            "IPOVITCH_JWT_SECRET requires IPOVITCH_LOGIN_PASSWORD or IPOVITCH_LOGIN_PASSWORD_HASH",
        )
    if j_raw and len(j_raw) < 32:
        raise ValueError("IPOVITCH_JWT_SECRET must be at least 32 characters")


def openapi_enabled() -> bool:
    raw = os.environ.get("IPOVITCH_OPENAPI_ENABLED", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def login_rate_limit_per_minute() -> int | None:
    """Brute-force guard on POST /v1/auth/token. None = disabled (not recommended in production)."""
    raw = os.environ.get("IPOVITCH_LOGIN_RATE_PER_MINUTE", "20").strip().lower()
    if raw in ("", "0", "off", "none", "false"):
        return None
    try:
        n = int(raw)
    except ValueError:
        return 20
    if n <= 0:
        return None
    return min(n, 500)


def hsts_max_age_seconds() -> int | None:
    """If set, send Strict-Transport-Security (use only behind HTTPS)."""
    raw = os.environ.get("IPOVITCH_HSTS_MAX_AGE", "").strip()
    if raw == "":
        return None
    try:
        n = int(raw)
    except ValueError:
        return None
    return n if n > 0 else None


def rate_limit_per_minute() -> int | None:
    raw = os.environ.get("IPOVITCH_RATE_LIMIT_PER_MINUTE", "").strip()
    if raw == "":
        return None
    try:
        n = int(raw)
    except ValueError:
        return None
    return n if n > 0 else None


def cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS")
    if raw is None or raw.strip() == "":
        return list(CORS_ORIGINS_DEFAULT)
    out: list[str] = []
    for part in raw.split(","):
        o = part.strip()
        if o == "":
            continue
        if not _valid_cors_origin(o):
            msg = f"Invalid CORS origin (use full http(s) URL, no wildcards): {o!r}"
            raise ValueError(msg)
        out.append(o)
    return out if out else list(CORS_ORIGINS_DEFAULT)
