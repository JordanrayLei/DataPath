from __future__ import annotations

import base64
import hashlib
import hmac


def sign_value(value: str, secret: str) -> str:
    digest = hmac.new(secret.encode(), value.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def create_execution_token(query_id: str, fingerprint: str, expires_at: str, secret: str) -> str:
    payload = f"{query_id}|{fingerprint}|{expires_at}"
    return f"v1.{sign_value(payload, secret)}"


def verify_execution_token(
    token: str,
    query_id: str,
    fingerprint: str,
    expires_at: str,
    secret: str,
) -> bool:
    expected = create_execution_token(query_id, fingerprint, expires_at, secret)
    return hmac.compare_digest(token, expected)

