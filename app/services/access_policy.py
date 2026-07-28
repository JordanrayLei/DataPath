from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass

from app.config import get_settings


POLICY_VERSION = "production_tenant_v1"


@dataclass(frozen=True)
class IdentityPolicy:
    operator_id: str
    role_id: str
    allowed_domains: tuple[str, ...]
    tenant_ids: tuple[int, ...] | None = None
    can_query_business_data: bool = True

    @property
    def scope_label(self) -> str:
        if self.tenant_ids is not None:
            return "租户 " + "、".join(str(item) for item in self.tenant_ids)
        return "全国"

    @property
    def scope_fingerprint(self) -> str:
        raw = (
            f"{POLICY_VERSION}|{self.operator_id}|{self.role_id}|"
            f"{self.tenant_ids}"
        )
        return hashlib.sha256(raw.encode()).hexdigest()


def _policies() -> dict[str, IdentityPolicy]:
    return {
        "public_demo_user": IdentityPolicy(
            operator_id="public_demo_user",
            role_id="public_viewer",
            allowed_domains=("production_benchmark",),
        ),
        "metric_admin": IdentityPolicy(
            operator_id="metric_admin",
            role_id="metric_admin",
            allowed_domains=(),
            can_query_business_data=False,
        ),
        "production_analyst": IdentityPolicy(
            operator_id="production_analyst",
            role_id="production_analyst",
            allowed_domains=("production_benchmark",),
        ),
        "production_tenant_1": IdentityPolicy(
            operator_id="production_tenant_1",
            role_id="production_tenant_analyst",
            allowed_domains=("production_benchmark",),
            tenant_ids=(1,),
        ),
        "production_tenant_2": IdentityPolicy(
            operator_id="production_tenant_2",
            role_id="production_tenant_analyst",
            allowed_domains=("production_benchmark",),
            tenant_ids=(2,),
        ),
    }


def resolve_identity_token(token: str) -> IdentityPolicy | None:
    settings = get_settings()
    if token.startswith("idt.v1."):
        try:
            _, _, encoded, signature = token.split(".", 3)
            expected = hmac.new(
                settings.signing_secret.encode(), encoded.encode(), hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected):
                return None
            padding = "=" * (-len(encoded) % 4)
            payload = json.loads(base64.urlsafe_b64decode(encoded + padding))
            if int(payload["exp"]) < int(time.time()):
                return None
            return _policies().get(str(payload["operator_id"]))
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            return None
    token_map = {
        "": "public_demo_user",
        settings.demo_identity_token: "public_demo_user",
    }
    operator_id = token_map.get(token)
    return _policies().get(operator_id) if operator_id else None


def policy_for_operator(operator_id: str) -> IdentityPolicy | None:
    return _policies().get(operator_id)


def issue_demo_identity_token(operator_id: str, expires_at: int | None = None) -> str:
    settings = get_settings()
    if operator_id not in _policies():
        raise ValueError("operator policy does not exist")
    payload = {
        "operator_id": operator_id,
        "exp": expires_at
        if expires_at is not None
        else int(time.time()) + settings.demo_identity_ttl_seconds,
    }
    encoded = base64.urlsafe_b64encode(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).decode().rstrip("=")
    signature = hmac.new(
        settings.signing_secret.encode(), encoded.encode(), hashlib.sha256
    ).hexdigest()
    return f"idt.v1.{encoded}.{signature}"
