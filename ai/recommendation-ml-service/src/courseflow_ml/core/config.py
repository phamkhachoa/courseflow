from __future__ import annotations

import ipaddress
from functools import lru_cache
from urllib.parse import quote_plus, urlparse

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_INTERNAL_JWT_SECRET_BYTES = 32
MIN_RECOMMENDATION_ML_PRINCIPAL_HASH_SECRET_BYTES = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "recommendation-ml-service"
    server_port: int = 8080
    recommendation_ml_db_url: str = "jdbc:postgresql://localhost:5432/cf_recommendation_ml"
    recommendation_ml_db_username: str = "courseflow"
    recommendation_ml_db_password: str = "courseflow"
    recommendation_ml_default_max_related_per_course: int = 24
    recommendation_ml_max_related_per_course: int = 100
    recommendation_ml_default_min_support: int = 1
    recommendation_ml_max_training_events: int = 250_000
    recommendation_ml_expected_migration_revision: str = "007_model_activation_governance"
    recommendation_ml_auto_activate_trained_models: bool = True
    recommendation_ml_training_job_lease_seconds: int = 1800
    recommendation_ml_training_job_max_attempts: int = 3
    recommendation_ml_training_job_requeue_delay_seconds: int = 60
    recommendation_ml_training_payload_retention_days: int = 30
    recommendation_ml_payload_scrub_interval_seconds: int = 86400
    recommendation_ml_principal_hash_secret: str = (
        "courseflow-local-recommendation-ml-principal-hash-secret-change-me-32"
    )
    recommendation_ml_active_model_stale_after_seconds: int = 604800
    recommendation_ml_require_active_model_ready: bool = False
    recommendation_ml_min_activation_event_count: int = 10
    recommendation_ml_min_activation_principal_count: int = 3
    recommendation_ml_min_activation_course_count: int = 2
    recommendation_ml_min_activation_pair_count: int = 1
    recommendation_ml_min_activation_quality_score: float = 0.01
    recommendation_ml_docs_enabled: bool = False
    recommendation_ml_sync_training_enabled: bool = True
    courseflow_internal_jwt_algorithm: str = "HS256"
    courseflow_internal_jwt_secret: str = ""
    courseflow_internal_jwt_public_key: str = ""
    courseflow_internal_jwt_verification_mode: str = "local"
    courseflow_internal_jwt_jwks_uri: str = ""
    courseflow_internal_jwt_jwks_cache_ttl_seconds: int = 300
    courseflow_internal_jwt_jwks_timeout_seconds: int = 5
    courseflow_internal_jwt_issuer: str = "courseflow-token-converter"
    courseflow_internal_jwt_audience: str = "courseflow-services"
    courseflow_internal_jwt_max_ttl_seconds: int = 900
    courseflow_internal_jwt_clock_skew_seconds: int = 30

    @model_validator(mode="after")
    def validate_internal_jwt_configuration(self) -> Settings:
        algorithm = self.courseflow_internal_jwt_algorithm.strip().upper()
        mode = self.courseflow_internal_jwt_verification_mode.strip().lower()
        if algorithm not in {"HS256", "RS256"}:
            raise ValueError("COURSEFLOW_INTERNAL_JWT_ALGORITHM must be HS256 or RS256")
        if mode not in {"local", "jwks"}:
            raise ValueError("COURSEFLOW_INTERNAL_JWT_VERIFICATION_MODE must be local or jwks")
        if not self.courseflow_internal_jwt_audience.strip():
            raise ValueError("COURSEFLOW_INTERNAL_JWT_AUDIENCE is required")
        if not self.courseflow_internal_jwt_issuer.strip():
            raise ValueError("COURSEFLOW_INTERNAL_JWT_ISSUER is required")
        if algorithm == "HS256":
            secret_bytes = self.courseflow_internal_jwt_secret.encode("utf-8")
            if len(secret_bytes) < MIN_INTERNAL_JWT_SECRET_BYTES:
                raise ValueError(
                    "COURSEFLOW_INTERNAL_JWT_SECRET must be at least "
                    f"{MIN_INTERNAL_JWT_SECRET_BYTES} bytes for HS256"
                )
            if mode != "local":
                raise ValueError("HS256 internal JWT verification must use local mode")
        if (
            algorithm == "RS256"
            and mode == "local"
            and not self.courseflow_internal_jwt_public_key.strip()
        ):
            raise ValueError("COURSEFLOW_INTERNAL_JWT_PUBLIC_KEY is required for RS256 local mode")
        if (
            algorithm == "RS256"
            and mode == "jwks"
            and not self.courseflow_internal_jwt_jwks_uri.strip()
        ):
            raise ValueError("COURSEFLOW_INTERNAL_JWT_JWKS_URI is required for RS256 jwks mode")
        if algorithm == "RS256" and mode == "jwks":
            self.courseflow_internal_jwt_jwks_uri = validate_jwks_uri(
                self.courseflow_internal_jwt_jwks_uri
            )
        self.courseflow_internal_jwt_algorithm = algorithm
        self.courseflow_internal_jwt_verification_mode = mode
        self.courseflow_internal_jwt_audience = self.courseflow_internal_jwt_audience.strip()
        self.courseflow_internal_jwt_issuer = self.courseflow_internal_jwt_issuer.strip()
        self.courseflow_internal_jwt_clock_skew_seconds = max(
            0,
            min(self.courseflow_internal_jwt_clock_skew_seconds, 120),
        )
        self.courseflow_internal_jwt_jwks_cache_ttl_seconds = max(
            30,
            min(self.courseflow_internal_jwt_jwks_cache_ttl_seconds, 3600),
        )
        self.courseflow_internal_jwt_jwks_timeout_seconds = max(
            1,
            min(self.courseflow_internal_jwt_jwks_timeout_seconds, 30),
        )
        self.courseflow_internal_jwt_max_ttl_seconds = max(
            30,
            min(self.courseflow_internal_jwt_max_ttl_seconds, 900),
        )
        self.recommendation_ml_training_payload_retention_days = max(
            1,
            min(self.recommendation_ml_training_payload_retention_days, 3650),
        )
        self.recommendation_ml_payload_scrub_interval_seconds = max(
            60,
            min(self.recommendation_ml_payload_scrub_interval_seconds, 604800),
        )
        if (
            len(self.recommendation_ml_principal_hash_secret.encode("utf-8"))
            < MIN_RECOMMENDATION_ML_PRINCIPAL_HASH_SECRET_BYTES
        ):
            raise ValueError(
                "RECOMMENDATION_ML_PRINCIPAL_HASH_SECRET must be at least "
                f"{MIN_RECOMMENDATION_ML_PRINCIPAL_HASH_SECRET_BYTES} bytes"
            )
        return self

    @property
    def database_url(self) -> str:
        raw = self.recommendation_ml_db_url
        if raw.startswith("jdbc:postgresql://"):
            path = raw.removeprefix("jdbc:postgresql://")
            username = quote_plus(self.recommendation_ml_db_username)
            password = quote_plus(self.recommendation_ml_db_password)
            return f"postgresql+psycopg://{username}:{password}@{path}"
        if raw.startswith("postgresql://"):
            return raw.replace("postgresql://", "postgresql+psycopg://", 1)
        return raw


def validate_jwks_uri(value: str) -> str:
    trimmed = value.strip()
    parsed = urlparse(trimmed)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("COURSEFLOW_INTERNAL_JWT_JWKS_URI must be an HTTP(S) URL")
    host = (parsed.hostname or "").strip().lower()
    if is_local_jwks_host(host):
        raise ValueError("COURSEFLOW_INTERNAL_JWT_JWKS_URI must not point to a local host")
    return trimmed


def is_local_jwks_host(host: str) -> bool:
    if host in {"localhost", "host.docker.internal"}:
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_loopback or ip.is_unspecified


@lru_cache
def get_settings() -> Settings:
    return Settings()
