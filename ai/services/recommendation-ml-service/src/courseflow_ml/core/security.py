from __future__ import annotations

import base64
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import jwt
from fastapi import Header, HTTPException, Request, status
from jwt import PyJWKClient

from courseflow_ml.core.config import Settings, get_settings
from courseflow_ml.core.telemetry import record_internal_auth_rejection

TRAIN_SCOPE = "internal:recommendation-ml:train"
INFER_SCOPE = "internal:recommendation-ml:infer"
OPS_SCOPE = "internal:recommendation-ml:ops"


@dataclass(frozen=True, slots=True)
class Principal:
    actor_type: str
    actor_id: str
    scopes: set[str]
    roles: set[str]


class InternalJwtVerifier:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._jwks_client = self._build_jwks_client()

    def verify(self, token: str) -> dict[str, Any]:
        algorithm = self.settings.courseflow_internal_jwt_algorithm
        try:
            key = self.verification_key(token)
            claims = jwt.decode(
                token,
                key,
                algorithms=[algorithm],
                audience=self.settings.courseflow_internal_jwt_audience,
                issuer=self.settings.courseflow_internal_jwt_issuer,
                leeway=self.settings.courseflow_internal_jwt_clock_skew_seconds,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
        except HTTPException:
            raise
        except jwt.PyJWTError as exc:
            record_internal_auth_rejection("invalid_jwt")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid internal JWT",
            ) from exc
        except Exception as exc:
            record_internal_auth_rejection("verifier_unavailable")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Internal JWT verifier unavailable",
            ) from exc
        if claims.get("token_use") != "internal":
            record_internal_auth_rejection("wrong_token_use")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Wrong token use")
        actor_type = claims.get("actor_type")
        if actor_type not in {"service", "user"}:
            record_internal_auth_rejection("wrong_actor_type")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Wrong actor type")
        self.validate_token_ttl(claims)
        return claims

    def verification_key(self, token: str) -> str | Any:
        algorithm = self.settings.courseflow_internal_jwt_algorithm
        mode = self.settings.courseflow_internal_jwt_verification_mode.lower()
        if mode == "jwks":
            if self._jwks_client is None:
                raise HTTPException(status_code=503, detail="JWKS verifier is not configured")
            return self._jwks_client.get_signing_key_from_jwt(token).key
        if algorithm.upper().startswith("RS"):
            return self.settings.courseflow_internal_jwt_public_key
        return self.settings.courseflow_internal_jwt_secret

    def _build_jwks_client(self) -> PyJWKClient | None:
        if self.settings.courseflow_internal_jwt_verification_mode.lower() != "jwks":
            return None
        return PyJWKClient(
            self.settings.courseflow_internal_jwt_jwks_uri,
            cache_keys=True,
            max_cached_keys=16,
            cache_jwk_set=True,
            lifespan=self.settings.courseflow_internal_jwt_jwks_cache_ttl_seconds,
            timeout=self.settings.courseflow_internal_jwt_jwks_timeout_seconds,
        )

    def validate_token_ttl(self, claims: dict[str, Any]) -> None:
        issued_at = numeric_date_claim(claims.get("iat"))
        expires_at = numeric_date_claim(claims.get("exp"))
        if issued_at is None or expires_at is None or expires_at <= issued_at:
            record_internal_auth_rejection("invalid_lifetime")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid internal JWT lifetime",
            )
        ttl_seconds = expires_at - issued_at
        if ttl_seconds > self.settings.courseflow_internal_jwt_max_ttl_seconds:
            record_internal_auth_rejection("lifetime_exceeds_policy")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Internal JWT lifetime exceeds policy",
            )


@lru_cache
def get_internal_jwt_verifier() -> InternalJwtVerifier:
    return InternalJwtVerifier(get_settings())


def require_platform_admin_or_scope(required_scope: str) -> Callable[..., Awaitable[Principal]]:
    async def dependency(
        _request: Request,
        authorization: str | None = Header(default=None),
        x_internal_authorization: str | None = Header(
            default=None,
            alias="X-Internal-Authorization",
        ),
        x_user_id: str | None = Header(default=None, alias="X-User-Id"),
        x_user_email: str | None = Header(default=None, alias="X-User-Email"),
        x_user_role: str | None = Header(default=None, alias="X-User-Role"),
        x_user_roles: str | None = Header(default=None, alias="X-User-Roles"),
        x_user_role_scopes: str | None = Header(default=None, alias="X-User-Role-Scopes"),
    ) -> Principal:
        token = bearer_token(x_internal_authorization) or bearer_token(authorization)
        if token is None:
            record_internal_auth_rejection("missing_token")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Internal JWT required",
            )
        claims = get_internal_jwt_verifier().verify(token)
        actor_type = str(claims.get("actor_type"))
        scopes = extract_scopes(claims)
        roles = extract_role_codes(claims)

        if actor_type == "service":
            if required_scope in scopes:
                return Principal("service", str(claims.get("sub", "service")), scopes, roles)
            record_internal_auth_rejection("insufficient_scope")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient service scope",
            )

        if actor_type == "user":
            if not identity_claims_match_headers(
                claims,
                x_user_id,
                x_user_email,
                x_user_role,
                x_user_roles,
                x_user_role_scopes,
            ):
                record_internal_auth_rejection("gateway_identity_mismatch")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Gateway identity mismatch",
                )
            if "ADMIN" in {role.upper() for role in roles}:
                return Principal("user", f"user:{x_user_id}", scopes, roles)
            record_internal_auth_rejection("platform_admin_required")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Platform admin required",
            )

        record_internal_auth_rejection("forbidden")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    return dependency


def bearer_token(header: str | None) -> str | None:
    if not header:
        return None
    value = header.strip()
    if value.lower().startswith("bearer "):
        value = value[7:].strip()
    return value or None


def numeric_date_claim(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def extract_scopes(claims: dict[str, Any]) -> set[str]:
    scopes: set[str] = set()
    raw_scope = claims.get("scope")
    if raw_scope:
        scopes.update(scope.strip() for scope in str(raw_scope).split() if scope.strip())
    raw_scp = claims.get("scp")
    if isinstance(raw_scp, list):
        scopes.update(str(scope).strip() for scope in raw_scp if str(scope).strip())
    return scopes


def identity_claims_match_headers(
    claims: dict[str, Any],
    user_id_header: str | None,
    user_email_header: str | None,
    user_role_header: str | None,
    user_roles_header: str | None,
    user_role_scopes_header: str | None,
) -> bool:
    uid = claims.get("uid")
    if uid is None or not user_id_header or str(uid) != user_id_header:
        return False
    email_claim = claims.get("email")
    if (
        user_email_header
        and user_email_header.strip()
        and (email_claim is None or str(email_claim) != user_email_header)
    ):
        return False

    roles = extract_role_codes(claims)
    if not roles:
        return False
    if user_role_header and user_role_header.strip() and user_role_header.strip() not in roles:
        return False
    if user_roles_header and user_roles_header.strip() and roles != parse_csv(user_roles_header):
        return False
    return (
        not user_role_scopes_header
        or not user_role_scopes_header.strip()
        or encoded_role_scopes(claims) == parse_csv(user_role_scopes_header)
    )


def extract_role_codes(claims: dict[str, Any]) -> set[str]:
    roles: set[str] = set()
    raw_roles = claims.get("roles")
    if isinstance(raw_roles, list):
        add_role_codes(roles, raw_roles)
    raw_assignments = claims.get("role_assignments")
    if isinstance(raw_assignments, list):
        add_role_codes(roles, raw_assignments)
    return roles


def add_role_codes(roles: set[str], raw_values: Iterable[Any]) -> None:
    for raw in raw_values:
        if isinstance(raw, dict):
            code = raw.get("code")
            if code is not None and str(code).strip():
                roles.add(str(code))
        elif raw is not None and str(raw).strip():
            roles.add(str(raw))


def encoded_role_scopes(claims: dict[str, Any]) -> set[str]:
    raw_assignments = claims.get("role_assignments")
    if not isinstance(raw_assignments, list):
        return set()
    encoded: set[str] = set()
    for raw in raw_assignments:
        if not isinstance(raw, dict):
            continue
        code = raw.get("code")
        if code is None or not str(code).strip():
            continue
        encoded.add(
            ".".join(
                (
                    base64_url(str(code)),
                    base64_url(raw.get("scopeType")),
                    base64_url(raw.get("scopeId")),
                )
            )
        )
    return encoded


def base64_url(raw: Any) -> str:
    if raw is None or not str(raw).strip():
        return ""
    return base64.urlsafe_b64encode(str(raw).encode("utf-8")).decode("ascii").rstrip("=")


def parse_csv(value: str | None) -> set[str]:
    if not value:
        return set()
    return {item.strip() for item in value.split(",") if item.strip()}


def parse_roles(value: str | None) -> set[str]:
    return parse_csv(value)
