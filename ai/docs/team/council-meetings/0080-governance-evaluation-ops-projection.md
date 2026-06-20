# Council 0080: Governance Evaluation Ops Projection

Date: 2026-06-17

## Participants

| Role | Decision focus |
| --- | --- |
| SA AI Platform | Promote governance evaluation from service boundary to observable platform control plane |
| SA AI Engineer | Build deterministic release-gate drills, privacy guardrail drills and snapshot tests |
| PO/BA | Ensure LMS and non-LMS product owners can read release decision health without service internals |
| Governance Reviewer | Validate blocked, review-required, approved and privacy-rejection counters |
| Admin/Ops | Surface release gate health in the cockpit and rendered dashboard |

## Decision

Add `governance_evaluation_ops` as a first-class AI Platform ops report and connect it to:

| Surface | Outcome |
| --- | --- |
| Governance report | `platform/governance/reports/governance-evaluation-service-v1.yaml` records release-gate drills and privacy guardrail counters |
| Operating cockpit | `platform/operations/reports/operating-cockpit-v1.yaml` embeds governance evaluation ops status and decision counts |
| Admin/Ops dashboard | `platform/operations/reports/admin-ops-dashboard-v1.html` shows Governance Eval status, assessment count, review-required count, blocked count and privacy rejects |
| CLI | `--write-governance-evaluation-ops-report` writes the standalone report for CI and release review |

## Enterprise Scope

| Product | Drill |
| --- | --- |
| LMS CourseFlow | approved recommendation active baseline release gate |
| Support Platform | review-required support agent assist release gate |
| Support Platform | blocked external auto-send release gate |

The same service boundary remains reusable for finance, operations, RAG, LLM and future enterprise AI releases because principals stay scoped by tenant, product and use case.

## Guardrails

- Direct identifiers are rejected during release evidence assessment.
- Secret values are rejected during release evidence assessment.
- External auto-send is blocked unless explicit policy allows it.
- Unexpected governance evaluation service errors block ops status.
- Drill mismatches block ops status before release health can be considered observable.

## Evidence

| Artifact | Path |
| --- | --- |
| Ops runtime | `platform/src/courseflow_ai_platform/governance_evaluation_ops.py` |
| Standalone report | `platform/governance/reports/governance-evaluation-service-v1.yaml` |
| Cockpit projection | `platform/operations/reports/operating-cockpit-v1.yaml` |
| Dashboard projection | `platform/operations/reports/admin-ops-dashboard-v1.html` |
| Platform tests | `platform/tests/test_governance_evaluation_ops.py` |
| CLI tests | `platform/tests/test_cli.py` |

## Outcome

Governance Evaluation Service is now visible as `release_gate_observable` in Admin/Ops.
The current drill set proves 3 assessments, 1 approved decision, 1 review-required decision,
1 blocked decision, 1 direct-identifier rejection, 1 secret-value rejection and 0 unexpected errors.
Council 0081 routes that observable status into the delivery backlog, SLA and owner views as an
Admin/Ops release-gate alert drill.
