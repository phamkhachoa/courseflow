# Council 0062: LLM Provider Credential Readiness

Date: 2026-06-17

## Participants

- PO/BA Agent
- SA AI Platform Agent
- SA AI Engineer Agent
- Governance Reviewer
- Admin/Ops Reviewer

## Decision

Add a credential-readiness gate for the LLM adapter before live external
provider credentials are wired. The platform now reports whether each active
provider is still a contract stub, ready for live secret references, or blocked
by unsafe credential/deployment evidence.

## Delivered Evidence

| Evidence | Path |
| --- | --- |
| Credential readiness policy | `platform/governance/policies/llm-provider-credential-readiness.yaml` |
| Readiness report | `platform/governance/reports/llm-provider-readiness-v1.yaml` |
| Runtime/report builder | `platform/src/courseflow_ai_platform/llm_provider_readiness.py` |
| CLI write flag | `platform/src/courseflow_ai_platform/cli.py` |
| Platform tests | `platform/tests/test_llm_provider_readiness.py` |
| Service contract | `services/llm-adapter-service/service.yaml` |

## Guardrails

- Contract stubs must use `local_stub` credential mode and `local://` refs.
- Live network providers must use secret-reference URIs, not plaintext keys.
- Allowed live secret schemes are `vault://`, `aws-sm://`, `gcp-sm://` and
  `azure-kv://`.
- Live credentials require rotation evidence within the configured maximum age.
- Deployment checks must prove runtime secret resolution, egress allowlist,
  provider cost monitoring and mandatory Prompt Gateway routing.
- Credential refs in readiness evidence must match provider ops policy refs.

## Product Impact

| Product | Reuse |
| --- | --- |
| LMS CourseFlow | RAG Tutor and auto-grading can move from stub to live providers only after secret readiness passes |
| Support Platform | Agent assist inherits the same secret and deployment readiness gate |
| Billing/Finance | Reconciliation/document assistants avoid plaintext provider key leakage |
| AI Platform | Admin/Ops has a generated readiness report before approving live provider rollout |

## Next Step

Completed in Council 0063: runtime probe and cost/latency observability evidence
now exists for contract-stub providers.

Completed in Council 0065: generated provider budget/latency alert routes now
exist as a policy and report.

Council 0066 added the secret rotation control plane. Next, bind real live
secret refs only when a network provider is approved and keep the refs outside
source control.
