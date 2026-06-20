# Prompt Gateway Service

Independent AI Platform service package for GenAI, LLM and RAG prompt safety.

It exposes the shared runtime prompt gateway as a policy-enforced service
boundary. Product services call it before any external or hosted LLM adapter:

- redact PII, identifiers, bearer tokens and API keys
- filter retrieved context by tenant before prompt assembly
- enforce input, output and total token budgets
- block external auto-send by default
- require human review for high-impact prompt outputs
- emit in-memory request, block and error metrics

## Routes

| Method | Path | Scope |
| --- | --- | --- |
| `POST` | `/v1/prompt-gateway/evaluate` | `internal:ai-platform:prompt-gateway:evaluate` |
| `GET` | `/v1/prompt-gateway/health` | `internal:ai-platform:prompt-gateway:ops` |
| `GET` | `/v1/prompt-gateway/metrics` | `internal:ai-platform:prompt-gateway:ops` |

## Local Commands

```bash
PYTHONPATH=../../platform/src:src python3.11 -m pytest
PYTHONPATH=../../platform/src:src python3.11 -m courseflow_prompt_gateway_service.cli --ai-root ../.. manifest
PYTHONPATH=../../platform/src:src python3.11 -m courseflow_prompt_gateway_service.cli --ai-root ../.. --principal-id service:ai-platform-prompt-ops health
```
