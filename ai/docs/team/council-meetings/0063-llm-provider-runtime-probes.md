# Council 0063: LLM Provider Runtime Probes

Date: 2026-06-17

## Participants

- PO/BA Agent
- SA AI Platform Agent
- SA AI Engineer Agent
- Governance Reviewer
- Admin/Ops Reviewer

## Decision

Add runtime probe and cost/latency observability evidence for the LLM adapter
service. Live provider rollout now needs both credential readiness and runtime
probe evidence before network providers can be treated as rollout-ready.

## Delivered Evidence

| Evidence | Path |
| --- | --- |
| Runtime probe policy | `platform/governance/policies/llm-provider-runtime-probe-policy.yaml` |
| Runtime probe report | `platform/operations/reports/llm-provider-runtime-probes-v1.yaml` |
| Runtime probe builder | `platform/src/courseflow_ai_platform/llm_provider_runtime_probes.py` |
| Adapter cost/latency metrics | `platform/src/courseflow_ai_platform/llm_provider_adapter.py` |
| Platform tests | `platform/tests/test_llm_provider_runtime_probes.py` |
| Service contract | `services/llm-adapter-service/service.yaml` |

## Guardrails

- Runtime probe evidence must reference active adapter providers.
- Contract stubs remain observable but do not resolve live secrets.
- Live providers must pass runtime secret resolution, egress allowlist, Prompt
  Gateway, cost monitoring and latency monitoring checks.
- Live providers must define non-zero provider cost rates before rollout.
- Adapter metrics expose provider latency samples and estimated cost micros.

## Product Impact

| Product | Reuse |
| --- | --- |
| LMS CourseFlow | RAG Tutor and auto-grading can inherit live provider rollout checks |
| Support Platform | Agent assist gets provider latency/cost counters through the shared adapter |
| Billing/Finance | Finance assistants inherit secret probe and budget evidence before live calls |
| AI Platform | Admin/Ops has a generated runtime probe report for rollout review |

## Next Step

Completed in Council 0064: provider cost/latency status is projected into the
operating cockpit, delivery backlog, owner views and Admin/Ops dashboard.

Council 0066 added the secret rotation control plane. Next, run the first
network provider probe only after approved secret-manager refs, rotation evidence
and alert-route drill evidence are available outside source control.
