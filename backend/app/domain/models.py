from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app import config as app_config


class NodeData(BaseModel):
    label: str
    ip: str
    os: str | None = None
    ports: list[int] = Field(default_factory=list)
    services: list[str] | None = None


class NetworkNode(BaseModel):
    id: str
    type: Literal["host", "gateway", "subnet", "unknown"]
    data: NodeData


class NetworkEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str | None = None


class NetworkGraph(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    schema_version: int = Field(alias="schemaVersion", default=1)
    nodes: list[NetworkNode]
    edges: list[NetworkEdge]


class TabularMapping(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    source_key: str = Field(alias="sourceKey")
    target_key: str = Field(alias="targetKey")
    label_key: str | None = Field(default=None, alias="labelKey")


class HostIpPasteRequest(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def _utf8_within_upload_limit(cls, value: str) -> str:
        if len(value.encode("utf-8")) > app_config.max_upload_bytes():
            raise ValueError("UPLOAD_TOO_LARGE")
        return value


class ErrorBody(BaseModel):
    code: str
    detail: str


class LoginRequest(BaseModel):
    password: str = Field(..., max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthStatusResponse(BaseModel):
    token_login: bool
    requires_auth: bool
