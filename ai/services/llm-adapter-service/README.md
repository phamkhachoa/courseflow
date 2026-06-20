# LLM Adapter Service

Independent AI Platform service package for provider-neutral GenAI/LLM calls.

Product services call this adapter instead of calling a provider directly. The
adapter resolves a product/use-case/tenant scoped principal, evaluates the prompt
through Prompt Gateway, skips provider generation when blocked and records a
sanitized prompt audit event.

Provider operations are policy-defined in
`platform/governance/policies/llm-provider-ops-policy.yaml`: rate limits,
timeouts, circuit-breaker thresholds and failover providers are configured per
provider before live credentials are connected.
Credential readiness is reported in
`platform/governance/reports/llm-provider-readiness-v1.yaml`; plaintext provider
credentials are never accepted in source.
Runtime probes and cost/latency observability are reported in
`platform/operations/reports/llm-provider-runtime-probes-v1.yaml` before live
provider rollout.

## Routes

| Route | Scope | Purpose |
| --- | --- | --- |
| `POST /v1/llm-adapter/generate` | `internal:ai-platform:llm-adapter:generate` | prompt-gateway-bound generation |
| `GET /v1/llm-adapter/health` | `internal:ai-platform:llm-adapter:ops` | service health |
| `GET /v1/llm-adapter/metrics` | `internal:ai-platform:llm-adapter:ops` | request, blocked, provider-call and audit counters |

## Provider Ops

| Control | Evidence |
| --- | --- |
| Rate limit | principal, tenant, product, use-case and provider keyed in-memory limiter |
| Timeout | provider policy field `request_timeout_ms` |
| Circuit breaker | provider policy failure threshold and cooldown |
| Failover | provider policy `failover_provider_ids` |
| Cost rates | provider policy `cost` block, exported through adapter metrics |
| Credential readiness | `platform/governance/reports/llm-provider-readiness-v1.yaml` |
| Runtime probes | `platform/operations/reports/llm-provider-runtime-probes-v1.yaml` |

## Local Commands

```bash
PYTHONPATH=../../platform/src:src python3.11 -m pytest -q
PYTHONPATH=../../platform/src:src python3.11 -m ruff check
PYTHONPATH=../../platform/src:src python3.11 -m courseflow_llm_adapter_service.cli manifest
PYTHONPATH=../../platform/src:src python3.11 -m courseflow_llm_adapter_service.cli --ai-root ../.. --principal-id service:ai-platform-llm-ops health
```
