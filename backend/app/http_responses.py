from fastapi.responses import JSONResponse

from app import config as app_config
from app.domain.models import ErrorBody


def json_413_upload_limit(limit: int) -> JSONResponse:
    body = ErrorBody(code="UPLOAD_TOO_LARGE", detail=str(limit))
    return JSONResponse(status_code=413, content=body.model_dump())


def json_422_value_error(exc: ValueError) -> JSONResponse:
    code = str(exc.args[0]) if exc.args else "PARSE_ERROR"
    body = ErrorBody(code=code, detail=code)
    return JSONResponse(status_code=422, content=body.model_dump())


def reject_if_oversized(raw: bytes) -> JSONResponse | None:
    limit = app_config.max_upload_bytes()
    if len(raw) > limit:
        return json_413_upload_limit(limit)
    return None
