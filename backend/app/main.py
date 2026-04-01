import logging
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.application import ingest
from app.auth_dependency import require_v1_auth
from app.auth_rate_limit import AuthLoginRateLimiter
from app.auth_routes import router as auth_router
from app.config import (
    GRAPH_VALIDATE_MAX_EDGES,
    GRAPH_VALIDATE_MAX_NODES,
    TABULAR_MAPPING_JSON_MAX_LEN,
    cors_origins,
    login_rate_limit_per_minute,
    openapi_enabled,
    rate_limit_per_minute,
    validate_auth_env,
)
from app.domain.models import ErrorBody, HostIpPasteRequest, NetworkGraph, TabularMapping
from app.http_responses import json_422_value_error, reject_if_oversized
from app.max_body import MaxBodySizeMiddleware
from app.parsers import host_ip_table
from app.request_logging import RequestLogMiddleware
from app.security_headers import SecurityHeadersMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s %(message)s",
)


def _graph_response(graph: NetworkGraph) -> Response:
    return Response(
        content=graph.model_dump_json(by_alias=True),
        media_type="application/json",
    )


def create_app() -> FastAPI:
    validate_auth_env()
    rpm = rate_limit_per_minute()
    lim_on = rpm is not None
    default_limits = [f"{rpm}/minute"] if lim_on else []
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=default_limits,
        enabled=lim_on,
    )
    oa = openapi_enabled()
    app = FastAPI(
        title="IPovtich API",
        version="0.1.0",
        description=(
            "Stable HTTP surface under prefix **/v1**. "
            "`GET /health` stays at the root for probes. "
            "Breaking changes will bump the path prefix (e.g. /v2) before removal.\n\n"
            "**Auth (choose one or combine):** "
            "(1) **JWT session** — set **IPOVITCH_JWT_SECRET** (≥32 chars) plus "
            "**IPOVITCH_LOGIN_PASSWORD** or **IPOVITCH_LOGIN_PASSWORD_HASH** (bcrypt); "
            "exchange password at `POST /v1/auth/token`, then send `Authorization: Bearer <jwt>`. "
            "(2) **Static API key** — **IPOVITCH_API_KEY** for scripts and automation. "
            "Browsers should prefer JWT (no secret in the frontend build). "
            "Set **IPOVITCH_OPENAPI_ENABLED=0** to hide docs. "
            "Optional **IPOVITCH_RATE_LIMIT_PER_MINUTE** for per-IP limits."
        ),
        docs_url="/docs" if oa else None,
        openapi_url="/openapi.json" if oa else None,
        redoc_url="/redoc" if oa else None,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    login_rl = login_rate_limit_per_minute()
    app.state.auth_login_rl = (
        AuthLoginRateLimiter(login_rl) if login_rl is not None else None
    )

    app.add_middleware(MaxBodySizeMiddleware)
    app.add_middleware(RequestLogMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=[
            "Accept",
            "Content-Type",
            "X-Request-ID",
            "Authorization",
            "X-Api-Key",
        ],
    )

    v1 = APIRouter(prefix="/v1", dependencies=[Depends(require_v1_auth)])

    @v1.post("/parse/nmap")
    async def parse_nmap(
        file: UploadFile = File(...),
    ) -> Response:
        raw = await file.read()
        too_large = reject_if_oversized(raw)
        if too_large is not None:
            return too_large
        name = file.filename or "scan.xml"
        try:
            graph = ingest.parse_nmap_file(name, raw)
        except ValueError as e:
            return json_422_value_error(e)
        return _graph_response(graph)

    @v1.post("/parse/host-ip-table")
    async def parse_host_ip_table_route(
        file: UploadFile = File(...),
    ) -> Response:
        raw = await file.read()
        too_large = reject_if_oversized(raw)
        if too_large is not None:
            return too_large
        try:
            graph = host_ip_table.parse_host_ip_table(raw)
        except ValueError as e:
            return json_422_value_error(e)
        return _graph_response(graph)

    @v1.post("/parse/host-ip-table-paste")
    async def parse_host_ip_paste(payload: HostIpPasteRequest) -> Response:
        raw = payload.text.encode("utf-8")
        try:
            graph = host_ip_table.parse_host_ip_table(raw)
        except ValueError as e:
            return json_422_value_error(e)
        return _graph_response(graph)

    @v1.post("/parse/tabular")
    async def parse_tabular_route(
        mapping: Annotated[str, Form()],
        file: UploadFile = File(...),
    ) -> Response:
        raw = await file.read()
        too_large = reject_if_oversized(raw)
        if too_large is not None:
            return too_large
        if len(mapping) > TABULAR_MAPPING_JSON_MAX_LEN:
            body = ErrorBody(code="MAPPING_TOO_LARGE", detail="MAPPING_TOO_LARGE")
            return JSONResponse(status_code=422, content=body.model_dump())
        try:
            m = TabularMapping.model_validate_json(mapping)
        except ValidationError:
            body = ErrorBody(code="MAPPING_INVALID", detail="MAPPING_INVALID")
            return JSONResponse(status_code=422, content=body.model_dump())
        try:
            graph = ingest.parse_tabular_file(raw, m)
        except ValueError as e:
            return json_422_value_error(e)
        return _graph_response(graph)

    @v1.post("/graph/validate")
    async def validate_topology(request: Request) -> Response:
        raw = await request.body()
        too_large = reject_if_oversized(raw)
        if too_large is not None:
            return too_large
        try:
            graph = NetworkGraph.model_validate_json(raw)
        except ValidationError:
            body = ErrorBody(code="GRAPH_INVALID", detail="GRAPH_INVALID")
            return JSONResponse(status_code=422, content=body.model_dump())
        if len(graph.nodes) > GRAPH_VALIDATE_MAX_NODES:
            body = ErrorBody(
                code="GRAPH_TOO_MANY_NODES",
                detail=str(GRAPH_VALIDATE_MAX_NODES),
            )
            return JSONResponse(status_code=422, content=body.model_dump())
        if len(graph.edges) > GRAPH_VALIDATE_MAX_EDGES:
            body = ErrorBody(
                code="GRAPH_TOO_MANY_EDGES",
                detail=str(GRAPH_VALIDATE_MAX_EDGES),
            )
            return JSONResponse(status_code=422, content=body.model_dump())
        return _graph_response(graph)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth_router)
    app.include_router(v1)
    return app


app = create_app()
