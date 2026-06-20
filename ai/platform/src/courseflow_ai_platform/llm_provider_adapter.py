from __future__ import annotations

import math
import re
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from courseflow_ai_platform.prompt_audit import (
    JsonlPromptAuditStore,
    PromptAuditLedger,
    PromptAuditStore,
    build_prompt_audit_record,
)
from courseflow_ai_platform.prompt_gateway import (
    PromptContext,
    PromptGatewayRequest,
    PromptGatewayResult,
)
from courseflow_ai_platform.prompt_gateway_service import (
    PROMPT_GATEWAY_EVALUATE_SCOPE,
    PromptGatewayRuntime,
    load_prompt_gateway_access_policy,
    prompt_gateway_request_from_dict,
)
from courseflow_ai_platform.registry import RegistryValidationError, load_yaml, require_str

LLM_ADAPTER_GENERATE_SCOPE = "internal:ai-platform:llm-adapter:generate"
LLM_ADAPTER_OPS_SCOPE = "internal:ai-platform:llm-adapter:ops"
LLM_ADAPTER_ROUTE_SCOPES = {
    ("POST", "/v1/llm-adapter/generate"): LLM_ADAPTER_GENERATE_SCOPE,
    ("GET", "/v1/llm-adapter/health"): LLM_ADAPTER_OPS_SCOPE,
    ("GET", "/v1/llm-adapter/metrics"): LLM_ADAPTER_OPS_SCOPE,
}


class LlmProviderAdapterError(ValueError):
    """Raised when the LLM provider adapter request or policy is invalid."""


@dataclass(frozen=True, slots=True)
class LlmProviderConfig:
    provider_id: str
    provider_type: str
    model_id: str
    network_enabled: bool


@dataclass(frozen=True, slots=True)
class LlmProviderRateLimitConfig:
    requests_per_minute: int
    burst: int

    @property
    def max_requests_per_window(self) -> int:
        return self.requests_per_minute + self.burst


@dataclass(frozen=True, slots=True)
class LlmProviderCircuitBreakerConfig:
    failure_threshold: int
    cooldown_seconds: int


@dataclass(frozen=True, slots=True)
class LlmProviderCostConfig:
    currency: str
    input_micros_per_1k_tokens: int
    output_micros_per_1k_tokens: int


@dataclass(frozen=True, slots=True)
class LlmProviderOpsConfig:
    provider_id: str
    deployment_readiness: str
    credential_ref: str
    request_timeout_ms: int
    max_retries: int
    rate_limit: LlmProviderRateLimitConfig
    circuit_breaker: LlmProviderCircuitBreakerConfig
    cost: LlmProviderCostConfig
    failover_provider_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LlmProviderOpsPolicy:
    policy_id: str
    providers: Mapping[str, LlmProviderOpsConfig]
    prompt_gateway_required_before_provider: bool = True
    live_network_providers_require_credential_ref: bool = True
    deny_when_rate_limited: bool = True

    def resolve_provider(self, provider_id: str) -> LlmProviderOpsConfig:
        config = self.providers.get(provider_id)
        if config is None:
            raise LlmProviderAdapterError(
                f"LLM provider ops policy is not configured: {provider_id}"
            )
        return config


@dataclass(frozen=True, slots=True)
class LlmAdapterPrincipal:
    principal_id: str
    scopes: tuple[str, ...]
    tenant_ids: tuple[str, ...] = ()
    product_ids: tuple[str, ...] = ()
    use_case_ids: tuple[str, ...] = ()
    provider_ids: tuple[str, ...] = ()
    prompt_gateway_principal_id: str = ""

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> LlmAdapterPrincipal:
        return cls(
            principal_id=required_non_empty_str(row, "principal_id", "principalId"),
            scopes=normalize_string_tuple(row.get("scopes", row.get("scope"))),
            tenant_ids=normalize_string_tuple(row.get("tenant_ids", row.get("tenantIds"))),
            product_ids=normalize_string_tuple(row.get("product_ids", row.get("productIds"))),
            use_case_ids=normalize_string_tuple(
                row.get("use_case_ids", row.get("useCaseIds"))
            ),
            provider_ids=normalize_string_tuple(
                row.get("provider_ids", row.get("providerIds"))
            ),
            prompt_gateway_principal_id=optional_string_any(
                row,
                "prompt_gateway_principal_id",
                "promptGatewayPrincipalId",
            ),
        )


@dataclass(frozen=True, slots=True)
class LlmAdapterPrincipalGrant:
    principal_id: str
    owner_role: str
    product: str
    scopes: tuple[str, ...]
    tenant_ids: tuple[str, ...]
    product_ids: tuple[str, ...]
    use_case_ids: tuple[str, ...]
    provider_ids: tuple[str, ...]
    prompt_gateway_principal_id: str

    def resolve(self, requested_scopes: object | None = None) -> LlmAdapterPrincipal:
        scopes = (
            self.scopes
            if requested_scopes is None
            else normalize_string_tuple(requested_scopes)
        )
        missing_scopes = sorted(set(scopes) - set(self.scopes))
        if missing_scopes:
            raise LlmProviderAdapterError(
                f"principal {self.principal_id} requested ungranted scopes: "
                + ", ".join(missing_scopes)
            )
        return LlmAdapterPrincipal(
            principal_id=self.principal_id,
            scopes=scopes,
            tenant_ids=self.tenant_ids,
            product_ids=self.product_ids,
            use_case_ids=self.use_case_ids,
            provider_ids=self.provider_ids,
            prompt_gateway_principal_id=self.prompt_gateway_principal_id,
        )


@dataclass(frozen=True, slots=True)
class LlmAdapterAccessPolicy:
    policy_id: str
    providers: Mapping[str, LlmProviderConfig]
    principals: Mapping[str, LlmAdapterPrincipalGrant]
    wildcard_scopes_allowed: bool = False
    prompt_gateway_required: bool = True

    def resolve_principal(
        self,
        principal_id: str,
        requested_scopes: object | None = None,
    ) -> LlmAdapterPrincipal:
        grant = self.principals.get(principal_id)
        if grant is None:
            raise LlmProviderAdapterError(
                f"LLM adapter principal is not registered: {principal_id}"
            )
        return grant.resolve(requested_scopes)


@dataclass(frozen=True, slots=True)
class LlmGenerationRequest:
    provider_id: str
    prompt_request: PromptGatewayRequest
    generation_question: str = ""


@dataclass(frozen=True, slots=True)
class LlmProviderOutput:
    provider_id: str
    model_id: str
    generated_text: str
    citation_ids: tuple[str, ...]
    refused: bool
    provider_called: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "citationIds": self.citation_ids,
            "generatedText": self.generated_text,
            "modelId": self.model_id,
            "providerCalled": self.provider_called,
            "providerId": self.provider_id,
            "refused": self.refused,
        }


class LlmProvider(Protocol):
    def generate(
        self,
        request: LlmGenerationRequest,
        gateway_result: PromptGatewayResult,
    ) -> LlmProviderOutput:
        """Generate provider output for an already-gated LLM request."""


@dataclass(frozen=True, slots=True)
class LlmAdapterGeneration:
    request: LlmGenerationRequest
    gateway_result: PromptGatewayResult
    provider_output: LlmProviderOutput
    audit_event_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "auditEventId": self.audit_event_id,
            "blockedReasons": self.gateway_result.blocked_reasons,
            "contextIds": self.gateway_result.context_ids,
            "gatewayAllowed": self.gateway_result.allowed,
            "provider": self.provider_output.to_dict(),
            "requireHumanReview": self.gateway_result.require_human_review,
            "tenantId": self.request.prompt_request.tenant_id,
            "product": self.request.prompt_request.product,
            "useCaseId": self.request.prompt_request.use_case_id,
        }


@dataclass(frozen=True, slots=True)
class LlmAdapterMetricsSnapshot:
    request_count: int
    generation_count: int
    blocked_count: int
    provider_call_count: int
    refused_count: int
    audit_record_count: int
    error_count: int
    rate_limited_count: int
    provider_error_count: int
    failover_count: int
    estimated_cost_micros: int
    provider_latency_ms_total: float
    provider_latency_sample_count: int
    by_product: dict[str, int]
    by_use_case: dict[str, int]
    by_provider: dict[str, int]
    by_provider_cost_micros: dict[str, int]
    by_provider_latency_ms_total: dict[str, float]
    by_provider_latency_sample_count: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "auditRecordCount": self.audit_record_count,
            "blockedCount": self.blocked_count,
            "byProviderCostMicros": self.by_provider_cost_micros,
            "byProviderLatencyMsTotal": self.by_provider_latency_ms_total,
            "byProviderLatencySampleCount": self.by_provider_latency_sample_count,
            "byProduct": self.by_product,
            "byProvider": self.by_provider,
            "byUseCase": self.by_use_case,
            "errorCount": self.error_count,
            "estimatedCostMicros": self.estimated_cost_micros,
            "generationCount": self.generation_count,
            "providerCallCount": self.provider_call_count,
            "providerErrorCount": self.provider_error_count,
            "providerLatencyMsTotal": self.provider_latency_ms_total,
            "providerLatencySampleCount": self.provider_latency_sample_count,
            "rateLimitedCount": self.rate_limited_count,
            "refusedCount": self.refused_count,
            "requestCount": self.request_count,
            "failoverCount": self.failover_count,
        }


class LlmAdapterMetrics:
    def __init__(self) -> None:
        self.request_count = 0
        self.generation_count = 0
        self.blocked_count = 0
        self.provider_call_count = 0
        self.refused_count = 0
        self.audit_record_count = 0
        self.error_count = 0
        self.rate_limited_count = 0
        self.provider_error_count = 0
        self.failover_count = 0
        self.estimated_cost_micros = 0
        self.provider_latency_ms_total = 0.0
        self.provider_latency_sample_count = 0
        self.by_product: dict[str, int] = {}
        self.by_use_case: dict[str, int] = {}
        self.by_provider: dict[str, int] = {}
        self.by_provider_cost_micros: dict[str, int] = {}
        self.by_provider_latency_ms_total: dict[str, float] = {}
        self.by_provider_latency_sample_count: dict[str, int] = {}

    def record_generation(self, generation: LlmAdapterGeneration) -> None:
        self.request_count += 1
        self.generation_count += 1
        request = generation.request
        if not generation.gateway_result.allowed:
            self.blocked_count += 1
        if generation.provider_output.provider_called:
            self.provider_call_count += 1
        if generation.provider_output.refused:
            self.refused_count += 1
        if generation.audit_event_id:
            self.audit_record_count += 1
        product = request.prompt_request.product
        use_case_id = request.prompt_request.use_case_id
        self.by_product[product] = self.by_product.get(product, 0) + 1
        self.by_use_case[use_case_id] = self.by_use_case.get(use_case_id, 0) + 1
        provider_id = generation.provider_output.provider_id or request.provider_id
        self.by_provider[provider_id] = self.by_provider.get(provider_id, 0) + 1

    def record_error(self) -> None:
        self.request_count += 1
        self.error_count += 1

    def record_rate_limited(self, provider_id: str) -> None:
        self.rate_limited_count += 1
        self.by_provider[provider_id] = self.by_provider.get(provider_id, 0) + 1

    def record_provider_error(self, provider_id: str) -> None:
        self.provider_error_count += 1
        self.by_provider[provider_id] = self.by_provider.get(provider_id, 0) + 1

    def record_failover(self) -> None:
        self.failover_count += 1

    def record_provider_observability(
        self,
        provider_id: str,
        *,
        latency_ms: float,
        estimated_cost_micros: int,
    ) -> None:
        self.estimated_cost_micros += estimated_cost_micros
        self.provider_latency_ms_total += latency_ms
        self.provider_latency_sample_count += 1
        self.by_provider_cost_micros[provider_id] = (
            self.by_provider_cost_micros.get(provider_id, 0) + estimated_cost_micros
        )
        self.by_provider_latency_ms_total[provider_id] = (
            self.by_provider_latency_ms_total.get(provider_id, 0.0) + latency_ms
        )
        self.by_provider_latency_sample_count[provider_id] = (
            self.by_provider_latency_sample_count.get(provider_id, 0) + 1
        )

    def snapshot(self) -> LlmAdapterMetricsSnapshot:
        return LlmAdapterMetricsSnapshot(
            request_count=self.request_count,
            generation_count=self.generation_count,
            blocked_count=self.blocked_count,
            provider_call_count=self.provider_call_count,
            refused_count=self.refused_count,
            audit_record_count=self.audit_record_count,
            error_count=self.error_count,
            rate_limited_count=self.rate_limited_count,
            provider_error_count=self.provider_error_count,
            failover_count=self.failover_count,
            estimated_cost_micros=self.estimated_cost_micros,
            provider_latency_ms_total=round(self.provider_latency_ms_total, 6),
            provider_latency_sample_count=self.provider_latency_sample_count,
            by_product=dict(sorted(self.by_product.items())),
            by_use_case=dict(sorted(self.by_use_case.items())),
            by_provider=dict(sorted(self.by_provider.items())),
            by_provider_cost_micros=dict(sorted(self.by_provider_cost_micros.items())),
            by_provider_latency_ms_total={
                provider_id: round(total, 6)
                for provider_id, total in sorted(self.by_provider_latency_ms_total.items())
            },
            by_provider_latency_sample_count=dict(
                sorted(self.by_provider_latency_sample_count.items())
            ),
        )


class LlmProviderRateLimiter:
    def __init__(self) -> None:
        self._windows: dict[str, tuple[int, int]] = {}

    def check(self, key: str, config: LlmProviderRateLimitConfig) -> None:
        current_window = int(time.time() // 60)
        window, count = self._windows.get(key, (current_window, 0))
        if window != current_window:
            window = current_window
            count = 0
        if count >= config.max_requests_per_window:
            raise LlmProviderAdapterError("LLM provider rate limit exceeded")
        self._windows[key] = (window, count + 1)


class LlmProviderCircuitBreaker:
    def __init__(self) -> None:
        self._states: dict[str, tuple[int, float | None]] = {}

    def assert_closed(
        self,
        provider_id: str,
        config: LlmProviderCircuitBreakerConfig,
    ) -> None:
        failure_count, opened_at = self._states.get(provider_id, (0, None))
        if opened_at is None:
            return
        if time.monotonic() - opened_at >= config.cooldown_seconds:
            self._states[provider_id] = (0, None)
            return
        raise LlmProviderAdapterError(f"LLM provider circuit is open: {provider_id}")

    def record_success(self, provider_id: str) -> None:
        self._states[provider_id] = (0, None)

    def record_failure(
        self,
        provider_id: str,
        config: LlmProviderCircuitBreakerConfig,
    ) -> None:
        failure_count, opened_at = self._states.get(provider_id, (0, None))
        if opened_at is not None:
            return
        failure_count += 1
        opened_at = time.monotonic() if failure_count >= config.failure_threshold else None
        self._states[provider_id] = (failure_count, opened_at)


class DeterministicContractLlmProvider:
    def __init__(self, config: LlmProviderConfig) -> None:
        self.config = config

    def generate(
        self,
        request: LlmGenerationRequest,
        gateway_result: PromptGatewayResult,
    ) -> LlmProviderOutput:
        prompt_request = request.prompt_request
        if not gateway_result.allowed:
            return LlmProviderOutput(
                provider_id=request.provider_id,
                model_id=self.config.model_id,
                generated_text="",
                citation_ids=(),
                refused=True,
                provider_called=False,
            )
        question = request.generation_question or prompt_request.user_input
        contexts = [
            context
            for context in prompt_request.retrieved_context
            if context.context_id in set(gateway_result.context_ids)
        ]
        if mentions_other_tenant(question, prompt_request.tenant_id):
            return refused_provider_output(request.provider_id, self.config.model_id)
        ranked_contexts = rank_contexts(question, contexts)
        if not ranked_contexts:
            return refused_provider_output(request.provider_id, self.config.model_id)
        context = ranked_contexts[0]
        return LlmProviderOutput(
            provider_id=request.provider_id,
            model_id=self.config.model_id,
            generated_text=f"{context.text} Citation: [{context.context_id}]",
            citation_ids=(context.context_id,),
            refused=False,
            provider_called=True,
        )


class LlmProviderAdapterRuntime:
    """Provider-neutral adapter that enforces Prompt Gateway before generation."""

    def __init__(
        self,
        ai_root: Path | str,
        *,
        audit_store: PromptAuditStore | None = None,
        audit_log_path: Path | str | None = None,
        audit_retention_days: int = 30,
        provider_ops_policy: LlmProviderOpsPolicy | None = None,
        provider_overrides: Mapping[str, LlmProvider] | None = None,
        rate_limiter: LlmProviderRateLimiter | None = None,
        circuit_breaker: LlmProviderCircuitBreaker | None = None,
    ) -> None:
        if audit_store is not None and audit_log_path is not None:
            raise LlmProviderAdapterError(
                "configure either audit_store or audit_log_path, not both"
            )
        self.ai_root = Path(ai_root)
        self.policy = load_llm_adapter_access_policy(self.ai_root)
        self.provider_ops_policy = provider_ops_policy or load_llm_provider_ops_policy(
            self.ai_root,
            self.policy,
        )
        self.prompt_gateway_policy = load_prompt_gateway_access_policy(self.ai_root)
        self.prompt_gateway_runtime = PromptGatewayRuntime(self.ai_root)
        self.audit_store = (
            JsonlPromptAuditStore(audit_log_path)
            if audit_log_path is not None
            else audit_store or PromptAuditLedger()
        )
        self.audit_retention_days = audit_retention_days
        self.metrics = LlmAdapterMetrics()
        self.provider_overrides = dict(provider_overrides or {})
        self.rate_limiter = rate_limiter or LlmProviderRateLimiter()
        self.circuit_breaker = circuit_breaker or LlmProviderCircuitBreaker()

    def generate(
        self,
        request: LlmGenerationRequest | Mapping[str, Any],
        principal: LlmAdapterPrincipal | Mapping[str, Any] | None = None,
    ) -> LlmAdapterGeneration:
        generation_request = (
            request if isinstance(request, LlmGenerationRequest) else llm_request_from_dict(request)
        )
        try:
            resolved_principal = normalize_principal(principal)
            authorize_llm_adapter_generate(
                resolved_principal,
                generation_request,
                self.policy,
            )
            prompt_principal = self.prompt_gateway_policy.resolve_principal(
                resolved_principal.prompt_gateway_principal_id,
                (PROMPT_GATEWAY_EVALUATE_SCOPE,),
            )
            gateway_evaluation = self.prompt_gateway_runtime.evaluate(
                generation_request.prompt_request,
                prompt_principal,
            )
            provider_output = self.generate_with_provider_ops(
                generation_request,
                gateway_evaluation.result,
                resolved_principal,
            )
            audit_record = build_prompt_audit_record(
                generation_request.prompt_request,
                gateway_evaluation.result,
                response_text=provider_output.generated_text,
                retention_days=self.audit_retention_days,
            )
            self.audit_store.append(audit_record)
        except Exception:
            self.metrics.record_error()
            raise

        generation = LlmAdapterGeneration(
            request=generation_request,
            gateway_result=gateway_evaluation.result,
            provider_output=provider_output,
            audit_event_id=audit_record.event_id,
        )
        self.metrics.record_generation(generation)
        return generation

    def health(self) -> dict[str, Any]:
        return {
            "failoverProviderCount": sum(
                1 for config in self.provider_ops_policy.providers.values()
                if config.failover_provider_ids
            ),
            "networkProviderCount": sum(
                1 for provider in self.policy.providers.values()
                if provider.network_enabled
            ),
            "opsPolicyId": self.provider_ops_policy.policy_id,
            "providerCount": len(self.policy.providers),
            "serviceStatus": "healthy",
        }

    def snapshot_metrics(self) -> LlmAdapterMetricsSnapshot:
        return self.metrics.snapshot()

    def generate_with_provider_ops(
        self,
        request: LlmGenerationRequest,
        gateway_result: PromptGatewayResult,
        principal: LlmAdapterPrincipal,
    ) -> LlmProviderOutput:
        if not gateway_result.allowed:
            return self.provider_for(request.provider_id).generate(request, gateway_result)
        last_error: Exception | None = None
        for candidate_provider_id in self.provider_chain(request.provider_id):
            if principal.provider_ids and candidate_provider_id not in principal.provider_ids:
                raise LlmProviderAdapterError(
                    "LLM adapter failover provider is not granted to principal"
                )
            provider_request = LlmGenerationRequest(
                provider_id=candidate_provider_id,
                prompt_request=request.prompt_request,
                generation_question=request.generation_question,
            )
            ops_config = self.provider_ops_policy.resolve_provider(candidate_provider_id)
            self.circuit_breaker.assert_closed(
                candidate_provider_id,
                ops_config.circuit_breaker,
            )
            try:
                self.rate_limiter.check(
                    rate_limit_key(principal, provider_request),
                    ops_config.rate_limit,
                )
            except LlmProviderAdapterError:
                self.metrics.record_rate_limited(candidate_provider_id)
                raise
            try:
                started = time.perf_counter()
                output = self.provider_for(candidate_provider_id).generate(
                    provider_request,
                    gateway_result,
                )
            except Exception as exc:
                last_error = exc
                self.metrics.record_provider_error(candidate_provider_id)
                self.circuit_breaker.record_failure(
                    candidate_provider_id,
                    ops_config.circuit_breaker,
                )
                continue
            self.circuit_breaker.record_success(candidate_provider_id)
            if output.provider_called:
                self.metrics.record_provider_observability(
                    candidate_provider_id,
                    latency_ms=(time.perf_counter() - started) * 1000,
                    estimated_cost_micros=estimate_provider_cost_micros(
                        gateway_result,
                        ops_config.cost,
                    ),
                )
            if candidate_provider_id != request.provider_id:
                self.metrics.record_failover()
            return output
        raise LlmProviderAdapterError("LLM provider call failed after failover") from last_error

    def provider_chain(self, provider_id: str) -> tuple[str, ...]:
        ops_config = self.provider_ops_policy.resolve_provider(provider_id)
        return (provider_id, *ops_config.failover_provider_ids)

    def provider_for(self, provider_id: str) -> LlmProvider:
        provider_override = self.provider_overrides.get(provider_id)
        if provider_override is not None:
            return provider_override
        provider = self.policy.providers.get(provider_id)
        if provider is None:
            raise LlmProviderAdapterError(f"LLM provider is not registered: {provider_id}")
        if provider.provider_type != "external_contract_stub":
            raise LlmProviderAdapterError(
                f"unsupported LLM provider type: {provider.provider_type}"
            )
        return DeterministicContractLlmProvider(provider)


def load_llm_adapter_access_policy(ai_root: Path | str) -> LlmAdapterAccessPolicy:
    root = Path(ai_root)
    policy_path = root / "platform" / "governance" / "policies" / (
        "llm-adapter-access-policy.yaml"
    )
    policy = load_yaml(policy_path)
    raw_scope_aliases = policy.get("scope_aliases", {})
    if not isinstance(raw_scope_aliases, dict):
        raise RegistryValidationError(f"{policy_path} must define mapping field scope_aliases")
    scope_aliases = {
        "generate": LLM_ADAPTER_GENERATE_SCOPE,
        "ops": LLM_ADAPTER_OPS_SCOPE,
        **raw_scope_aliases,
    }
    providers: dict[str, LlmProviderConfig] = {}
    for row in require_mapping_list(policy, "providers", policy_path):
        provider_id = require_str(row, "provider_id", str(policy_path))
        if provider_id in providers:
            raise RegistryValidationError(f"{policy_path} duplicates provider: {provider_id}")
        providers[provider_id] = LlmProviderConfig(
            provider_id=provider_id,
            provider_type=require_str(row, "provider_type", str(policy_path)),
            model_id=require_str(row, "model_id", str(policy_path)),
            network_enabled=required_bool(row, "network_enabled", str(policy_path)),
        )
    grants: dict[str, LlmAdapterPrincipalGrant] = {}
    for row in require_mapping_list(policy, "principals", policy_path):
        principal_id = require_str(row, "principal_id", str(policy_path))
        if principal_id in grants:
            raise RegistryValidationError(f"{policy_path} duplicates principal: {principal_id}")
        product = require_str(row, "product", str(policy_path))
        provider_ids = normalize_string_tuple(row.get("provider_ids", []))
        unknown_providers = sorted(set(provider_ids) - set(providers))
        if unknown_providers:
            raise RegistryValidationError(
                f"{policy_path} principal {principal_id} references unknown providers: "
                + ", ".join(unknown_providers)
            )
        grants[principal_id] = LlmAdapterPrincipalGrant(
            principal_id=principal_id,
            owner_role=require_str(row, "owner_role", str(policy_path)),
            product=product,
            scopes=tuple(
                sorted(
                    {
                        expand_scope_alias(scope, scope_aliases, policy_path)
                        for scope in normalize_string_tuple(row.get("scopes", []))
                    }
                )
            ),
            tenant_ids=tuple(sorted(normalize_string_tuple(row.get("tenant_ids", [])))),
            product_ids=tuple(
                sorted(normalize_string_tuple(row.get("product_ids", [product])))
            ),
            use_case_ids=tuple(sorted(normalize_string_tuple(row.get("use_case_ids", [])))),
            provider_ids=tuple(sorted(provider_ids)),
            prompt_gateway_principal_id=require_str(
                row,
                "prompt_gateway_principal_id",
                str(policy_path),
            ),
        )
    defaults = policy.get("defaults", {})
    if not isinstance(defaults, dict):
        raise RegistryValidationError(f"{policy_path} defaults must be a mapping")
    return LlmAdapterAccessPolicy(
        policy_id=require_str(policy, "policy_id", str(policy_path)),
        providers=dict(sorted(providers.items())),
        principals=dict(sorted(grants.items())),
        wildcard_scopes_allowed=bool(defaults.get("wildcard_scopes_allowed", False)),
        prompt_gateway_required=bool(defaults.get("prompt_gateway_required", True)),
    )


def load_llm_provider_ops_policy(
    ai_root: Path | str,
    access_policy: LlmAdapterAccessPolicy | None = None,
) -> LlmProviderOpsPolicy:
    root = Path(ai_root)
    policy_path = (
        root
        / "platform"
        / "governance"
        / "policies"
        / "llm-provider-ops-policy.yaml"
    )
    policy = load_yaml(policy_path)
    adapter_policy = access_policy or load_llm_adapter_access_policy(root)
    providers: dict[str, LlmProviderOpsConfig] = {}
    for row in require_mapping_list(policy, "providers", policy_path):
        provider_id = require_str(row, "provider_id", str(policy_path))
        if provider_id in providers:
            raise RegistryValidationError(
                f"{policy_path} duplicates provider ops config: {provider_id}"
            )
        if provider_id not in adapter_policy.providers:
            raise RegistryValidationError(
                f"{policy_path} references unknown LLM adapter provider: {provider_id}"
            )
        rate_limit = require_mapping(row, "rate_limit", policy_path)
        circuit_breaker = require_mapping(row, "circuit_breaker", policy_path)
        cost = require_mapping(row, "cost", policy_path)
        failover_provider_ids = normalize_string_tuple(row.get("failover_provider_ids", []))
        unknown_failovers = sorted(set(failover_provider_ids) - set(adapter_policy.providers))
        if unknown_failovers:
            raise RegistryValidationError(
                f"{policy_path} provider {provider_id} references unknown failovers: "
                + ", ".join(unknown_failovers)
            )
        provider = adapter_policy.providers[provider_id]
        credential_ref = require_str(row, "credential_ref", str(policy_path))
        providers[provider_id] = LlmProviderOpsConfig(
            provider_id=provider_id,
            deployment_readiness=require_str(row, "deployment_readiness", str(policy_path)),
            credential_ref=credential_ref,
            request_timeout_ms=required_positive_int(
                row,
                "request_timeout_ms",
                str(policy_path),
            ),
            max_retries=required_non_negative_int(row, "max_retries", str(policy_path)),
            rate_limit=LlmProviderRateLimitConfig(
                requests_per_minute=required_positive_int(
                    rate_limit,
                    "requests_per_minute",
                    str(policy_path),
                ),
                burst=required_non_negative_int(rate_limit, "burst", str(policy_path)),
            ),
            circuit_breaker=LlmProviderCircuitBreakerConfig(
                failure_threshold=required_positive_int(
                    circuit_breaker,
                    "failure_threshold",
                    str(policy_path),
                ),
                cooldown_seconds=required_positive_int(
                    circuit_breaker,
                    "cooldown_seconds",
                    str(policy_path),
                ),
            ),
            cost=LlmProviderCostConfig(
                currency=require_str(cost, "currency", str(policy_path)),
                input_micros_per_1k_tokens=required_non_negative_int(
                    cost,
                    "input_micros_per_1k_tokens",
                    str(policy_path),
                ),
                output_micros_per_1k_tokens=required_non_negative_int(
                    cost,
                    "output_micros_per_1k_tokens",
                    str(policy_path),
                ),
            ),
            failover_provider_ids=failover_provider_ids,
        )
        defaults = policy.get("defaults", {})
        if not isinstance(defaults, dict):
            raise RegistryValidationError(f"{policy_path} defaults must be a mapping")
        if (
            bool(defaults.get("live_network_providers_require_credential_ref", True))
            and provider.network_enabled
            and credential_ref.startswith("local://")
        ):
            raise RegistryValidationError(
                f"{policy_path} provider {provider_id} needs a non-local credential ref"
            )
    missing_provider_ids = sorted(set(adapter_policy.providers) - set(providers))
    if missing_provider_ids:
        raise RegistryValidationError(
            f"{policy_path} is missing provider ops configs: "
            + ", ".join(missing_provider_ids)
        )
    defaults = policy.get("defaults", {})
    if not isinstance(defaults, dict):
        raise RegistryValidationError(f"{policy_path} defaults must be a mapping")
    return LlmProviderOpsPolicy(
        policy_id=require_str(policy, "policy_id", str(policy_path)),
        providers=dict(sorted(providers.items())),
        prompt_gateway_required_before_provider=bool(
            defaults.get("prompt_gateway_required_before_provider", True)
        ),
        live_network_providers_require_credential_ref=bool(
            defaults.get("live_network_providers_require_credential_ref", True)
        ),
        deny_when_rate_limited=bool(defaults.get("deny_when_rate_limited", True)),
    )


def authorize_llm_adapter_generate(
    principal: LlmAdapterPrincipal | None,
    request: LlmGenerationRequest,
    policy: LlmAdapterAccessPolicy,
) -> None:
    if principal is None:
        raise LlmProviderAdapterError("LLM adapter principal is required")
    if "*" in principal.scopes or "*" in principal.provider_ids:
        raise LlmProviderAdapterError("wildcard LLM adapter scopes or providers are forbidden")
    if LLM_ADAPTER_GENERATE_SCOPE not in principal.scopes:
        raise LlmProviderAdapterError("LLM adapter generate scope is required")
    if policy.prompt_gateway_required and not principal.prompt_gateway_principal_id:
        raise LlmProviderAdapterError("LLM adapter prompt gateway principal is required")
    prompt_request = request.prompt_request
    if principal.tenant_ids and prompt_request.tenant_id not in principal.tenant_ids:
        raise LlmProviderAdapterError("LLM adapter tenant is not granted to principal")
    if principal.product_ids and prompt_request.product not in principal.product_ids:
        raise LlmProviderAdapterError("LLM adapter product is not granted to principal")
    if principal.use_case_ids and prompt_request.use_case_id not in principal.use_case_ids:
        raise LlmProviderAdapterError("LLM adapter use case is not granted to principal")
    if principal.provider_ids and request.provider_id not in principal.provider_ids:
        raise LlmProviderAdapterError("LLM adapter provider is not granted to principal")
    if request.provider_id not in policy.providers:
        raise LlmProviderAdapterError(f"LLM provider is not registered: {request.provider_id}")


def llm_request_from_dict(row: Mapping[str, Any]) -> LlmGenerationRequest:
    return LlmGenerationRequest(
        provider_id=required_non_empty_str(row, "provider_id", "providerId"),
        prompt_request=prompt_gateway_request_from_dict(row),
        generation_question=optional_string_any(
            row,
            "generation_question",
            "generationQuestion",
        ),
    )


def normalize_principal(
    principal: LlmAdapterPrincipal | Mapping[str, Any] | None,
) -> LlmAdapterPrincipal | None:
    if principal is None or isinstance(principal, LlmAdapterPrincipal):
        return principal
    return LlmAdapterPrincipal.from_dict(principal)


def rate_limit_key(principal: LlmAdapterPrincipal, request: LlmGenerationRequest) -> str:
    prompt_request = request.prompt_request
    return "|".join(
        (
            principal.principal_id,
            prompt_request.tenant_id,
            prompt_request.product,
            prompt_request.use_case_id,
            request.provider_id,
        )
    )


def estimate_provider_cost_micros(
    gateway_result: PromptGatewayResult,
    cost_config: LlmProviderCostConfig,
) -> int:
    input_cost = (
        gateway_result.estimated_input_tokens
        * cost_config.input_micros_per_1k_tokens
    )
    output_cost = (
        gateway_result.estimated_output_tokens
        * cost_config.output_micros_per_1k_tokens
    )
    return math.ceil((input_cost + output_cost) / 1000)


def refused_provider_output(provider_id: str, model_id: str) -> LlmProviderOutput:
    return LlmProviderOutput(
        provider_id=provider_id,
        model_id=model_id,
        generated_text=(
            "I do not have enough trusted source evidence to answer. "
            "Please provide more context or route this to a human reviewer."
        ),
        citation_ids=(),
        refused=True,
        provider_called=True,
    )


def rank_contexts(question: str, contexts: list[PromptContext]) -> list[PromptContext]:
    query_tokens = tokenize(question)
    scored: list[tuple[float, str, PromptContext]] = []
    for context in contexts:
        score = lexical_score(query_tokens, tokenize(f"{context.source_ref} {context.text}"))
        if score > 0:
            scored.append((score, context.context_id, context))
    scored.sort(key=lambda row: (-row[0], row[1]))
    return [context for _, _, context in scored]


def mentions_other_tenant(text: str, tenant_id: str) -> bool:
    current = tenant_id.lower().replace("_", "-")
    for suffix in re.findall(r"\btenant[\s_-]+([a-z0-9]+)\b", text.lower()):
        mentioned = f"tenant-{suffix}"
        if mentioned != current:
            return True
    return False


def tokenize(text: str) -> set[str]:
    stopwords = {
        "a",
        "an",
        "and",
        "are",
        "before",
        "by",
        "for",
        "in",
        "is",
        "of",
        "or",
        "the",
        "to",
        "with",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if token not in stopwords and len(token) > 1
    }


def lexical_score(query_tokens: set[str], document_tokens: set[str]) -> float:
    if not query_tokens or not document_tokens:
        return 0.0
    overlap = query_tokens & document_tokens
    return len(overlap) / math.sqrt(len(query_tokens) * len(document_tokens))


def normalize_string_tuple(value: object | None) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if not isinstance(value, list | tuple):
        raise LlmProviderAdapterError("LLM adapter policy values must be strings or lists")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise LlmProviderAdapterError(
                "LLM adapter policy list values must be non-empty strings"
            )
        result.append(item.strip())
    return tuple(result)


def expand_scope_alias(scope: str, scope_aliases: Mapping[str, str], policy_path: Path) -> str:
    expanded = scope_aliases.get(scope, scope)
    if not expanded.startswith("internal:ai-platform:llm-adapter:"):
        raise RegistryValidationError(f"{policy_path} has unsupported LLM scope: {scope}")
    return expanded


def required_non_empty_str(row: Mapping[str, Any], snake_key: str, camel_key: str) -> str:
    value = row.get(snake_key, row.get(camel_key))
    if not isinstance(value, str) or not value.strip():
        raise LlmProviderAdapterError(
            f"LLM adapter request must define {snake_key} or {camel_key}"
        )
    return value.strip()


def optional_string_any(row: Mapping[str, Any], snake_key: str, camel_key: str) -> str:
    value = row.get(snake_key, row.get(camel_key, ""))
    if value is None:
        return ""
    if not isinstance(value, str):
        raise LlmProviderAdapterError(f"LLM adapter field {snake_key} must be a string")
    return value.strip()


def required_bool(row: Mapping[str, Any], key: str, owner: str) -> bool:
    value = row.get(key)
    if not isinstance(value, bool):
        raise RegistryValidationError(f"{owner} must define boolean field {key}")
    return value


def required_positive_int(row: Mapping[str, Any], key: str, owner: str) -> int:
    value = row.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise RegistryValidationError(f"{owner} must define positive integer field {key}")
    return value


def required_non_negative_int(row: Mapping[str, Any], key: str, owner: str) -> int:
    value = row.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise RegistryValidationError(
            f"{owner} must define non-negative integer field {key}"
        )
    return value


def require_mapping(row: Mapping[str, Any], key: str, owner: Path) -> dict[str, Any]:
    value = row.get(key)
    if not isinstance(value, dict):
        raise RegistryValidationError(f"{owner} must define mapping field {key}")
    return value


def require_mapping_list(row: Mapping[str, Any], key: str, owner: Path) -> list[dict[str, Any]]:
    value = row.get(key)
    if not isinstance(value, list):
        raise RegistryValidationError(f"{owner} must define list field {key}")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise RegistryValidationError(f"{owner} {key}[{index}] must be a mapping")
        result.append(item)
    return result
