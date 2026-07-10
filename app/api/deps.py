from __future__ import annotations

from typing import Annotated

from fastapi import Header, HTTPException, status

from app.config import get_settings


def require_service_token(
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    expected = f"Bearer {get_settings().chatbi_api_token}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_SERVICE_TOKEN", "message": "服务认证失败。"},
        )

