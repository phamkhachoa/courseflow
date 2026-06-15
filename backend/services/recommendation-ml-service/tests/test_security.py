from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from unittest.mock import Mock, patch

import jwt
from fastapi import HTTPException
from pydantic import ValidationError

from courseflow_ml.core.config import Settings
from courseflow_ml.core.security import (
    TRAIN_SCOPE,
    InternalJwtVerifier,
    encoded_role_scopes,
    extract_role_codes,
    identity_claims_match_headers,
)


class SecurityHeaderParityTest(unittest.TestCase):
    def test_identity_headers_match_verified_internal_claims(self) -> None:
        claims = {
            "uid": "42",
            "email": "admin@example.com",
            "roles": ["ADMIN", "INSTRUCTOR"],
            "role_assignments": [
                {"code": "ADMIN", "scopeType": "PLATFORM", "scopeId": None},
                {"code": "INSTRUCTOR", "scopeType": "ORG", "scopeId": "7"},
            ],
        }

        self.assertTrue(
            identity_claims_match_headers(
                claims,
                "42",
                "admin@example.com",
                "ADMIN",
                "ADMIN,INSTRUCTOR",
                ",".join(sorted(encoded_role_scopes(claims))),
            )
        )

    def test_forged_admin_header_does_not_match_student_token(self) -> None:
        claims = {
            "uid": "42",
            "email": "learner@example.com",
            "roles": ["STUDENT"],
            "role_assignments": [
                {"code": "STUDENT", "scopeType": "PLATFORM", "scopeId": None},
            ],
        }

        self.assertFalse(
            identity_claims_match_headers(
                claims,
                "42",
                "learner@example.com",
                "ADMIN",
                "ADMIN",
                None,
            )
        )

    def test_role_codes_support_gateway_assignment_claim_shape(self) -> None:
        claims = {
            "role_assignments": [
                {"code": "ADMIN", "scopeType": "PLATFORM", "scopeId": None},
                {"code": "INSTRUCTOR", "scopeType": "ORG", "scopeId": "7"},
            ],
        }

        self.assertEqual(extract_role_codes(claims), {"ADMIN", "INSTRUCTOR"})

    def test_settings_reject_missing_hs256_secret(self) -> None:
        with self.assertRaises(ValidationError):
            settings_without_env(courseflow_internal_jwt_secret="")

    def test_settings_reject_short_recommendation_ml_principal_hash_secret(self) -> None:
        with self.assertRaises(ValidationError):
            settings_without_env(recommendation_ml_principal_hash_secret="too-short")

    def test_settings_rejects_non_http_jwks_uri(self) -> None:
        with self.assertRaises(ValidationError):
            settings_without_env(
                courseflow_internal_jwt_algorithm="RS256",
                courseflow_internal_jwt_verification_mode="jwks",
                courseflow_internal_jwt_jwks_uri="file:///tmp/jwks.json",
            )

    def test_settings_rejects_local_jwks_uri(self) -> None:
        for uri in (
            "http://localhost:8080/oauth/jwks",
            "http://127.0.0.1:8080/oauth/jwks",
            "http://0.0.0.0:8080/oauth/jwks",
            "http://[::1]:8080/oauth/jwks",
            "http://host.docker.internal:8080/oauth/jwks",
        ):
            with self.subTest(uri=uri):
                with self.assertRaises(ValidationError):
                    settings_without_env(
                        courseflow_internal_jwt_algorithm="RS256",
                        courseflow_internal_jwt_verification_mode="jwks",
                        courseflow_internal_jwt_jwks_uri=uri,
                    )

    def test_settings_allows_internal_service_dns_jwks_uri(self) -> None:
        settings = settings_without_env(
            courseflow_internal_jwt_algorithm="RS256",
            courseflow_internal_jwt_verification_mode="jwks",
            courseflow_internal_jwt_jwks_uri=(
                "http://identity-token-converter-service:8080/oauth/jwks"
            ),
        )

        self.assertEqual(
            settings.courseflow_internal_jwt_jwks_uri,
            "http://identity-token-converter-service:8080/oauth/jwks",
        )

    def test_internal_jwt_verifier_accepts_expected_issuer_and_audience(self) -> None:
        secret = "courseflow-local-internal-jwt-secret-change-me-32"
        settings = settings_without_env(courseflow_internal_jwt_secret=secret)
        now = datetime.now(UTC)
        token = jwt.encode(
            {
                "iss": settings.courseflow_internal_jwt_issuer,
                "aud": settings.courseflow_internal_jwt_audience,
                "sub": "service:analytics-service",
                "iat": now,
                "exp": now + timedelta(minutes=5),
                "token_use": "internal",
                "actor_type": "service",
                "scope": TRAIN_SCOPE,
            },
            secret,
            algorithm="HS256",
        )

        claims = InternalJwtVerifier(settings).verify(token)

        self.assertEqual(claims["sub"], "service:analytics-service")
        self.assertEqual(claims["iss"], "courseflow-token-converter")

    def test_internal_jwt_verifier_rejects_wrong_issuer(self) -> None:
        secret = "courseflow-local-internal-jwt-secret-change-me-32"
        settings = settings_without_env(courseflow_internal_jwt_secret=secret)
        now = datetime.now(UTC)
        token = jwt.encode(
            {
                "iss": "wrong-issuer",
                "aud": settings.courseflow_internal_jwt_audience,
                "sub": "service:analytics-service",
                "iat": now,
                "exp": now + timedelta(minutes=5),
                "token_use": "internal",
                "actor_type": "service",
                "scope": TRAIN_SCOPE,
            },
            secret,
            algorithm="HS256",
        )

        with self.assertRaises(HTTPException) as raised:
            InternalJwtVerifier(settings).verify(token)

        self.assertEqual(raised.exception.status_code, 403)

    def test_internal_jwt_verifier_rejects_missing_iat(self) -> None:
        secret = "courseflow-local-internal-jwt-secret-change-me-32"
        settings = settings_without_env(courseflow_internal_jwt_secret=secret)
        token = jwt.encode(
            {
                "iss": settings.courseflow_internal_jwt_issuer,
                "aud": settings.courseflow_internal_jwt_audience,
                "sub": "service:analytics-service",
                "exp": datetime.now(UTC) + timedelta(minutes=5),
                "token_use": "internal",
                "actor_type": "service",
                "scope": TRAIN_SCOPE,
            },
            secret,
            algorithm="HS256",
        )

        with self.assertRaises(HTTPException) as raised:
            InternalJwtVerifier(settings).verify(token)

        self.assertEqual(raised.exception.status_code, 403)

    def test_internal_jwt_verifier_rejects_ttl_above_policy(self) -> None:
        secret = "courseflow-local-internal-jwt-secret-change-me-32"
        settings = settings_without_env(
            courseflow_internal_jwt_secret=secret,
            courseflow_internal_jwt_max_ttl_seconds=900,
        )
        now = datetime.now(UTC)
        token = jwt.encode(
            {
                "iss": settings.courseflow_internal_jwt_issuer,
                "aud": settings.courseflow_internal_jwt_audience,
                "sub": "service:analytics-service",
                "iat": now,
                "exp": now + timedelta(seconds=901),
                "token_use": "internal",
                "actor_type": "service",
                "scope": TRAIN_SCOPE,
            },
            secret,
            algorithm="HS256",
        )

        with self.assertRaises(HTTPException) as raised:
            InternalJwtVerifier(settings).verify(token)

        self.assertEqual(raised.exception.status_code, 403)

    def test_jwks_verifier_uses_bounded_cached_client(self) -> None:
        with patch("courseflow_ml.core.security.PyJWKClient") as jwks_client:
            InternalJwtVerifier(
                settings_without_env(
                    courseflow_internal_jwt_algorithm="RS256",
                    courseflow_internal_jwt_verification_mode="jwks",
                    courseflow_internal_jwt_jwks_uri="https://issuer.example.test/jwks",
                    courseflow_internal_jwt_jwks_cache_ttl_seconds=120,
                    courseflow_internal_jwt_jwks_timeout_seconds=3,
                )
            )

        jwks_client.assert_called_once_with(
            "https://issuer.example.test/jwks",
            cache_keys=True,
            max_cached_keys=16,
            cache_jwk_set=True,
            lifespan=120,
            timeout=3,
        )

    def test_jwks_lookup_errors_fail_closed_without_500(self) -> None:
        verifier = InternalJwtVerifier(
            settings_without_env(
                courseflow_internal_jwt_algorithm="RS256",
                courseflow_internal_jwt_verification_mode="jwks",
                courseflow_internal_jwt_jwks_uri="https://issuer.example.test/jwks",
            )
        )
        jwks_client = Mock()
        jwks_client.get_signing_key_from_jwt.side_effect = jwt.PyJWKClientError(
            "signing key unavailable"
        )
        cast(Any, verifier)._jwks_client = jwks_client

        with self.assertRaises(HTTPException) as raised:
            verifier.verify("token-with-missing-key")

        self.assertEqual(raised.exception.status_code, 403)


def settings_without_env(**overrides: object) -> Settings:
    factory = cast(Any, Settings)
    return cast(Settings, factory(_env_file=None, **overrides))


if __name__ == "__main__":
    unittest.main()
