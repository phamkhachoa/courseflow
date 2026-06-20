# Council 0055: Model Serving Service Package

Date: 2026-06-17

## Participants

- PO/BA Agent
- SA AI Platform Agent
- SA AI Engineer Agent
- Governance Reviewer
- Admin/Ops Reviewer

## Decision

The AI Platform now has an independently runnable model-serving service package. The service does not duplicate model logic; it packages the platform hosted adapter behind a policy-enforced CLI/HTTP boundary that can expose catalog, invocation, metrics, health and cockpit routes for LMS and non-LMS products.

The platform added:

- `services/model-serving-service/service.yaml`
- `services/model-serving-service/src/courseflow_model_serving_service/service.py`
- `services/model-serving-service/src/courseflow_model_serving_service/cli.py`
- `services/model-serving-service/src/courseflow_model_serving_service/http_server.py`
- `services/model-serving-service/tests/test_service_contract.py`
- service `Dockerfile`, `Makefile`, `pyproject.toml` and README

## Service Contract

| Route | Scope | Purpose |
|---|---|---|
| `GET /v1/models` | `internal:ai-platform:model-serving:catalog` | model catalog |
| `POST /v1/model-invocations` | `internal:ai-platform:model-serving:invoke` | model invocation |
| `GET /v1/model-serving/metrics` | `internal:ai-platform:model-serving:ops` | serving metrics |
| `GET /v1/model-serving/health` | `internal:ai-platform:model-serving:ops` | serving health |
| `GET /v1/model-serving/cockpit` | `internal:ai-platform:model-serving:ops` | operating cockpit projection |

## Guardrails

- Route scopes are resolved from AI governance policy.
- Service principals are resolved from `model-serving-access-policy.yaml`.
- Product principals cannot read ops metrics unless the access policy grants the ops scope.
- Invocation payloads still pass through tenant and model allowlist checks.
- Metrics export uses the service runtime counters and keeps the same per-model total validation.

## Validation Evidence

| Check | Result |
|---|---|
| Service contract tests | 5 passed |
| Service lint | passed |
| Platform registry validation | covered by platform test suite |

## Next Step

Completed in Council 0056: retrieval is now packaged as an independently runnable AI Platform service boundary.

Completed in Council 0058: prompt gateway is now packaged as its own policy-enforced AI Platform service.

Completed in Council 0059: Prompt Gateway is connected to LLM adapter shadow evaluation.

Completed in Council 0060: the provider-neutral LLM adapter is packaged as an independent service boundary.

Next harden model-serving, retrieval, prompt-gateway and LLM-adapter deployment gates, then connect live provider credentials and rate limits.
