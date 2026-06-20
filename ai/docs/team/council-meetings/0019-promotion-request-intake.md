# AI Platform Product Council 0019

Date: 2026-06-16

## Topic

Add promotion request intake for candidate AI artifacts before they become
formal promotions.

## Decision

Create `platform/artifacts/promotions/requests.yaml` and
`platform/src/courseflow_ai_platform/promotion_intake.py`.

Promotion readiness answers whether existing promoted artifacts are safe to
operate. Promotion intake answers what is waiting to enter the release process:
ready-for-approval requests and requests blocked by missing artifact, evaluation,
privacy review or simulator evidence.

## Delivered In This Cycle

| Artifact | Path |
|---|---|
| Request registry | `platform/artifacts/promotions/requests.yaml` |
| Intake projection | `platform/src/courseflow_ai_platform/promotion_intake.py` |
| Intake report | `platform/artifacts/promotions/reports/promotion-intake-v1.yaml` |
| Tests | `platform/tests/test_promotion_intake.py`, `platform/tests/test_cli.py` |
| CLI output | `promotionIntake` top-level key and optional report writer |
| Capability registry update | `platform/capabilities/registry.yaml` |

## Runtime Guarantees

| Guarantee | Behavior |
|---|---|
| Product scope | Every request must reference a known product and matching use case |
| Stage policy | Requested stages must be allowed by promotion policy |
| Ready queue | Ready-for-approval requests require known artifact, ready gates and ready source promotion when supplied |
| Waiting queues | Roadmap requests are grouped by artifact, evaluation, privacy and simulator blockers |
| Non-LMS coverage | Support, finance and operations requests use the same intake path as LMS |

## Product Impact

| User | Benefit |
|---|---|
| Admin/Ops | See what can be reviewed now and what is waiting on evidence |
| Product Owner | Track release intent for LMS and non-LMS AI use cases |
| AI Engineer | See missing artifact/evaluation work before promotion |
| Governance Reviewer | Separate privacy/simulator blockers from normal release approval |

## Next Actions

1. Add intake-to-promotion conversion for ready approved requests.
2. Add owner SLA and due date fields for waiting queues.
3. Add Admin/Ops UI that combines intake queue and readiness queue.
